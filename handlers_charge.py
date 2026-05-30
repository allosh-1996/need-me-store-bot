import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID, USDT_WALLET, SYP_RATE
from lang import t, get_user_lang

logger = logging.getLogger(__name__)

WAITING_METHOD, WAITING_AMOUNT, WAITING_TXHASH = range(20, 23)

async def charge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    balance = db.get_balance(user.id)

    method_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(" USDT BEP-20  (دولار  |  USD)", callback_data="chg_method_usdt")],
        [InlineKeyboardButton(" Syriatel Cash  (ليرة سورية  |  SYP)", callback_data="chg_method_syriatel")],
        [InlineKeyboardButton(" Back  |  رجوع", callback_data="back_main")]
    ])

    text = (
        f"💳 *شحن الرصيد | Top Up*\n"
        f"\n—————————————————\n\n"
        f"💰 رصيدك الحالي: *${balance:.2f}*\n\n"
        f"_اختر طريقة الشحن  |  Choose payment method:_"
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
            f"💵 *USDT BEP-20*\n"
            f"\n—————————————————\n\n"
            f"👛 عنوان المحفظة:\n"
            f"`{USDT_WALLET}`\n\n"
            f"⚠️ _شبكة BEP-20 فقط_\n\n"
            f"كم دولار تريد تشحن؟"
        )
    else:
        from config import SYRIATEL_CASH
        text = (
            f"📱 *Syriatel Cash*\n"
            f"\n—————————————————\n\n"
            f"📞 الرقم:\n"
            f"`{SYRIATEL_CASH}`\n\n"
            f"💱 سعر الصرف: *{SYP_RATE:,.0f} ل.س = $1*\n\n"
            f"كم ليرة تريد تشحن؟"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    return WAITING_AMOUNT

async def charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if any(x in text for x in ["ابدأ", "Start"]):
        return await charge_back_to_main(update, context)

    method = context.user_data.get("charge_method", "usdt")
    raw = text.replace("$", "").replace(",", "").replace("،", "")

    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(" أرسل رقم صحيح أكبر من صفر  |  Send a valid positive number")
        return WAITING_AMOUNT

    if method == "usdt":
        if amount > 10000:
            await update.message.reply_text(" الحد الأقصى $10,000  |  Maximum $10,000")
            return WAITING_AMOUNT
        display = f"${amount}"
    else:
        amount_usd = round(amount / SYP_RATE, 2)
        display = f"{amount:,.0f} ل.س (≈ ${amount_usd:.2f})"
        context.user_data["charge_amount"] = amount_usd
        context.user_data["charge_display"] = display
        context.user_data["charge_amount_syp"] = amount
        amount = amount_usd  # نحفظ بالدولار

    context.user_data["charge_amount"] = amount
    context.user_data["charge_display"] = display

    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton(" Cancel  |  إلغاء", callback_data="back_main")]])
    await update.message.reply_text(
        f" Amount  |  المبلغ: `{display}`\n\n"
        f"\n"
        f" أرسل صورة الإيصال أو TXID \n"
        f"_Send receipt screenshot or transaction ID_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_kb
    )
    return WAITING_TXHASH

