import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID

logger = logging.getLogger(__name__)

(ADM_PROD_NAME, ADM_PROD_DESC, ADM_PROD_PRICE_USD, ADM_PROD_PRICE_SYP,
 ADM_PROD_CATEGORY, ADM_PROD_STOCK, ADM_BROADCAST_MSG, ADM_STOCK_UPDATE) = range(10, 18)

# عدد الطلبات لكل صفحة في لوحة الأدمن
ORDERS_PAGE_SIZE = 8


def is_admin(user_id):
    result = user_id == ADMIN_ID
    if result:
        logger.info(f"Admin access granted: user_id={user_id}")
    else:
        logger.warning(f"Unauthorized admin access attempt: user_id={user_id}")
    return result


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return

    text = (
        " *Admin Panel  |  لوحة التحكم*\n\n"
        " NexVault — Admin\n"
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
        f"📊 *إحصائيات المتجر*\n"
        f"\n—————————————————\n\n"
        f"👥 المستخدمين: *{stats['users']}*\n"
        f"🛍️ المنتجات: *{stats['products']}*\n\n"
        f"📦 إجمالي الطلبات: *{stats['total_orders']}*\n"
        f"⏳ معلقة: *{stats['pending_orders']}*\n"
        f"✅ مكتملة: *{stats['completed_orders']}*\n"
        f"\n—————————————————\n"
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
    except Exception:
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
    except Exception:
        await update.message.reply_text(" أرسل رقم صحيح  |  Send a valid number:")
        return ADM_PROD_PRICE_SYP


async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_product']['category'] = update.message.text
    context.user_data['new_product']['platform'] = 'general'
    await update.message.reply_text(
        " *المخزون  |  Stock*\n\n"
        "_المحتوى الذي سيُرسل للعميل_\n"
        "_Content to be sent to the customer_\n\n"
        "مثال:\n`account@email.com:password`\n`or download link`",
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
    logger.info(f"Admin added product #{product_id}: {p['name']}")

    await update.message.reply_text(
        f" *Product Added!  |  تم إضافة المنتج!*\n\n"
        f" ID: `#{product_id}`\n"
        f" {p['name']}\n"
        f" ${p['price_usd']}  |  {p['price_syp']:,.0f} ل.س\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    context.user_data.pop('new_product', None)
    return ConversationHandler.END


# ═══ Pending Orders — مع Pagination ═══

async def show_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    # استخرج رقم الصفحة من callback_data لو موجود
    data = query.data  # مثال: adm_orders أو adm_orders_p2
    page = 0
    if "_p" in data:
        try:
            page = int(data.split("_p")[-1]) - 1  # تحويل من 1-based إلى 0-based
        except ValueError:
            page = 0

    offset = page * ORDERS_PAGE_SIZE
    orders = db.get_pending_orders()  # كل الطلبات المعلقة

    if not orders:
        await query.edit_message_text(
            " *No Pending Orders  |  لا يوجد طلبات معلقة*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
        return

    total = len(orders)
    page_orders = orders[offset: offset + ORDERS_PAGE_SIZE]
    total_pages = (total + ORDERS_PAGE_SIZE - 1) // ORDERS_PAGE_SIZE

    text = f" *Pending Orders  |  الطلبات المعلقة* ({total})\n"
    text += f"_صفحة {page + 1} من {total_pages}_\n\n"
    for o in page_orders:
        text += (
            f" `#{o['id']}` — {o['product_name']}\n"
            f" {o['full_name']}  |   {o['payment_method'].upper()}\n"
            f" ${o['price_usd']}\n\n"
        )

    # أزرار التنقل بين الصفحات
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"adm_orders_p{page}"))
    if page + 1 < total_pages:
        nav_buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"adm_orders_p{page + 2}"))

    keyboard = kb.admin_main_menu().inline_keyboard
    if nav_buttons:
        keyboard = [nav_buttons] + list(keyboard)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    item, remaining = db.pop_stock_item(order['product_id'])
    if not item:
        await query.edit_message_text(
            " المنتج لا يحتوي على مخزون  |  Product has no stock\n"
            "_أضف مخزون جديد من لوحة التحكم_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
        return

    db.update_order_delivered_item(order_id, item)
    logger.info(f"Admin confirmed order #{order_id}, product={order['product_name']}, remaining_stock={remaining}")

    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=(
                f"✅ *تم تأكيد طلبك!*\n"
                f"\n—————————————————\n\n"
                f"🛍️ *{order['product_name']}*\n"
                f"💵 المبلغ: *${order['price_usd']}*\n"
                f"\n—————————————————\n\n"
                f"_شكراً لثقتك_ 🙏"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=(
                f"🎁 *تفاصيل المنتج  |  Product Details*\n"
                f"\n—————————————————\n\n"
                f"`{item}`\n"
                f"\n—————————————————\n\n"
                f"_احفظ هذه المعلومات بأمان_"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        db.update_order_status(order_id, 'completed', 'تم الإرسال')
        confirm_text = f" *Order `#{order_id}` Confirmed!*\n_Sent to {order['full_name']}_ | Stock remaining: {remaining}"
        try:
            await query.edit_message_caption(confirm_text)
        except Exception:
            await query.edit_message_text(
                confirm_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.admin_main_menu()
            )
    except Exception as e:
        logger.error(f"confirm_order error: {e}")
        await query.edit_message_text(f" Error: {e}", reply_markup=kb.admin_main_menu())


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    order_id = int(query.data.replace("adm_reject_", ""))
    order = db.get_order(order_id)
    db.update_order_status(order_id, 'rejected', 'رُفض من الأدمن')
    logger.info(f"Admin rejected order #{order_id}")

    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=(
                f"❌ *تم رفض طلبك*\n"
                f"\n—————————————————\n\n"
                f"🔖 رقم الطلب: `#{order_id}`\n"
                f"🛍️ {order['product_name']}\n"
                f"💵 ${order['price_usd']}\n"
                f"\n—————————————————\n\n"
                f"_للاستفسار تواصل مع الأدمن_ 👤 @Allosh96ha"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu("ar")
        )
    except Exception:
        pass

    try:
        await query.edit_message_caption(f" Order #{order_id} rejected")
    except Exception:
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

    keyboard = []
    for p in products:
        status = "✅" if p['active'] else "❌"
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
    if not is_admin(query.from_user.id):
        return
    product_id = int(query.data.replace("adm_prod_detail_", ""))
    product = db.get_product(product_id)

    if not product:
        await query.edit_message_text(" المنتج غير موجود  |  Product not found")
        return

    stock_count = db.get_stock_count(product_id)
    text = (
        f" *{product['name']}*\n\n"
        f" ID: `{product['id']}`\n"
        f" Category: {product['category']}\n"
        f" USD: `${product['price_usd']}`\n"
        f" SYP: `{product['price_syp']:,.0f}`\n"
        f" Stock Count: `{stock_count} units`\n\n"
        f" Stock Preview:\n"
        f"`{product['stock'][:200] if product['stock'] else 'Empty'}...`\n"
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
    stock_count = db.get_stock_count(product_id)
    logger.info(f"Admin updated stock for product #{product_id}: {stock_count} units")
    await update.message.reply_text(
        f" *Stock Updated!  |  تم تحديث المخزون!*\n\n`{stock_count}` units added",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    return ConversationHandler.END


async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    product_id = int(query.data.replace("adm_del_", ""))
    db.delete_product(product_id)
    logger.info(f"Admin deleted product #{product_id}")
    await query.edit_message_text(
        " *Product Deleted  |  تم حذف المنتج*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )


# ═══ Broadcast — مع Batching ═══

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
    total = len(users)
    sent = 0
    failed = 0

    await update.message.reply_text(f" Sending to {total} users...")

    # إرسال على دفعات — 25 في نفس الوقت مع sleep بين الدفعات
    BATCH_SIZE = 25
    BATCH_DELAY = 1.0  # ثانية بين كل دفعة — يبقينا تحت حد تيليغرام (30/ثانية)

    async def send_one(user):
        try:
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=user['id'],
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption or ""
                )
            else:
                await context.bot.send_message(chat_id=user['id'], text=update.message.text)
            return True
        except Exception:
            return False

    for i in range(0, total, BATCH_SIZE):
        batch = users[i: i + BATCH_SIZE]
        results = await asyncio.gather(*[send_one(u) for u in batch], return_exceptions=True)
        for r in results:
            if r is True:
                sent += 1
            else:
                failed += 1
        if i + BATCH_SIZE < total:
            await asyncio.sleep(BATCH_DELAY)

    logger.info(f"Admin broadcast sent: {sent} success, {failed} failed")
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


# ══════════════════════════════════════════════════════
# AppsFlyer — قبول / رفض الطلبات
# ══════════════════════════════════════════════════════

async def appsflyer_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    order_id = int(query.data.replace("af_accept_", ""))
    order = db.get_appsflyer_order(order_id)

    if not order:
        await query.answer("❌ الطلب غير موجود", show_alert=True)
        return

    if order["status"] != "pending":
        await query.answer("⚠️ الطلب تمت معالجته مسبقاً", show_alert=True)
        return

    db.update_appsflyer_order_status(order_id, "accepted")

    await query.edit_message_text(
        query.message.text + f"\n\n✅ *تم القبول*",
        parse_mode="Markdown"
    )

    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"✅ *تم قبول طلبك!*\n\n"
                f"🎮 *اللعبة:* {order['game_name']}\n"
                f"🔢 *رقم الطلب:* `#{order_id}`\n\n"
                f"🚀 *طلبك الآن قيد التنفيذ*\n\n"
                f"\n—————————————————\n\n"
                f"📩 للمتابعة تواصل مع الأدمن:\n"
                f"👤 @Allosh96ha\n"
                f"\n—————————————————\n"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify user {order['user_id']}: {e}")


async def appsflyer_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    order_id = int(query.data.replace("af_reject_", ""))
    order = db.get_appsflyer_order(order_id)

    if not order:
        await query.answer("❌ الطلب غير موجود", show_alert=True)
        return

    if order["status"] != "pending":
        await query.answer("⚠️ الطلب تمت معالجته مسبقاً", show_alert=True)
        return

    db.add_balance(order["user_id"], order["price_usd"])
    db.update_appsflyer_order_status(order_id, "rejected")
    new_balance = db.get_balance(order["user_id"])

    await query.edit_message_text(
        query.message.text + f"\n\n❌ *تم الرفض — رُجع الرصيد للمستخدم* (`${order['price_usd']:.2f}`)",
        parse_mode="Markdown"
    )

    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"❌ *تم رفض طلبك*\n\n"
                f"🎮 *اللعبة:* {order['game_name']}\n"
                f"🔢 *رقم الطلب:* `#{order_id}`\n\n"
                f"💰 *تم إعادة المبلغ إلى رصيدك:* `${order['price_usd']:.2f}`\n"
                f"💳 *رصيدك الحالي:* `${new_balance:.2f}`\n\n"
                f"\n—————————————————\n\n"
                f"📩 للاستفسار تواصل مع الأدمن:\n"
                f"👤 @Allosh96ha\n"
                f"\n—————————————————\n"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify user {order['user_id']}: {e}")
