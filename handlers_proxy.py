from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID, PROXY_TYPES

# حالات المحادثة
PROXY_TYPE, PROXY_QTY, PROXY_COUNTRY, PROXY_NOTES = range(30, 34)

# ═══ قائمة البروكسي ═══
async def proxy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    keyboard = [
        [InlineKeyboardButton("🌐 HTTP/HTTPS", callback_data="prx_http"),
         InlineKeyboardButton("🔌 SOCKS5", callback_data="prx_socks5")],
        [InlineKeyboardButton("🏠 Residential", callback_data="prx_residential"),
         InlineKeyboardButton("📱 Mobile 4G/5G", callback_data="prx_mobile")],
        [InlineKeyboardButton("🖥️ Modem Private", callback_data="prx_modem")],
        [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="back_main")],
    ]

    text = (
        "🔒 *Proxies  |  بروكسيات*\n\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "اختر نوع البروكسي\n"
        "_Choose proxy type_\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=InlineKeyboardMarkup(keyboard))
    return PROXY_TYPE

# ═══ اختيار النوع ═══
async def proxy_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    proxy_type = query.data.replace("prx_", "")
    type_label = PROXY_TYPES.get(proxy_type, proxy_type)
    context.user_data["proxy_type"] = proxy_type
    context.user_data["proxy_type_label"] = type_label

    await query.edit_message_text(
        f"✅ النوع  |  Type: *{type_label}*\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🔢 كم بروكسي تريد؟\n"
        f"_How many proxies do you need?_\n\n"
        f"_مثال  |  Example: 10_",
        parse_mode=ParseMode.MARKDOWN
    )
    return PROXY_QTY

# ═══ الكمية ═══
async def proxy_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        qty = int(text)
        if qty < 1 or qty > 10000:
            raise ValueError
    except:
        await update.message.reply_text(
            "🔴 أرسل رقم صحيح بين 1 و 10000\n_Send a valid number between 1-10000_",
            parse_mode=ParseMode.MARKDOWN
        )
        return PROXY_QTY

    context.user_data["proxy_qty"] = qty

    await update.message.reply_text(
        f"✅ الكمية  |  Quantity: *{qty}*\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🌍 من أي دولة؟\n"
        f"_Which country?_\n\n"
        f"_مثال  |  Example: USA, UK, Syria, Any_",
        parse_mode=ParseMode.MARKDOWN
    )
    return PROXY_COUNTRY

# ═══ الدولة ═══
async def proxy_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["proxy_country"] = update.message.text.strip()

    await update.message.reply_text(
        f"🌍 الدولة  |  Country: *{context.user_data['proxy_country']}*\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"📝 أي ملاحظات إضافية؟\n"
        f"_Any additional notes?_\n\n"
        f"_أرسل `-` إذا ما في  |  Send `-` if none_",
        parse_mode=ParseMode.MARKDOWN
    )
    return PROXY_NOTES

# ═══ الملاحظات وإرسال الطلب ═══
async def proxy_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    notes = update.message.text.strip()
    if notes == "-":
        notes = "—"

    proxy_type = context.user_data.get("proxy_type", "")
    type_label = context.user_data.get("proxy_type_label", "")
    qty = context.user_data.get("proxy_qty", 0)
    country = context.user_data.get("proxy_country", "")

    # إشعار الأدمن
    admin_text = (
        f"🔒 *New Proxy Order  |  طلب بروكسي جديد*\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"👤 {user.full_name} (@{user.username or '—'})\n"
        f"🆔 `{user.id}`\n\n"
        f"📦 Type  |  النوع: *{type_label}*\n"
        f"🔢 Quantity  |  الكمية: *{qty}*\n"
        f"🌍 Country  |  الدولة: *{country}*\n"
        f"📝 Notes  |  ملاحظات: {notes}\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"💵 Format: `ip:port:user:pass`"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    admin_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ تم الإرسال", callback_data=f"prx_done_{user.id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"prx_reject_{user.id}")
    ]])

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_kb
        )
    except Exception as e:
        print(f"Admin notify error: {e}")

    # رد على المستخدم
    done_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Home  |  الرئيسية", callback_data="back_main")
    ]])

    await update.message.reply_text(
        f"✅ *Order Sent!  |  تم إرسال طلبك!*\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"📦 {type_label}\n"
        f"🔢 {qty} proxies\n"
        f"🌍 {country}\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"⏳ سيتم التواصل معك قريباً\n"
        f"_We'll contact you soon_ 🚀",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )

    # تنظيف
    for k in ["proxy_type", "proxy_type_label", "proxy_qty", "proxy_country"]:
        context.user_data.pop(k, None)

    return ConversationHandler.END

# ═══ ردود الأدمن ═══
async def proxy_admin_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    user_id = int(query.data.replace("prx_done_", ""))
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ *Proxies Ready!  |  البروكسيات جاهزة!*\n\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "تم تجهيز طلبك، راجع رسائلك\n"
                "_Your order is ready, check your messages_\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu()
        )
        await query.edit_message_text(f"✅ تم إشعار المستخدم `{user_id}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await query.edit_message_text(f"🔴 Error: {e}")

async def proxy_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    user_id = int(query.data.replace("prx_reject_", ""))
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🔴 *Order Rejected  |  تم رفض طلبك*\n\n"
                "_للاستفسار تواصل مع الأدمن_\n"
                "_Contact admin for more info_"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        await query.edit_message_text(f"🔴 تم رفض طلب `{user_id}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await query.edit_message_text(f"🔴 Error: {e}")

async def proxy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled  |  تم الإلغاء", reply_markup=kb.persistent_menu())
    return ConversationHandler.END
