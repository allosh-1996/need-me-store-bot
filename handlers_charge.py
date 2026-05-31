import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID, USDT_WALLET, SYRIATEL_CASH, SYP_RATE
from lang import t, get_user_lang

logger = logging.getLogger(__name__)

WAITING_METHOD, WAITING_AMOUNT, WAITING_TXHASH = range(20, 23)


async def charge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user    = update.effective_user
    lang    = get_user_lang(context, user.id)
    balance = db.get_balance(user.id)

    method_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 USDT BEP-20  (USD)", callback_data="chg_method_usdt")],
        [InlineKeyboardButton("📱 Syriatel Cash  (SYP)", callback_data="chg_method_syriatel")],
        [InlineKeyboardButton(t("back", lang), callback_data="back_main")],
    ])

    text = (
        f"💳 *{t('top_up_title', lang)}*\n"
        f"\n—————————————————\n\n"
        f"💰 {t('current_balance', lang)}: *${balance:.2f}*\n\n"
        f"_{t('choose_method', lang)}_"
    )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=method_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=method_kb)

    return WAITING_METHOD


async def charge_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    method = query.data.replace("chg_method_", "")
    lang   = get_user_lang(context, update.effective_user.id)
    context.user_data["charge_method"] = method

    if method == "usdt":
        text = (
            f"💵 *USDT BEP-20*\n"
            f"\n—————————————————\n\n"
            f"👛 {t('wallet_address', lang)}:\n"
            f"`{USDT_WALLET}`\n\n"
            f"⚠️ _{t('bep20_only', lang)}_\n\n"
            f"_{t('how_much_usd', lang)}_"
        )
    else:
        text = (
            f"📱 *Syriatel Cash*\n"
            f"\n—————————————————\n\n"
            f"📞 {t('number', lang)}:\n"
            f"`{SYRIATEL_CASH}`\n\n"
            f"💱 سعر الصرف: *{SYP_RATE:,.0f} ل.س = $1*\n\n"
            f"_{t('how_much_syp', lang)}_"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    return WAITING_AMOUNT


async def charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lang = get_user_lang(context, update.effective_user.id)

    if any(x in text for x in ["ابدأ", "Start"]):
        return await charge_back_to_main(update, context)

    method = context.user_data.get("charge_method", "usdt")
    raw    = text.replace("$", "").replace(",", "").replace("،", "")

    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ " + ("Send a valid positive number" if lang == "en" else "أرسل رقم صحيح أكبر من صفر")
        )
        return WAITING_AMOUNT

    if method == "usdt":
        if amount > 10000:
            await update.message.reply_text(
                "❌ " + ("Maximum $10,000" if lang == "en" else "الحد الأقصى $10,000")
            )
            return WAITING_AMOUNT
        display = f"${amount}"
    else:
        amount_usd = round(amount / SYP_RATE, 2)
        display    = f"{amount:,.0f} ل.س (≈ ${amount_usd:.2f})"
        context.user_data["charge_amount_syp"] = amount
        amount = amount_usd

    context.user_data["charge_amount"]  = amount
    context.user_data["charge_display"] = display

    cancel_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("back", lang), callback_data="back_main")]]
    )
    await update.message.reply_text(
        f"💵 {t('amount', lang)}: `{display}`\n\n"
        f"_{t('send_receipt', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_kb,
    )
    return WAITING_TXHASH


async def charge_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        txt = update.message.text.strip()
        if any(x in txt for x in ["ابدأ", "Start"]):
            return await charge_back_to_main(update, context)

    user         = update.effective_user
    lang         = get_user_lang(context, user.id)
    amount       = context.user_data.get("charge_amount", 0)
    method       = context.user_data.get("charge_method", "usdt")
    display      = context.user_data.get("charge_display", f"${amount}")
    method_label = "USDT BEP-20" if method == "usdt" else "Syriatel Cash"

    if not amount:
        await update.message.reply_text(t("session_expired", lang))
        return ConversationHandler.END

    if update.message.photo:
        proof      = update.message.photo[-1].file_id
        proof_type = "photo"
        tx_hash    = update.message.caption or "photo"
    elif update.message.document:
        proof      = update.message.document.file_id
        proof_type = "document"
        tx_hash    = update.message.caption or "file"
    else:
        proof      = update.message.text or ""
        proof_type = "text"
        tx_hash    = proof

    db.upsert_user(user.id, user.username or "", user.full_name or "")
    try:
        req_id = db.create_charge_request(
            user_id=user.id, username=user.username or "",
            full_name=user.full_name or "", amount_usd=amount,
            tx_hash=tx_hash, method=method,
        )
        db.update_charge_proof(req_id, proof)
    except Exception as e:
        logger.error(f"DB Error in charge_proof: {e}")
        await update.message.reply_text("❌ خطأ في الحفظ — حاول مجدداً")
        return ConversationHandler.END

    admin_text = (
        f"💰 *Top Up Request #{req_id}*\n\n"
        f"👤 {user.full_name} (@{user.username or '—'})\n"
        f"🆔 `{user.id}`\n"
        f"💵 Amount: `{display}`\n"
        f"💳 Method: `{method_label}`\n"
        f"🔗 TXID: `{tx_hash[:60]}`"
    )
    admin_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ Confirm {display}", callback_data=f"chg_confirm_{req_id}"),
        InlineKeyboardButton("❌ Reject",             callback_data=f"chg_reject_{req_id}"),
    ]])

    try:
        if proof_type == "photo":
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb,
            )
        elif proof_type == "document":
            await context.bot.send_document(
                chat_id=ADMIN_ID, document=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb,
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=admin_text,
                parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb,
            )
    except Exception as e:
        logger.error(f"Admin notify error in charge_proof: {e}")

    done_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("home", lang), callback_data="back_main")]]
    )
    await update.message.reply_text(
        f"✅ *{t('top_up_sent', lang)}*\n"
        f"\n—————————————————\n\n"
        f"🔖 {t('request_id', lang)}: `#{req_id}`\n"
        f"💵 {t('amount', lang)}: *{display}*\n"
        f"💳 {t('method', lang)}: {method_label}\n"
        f"\n—————————————————\n\n"
        f"⏳ _{t('top_up_sent', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb,
    )

    for k in ["charge_amount", "charge_method", "charge_display", "charge_amount_syp"]:
        context.user_data.pop(k, None)
    return ConversationHandler.END


