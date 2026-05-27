from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID, PROXY_TYPES

# حالات المحادثة
PROXY_TYPE, PROXY_QTY, PROXY_QTY_CUSTOM, PROXY_COUNTRY, PROXY_COUNTRY_CUSTOM, PROXY_NOTES, PROXY_CONFIRM = range(30, 37)

# ═══ قوائم الخيارات ═══
COUNTRY_OPTIONS = [
    (" USA", "USA"),
    (" UK", "UK"),
    (" Germany", "Germany"),
    (" France", "France"),
    (" Turkey", "Turkey"),
    (" Syria", "Syria"),
    (" Saudi Arabia", "Saudi Arabia"),
    (" UAE", "UAE"),
    (" Any", "Any"),
]

QTY_OPTIONS = [1, 5, 10, 25, 50, 100]


def proxy_type_keyboard():
    keyboard = [
        [InlineKeyboardButton(" HTTP/HTTPS", callback_data="prx_http"),
         InlineKeyboardButton(" SOCKS5", callback_data="prx_socks5")],
        [InlineKeyboardButton(" Residential", callback_data="prx_residential"),
         InlineKeyboardButton(" Mobile 4G/5G", callback_data="prx_mobile")],
        [InlineKeyboardButton(" Modem Private", callback_data="prx_modem")],
        [InlineKeyboardButton(" Back  |  رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def proxy_qty_keyboard():
    row1 = [InlineKeyboardButton(str(q), callback_data=f"prxq_{q}") for q in QTY_OPTIONS[:3]]
    row2 = [InlineKeyboardButton(str(q), callback_data=f"prxq_{q}") for q in QTY_OPTIONS[3:]]
    keyboard = [
        row1, row2,
        [InlineKeyboardButton(" كمية مخصصة  |  Custom", callback_data="prxq_custom")],
        [InlineKeyboardButton(" Back  |  رجوع", callback_data="prx_back_type")],
    ]
    return InlineKeyboardMarkup(keyboard)


def proxy_country_keyboard():
    keyboard = []
    row = []
    for label, val in COUNTRY_OPTIONS:
        row.append(InlineKeyboardButton(label, callback_data=f"prxc_{val}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(" دولة أخرى  |  Other", callback_data="prxc_other")])
    keyboard.append([InlineKeyboardButton(" Back  |  رجوع", callback_data="prx_back_qty")])
    return InlineKeyboardMarkup(keyboard)


def proxy_notes_keyboard():
    keyboard = [
        [InlineKeyboardButton(" بدون ملاحظات  |  No Notes", callback_data="prxn_none")],
        [InlineKeyboardButton(" Back  |  رجوع", callback_data="prx_back_country")],
    ]
    return InlineKeyboardMarkup(keyboard)


def proxy_confirm_keyboard():
    keyboard = [
        [InlineKeyboardButton(" إرسال الطلب  |  Send Order", callback_data="prx_confirm_send")],
        [InlineKeyboardButton(" Back  |  رجوع", callback_data="prx_back_notes")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ═══ قائمة البروكسي ═══
async def proxy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    text = (
        " *Proxies  |  بروكسيات*\n\n"
        "\n"
        "اختر نوع البروكسي\n"
        "_Choose proxy type_\n"
        ""
    )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=proxy_type_keyboard())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=proxy_type_keyboard())
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
        f" النوع  |  Type: *{type_label}*\n\n"
        f"\n"
        f" كم بروكسي تريد؟\n"
        f"_How many proxies?_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=proxy_qty_keyboard()
    )
    return PROXY_QTY


# ═══ الكمية (أزرار) ═══
async def proxy_qty_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # رجوع للنوع
    if query.data == "prx_back_type":
        await query.edit_message_text(
            " *Proxies  |  بروكسيات*\n\n"
            "\n"
            "اختر نوع البروكسي\n"
            "_Choose proxy type_\n"
            "",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=proxy_type_keyboard()
        )
        return PROXY_TYPE

    # كمية مخصصة
    if query.data == "prxq_custom":
        await query.edit_message_text(
            f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n\n"
            f"\n"
            f" اكتب الكمية يدوياً\n"
            f"_Type quantity manually (1–10000):_",
            parse_mode=ParseMode.MARKDOWN
        )
        return PROXY_QTY_CUSTOM

    qty = int(query.data.replace("prxq_", ""))
    context.user_data["proxy_qty"] = qty

    await query.edit_message_text(
        f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n"
        f" الكمية  |  Qty: *{qty}*\n\n"
        f"\n"
        f" اختر الدولة\n"
        f"_Choose country_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=proxy_country_keyboard()
    )
    return PROXY_COUNTRY


# ═══ الكمية المخصصة (نص) ═══
async def proxy_qty_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        qty = int(text)
        if qty < 1 or qty > 10000:
            raise ValueError
    except:
        await update.message.reply_text(
            " أرسل رقم صحيح بين 1 و 10000\n_Send a valid number between 1–10000_",
            parse_mode=ParseMode.MARKDOWN
        )
        return PROXY_QTY_CUSTOM

    context.user_data["proxy_qty"] = qty

    await update.message.reply_text(
        f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n"
        f" الكمية  |  Qty: *{qty}*\n\n"
        f"\n"
        f" اختر الدولة\n"
        f"_Choose country_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=proxy_country_keyboard()
    )
    return PROXY_COUNTRY


# ═══ الدولة (أزرار) ═══
async def proxy_country_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # رجوع للكمية
    if query.data == "prx_back_qty":
        await query.edit_message_text(
            f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n\n"
            f"\n"
            f" كم بروكسي تريد؟\n"
            f"_How many proxies?_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=proxy_qty_keyboard()
        )
        return PROXY_QTY

    # دولة أخرى
    if query.data == "prxc_other":
        await query.edit_message_text(
            f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n"
            f" الكمية: *{context.user_data.get('proxy_qty', '')}*\n\n"
            f"\n"
            f" اكتب اسم الدولة\n"
            f"_Type country name:_",
            parse_mode=ParseMode.MARKDOWN
        )
        return PROXY_COUNTRY_CUSTOM

    country = query.data.replace("prxc_", "")
    context.user_data["proxy_country"] = country

    await query.edit_message_text(
        f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n"
        f" الكمية: *{context.user_data.get('proxy_qty', '')}*\n"
        f" الدولة  |  Country: *{country}*\n\n"
        f"\n"
        f" أي ملاحظات إضافية؟\n"
        f"_Any additional notes?_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=proxy_notes_keyboard()
    )
    return PROXY_NOTES


# ═══ الدولة المخصصة (نص) ═══
async def proxy_country_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = update.message.text.strip()
    context.user_data["proxy_country"] = country

    await update.message.reply_text(
        f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n"
        f" الكمية: *{context.user_data.get('proxy_qty', '')}*\n"
        f" الدولة  |  Country: *{country}*\n\n"
        f"\n"
        f" أي ملاحظات إضافية؟\n"
        f"_Any additional notes?_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=proxy_notes_keyboard()
    )
    return PROXY_NOTES


# ═══ الملاحظات ═══
async def proxy_notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query:
        await query.answer()

        # رجوع للدولة
        if query.data == "prx_back_country":
            await query.edit_message_text(
                f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n"
                f" الكمية: *{context.user_data.get('proxy_qty', '')}*\n\n"
                f"\n"
                f" اختر الدولة\n"
                f"_Choose country_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=proxy_country_keyboard()
            )
            return PROXY_COUNTRY

        # بدون ملاحظات
        if query.data == "prxn_none":
            context.user_data["proxy_notes"] = "—"
            await _show_confirm(query, context, edit=True)
            return PROXY_CONFIRM
    else:
        # كتب ملاحظة
        context.user_data["proxy_notes"] = update.message.text.strip()
        await _show_confirm(update, context, edit=False)
        return PROXY_CONFIRM


async def _show_confirm(target, context, edit=True):
    type_label = context.user_data.get("proxy_type_label", "")
    qty = context.user_data.get("proxy_qty", "")
    country = context.user_data.get("proxy_country", "")
    notes = context.user_data.get("proxy_notes", "—")

    text = (
        f" *ملخص الطلب  |  Order Summary*\n\n"
        f"\n"
        f" النوع  |  Type: *{type_label}*\n"
        f" الكمية  |  Qty: *{qty}*\n"
        f" الدولة  |  Country: *{country}*\n"
        f" ملاحظات  |  Notes: {notes}\n"
        f"\n"
        f"_تأكد من المعلومات قبل الإرسال_\n"
        f"_Confirm details before sending_"
    )

    if edit:
        await target.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=proxy_confirm_keyboard())
    else:
        await target.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=proxy_confirm_keyboard())


# ═══ تأكيد الإرسال ═══
async def proxy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # رجوع للملاحظات
    if query.data == "prx_back_notes":
        await query.edit_message_text(
            f" النوع: *{context.user_data.get('proxy_type_label', '')}*\n"
            f" الكمية: *{context.user_data.get('proxy_qty', '')}*\n"
            f" الدولة: *{context.user_data.get('proxy_country', '')}*\n\n"
            f"\n"
            f" أي ملاحظات إضافية؟\n"
            f"_Any additional notes?_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=proxy_notes_keyboard()
        )
        return PROXY_NOTES

    # إرسال الطلب
    user = query.from_user
    type_label = context.user_data.get("proxy_type_label", "")
    proxy_type = context.user_data.get("proxy_type", "")
    qty = context.user_data.get("proxy_qty", "")
    country = context.user_data.get("proxy_country", "")
    notes = context.user_data.get("proxy_notes", "—")

    # تسجيل المستخدم + حفظ الطلب بقاعدة البيانات
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    order_id = db.create_proxy_order(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        proxy_type=proxy_type,
        proxy_type_label=type_label,
        quantity=qty,
        country=country,
        notes=notes
    )

    admin_text = (
        f" *New Proxy Order  |  طلب بروكسي جديد*\n\n"
        f"\n"
        f" {user.full_name} (@{user.username or '—'})\n"
        f" `{user.id}`\n\n"
        f" Type  |  النوع: *{type_label}*\n"
        f" Quantity  |  الكمية: *{qty}*\n"
        f" Country  |  الدولة: *{country}*\n"
        f" Notes  |  ملاحظات: {notes}\n"
        f"\n"
        f" Format: `ip:port:user:pass`\n"
        f" Order ID: `#{order_id}`"
    )

    admin_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(" تم الإرسال", callback_data=f"prx_done_{user.id}_{order_id}"),
        InlineKeyboardButton(" رفض", callback_data=f"prx_reject_{user.id}_{order_id}")
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

    done_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(" Home  |  الرئيسية", callback_data="back_main")
    ]])

    await query.edit_message_text(
        f" *Order Sent!  |  تم إرسال طلبك!*\n\n"
        f"\n"
        f" {type_label}\n"
        f" {qty} proxies\n"
        f" {country}\n"
        f"\n"
        f"⏳ سيتم التواصل معك قريباً\n"
        f"_We'll contact you soon_ ",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )

    for k in ["proxy_type", "proxy_type_label", "proxy_qty", "proxy_country", "proxy_notes"]:
        context.user_data.pop(k, None)

    return ConversationHandler.END


