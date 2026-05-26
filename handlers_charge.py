from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID, USDT_WALLET

# حالات المحادثة
WAITING_METHOD, WAITING_AMOUNT, WAITING_TXHASH = range(20, 23)

# ============ طلب شحن رصيد ============
async def charge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    balance = db.get_balance(user.id)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    method_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 USDT BEP-20 (دولار)", callback_data="chg_method_usdt")],
        [InlineKeyboardButton("📱 Syriatel Cash (ليرة سورية)", callback_data="chg_method_syriatel")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

    text = (
        f"💳 *شحن الرصيد*\n\n"
        f"رصيدك الحالي: `${balance:.2f}`\n\n"
        f"اختر طريقة الشحن:"
    )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=method_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=method_kb)

    return WAITING_METHOD

async def charge_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("chg_method_", "")
    context.user_data["charge_method"] = method

    if method == "usdt":
        text = (
            f"💰 *الشحن عبر USDT BEP-20*\n\n"
            f"📌 عنوان المحفظة:\n"
            f"`{USDT_WALLET}`\n\n"
            f"⚠️ *شبكة BEP-20 فقط*\n\n"
            f"كم دولار تريد تشحن؟ (الحد الأدنى $1)"
        )
    else:
        from config import SYRIATEL_CASH
        text = (
            f"📱 *الشحن عبر Syriatel Cash*\n\n"
            f"📞 رقم الاستلام:\n"
            f"`{SYRIATEL_CASH}`\n\n"
            f"كم ليرة سورية تريد تشحن؟\n"
            f"(الحد الأدنى 50,000 ل.س)"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    return WAITING_AMOUNT

async def charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = context.user_data.get("charge_method", "usdt")
    raw = update.message.text.strip().replace("$", "").replace(",", "").replace("،", "")

    try:
        amount = float(raw)
    except ValueError:
        await update.message.reply_text("❌ أرسل رقم فقط مثل: 5 أو 50000")
        return WAITING_AMOUNT

    if method == "usdt":
        if amount < 1:
            await update.message.reply_text("❌ الحد الأدنى $1:")
            return WAITING_AMOUNT
        if amount > 10000:
            await update.message.reply_text("❌ الحد الأقصى $10,000:")
            return WAITING_AMOUNT
        display = f"${amount}"
    else:
        if amount < 50000:
            await update.message.reply_text("❌ الحد الأدنى 50,000 ل.س:")
            return WAITING_AMOUNT
        display = f"{amount:,.0f} ل.س"

    context.user_data["charge_amount"] = amount
    context.user_data["charge_display"] = display

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="back_main")]])
    await update.message.reply_text(
        f"✅ المبلغ: *{display}*\n\n"
        f"الآن أرسل صورة إيصال التحويل\n"
        f"أو أرسل رقم العملية (TXID) 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_kb
    )
    return WAITING_TXHASH

async def charge_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get('charge_amount', 0)

    # استقبال الإيصال
    if update.message.photo:
        proof = update.message.photo[-1].file_id
        proof_type = "photo"
        tx_hash = update.message.caption or ""
    else:
        proof = update.message.text
        proof_type = "text"
        tx_hash = proof

    # إنشاء طلب الشحن
    method = context.user_data.get("charge_method", "usdt")
    display = context.user_data.get("charge_display", f"${amount}")
    req_id = db.create_charge_request(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        amount_usd=amount,
        tx_hash=tx_hash,
        method=method
    )
    db.update_charge_proof(req_id, proof)

    # إشعار الأدمن
    method = context.user_data.get("charge_method", "usdt")
    display = context.user_data.get("charge_display", f"${amount}")
    method_label = "USDT BEP-20" if method == "usdt" else "Syriatel Cash"
    admin_text = (
        f"💰 *طلب شحن رصيد #{req_id}*\n\n"
        f"👤 {user.full_name} (@{user.username or 'لا يوجد'})\n"
        f"🆔 `{user.id}`\n"
        f"💵 المبلغ: *{display}*\n"
        f"💳 الطريقة: *{method_label}*\n"
        f"🔗 TXID: `{tx_hash[:60] if tx_hash else 'صورة'}`"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ تأكيد ${amount}", callback_data=f"chg_confirm_{req_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"chg_reject_{req_id}")
        ]
    ])

    try:
        if proof_type == "photo":
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_kb
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=admin_text,
                parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb
            )
    except Exception as e:
        print(f"خطأ إشعار أدمن: {e}")

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    done_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]])
    await update.message.reply_text(
        f"✅ *تم استلام طلب الشحن!*\n\n"
        f"🔖 رقم الطلب: `#{req_id}`\n"
        f"💵 المبلغ: `{display}`\n\n"
        f"سيتم مراجعة التحويل وإضافة الرصيد خلال وقت قصير ⏳",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )

    context.user_data.pop('charge_amount', None)
    return ConversationHandler.END

async def charge_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('charge_amount', None)
    await update.message.reply_text("❌ تم إلغاء الشحن.", reply_markup=kb.persistent_menu())
    return ConversationHandler.END

# ============ عرض الرصيد ============
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    balance = db.get_balance(user.id)

    conn = db.get_conn()
    c = conn.cursor()
    c.execute("SELECT total_charged, total_spent FROM balances WHERE user_id=?", (user.id,))
    row = c.fetchone()
    conn.close()

    total_charged = row['total_charged'] if row else 0
    total_spent = row['total_spent'] if row else 0

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    bal_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 شحن رصيد", callback_data="charge_start")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

    text = (
        f"💰 *رصيدك*\n\n"
        f"💵 الرصيد الحالي: `${balance:.2f}`\n"
        f"📥 إجمالي الشحن: `${total_charged:.2f}`\n"
        f"📤 إجمالي الإنفاق: `${total_spent:.2f}`"
    )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=bal_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=bal_kb)

# ============ تأكيد/رفض الشحن من الأدمن ============
async def admin_confirm_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    req_id = int(query.data.replace("chg_confirm_", ""))
    req = db.confirm_charge(req_id)

    if not req:
        await query.edit_message_caption("❌ الطلب مش موجود أو تم معالجته مسبقاً.")
        return

    new_balance = db.get_balance(req['user_id'])

    try:
        await context.bot.send_message(
            chat_id=req['user_id'],
            text=(
                f"✅ *تم شحن رصيدك!*\n\n"
                f"💵 المبلغ المضاف: `${req['amount_usd']}`\n"
                f"💰 رصيدك الحالي: `${new_balance:.2f}`\n\n"
                f"يمكنك الآن التسوق 🛍️"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu()
        )
    except Exception as e:
        print(f"خطأ إرسال إشعار: {e}")

    try:
        await query.edit_message_caption(
            f"✅ تم تأكيد الشحن #{req_id} — ${req['amount_usd']} لـ {req['full_name']}"
        )
    except:
        await query.edit_message_text(
            f"✅ تم تأكيد الشحن #{req_id} — ${req['amount_usd']} لـ {req['full_name']}"
        )

async def admin_reject_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    req_id = int(query.data.replace("chg_reject_", ""))
    req = db.get_charge_request(req_id)
    db.reject_charge(req_id)

    try:
        await context.bot.send_message(
            chat_id=req['user_id'],
            text=f"❌ تم رفض طلب الشحن #{req_id}.\n\nللاستفسار تواصل مع الأدمن.",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

    try:
        await query.edit_message_caption(f"❌ تم رفض الشحن #{req_id}")
    except:
        await query.edit_message_text(f"❌ تم رفض الشحن #{req_id}")
