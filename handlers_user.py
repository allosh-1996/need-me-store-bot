from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import WELCOME_MSG, PAYMENT_MSG, USDT_WALLET, SYRIATEL_CASH, ADMIN_ID

# حالات المحادثة
WAITING_PROOF = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    # أرسل القائمة الثابتة أولاً (تظهر دايماً)
    await update.message.reply_text(
        "👋",
        reply_markup=kb.persistent_menu()
    )
    # ثم رسالة الترحيب مع الأزرار الداخلية
    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *الأوامر المتاحة:*\n\n"
        "/start — الصفحة الرئيسية\n"
        "/products — عرض المنتجات\n"
        "/orders — طلباتي\n"
        "/payment — طرق الدفع\n"
        "/help — المساعدة",
        parse_mode=ParseMode.MARKDOWN
    )

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    products = db.get_all_products()
    if not products:
        msg = "❌ لا يوجد منتجات متاحة حالياً."
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    # تجميع الفئات
    categories = list(set(p['category'] for p in products if p['category']))
    if not categories:
        categories = ['عام']

    text = "🛍️ *اختر الفئة:*"
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=kb.categories_menu(categories))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=kb.categories_menu(categories))

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("cat_", "")
    
    products = db.get_all_products()
    cat_products = [p for p in products if p['category'] == category]
    
    if not cat_products:
        await query.edit_message_text("❌ لا يوجد منتجات في هذه الفئة.")
        return

    text = f"📦 *{category}*\n\nاختر المنتج:"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.products_menu(cat_products))

async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("prod_", ""))
    
    product = db.get_product(product_id)
    if not product:
        await query.edit_message_text("❌ المنتج غير موجود.")
        return

    has_stock = bool(product['stock'])
    stock_icon = "✅ متوفر" if has_stock else "❌ غير متوفر"
    
    text = (
        f"🏷️ *{product['name']}*\n\n"
        f"📝 {product['description'] or 'لا يوجد وصف'}\n\n"
        f"💵 السعر: ${product['price_usd']} USD\n"
        f"💴 السعر: {product['price_syp']:,.0f} SYP\n\n"
        f"📦 الحالة: {stock_icon}"
    )
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.product_detail_menu(product_id, has_stock))

async def initiate_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    product_id = int(parts[1])  # buy_ID

    user = update.effective_user
    product = db.get_product(product_id)
    if not product or not product["stock"]:
        await query.edit_message_text("❌ المنتج غير متوفر حالياً.")
        return

    balance = db.get_balance(user.id)
    price = product["price_usd"]

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    if balance >= price:
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ شراء بـ ${price} من رصيدي", callback_data=f"confirm_buy_{product_id}")],
            [InlineKeyboardButton("💳 شحن رصيد", callback_data="charge_start")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"🛒 *تأكيد الشراء*\n\n"
            f"المنتج: *{product['name']}*\n"
            f"السعر: *${price}*\n"
            f"رصيدك: *${balance:.2f}*\n\n"
            f"بعد الشراء سيتبقى: *${balance - price:.2f}*"
        )
    else:
        needed = price - balance
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 شحن رصيد (تحتاج ${needed:.2f} إضافية)", callback_data="charge_start")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"🛒 *{product['name']}*\n\n"
            f"السعر: *${price}*\n"
            f"رصيدك: *${balance:.2f}*\n\n"
            f"❌ رصيدك غير كافٍ — تحتاج *${needed:.2f}* إضافية"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_kb)

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")  # pay_ID_currency_method
    product_id = int(parts[1])
    currency = parts[2].upper()
    method = parts[3]
    
    product = db.get_product(product_id)
    user = update.effective_user
    
    # إنشاء الطلب
    order_id = db.create_order(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        product_id=product_id,
        product_name=product['name'],
        price_usd=product['price_usd'],
        price_syp=product['price_syp'],
        currency=currency,
        payment_method=method
    )
    
    context.user_data['pending_order_id'] = order_id
    
    price = f"${product['price_usd']}" if currency == "USD" else f"{product['price_syp']:,.0f} SYP"
    
    if method == "usdt":
        payment_text = (
            f"💰 *الدفع عبر USDT (BEP-20)*\n\n"
            f"المبلغ: *{price}*\n\n"
            f"📋 عنوان المحفظة:\n`{USDT_WALLET}`\n\n"
            f"⚠️ *تأكد من إرسال على شبكة BEP-20 فقط*\n\n"
            f"بعد الدفع، أرسل صورة الإيصال أو hash العملية 👇"
        )
    else:
        payment_text = (
            f"📱 *الدفع عبر Syriatel Cash*\n\n"
            f"المبلغ: *{price}*\n\n"
            f"📞 رقم الاستلام:\n`{SYRIATEL_CASH}`\n\n"
            f"بعد الدفع، أرسل صورة الإيصال 👇"
        )
    
    await query.edit_message_text(
        payment_text + f"\n\n🔖 رقم طلبك: `#{order_id}`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return WAITING_PROOF

async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get('pending_order_id')
    if not order_id:
        await update.message.reply_text("❌ لم يتم العثور على طلب نشط. ابدأ من /start")
        return ConversationHandler.END
    
    user = update.effective_user
    order = db.get_order(order_id)
    
    # حفظ الإيصال
    if update.message.photo:
        proof = update.message.photo[-1].file_id
        proof_type = "photo"
    elif update.message.document:
        proof = update.message.document.file_id
        proof_type = "document"
    else:
        proof = update.message.text
        proof_type = "text"
    
    db.update_order_proof(order_id, proof)
    
    # إشعار الأدمن
    admin_text = (
        f"🔔 *طلب جديد #{order_id}*\n\n"
        f"👤 العميل: {user.full_name} (@{user.username or 'لا يوجد'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📦 المنتج: {order['product_name']}\n"
        f"💰 السعر: ${order['price_usd']} / {order['price_syp']:,.0f} SYP\n"
        f"💳 طريقة الدفع: {order['payment_method'].upper()}\n"
        f"📅 الوقت: {order['created_at']}"
    )
    
    try:
        if proof_type == "photo":
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=proof,
                caption=admin_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.order_confirm_menu(order_id)
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text + f"\n\n📎 الإيصال: {proof}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.order_confirm_menu(order_id)
            )
    except Exception as e:
        print(f"خطأ في إرسال إشعار الأدمن: {e}")
    
    await update.message.reply_text(
        f"✅ *تم استلام طلبك بنجاح!*\n\n"
        f"🔖 رقم الطلب: `#{order_id}`\n\n"
        f"سيتم مراجعة الدفع وإرسال المنتج خلال وقت قصير 🚀\n"
        f"شكراً لثقتك بنا 🙏",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu()
    )
    
    context.user_data.pop('pending_order_id', None)
    return ConversationHandler.END

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    orders = db.get_user_orders(user.id)
    
    if not orders:
        text = "📋 ليس لديك طلبات سابقة."
    else:
        status_emoji = {'pending': '⏳', 'completed': '✅', 'rejected': '❌'}
        text = "📋 *طلباتك الأخيرة:*\n\n"
        for o in orders:
            emoji = status_emoji.get(o['status'], '❓')
            text += f"{emoji} #{o['id']} — {o['product_name']} — {o['status']}\n"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]])
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)