# ═══ ردود الأدمن ═══
async def proxy_admin_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    parts = query.data.replace("prx_done_", "").split("_")
    user_id = int(parts[0])
    order_id = int(parts[1]) if len(parts) > 1 else None
    if order_id:
        db.update_proxy_order_status(order_id, "completed")
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f" *تم قبول طلب البروكسي!  |  Proxy Order Accepted!*\n\n"
                f"\n"
                f" Order ID: `#{order_id}`\n"
                f"\n"
                f"⏳ _سيتم التواصل معك وإرسال البروكسيات قريباً_\n"
                f"_We'll send your proxies shortly_ "
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu()
        )
        await query.edit_message_text(f" تم إشعار المستخدم `{user_id}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await query.edit_message_text(f" Error: {e}")


async def proxy_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    parts = query.data.replace("prx_reject_", "").split("_")
    user_id = int(parts[0])
    order_id = int(parts[1]) if len(parts) > 1 else None
    if order_id:
        db.update_proxy_order_status(order_id, "rejected")
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f" *تم رفض طلب البروكسي  |  Proxy Order Rejected*\n\n"
                f"\n"
                f" Order ID: `#{order_id}`\n"
                f"\n"
                f"_للاستفسار تواصل مع الأدمن_\n"
                f"_Contact admin for more info_"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu()
        )
        await query.edit_message_text(f" تم رفض طلب `{user_id}`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await query.edit_message_text(f" Error: {e}")


async def proxy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(" Cancelled  |  تم الإلغاء", reply_markup=kb.persistent_menu())
    return ConversationHandler.END
