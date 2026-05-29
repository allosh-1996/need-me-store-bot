from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID

(ADM_PROD_NAME, ADM_PROD_DESC, ADM_PROD_PRICE_USD, ADM_PROD_PRICE_SYP,
 ADM_PROD_CATEGORY, ADM_PROD_PLATFORM, ADM_PROD_STOCK, ADM_BROADCAST_MSG, ADM_STOCK_UPDATE,
 ADM_CONFIRM_DELIVERY) = range(10, 20)

def is_admin(user_id):
    return user_id == ADMIN_ID

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return

    text = (
        " *Admin Panel  |  لوحة التحكم*\n\n"
        "\n"
        " NexVault — Admin\n"
        ""
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                                       reply_markup=kb.admin_main_menu())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=kb.admin_main_menu())

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    stats = db.get_stats()
    text = (
        f" *Store Stats  |  إحصائيات المتجر*\n\n"
        f"\n"
        f" Users  |  المستخدمين: `{stats['users']}`\n"
        f" Products  |  المنتجات: `{stats['products']}`\n"
        f"\n"
        f" Total Orders: `{stats['total_orders']}`\n"
        f"⏳ Pending  |  معلقة: `{stats['pending_orders']}`\n"
        f" Completed  |  مكتملة: `{stats['completed_orders']}`\n"
        f""
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.admin_main_menu())

# ═══ Add Product ═══
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await query.edit_message_text(
        " *Add Product  |  إضافة منتج*\n\n"
        "\n"
        " أرسل اسم المنتج:\n_Send product name:_",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADM_PROD_NAME

async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product'] = {'name': update.message.text}
    await update.message.reply_text(" أرسل الوصف (أو `-` للتخطي):\n_Description (or `-` to skip):_",
                                     parse_mode=ParseMode.MARKDOWN)
    return ADM_PROD_DESC

async def add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text
    context.user_data['new_product']['description'] = "" if desc == "-" else desc
    await update.message.reply_text(" السعر بالدولار  |  Price in USD:")
    return ADM_PROD_PRICE_USD

async def add_product_price_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['new_product']['price_usd'] = price
        await update.message.reply_text(" السعر بالليرة السورية  |  Price in SYP:")
        return ADM_PROD_PRICE_SYP
    except:
        await update.message.reply_text(" أرسل رقم صحيح  |  Send a valid number:")
        return ADM_PROD_PRICE_USD

async def add_product_price_syp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['new_product']['price_syp'] = price
        await update.message.reply_text(
            " الفئة  |  Category:\n\n"
            "_مثال  |  Example:_\n"
            "`Apple iCloud` | `إيميلات` | `Survey` | `شروحات`",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADM_PROD_CATEGORY
    except:
        await update.message.reply_text(" أرسل رقم صحيح  |  Send a valid number:")
        return ADM_PROD_PRICE_SYP

async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product']['category'] = update.message.text

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    platform_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(" iOS", callback_data="adm_platform_iOS"),
         InlineKeyboardButton(" Android", callback_data="adm_platform_Android")],
        [InlineKeyboardButton(" iOS & Android", callback_data="adm_platform_iOS & Android")],
    ])
    await update.message.reply_text(
        " *المنظومة  |  Platform*\n\n"
        "_اختر منظومة المنتج:_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=platform_kb
    )
    return ADM_PROD_PLATFORM