async def payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = PAYMENT_MSG.format(usdt_wallet=USDT_WALLET, syriatel_cash=SYRIATEL_CASH)
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.main_menu())

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📞 *تواصل معنا:*\n\nللاستفسار أو الدعم تواصل مع الأدمن مباشرة.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu()
    )

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        WELCOME_MSG,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu()
    )


# ============ معالجات القائمة الثابتة ============
async def handle_persistent_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🚀 ابدأ":
        await start(update, context)
    
    elif text == "💬 Support":
        from config import ADMIN_ID
        await update.message.reply_text(
            "💬 *الدعم والمساعدة*\n\n"
            "للتواصل المباشر مع الأدمن:\n"
            "👉 @Allosh96ha\n\n"
            "أو راسلنا وسنرد في أقرب وقت 🙏",
            parse_mode="Markdown",
            reply_markup=kb.persistent_menu()
        )
    
    elif text == "ℹ️ About":
        await update.message.reply_text(
            "ℹ️ *Need Me Store*\n\n"
            "🛍️ متجرك الرقمي الموثوق\n\n"
            "نوفر:\n"
            "• 🍎 حسابات Apple iCloud\n"
            "• 📧 إيميلات جاهزة\n"
            "• 📋 حسابات استبيانات Survey\n"
            "• 📚 شروحات وطرق حصرية\n\n"
            "💳 طرق الدفع: USDT BEP-20 | Syriatel Cash\n\n"
            "⚡️ توصيل فوري بعد تأكيد الدفع",
            parse_mode="Markdown",
            reply_markup=kb.persistent_menu()
        )


async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("confirm_buy_", ""))

    user = update.effective_user
    product = db.get_product(product_id)

    if not product or not product['stock']:
        await query.edit_message_text("❌ المنتج نفد من المخزون.")
        return

    balance = db.get_balance(user.id)
    price = product['price_usd']

    if balance < price:
        await query.edit_message_text(
            f"❌ رصيدك غير كافٍ.\n\nرصيدك: ${balance:.2f} | السعر: ${price}",
            reply_markup=kb.main_menu()
        )
        return

    # خصم الرصيد
    db.deduct_balance(user.id, price)

    # إنشاء الطلب
    order_id = db.create_order(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        product_id=product_id,
        product_name=product['name'],
        price_usd=price,
        price_syp=product['price_syp'],
        currency="USD",
        payment_method="balance"
    )
    db.update_order_status(order_id, 'completed', 'دفع من الرصيد')

    new_balance = db.get_balance(user.id)

    # إرسال المنتج مباشرة
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    done_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]])
    await query.edit_message_text(
        f"🎉 *تم الشراء بنجاح!*\n\n"
        f"📦 المنتج: *{product['name']}*\n"
        f"💵 المدفوع: *${price}*\n"
        f"💰 رصيدك المتبقي: *${new_balance:.2f}*\n\n"
        f"✅ *تفاصيل المنتج:*\n"
        f"`{product['stock']}`\n\n"
        f"شكراً لثقتك بنا! 🙏",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )

    # إشعار الأدمن
    try:
        from config import ADMIN_ID
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🛍️ *بيع جديد #{order_id}*\n\n"
                f"👤 {user.full_name} (@{user.username or '-'})\n"
                f"📦 {product['name']}\n"
                f"💵 ${price} (من الرصيد)"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass
