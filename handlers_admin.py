import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

import database as db
import keyboards as kb
from config import ADMIN_IDS
from lang import t
from utils import rate_limit, validate_text, validate_amount

logger = logging.getLogger(__name__)

(ADM_PROD_NAME, ADM_PROD_DESC, ADM_PROD_PRICE_USD, ADM_PROD_PRICE_SYP,
 ADM_PROD_CATEGORY, ADM_PROD_STOCK, ADM_BROADCAST_MSG, ADM_STOCK_UPDATE) = range(10, 18)

ORDERS_PAGE_SIZE = 8

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = "🔐 *Admin Panel | لوحة التحكم*\n\n NexVault — Admin\n"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.admin_main_menu()
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.admin_main_menu()
        )

@rate_limit(seconds=3)
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
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.admin_main_menu())

async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await query.edit_message_text(
        "➕ *Add Product | إضافة منتج*\n\nأرسل اسم المنتج:\n_Send product name:_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADM_PROD_NAME

async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid, err = validate_text(update.message.text, "name")
    if not valid:
        await update.message.reply_text(err)
        return ADM_PROD_NAME
    context.user_data["prod_name"] = update.message.text.strip()
    await update.message.reply_text("📝 أرسل الوصف (أو أرسل `-` لتخطيه):\n_Send description (or `-` to skip):_")
    return ADM_PROD_DESC

async def add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["prod_desc"] = "" if text == "-" else text[:300]
    await update.message.reply_text("💵 أرسل السعر بالدولار:\n_Send price in USD:_")
    return ADM_PROD_PRICE_USD

async def add_product_price_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid, amount, err = validate_amount(update.message.text, min_val=0.1, max_val=9999)
    if not valid:
        await update.message.reply_text(err)
        return ADM_PROD_PRICE_USD
    context.user_data["prod_price_usd"] = amount
    await update.message.reply_text("💴 أرسل السعر بالليرة السورية:\n_Send price in SYP:_")
    return ADM_PROD_PRICE_SYP

async def add_product_price_syp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid, amount, err = validate_amount(update.message.text, min_val=0, max_val=99_000_000)
    if not valid:
        await update.message.reply_text(err)
        return ADM_PROD_PRICE_SYP
    context.user_data["prod_price_syp"] = amount
    await update.message.reply_text("📂 أرسل الفئة:\n_Send category:_")
    return ADM_PROD_CATEGORY

async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid, err = validate_text(update.message.text, "category")
    if not valid:
        await update.message.reply_text(err)
        return ADM_PROD_CATEGORY
    context.user_data["prod_category"] = update.message.text.strip()
    await update.message.reply_text(
        "📦 أرسل المخزون (كل سطر = وحدة):\n_Send stock (one item per line):_\n\n_أرسل `-` إذا لا يوجد مخزون الآن_"
    )
    return ADM_PROD_STOCK

async def add_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text  = update.message.text.strip()
    stock = "" if text == "-" else text
    pid   = db.add_product(
        name=context.user_data["prod_name"],
        description=context.user_data.get("prod_desc", ""),
        price_usd=context.user_data["prod_price_usd"],
        price_syp=context.user_data.get("prod_price_syp", 0),
        category=context.user_data["prod_category"],
        stock=stock,
    )
    count = db.get_stock_count(pid)
    await update.message.reply_text(
        f"✅ *تم إضافة المنتج*\n\n📦 {context.user_data['prod_name']}\n🔢 المخزون: {count} وحدة",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def update_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    product_id = int(query.data.replace("adm_stock_", ""))
    context.user_data["stock_product_id"] = product_id
    product    = db.get_product(product_id)
    await query.edit_message_text(
        f"✏️ *تعديل مخزون: {product['name'] if product else product_id}*\n\n"
        f"أرسل المخزون الجديد (كل سطر = وحدة):\n_Send new stock (one item per line):_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADM_STOCK_UPDATE

async def update_stock_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get("stock_product_id")
    lines      = [l.strip() for l in update.message.text.splitlines() if l.strip()]
    db.set_stock_items(product_id, lines)
    count = db.get_stock_count(product_id)
    await update.message.reply_text(
        f"✅ تم تحديث المخزون — *{count} وحدة*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    return ConversationHandler.END

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    await query.edit_message_text(
        "📢 *رسالة جماعية*\n\nأرسل نص الرسالة:\n_Send broadcast message:_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ADM_BROADCAST_MSG

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid, err = validate_text(update.message.text, "message")
    if not valid:
        await update.message.reply_text(err)
        return ADM_BROADCAST_MSG
    msg   = update.message.text.strip()
    users = db.get_all_users()
    sent  = failed = 0
    status_msg = await update.message.reply_text(f"📢 جاري الإرسال لـ {len(users)} مستخدم...")
    for i, user in enumerate(users):
        try:
            await context.bot.send_message(chat_id=user["id"], text=msg)
            sent += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            await asyncio.sleep(1)
    await status_msg.edit_text(
        f"✅ *اكتمل الإرسال*\n\n✅ نجح: {sent}\n❌ فشل: {failed}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.admin_main_menu()
    )
    return ConversationHandler.END

@rate_limit(seconds=3)
async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    orders = db.get_orders_paginated(status="pending", limit=ORDERS_PAGE_SIZE)
    if not orders:
        await query.edit_message_text(
            "📋 *لا يوجد طلبات معلقة*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
        return
    for order in orders[:ORDERS_PAGE_SIZE]:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ تأكيد", callback_data=f"adm_order_confirm_{order['id']}"),
            InlineKeyboardButton("❌ رفض",   callback_data=f"adm_order_reject_{order['id']}"),
        ]])
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                f"🔖 *طلب #{order['id']}*\n"
                f"👤 {order['full_name']} (@{order['username'] or '—'})\n"
                f"📦 {order['product_name']}\n💵 ${order['price_usd']}"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

async def admin_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    parts    = query.data.split("_")
    action   = parts[2]
    order_id = int(parts[3])
    order    = db.get_order(order_id)
    if not order:
        await query.edit_message_text("❌ الطلب غير موجود")
        return
    if action == "confirm":
        item, remaining = db.pop_stock_item(order["product_id"])
        if not item:
            await query.edit_message_text(f"❌ لا يوجد مخزون للمنتج #{order['product_id']}")
            return
        db.update_order_delivered_item(order_id, item)
        db.update_order_status(order_id, "completed")
        try:
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=(
                    f"✅ *تم تأكيد طلبك!*\n\n—————————————————\n\n"
                    f"🔖 Order ID: `#{order_id}`\n📦 {order['product_name']}\n"
                    f"💵 ${order['price_usd']}\n\n—————————————————\n\nشكراً لثقتك 🙏"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=f"🎁 *تفاصيل المنتج*\n\n—————————————————\n\n`{item}`\n\n—————————————————\n\n_احفظ هذه المعلومات بأمان_",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
        await query.edit_message_text(f"✅ تم تأكيد الطلب #{order_id} — مخزون متبقٍ: {remaining}")
    elif action == "reject":
        refunded = db.refund_order(order_id)
        db.update_order_status(order_id, "rejected")
        try:
            refund_note = f"\n💰 تم إرجاع ${order['price_usd']:.2f} لرصيدك" if refunded else ""
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=(
                    f"🔴 *تم رفض طلبك*\n\n—————————————————\n\n"
                    f"🔖 Order ID: `#{order_id}`\n📦 {order['product_name']}\n\n"
                    f"_للاستفسار تواصل مع الأدمن_{refund_note}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
        await query.edit_message_text(f"❌ تم رفض الطلب #{order_id}" + (" — تم إرجاع المبلغ ✅" if refunded else ""))

@rate_limit(seconds=3)
async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    products = db.get_all_products(active_only=True)
    if not products:
        await query.edit_message_text(
            "📦 *لا يوجد منتجات*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.admin_main_menu()
        )
        return
    lines    = [f"• #{p['id']} {p['name']} — {p['stock_count']} وحدة" for p in products]
    keyboard = [[InlineKeyboardButton(f"✏️ #{p['id']} {p['name']}", callback_data=f"adm_stock_{p['id']}")] for p in products]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_panel")])
    await query.edit_message_text(
        "📦 *المنتجات*\n\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("تم الإلغاء ✅", reply_markup=kb.admin_main_menu())
    return ConversationHandler.END
