from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import WELCOME_MSG, PAYMENT_MSG, USDT_WALLET, SYRIATEL_CASH, ADMIN_ID

WAITING_PROOF = 1

# ═══════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Commands  |  الأوامر*\n\n"
        "`/start` — الرئيسية  |  Home\n"
        "`/products` — المنتجات  |  Products\n"
        "`/orders` — طلباتي  |  My Orders\n"
        "`/charge` — شحن رصيد  |  Top Up\n"
        "`/help` — مساعدة  |  Help",
        parse_mode=ParseMode.MARKDOWN
    )

# ═══════════════════════════════════════
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    platform_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🍎 iOS", callback_data="platform_iOS"),
         InlineKeyboardButton("🤖 Android", callback_data="platform_Android")],
        [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="back_main")],
    ])

    text = "🛍️ *NexVault Shop*\n\n_اختر المنظومة  |  Choose platform:_"
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=platform_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=platform_kb)

async def show_platform_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    platform = query.data.replace("platform_", "")
    context.user_data['selected_platform'] = platform

    products = db.get_all_products()
    platform_products = [p for p in products if platform in (p.get('platform') or 'iOS')]

    if not platform_products:
        await query.edit_message_text(
            f"🔴 *لا يوجد منتجات {platform} متاحة حالياً*\n_No {platform} products available_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="products")]])
        )
        return

    categories = list(set(p['category'] for p in platform_products if p['category']))
    icon = "🍎" if platform == "iOS" else "🤖"

    text = f"{icon} *{platform} Products*\n\n_اختر الفئة  |  Choose a category:_"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.categories_menu(categories, back_cb="products"))

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("cat_", "")

    platform = context.user_data.get('selected_platform', '')
    products = db.get_all_products()
    if platform:
        cat_products = [p for p in products if p['category'] == category and platform in (p.get('platform') or 'iOS')]
    else:
        cat_products = [p for p in products if p['category'] == category]

    if not cat_products:
        await query.edit_message_text(
            "🔴 لا يوجد منتجات في هذه الفئة\n_No products in this category_",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    text = f"📦 *{category}*\n\n_اختر المنتج  |  Select a product:_"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.products_menu(cat_products))

async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("prod_", ""))

    product = db.get_product(product_id)
    if not product:
        await query.edit_message_text("🔴 المنتج غير موجود  |  Product not found")
        return

    has_stock = bool(product['stock'])
    stock_status = "✅ متوفر  |  In Stock" if has_stock else "🔴 غير متوفر  |  Out of Stock"

    platform = product.get('platform', '') or ''
    platform_icon = '🍎' if 'iOS' in platform and 'Android' not in platform else ('🤖' if platform == 'Android' else '📱')
    platform_line = f"\n{platform_icon} *Platform:* `{platform}`" if platform else ""

    text = (
        f"🏷️ *{product['name']}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 {product['description'] or '_لا يوجد وصف  |  No description_'}"
        + platform_line +
        f"\n\n💵 *USD:* `${product['price_usd']}`\n"
        f"💴 *SYP:* `{product['price_syp']:,.0f} ل.س`\n\n"
        f"📦 *Status:* {stock_status}\n"
        f"━━━━━━━━━━━━━━━━"
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.product_detail_menu(product_id, has_stock))