async def charge_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        txt = update.message.text.strip()
        if any(x in txt for x in ["ابدأ", "Start"]):
            return await charge_back_to_main(update, context)

    user = update.effective_user
    amount = context.user_data.get("charge_amount", 0)
    method = context.user_data.get("charge_method", "usdt")
    display = context.user_data.get("charge_display", f"${amount}")
    method_label = "USDT BEP-20" if method == "usdt" else "Syriatel Cash"

    if not amount:
        await update.message.reply_text(
            " انتهت الجلسة  |  Session expired. Start again.",
            reply_markup=kb.persistent_menu()
        )
        return ConversationHandler.END

    if update.message.photo:
        proof = update.message.photo[-1].file_id
        proof_type = "photo"
        tx_hash = update.message.caption or "photo"
    elif update.message.document:
        proof = update.message.document.file_id
        proof_type = "document"
        tx_hash = update.message.caption or "file"
    else:
        proof = update.message.text or ""
        proof_type = "text"
        tx_hash = proof

    db.upsert_user(user.id, user.username or "", user.full_name or "")
    try:
        req_id = db.create_charge_request(
            user_id=user.id, username=user.username or "",
            full_name=user.full_name or "", amount_usd=amount,
            tx_hash=tx_hash, method=method
        )
        db.update_charge_proof(req_id, proof)
    except Exception as e:
        logger.error(f"DB Error in charge_proof: {e}")
        await update.message.reply_text(" خطأ في الحفظ  |  Save error, try again.")
        return ConversationHandler.END

    admin_text = (
        f" *Top Up Request  |  طلب شحن* `#{req_id}`\n\n"
        f"\n"
        f" {user.full_name} (@{user.username or '—'})\n"
        f" `{user.id}`\n"
        f" Amount: `{display}`\n"
        f" Method: `{method_label}`\n"
        f" TXID: `{tx_hash[:60]}`\n"
        f""
    )

    admin_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f" Confirm {display}", callback_data=f"chg_confirm_{req_id}"),
        InlineKeyboardButton(" Reject", callback_data=f"chg_reject_{req_id}")
    ]])

    try:
        if proof_type == "photo":
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb
            )
        elif proof_type == "document":
            await context.bot.send_document(
                chat_id=ADMIN_ID, document=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=admin_text,
                parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb
            )
    except Exception as e:
        logger.error(f"Admin notify error in charge_proof: {e}")

    done_kb = InlineKeyboardMarkup([[InlineKeyboardButton(" Home  |  الرئيسية", callback_data="back_main")]])
    await update.message.reply_text(
        f"✅ *تم إرسال طلب الشحن!*\n"
        f"\n—————————————————\n\n"
        f"🔖 رقم الطلب: `#{req_id}`\n"
        f"💵 المبلغ: *{display}*\n"
        f"💳 الطريقة: {method_label}\n"
        f"\n—————————————————\n\n"
        f"⏳ _سيتم مراجعة التحويل وإضافة الرصيد قريباً_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )

    for k in ["charge_amount", "charge_method", "charge_display"]:
        context.user_data.pop(k, None)
    return ConversationHandler.END

async def charge_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for k in ['charge_amount','charge_method','charge_display','charge_amount_syp']:
        context.user_data.pop(k, None)
    if update.message:
        await update.message.reply_text("تم الإلغاء ✅")
    return ConversationHandler.END

async def charge_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رجوع للقائمة الرئيسية — يشتغل مع callback أو message"""
    lang = get_user_lang(context)
    for k in ['charge_amount','charge_method','charge_display','charge_amount_syp']:
        context.user_data.pop(k, None)

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            t("welcome", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu(lang)
        )
    else:
        await update.message.reply_text(
            t("welcome", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu(lang)
        )
    return ConversationHandler.END

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    lang = get_user_lang(context)
    balance = db.get_balance(user.id)

    details = db.get_balance_details(user.id)
    total_charged = details['total_charged']
    total_spent = details['total_spent']

    bal_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(" Top Up  |  شحن رصيد", callback_data="charge_start")],
        [InlineKeyboardButton(" Back  |  رجوع", callback_data="back_main")]
    ])

    if lang == 'en':
        text = (
            f"💳 *My Balance*\n"
            f"\n—————————————————\n\n"
            f"💰 Balance: *${balance:.2f}*\n\n"
            f"📥 Total Charged: `${total_charged:.2f}`\n"
            f"📤 Total Spent: `${total_spent:.2f}`\n"
            f"\n—————————————————\n"
        )
    else:
        text = (
            f"💳 *رصيدي*\n"
            f"\n—————————————————\n\n"
            f"💰 الرصيد: *${balance:.2f}*\n\n"
            f"📥 إجمالي الشحن: `${total_charged:.2f}`\n"
            f"📤 إجمالي الإنفاق: `${total_spent:.2f}`\n"
            f"\n—————————————————\n"
        )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=bal_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=bal_kb)

async def admin_confirm_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    req_id = int(query.data.replace("chg_confirm_", ""))
    req = db.confirm_charge(req_id)

    if not req:
        try:
            await query.edit_message_caption(" الطلب غير موجود أو تمت معالجته مسبقاً  |  Not found or already processed")
        except:
            await query.edit_message_text(" Not found or already processed")
        return

    new_balance = db.get_balance(req['user_id'])

    # إشعار العميل بإضافة الرصيد
    try:
        await context.bot.send_message(
            chat_id=req['user_id'],
            text=(
                f" *تم شحن رصيدك!  |  Balance Added!*\n\n"
                f"\n"
                f" المبلغ المضاف  |  Added: `${req['amount_usd']}`\n"
                f" {('USDT BEP-20' if req['method'] == 'usdt' else 'Syriatel Cash')}\n"
                f" رصيدك الحالي  |  New Balance: `${new_balance:.2f}`\n"
                f"\n"
                f"_يمكنك الشراء الآن من المتجر_ \n"
                f"_You can now shop from the store_"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu("ar")
        )
    except Exception as e:
        logger.error(f"Notify error in admin_confirm_charge: {e}")

    try:
        await query.edit_message_caption(
            f" Confirmed #{req_id} — ${req['amount_usd']} added to {req['full_name']}\n"
            f" New balance: ${new_balance:.2f}"
        )
    except:
        await query.edit_message_text(
            f" Confirmed `#{req_id}` — `${req['amount_usd']}` added to {req['full_name']}\n"
            f" New balance: `${new_balance:.2f}`",
            parse_mode=ParseMode.MARKDOWN
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
        method_label = "USDT BEP-20" if req['method'] == 'usdt' else "Syriatel Cash"
        await context.bot.send_message(
            chat_id=req['user_id'],
            text=(
                f" *تم رفض طلب الشحن  |  Top Up Rejected*\n\n"
                f"\n"
                f" Request ID: `#{req_id}`\n"
                f" المبلغ  |  Amount: `${req['amount_usd']}`\n"
                f" {method_label}\n"
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
        await query.edit_message_caption(f" Rejected #{req_id}")
    except:
        await query.edit_message_text(f" Rejected `#{req_id}`", parse_mode=ParseMode.MARKDOWN)
