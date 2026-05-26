from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID

# حالات المحادثة للأدمن
(ADM_PROD_NAME, ADM_PROD_DESC, ADM_PROD_PRICE_USD, ADM_PROD_PRICE_SYP,
 ADM_PROD_CATEGORY, ADM_PROD_STOCK, ADM_BROADCAST_MSG, ADM_STOCK_UPDATE,
 ADM_CONFIRM_DELIVERY) = range(10, 19)

def is_admin(user_id):
    return user_id == ADMIN_ID

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "⚙️ *لوحة التحكم*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
    else:
        await update.message.reply_text(
            "⚙️ *لوحة التحكم*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    
    stats = db.get_stats()
    text = (
        f"📊 *إحصائيات المتجر*\n\n"
        f"👥 المستخدمين: {stats['users']}\n"
        f"📦 المنتجات النشطة: {stats['products']}\n"
        f"📋 إجمالي الطلبات: {stats['total_orders']}\n"
        f"⏳ طلبات معلقة: {stats['pending_orders']}\n"
        f"✅ طلبات مكتملة: {stats['completed_orders']}\n"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.admin_main_menu())

# ============ إضافة منتج ============
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "➕ *إضافة منتج جديد*\n\nأرسل اسم المنتج:",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADM_PROD_NAME

async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product'] = {'name': update.message.text}
    await update.message.reply_text("📝 أرسل وصف المنتج (أو أرسل - للتخطي):")
    return ADM_PROD_DESC

async def add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text
    context.user_data['new_product']['description'] = "" if desc == "-" else desc
    await update.message.reply_text("💵 أرسل السعر بالدولار (USD):")
    return ADM_PROD_PRICE_USD

async def add_product_price_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['new_product']['price_usd'] = price
        await update.message.reply_text("💴 أرسل السعر بالليرة السورية (SYP):")
        return ADM_PROD_PRICE_SYP
    except:
        await update.message.reply_text("❌ أرسل رقم صحيح:")
        return ADM_PROD_PRICE_USD

async def add_product_price_syp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['new_product']['price_syp'] = price
        await update.message.reply_text(
            "📂 أرسل الفئة:\n\n"
            "مثال: Apple iCloud | إيميلات | Survey | شروحات"
        )
        return ADM_PROD_CATEGORY
    except:
        await update.message.reply_text("❌ أرسل رقم صحيح:")
        return ADM_PROD_PRICE_SYP

async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product']['category'] = update.message.text
    await update.message.reply_text(
        "📦 أرسل المخزون (المحتوى الذي سيُرسل للعميل):\n\n"
        "مثال: account@example.com:password123\n"
        "أو رابط التحميل\n"
        "أو الكود\n\n"
        "يمكنك إرسال عدة عناصر مفصولة بسطر جديد:"
    )
    return ADM_PROD_STOCK

async def add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product']['stock'] = update.message.text
    p = context.user_data['new_product']
    
    product_id = db.add_product(
        name=p['name'],
        description=p['description'],
        price_usd=p['price_usd'],
        price_syp=p['price_syp'],
        category=p['category'],
        stock=p['stock']
    )
    
    await update.message.reply_text(
        f"✅ *تم إضافة المنتج بنجاح!*\n\n"
        f"🆔 ID: #{product_id}\n"
        f"📦 الاسم: {p['name']}\n"
        f"💵 السعر: ${p['price_usd']} / {p['price_syp']:,.0f} SYP",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    context.user_data.pop('new_product', None)
    return ConversationHandler.END

# ============ الطلبات المعلقة ============
async def show_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    
    orders = db.get_pending_orders()
    if not orders:
        await query.edit_message_text(
            "✅ لا يوجد طلبات معلقة.",
            reply_markup=kb.admin_main_menu()
        )
        return
    
    text = f"📋 *الطلبات المعلقة ({len(orders)}):*\n\n"
    for o in orders:
        text += (
            f"🔖 #{o['id']} — {o['product_name']}\n"
            f"👤 {o['full_name']} | 💳 {o['payment_method'].upper()}\n"
            f"💰 ${o['price_usd']}\n\n"
        )
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.admin_main_menu())

# ============ تأكيد الطلب ============
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    
    order_id = int(query.data.replace("adm_confirm_", ""))
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ الطلب غير موجود.")
        return
    
    product = db.get_product(order['product_id'])
    if not product or not product['stock']:
        await query.edit_message_text("❌ المنتج لا يحتوي على مخزون.")
        return
    
    # إرسال المنتج للعميل
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=(
                f"🎉 *تم تأكيد طلبك!*\n\n"
                f"📦 المنتج: *{order['product_name']}*\n\n"
                f"✅ *تفاصيل المنتج:*\n"
                f"`{product['stock']}`\n\n"
                f"شكراً لثقتك بنا! 🙏\nللاستفسار تواصل مع الأدمن."
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        
        db.update_order_status(order_id, 'completed', 'تم الإرسال')
        
        await query.edit_message_text(
            f"✅ *تم تأكيد الطلب #{order_id} وإرسال المنتج للعميل.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ خطأ في إرسال المنتج: {e}",
            reply_markup=kb.admin_main_menu()
        )

async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    
    order_id = int(query.data.replace("adm_reject_", ""))
    order = db.get_order(order_id)
    
    db.update_order_status(order_id, 'rejected', 'رُفض من الأدمن')
    
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=(
                f"❌ *تم رفض طلبك #{order_id}*\n\n"
                f"للاستفسار تواصل مع الأدمن."
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass
    
    await query.edit_message_text(
        f"❌ تم رفض الطلب #{order_id}.",
        reply_markup=kb.admin_main_menu()
    )

# ============ عرض المنتجات للأدمن ============
async def admin_show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    
    products = db.get_all_products(active_only=False)
    if not products:
        await query.edit_message_text("❌ لا يوجد منتجات.", reply_markup=kb.admin_main_menu())
        return
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = []
    for p in products:
        status = "✅" if p['active'] else "❌"
        keyboard.append([InlineKeyboardButton(
            f"{status} #{p['id']} {p['name']} — ${p['price_usd']}",
            callback_data=f"adm_prod_detail_{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_back")])
    
    await query.edit_message_text(
        "📦 *قائمة المنتجات:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("adm_prod_detail_", ""))
    product = db.get_product(product_id)
    
    if not product:
        await query.edit_message_text("❌ المنتج غير موجود.")
        return
    
    text = (
        f"📦 *{product['name']}*\n\n"
        f"🆔 ID: {product['id']}\n"
        f"📂 الفئة: {product['category']}\n"
        f"💵 USD: ${product['price_usd']}\n"
        f"💴 SYP: {product['price_syp']:,.0f}\n"
        f"📋 المخزون:\n`{product['stock'][:200] if product['stock'] else 'فارغ'}...`"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.admin_product_menu(product_id))

# ============ تحديث المخزون ============
async def update_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("adm_stock_", ""))
    context.user_data['stock_product_id'] = product_id
    await query.edit_message_text(
        "✏️ أرسل المخزون الجديد (سيستبدل القديم):"
    )
    return ADM_STOCK_UPDATE

async def update_stock_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get('stock_product_id')
    db.update_product_stock(product_id, update.message.text)
    await update.message.reply_text(
        "✅ تم تحديث المخزون.",
        reply_markup=kb.admin_main_menu()
    )
    return ConversationHandler.END

# ============ حذف منتج ============
async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("adm_del_", ""))
    db.delete_product(product_id)
    await query.edit_message_text(
        "🗑️ تم حذف المنتج.",
        reply_markup=kb.admin_main_menu()
    )

# ============ الرسائل الجماعية ============
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await query.edit_message_text("📢 أرسل الرسالة الجماعية (نص أو صورة مع تعليق):")
    return ADM_BROADCAST_MSG

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    
    users = db.get_all_users()
    sent = 0
    failed = 0
    
    await update.message.reply_text(f"📤 جاري الإرسال لـ {len(users)} مستخدم...")
    
    for user in users:
        try:
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=user['id'],
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption or ""
                )
            else:
                await context.bot.send_message(
                    chat_id=user['id'],
                    text=update.message.text
                )
            sent += 1
        except:
            failed += 1
    
    await update.message.reply_text(
        f"✅ تم الإرسال!\n\n📤 نجح: {sent}\n❌ فشل: {failed}",
        reply_markup=kb.admin_main_menu()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء.", reply_markup=kb.admin_main_menu())
    return ConversationHandler.END