async def initiate_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX: كان الـ pattern يتوقع buy_{id}_{currency} لكن الزر كان يرسل buy_{id} فقط.
    الحين keyboards.py يرسل buy_{id}_USD أو buy_{id}_SYP بشكل صحيح.
    """
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    product_id = int(parts[1])
    currency = parts[2].upper() if len(parts) > 2 else "USD"

    context.user_data['buy_currency'] = currency

    user = update.effective_user
    product = db.get_product(product_id)
    if not product or not product["stock"]:
        await query.edit_message_text(
            "🔴 المنتج غير متوفر حالياً\n_Product is currently unavailable_",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    balance = db.get_balance(user.id)
    price = product["price_usd"]
    price_syp = product["price_syp"]
    display_price = f"${price}" if currency == "USD" else f"{price_syp:,.0f} ل.س"

    if balance >= price:
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💰 شراء من الرصيد — ${price}", callback_data=f"confirm_buy_{product_id}")],
            [InlineKeyboardButton("🪙 USDT BEP-20", callback_data=f"pay_{product_id}_{currency}_usdt")],
            [InlineKeyboardButton("📱 Syriatel Cash", callback_data=f"pay_{product_id}_{currency}_syriatel")],
            [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"🛒 *اختر طريقة الدفع  |  Choose Payment*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📦 {product['name']}\n"
            f"💵 Price: `{display_price}`\n"
            f"💰 Balance: `${balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━"
        )
    else:
        needed = price - balance
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🪙 USDT BEP-20", callback_data=f"pay_{product_id}_{currency}_usdt")],
            [InlineKeyboardButton("📱 Syriatel Cash", callback_data=f"pay_{product_id}_{currency}_syriatel")],
            [InlineKeyboardButton(f"⚡ Top Up — Need ${needed:.2f} more", callback_data="charge_start")],
            [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"🛒 *{product['name']}*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 Price: `{display_price}`\n"
            f"💰 Your Balance: `${balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"_اختر طريقة الدفع  |  Choose payment method:_"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_kb)

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    product_id = int(parts[1])
    currency = parts[2].upper()
    method = parts[3]

    product = db.get_product(product_id)
    user = update.effective_user

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
    price = f"${product['price_usd']}" if currency == "USD" else f"{product['price_syp']:,.0f} ل.س"

    if method == "usdt":
        payment_text = (
            f"🪙 *USDT Payment  |  الدفع عبر USDT*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 Amount  |  المبلغ: `{price}`\n\n"
            f"📋 Wallet Address  |  عنوان المحفظة:\n"
            f"`{USDT_WALLET}`\n\n"
            f"⚠️ *BEP-20 Network Only*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📸 أرسل صورة الإيصال أو TXID 👇\n"
            f"_Send receipt screenshot or TXID_"
        )
    else:
        payment_text = (
            f"📱 *Syriatel Cash Payment*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 Amount  |  المبلغ: `{price}`\n\n"
            f"📞 Number  |  الرقم:\n"
            f"`{SYRIATEL_CASH}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📸 أرسل صورة الإيصال 👇\n"
            f"_Send receipt screenshot_"
        )

    await query.edit_message_text(
        payment_text + f"\n\n🔖 Order ID: `#{order_id}`",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_PROOF

async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get('pending_order_id')
    if not order_id:
        await update.message.reply_text(
            "🔴 لم يتم العثور على طلب نشط\n_No active order found. Start from /start_",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    user = update.effective_user
    order = db.get_order(order_id)

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

    admin_text = (
        f"🔔 *New Order  |  طلب جديد* `#{order_id}`\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 {user.full_name} (@{user.username or '—'})\n"
        f"🆔 `{user.id}`\n"
        f"📦 {order['product_name']}\n"
        f"💵 ${order['price_usd']}  |  {order['price_syp']:,.0f} ل.س\n"
        f"💳 {order['payment_method'].upper()}\n"
        f"━━━━━━━━━━━━━━━━"
    )

    try:
        if proof_type == "photo":
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.order_confirm_menu(order_id)
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text + f"\n\n📎 Receipt: `{proof}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.order_confirm_menu(order_id)
            )
    except Exception as e:
        print(f"Admin notify error: {e}")

    await update.message.reply_text(
        f"✅ *Order Received!  |  تم استلام طلبك!*\n\n"
        f"🔖 Order ID: `#{order_id}`\n\n"
        f"⏳ سيتم مراجعة الدفع وإرسال المنتج قريباً\n"
        f"_Your payment is under review. Product will be delivered soon_ 🚀\n\n"
        f"شكراً لثقتك 🙏  |  _Thank you!_",
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

    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="back_main")]])

    if not orders:
        text = "📋 *My Orders  |  طلباتي*\n\n_لا يوجد طلبات سابقة  |  No orders yet_"
        if query:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)
        return

    status_map = {"pending": "⏳ Pending", "completed": "✅ Done", "rejected": "🔴 Rejected"}
    lines = ["📋 *My Orders  |  طلباتي:*\n", "━━━━━━━━━━━━━━━━"]
    for o in orders:
        status = status_map.get(o["status"], "❓")
        lines.append(f"{status}  `#{o['id']}` — {o['product_name']}")
    lines.append("━━━━━━━━━━━━━━━━")
    text = "\n".join(lines)

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)

async def payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = PAYMENT_MSG.format(usdt_wallet=USDT_WALLET, syriatel_cash=SYRIATEL_CASH)
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu())

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📞 *Contact  |  تواصل معنا*\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "👤 Admin: @Allosh96ha\n\n"
        "_راسلنا وسنرد في أقرب وقت 🙏_\n"
        "_Message us and we'll reply ASAP_\n"
        "━━━━━━━━━━━━━━━━",
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

async def handle_persistent_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""

    if any(x in text for x in ["Start", "ابدأ", "🚀"]):
        user = update.effective_user
        db.upsert_user(user.id, user.username or "", user.full_name or "")
        await update.message.reply_text(WELCOME_MSG, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu())

    elif "Support" in text:
        await update.message.reply_text(
            "💬 *Support  |  الدعم*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "👤 @Allosh96ha\n\n"
            "_راسلنا وسنرد في أقرب وقت 🙏_\n"
            "_We reply as fast as possible_\n"
            "━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.persistent_menu()
        )

    elif "About" in text:
        await update.message.reply_text(
            "🌙 *NexVault*\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🛍️ متجرك الرقمي الموثوق\n"
            "_Your trusted digital store_\n\n"
            "🍎 Apple iCloud Accounts\n"
            "📧 Ready-made Emails\n"
            "📋 Survey Accounts\n"
            "📚 Exclusive Methods & Guides\n\n"
            "💳 USDT BEP-20  |  Syriatel Cash\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚡ _Instant delivery after payment_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.persistent_menu()
        )

async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("confirm_buy_", ""))

    user = update.effective_user
    product = db.get_product(product_id)

    if not product or not product['stock']:
        await query.edit_message_text(
            "🔴 المنتج نفد من المخزون\n_Product is out of stock_",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    balance = db.get_balance(user.id)
    price = product['price_usd']

    if balance < price:
        await query.edit_message_text(
            f"🔴 *Insufficient Balance*\n\n"
            f"💰 Balance: `${balance:.2f}`\n"
            f"💵 Price: `${price}`\n\n"
            f"_اشحن رصيدك أولاً  |  Top up your balance first_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Top Up  |  شحن", callback_data="charge_start")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"prod_{product_id}")]
            ])
        )
        return

    db.deduct_balance(user.id, price)
    order_id = db.create_order(
        user_id=user.id, username=user.username or "",
        full_name=user.full_name or "", product_id=product_id,
        product_name=product['name'], price_usd=price,
        price_syp=product['price_syp'], currency="USD",
        payment_method="balance"
    )
    db.update_order_status(order_id, 'completed', 'دفع من الرصيد')
    new_balance = db.get_balance(user.id)

    done_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home  |  الرئيسية", callback_data="back_main")]])
    await query.edit_message_text(
        f"🎉 *Purchase Successful!  |  تم الشراء!*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📦 {product['name']}\n"
        f"💵 Paid: `${price}`\n"
        f"💰 Remaining Balance: `${new_balance:.2f}`\n\n"
        f"✅ *Product Details:*\n"
        f"`{product['stock']}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"شكراً لثقتك 🙏  |  _Thank you!_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🛍️ *New Sale  |  بيع جديد* `#{order_id}`\n\n"
                f"👤 {user.full_name} (@{user.username or '—'})\n"
                f"📦 {product['name']}\n"
                f"💵 ${price} (Balance)"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

# ═══════════════════════════════════════
# إيميلات
# ═══════════════════════════════════════
async def emails_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    kb_emails = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔵 Outlook", callback_data="cat_Outlook")],
        [InlineKeyboardButton("🔴 Gmail", callback_data="cat_Gmail")],
        [InlineKeyboardButton("🟠 Hotmail", callback_data="cat_Hotmail")],
        [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="back_main")],
    ])

    await query.edit_message_text(
        "📧 *إيميلات  |  Emails*\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "_اختر النوع  |  Choose type:_",
        parse_mode="Markdown",
        reply_markup=kb_emails
    )