async def add_product_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    platform = query.data.replace("adm_platform_", "")
    context.user_data['new_product']['platform'] = platform

    await query.edit_message_text(
        f" المنظومة  |  Platform: *{platform}*\n\n"
        f" *المخزون  |  Stock*\n\n"
        f"_المحتوى الذي سيُرسل للعميل_\n"
        f"_Content to be sent to the customer_\n\n"
        f"مثال:\n`account@email.com:password`\n`or download link`",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADM_PROD_STOCK

async def add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product']['stock'] = update.message.text
    p = context.user_data['new_product']

    product_id = db.add_product(
        name=p['name'], description=p['description'],
        price_usd=p['price_usd'], price_syp=p['price_syp'],
        category=p['category'], stock=p['stock'],
        platform=p.get('platform', 'iOS')
    )

    await update.message.reply_text(
        f" *Product Added!  |  تم إضافة المنتج!*\n\n"
        f"\n"
        f" ID: `#{product_id}`\n"
        f" {p['name']}\n"
        f" ${p['price_usd']}  |  {p['price_syp']:,.0f} ل.س\n"
        f"",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    context.user_data.pop('new_product', None)
    return ConversationHandler.END

# ═══ Pending Orders ═══
async def show_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    orders = db.get_pending_orders()
    if not orders:
        await query.edit_message_text(
            " *No Pending Orders  |  لا يوجد طلبات معلقة*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
        return

    text = f" *Pending Orders  |  الطلبات المعلقة* ({len(orders)})\n\n\n"
    for o in orders:
        text += (
            f" `#{o['id']}` — {o['product_name']}\n"
            f" {o['full_name']}  |   {o['payment_method'].upper()}\n"
            f" ${o['price_usd']}\n\n"
        )
    text += ""

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.admin_main_menu())

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX: يستخدم pop_stock_item() لسحب وحدة واحدة فريدة من المخزون.
    كل مستخدم يحصل على وحدة مختلفة — لا تكرار.
    """
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    order_id = int(query.data.replace("adm_confirm_", ""))
    order = db.get_order(order_id)

    if not order:
        await query.edit_message_text(" الطلب غير موجود  |  Order not found")
        return

    product = db.get_product(order['product_id'])
    if not product:
        await query.edit_message_text(" المنتج غير موجود  |  Product not found")
        return

    # FIX: سحب وحدة فريدة من المخزون
    item, remaining = db.pop_stock_item(order['product_id'])
    if not item:
        await query.edit_message_text(
            " المنتج لا يحتوي على مخزون  |  Product has no stock\n"
            "_أضف مخزون جديد من لوحة التحكم_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
        return

    # احفظ الوحدة المُرسلة في الطلب
    db.update_order_delivered_item(order_id, item)

    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=(
                f" *Order Confirmed!  |  تم تأكيد طلبك!*\n\n"
                f"\n"
                f" {order['product_name']}\n\n"
                f" *Product Details:*\n"
                f"`{item}`\n"
                f"\n"
                f"شكراً لثقتك   |  _Thank you!_\n"
                f"_For support contact admin_"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        db.update_order_status(order_id, 'completed', 'تم الإرسال')
        confirm_text = f" *Order `#{order_id}` Confirmed!*\n_Sent to {order['full_name']}_ | Stock remaining: {remaining}"
        try:
            await query.edit_message_caption(confirm_text)
        except:
            await query.edit_message_text(
                confirm_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.admin_main_menu()
            )
    except Exception as e:
        await query.edit_message_text(f" Error: {e}", reply_markup=kb.admin_main_menu())

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
                f" *تم رفض طلبك  |  Order Rejected*\n\n"
                f"\n"
                f" Order ID: `#{order_id}`\n"
                f" {order['product_name']}\n"
                f" ${order['price_usd']}\n"
                f"\n"
                f"_للاستفسار تواصل مع الأدمن_\n"
                f"_Contact admin for more info_"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu("ar")
        )
    except:
        pass

    try:
        await query.edit_message_caption(f" Order #{order_id} rejected")
    except:
        await query.edit_message_text(f" Order `#{order_id}` rejected",
                                       parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=kb.admin_main_menu())

# ═══ Products Management ═══
async def admin_show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    products = db.get_all_products(active_only=False)
    if not products:
        await query.edit_message_text(" لا يوجد منتجات  |  No products",
                                       reply_markup=kb.admin_main_menu())
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = []
    for p in products:
        status = "" if p['active'] else ""
        keyboard.append([InlineKeyboardButton(
            f"{status}  #{p['id']}  {p['name']}  —  ${p['price_usd']}",
            callback_data=f"adm_prod_detail_{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton(" Back  |  رجوع", callback_data="adm_back")])

    await query.edit_message_text(
        " *Products  |  المنتجات:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("adm_prod_detail_", ""))
    product = db.get_product(product_id)

    if not product:
        await query.edit_message_text(" المنتج غير موجود  |  Product not found")
        return

    text = (
        f" *{product['name']}*\n\n"
        f"\n"
        f" ID: `{product['id']}`\n"
        f" Category: {product['category']}\n"
        f" USD: `${product['price_usd']}`\n"
        f" SYP: `{product['price_syp']:,.0f}`\n\n"
        f" Stock Preview:\n"
        f"`{product['stock'][:200] if product['stock'] else 'Empty'}...`\n"
        f""
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.admin_product_menu(product_id))

async def update_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("adm_stock_", ""))
    context.user_data['stock_product_id'] = product_id
    await query.edit_message_text(
        " *Update Stock  |  تحديث المخزون*\n\n"
        "_أرسل المخزون الجديد (سيستبدل القديم)_\n"
        "_Send new stock (replaces old):_",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADM_STOCK_UPDATE

async def update_stock_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get('stock_product_id')
    db.update_product_stock(product_id, update.message.text)
    await update.message.reply_text(
        " *Stock Updated!  |  تم تحديث المخزون!*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    return ConversationHandler.END

async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("adm_del_", ""))
    db.delete_product(product_id)
    await query.edit_message_text(
        " *Product Deleted  |  تم حذف المنتج*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )

# ═══ Broadcast ═══
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await query.edit_message_text(
        " *Broadcast  |  رسالة جماعية*\n\n"
        "_أرسل الرسالة (نص أو صورة مع تعليق)_\n"
        "_Send message (text or photo with caption):_",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADM_BROADCAST_MSG

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    users = db.get_all_users()
    sent = 0
    failed = 0

    await update.message.reply_text(f" Sending to {len(users)} users...")

    for user in users:
        try:
            if update.message.photo:
                await context.bot.send_photo(chat_id=user['id'],
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption or "")
            else:
                await context.bot.send_message(chat_id=user['id'], text=update.message.text)
            sent += 1
        except:
            failed += 1

    await update.message.reply_text(
        f" *Broadcast Done!*\n\n"
        f" Sent: `{sent}`\n"
        f" Failed: `{failed}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(" Cancelled  |  تم الإلغاء", reply_markup=kb.admin_main_menu())
    return ConversationHandler.END
