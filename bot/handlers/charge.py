from __future__ import annotations

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, CommandHandler, filters,
)
from repositories.users import ensure_user, get_user_language
from services.charges import ChargeService
from domain.errors import DuplicateProofError
from bot.render.keyboards import charge_methods, back_home, cancel_button
from bot.render.strings import t
from app.settings import get_settings

WAIT_METHOD, WAIT_AMOUNT, WAIT_PROOF = range(3)
service = ChargeService()


async def start_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    ensure_user(user.id, user.username or "", user.full_name or "")
    # Clear any stale data from a previous interrupted flow
    context.user_data.clear()
    lang = get_user_language(user.id)
    await query.edit_message_text(
        t("charge_methods", lang),
        parse_mode="HTML",
        reply_markup=charge_methods(lang),
    )
    return WAIT_METHOD


async def select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query.from_user.id)
    method = query.data.split(":")[-1]
    context.user_data["charge_method"] = method
    settings = get_settings()
    if method == "usdt":
        text = (
            f"💵 <b>USDT BEP-20</b>\n\n"
            f"👛 <code>{settings.usdt_wallet}</code>\n\n"
            f"⚠️ شبكة BEP-20 فقط\n\n"
            f"{t('send_amount_usdt', lang)}"
        )
    else:
        text = (
            f"📱 <b>Syriatel Cash</b>\n\n"
            f"📞 <code>{settings.syriatel_cash}</code>\n\n"
            f"💱 سعر الصرف: <b>{settings.syp_rate:,.0f} ل.س = $1</b>\n\n"
            f"{t('send_amount_syp', lang)}"
        )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=cancel_button(lang))
    return WAIT_AMOUNT


async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    try:
        raw = float(update.effective_message.text.strip().replace(",", ""))
        if raw <= 0:
            raise ValueError
    except ValueError:
        await update.effective_message.reply_text(
            t("invalid_amount", lang), reply_markup=cancel_button(lang)
        )
        return WAIT_AMOUNT

    method = context.user_data["charge_method"]
    context.user_data["amount_raw"] = raw
    if method == "usdt":
        context.user_data["amount_usd"] = raw
        prompt = t("send_tx_hash", lang)
    else:
        context.user_data["amount_usd"] = round(raw / get_settings().syp_rate, 2)
        prompt = t("send_proof", lang)

    await update.effective_message.reply_text(
        f"💵 {'$' if method == 'usdt' else ''}{raw:,.0f}"
        f"{'' if method == 'usdt' else ' ل.س'}"
        f" ≈ ${context.user_data['amount_usd']:.2f}\n\n{prompt}",
        parse_mode="HTML",
        reply_markup=cancel_button(lang),
    )
    return WAIT_PROOF


async def receive_text_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)
    try:
        charge_id = service.create_charge(
            user_id=user.id,
            method=context.user_data["charge_method"],
            amount_usd=context.user_data["amount_usd"],
            amount_raw=context.user_data["amount_raw"],
            tx_hash=update.effective_message.text.strip(),
            proof=None,
        )
    except DuplicateProofError:
        await update.effective_message.reply_text(t("duplicate_proof", lang))
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data.clear()
    await update.effective_message.reply_text(
        f"{t('charge_submitted', lang)}\n🔖 #{charge_id}\n\n{t('charge_pending', lang)}",
        parse_mode="HTML",
        reply_markup=back_home(lang),
    )
    return ConversationHandler.END


async def receive_photo_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)
    try:
        charge_id = service.create_charge(
            user_id=user.id,
            method=context.user_data["charge_method"],
            amount_usd=context.user_data["amount_usd"],
            amount_raw=context.user_data["amount_raw"],
            tx_hash=None,
            proof=update.effective_message.photo[-1].file_id,
        )
    except DuplicateProofError:
        await update.effective_message.reply_text(t("duplicate_proof", lang))
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data.clear()
    await update.effective_message.reply_text(
        f"{t('charge_submitted', lang)}\n🔖 #{charge_id}\n\n{t('charge_pending', lang)}",
        parse_mode="HTML",
        reply_markup=back_home(lang),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        lang = get_user_language(query.from_user.id)
        context.user_data.clear()
        await query.edit_message_text(t("cancelled", lang), reply_markup=back_home(lang))
    return ConversationHandler.END


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_charge, pattern=r"^charge:start$")],
        states={
            WAIT_METHOD: [
                CallbackQueryHandler(select_method, pattern=r"^charge:method:"),
                CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            ],
            WAIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount),
                CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            ],
            WAIT_PROOF: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_proof),
                MessageHandler(filters.PHOTO, receive_photo_proof),
                CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cancel),
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
        ],
        allow_reentry=True,
    )