async def charge_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context, update.effective_user.id)
    for k in ["charge_amount", "charge_method", "charge_display", "charge_amount_syp"]:
        context.user_data.pop(k, None)
    if update.message:
        await update.message.reply_text(t("cancel", lang))
    return ConversationHandler.END


async def charge_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context, update.effective_user.id)
    for k in ["charge_amount", "charge_method", "charge_display", "charge_amount_syp"]:
        context.user_data.pop(k, None)

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
        )
    else:
        await update.message.reply_text(
            t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
        )
    return ConversationHandler.END


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user    = update.effective_user
    lang    = get_user_lang(context, user.id)
    balance = db.get_balance(user.id)
    details = db.get_balance_details(user.id)

    bal_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 {t('top_up', lang)}", callback_data="charge_start")],
        [InlineKeyboardButton(t("back", lang),           callback_data="back_main")],
    ])

    text = (
        f"💳 *{t('my_balance', lang)}*\n"
        f"\n—————————————————\n\n"
        f"💰 {t('balance', lang)}: *${balance:.2f}*\n\n"
        f"📥 {t('total_charged', lang)}: `${details['total_charged']:.2f}`\n"
        f"📤 {t('total_spent', lang)}: `${details['total_spent']:.2f}`\n"
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
    req    = db.confirm_charge(req_id)

    if not req:
        try:
            await query.edit_message_caption("⚠️ Not found or already processed")
        except Exception:
            await query.edit_message_text("⚠️ Not found or already processed")
        return

    new_balance  = db.get_balance(req["user_id"])
    method_label = "USDT BEP-20" if req["method"] == "usdt" else "Syriatel Cash"

    # Notify user in their own language
    user_lang = db.get_user_lang(req["user_id"])
    try:
        await context.bot.send_message(
            chat_id=req["user_id"],
            text=(
                f"✅ *{t('balance_added', user_lang)}*\n\n"
                f"💵 {t('amount_added', user_lang)}: `${req['amount_usd']}`\n"
                f"💳 {method_label}\n"
                f"💰 {t('new_balance', user_lang)}: `${new_balance:.2f}`\n\n"
                f"_{t('can_shop_now', user_lang)}_ 🛍️"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu(user_lang),
        )
    except Exception as e:
        logger.error(f"Notify error in admin_confirm_charge: {e}")

    confirm_text = (
        f"✅ Confirmed #{req_id} — ${req['amount_usd']} → {req['full_name']}\n"
        f"New balance: ${new_balance:.2f}"
    )
    try:
        await query.edit_message_caption(confirm_text)
    except Exception:
        await query.edit_message_text(confirm_text, parse_mode=ParseMode.MARKDOWN)


async def admin_reject_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    req_id = int(query.data.replace("chg_reject_", ""))
    req    = db.get_charge_request(req_id)
    db.reject_charge(req_id)

    if req:
        method_label = "USDT BEP-20" if req["method"] == "usdt" else "Syriatel Cash"
        user_lang    = db.get_user_lang(req["user_id"])
        try:
            await context.bot.send_message(
                chat_id=req["user_id"],
                text=(
                    f"❌ *{t('top_up_rejected', user_lang)}*\n\n"
                    f"🔖 {t('request_id', user_lang)}: `#{req_id}`\n"
                    f"💵 {t('amount', user_lang)}: `${req['amount_usd']}`\n"
                    f"💳 {method_label}\n\n"
                    f"_{t('contact_admin', user_lang)}_"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.main_menu(user_lang),
            )
        except Exception:
            pass

    try:
        await query.edit_message_caption(f"❌ Rejected #{req_id}")
    except Exception:
        await query.edit_message_text(f"❌ Rejected `#{req_id}`", parse_mode=ParseMode.MARKDOWN)
