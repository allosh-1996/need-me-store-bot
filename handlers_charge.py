import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

import database as db
import keyboards as kb
from config import ADMIN_IDS, USDT_WALLET, SYRIATEL_CASH, SYP_RATE
from lang import t, get_user_lang
from utils import validate_amount

logger = logging.getLogger(__name__)

WAITING_METHOD, WAITING_AMOUNT, WAITING_TXHASH = range(20, 23)

_CANCEL_CB = "charge_cancel_conv"


def _cancel_kb(lang: str) -> InlineKeyboardMarkup:
    label = "❌ إلغاء العملية" if lang == "ar" else "❌ Cancel"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=_CANCEL_CB)]])


# ─────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────

async def charge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    user    = update.effective_user
    lang    = get_user_lang(context, user.id)
    balance = db.get_balance(user.id)

    text = (
        f"💳 *{t('top_up_title', lang)}*\n"
        f"\n—————————————————\n\n"
        f"💰 {t('current_balance', lang)}: *${balance:.2f}*\n\n"
        f"_{t('choose_method', lang)}_"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 USDT BEP-20 (USD)",   callback_data="chg_method_usdt")],
        [InlineKeyboardButton("📱 Syriatel Cash (SYP)", callback_data="chg_method_syriatel")],
        [InlineKeyboardButton(t("back", lang),           callback_data="back_main")],
    ])

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)

    return WAITING_METHOD


async def charge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/charge — يعرض زر يفتح الـ conversation."""
    lang    = get_user_lang(context, update.effective_user.id)
    balance = db.get_balance(update.effective_user.id)
    await update.message.reply_text(
        f"💳 *{t('top_up_title', lang)}*\n\n"
        f"💰 {t('current_balance', lang)}: *${balance:.2f}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t("top_up_title", lang), callback_data="charge_start")
        ]])
    )


# ─────────────────────────────────────────
# Step 1 — Method
# ─────────────────────────────────────────

async def charge_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    method = query.data.replace("chg_method_", "")
    lang   = get_user_lang(context, update.effective_user.id)
    context.user_data["charge_method"] = method

    if method == "usdt":
        text = (
            f"💵 *USDT BEP-20*\n\n—————————————————\n\n"
            f"👛 {t('wallet_address', lang)}:\n`{USDT_WALLET}`\n\n"
            f"⚠️ _{t('bep20_only', lang)}_\n\n"
            f"—————————————————\n\n"
            f"_{t('how_much_usd', lang)}_"
        )
    else:
        text = (
            f"📱 *Syriatel Cash*\n\n—————————————————\n\n"
            f"📞 {t('number', lang)}:\n`{SYRIATEL_CASH}`\n\n"
            f"💱 سعر الصرف: *{SYP_RATE:,.0f} ل.س = $1*\n\n"
            f"—————————————————\n\n"
            f"_{t('how_much_syp', lang)}_"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=_cancel_kb(lang))
    return WAITING_AMOUNT


# ─────────────────────────────────────────
# Step 2 — Amount
# ─────────────────────────────────────────

async def charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text   = update.message.text.strip()
    lang   = get_user_lang(context, update.effective_user.id)
    method = context.user_data.get("charge_method", "usdt")

    if method == "usdt":
        valid, amount, err = validate_amount(text, min_val=1.0, max_val=5000.0)
        if not valid:
            await update.message.reply_text(err, reply_markup=_cancel_kb(lang))
            return WAITING_AMOUNT
        context.user_data["charge_amount_usd"] = amount
        context.user_data["charge_amount_raw"] = amount
        await update.message.reply_text(
            f"💵 *${amount:.2f} USDT*\n\n—————————————————\n\n"
            f"أرسل الـ *TX Hash* بعد الإرسال:\n_Send the TX Hash after sending:_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_cancel_kb(lang),
        )
    else:
        valid, amount_syp, err = validate_amount(text, min_val=100, max_val=50_000_000)
        if not valid:
            await update.message.reply_text(err, reply_markup=_cancel_kb(lang))
            return WAITING_AMOUNT
        amount_usd = round(amount_syp / SYP_RATE, 2)
        context.user_data["charge_amount_usd"] = amount_usd
        context.user_data["charge_amount_raw"] = amount_syp
        await update.message.reply_text(
            f"📱 *{amount_syp:,.0f} ل.س ≈ ${amount_usd:.2f}*\n\n—————————————————\n\n"
            f"أرسل *صورة الإيصال* أو *رقم العملية*:\n_Send receipt photo or transaction number:_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_cancel_kb(lang),
        )

    return WAITING_TXHASH


# ─────────────────────────────────────────
# Step 3 — TX Hash
# ─────────────────────────────────────────

async def charge_txhash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx_hash    = update.message.text.strip()[:200]
    user       = update.effective_user
    lang       = get_user_lang(context, user.id)
    method     = context.user_data.get("charge_method", "usdt")
    amount_usd = context.user_data.get("charge_amount_usd", 0)
    amount_raw = context.user_data.get("charge_amount_raw", 0)

    charge_id = db.create_charge_request(
        user_id=user.id, username=user.username or "", full_name=user.full_name or "",
        method=method, amount_usd=amount_usd, amount_raw=amount_raw,
        tx_hash=tx_hash, proof=None,
    )
    if charge_id is None:
        await update.message.reply_text(
            "⚠️ هذا الـ TX Hash مستخدم مسبقاً.\n_This TX Hash was already used._",
            reply_markup=kb.main_menu(lang)
        )
        context.user_data.clear()
        return ConversationHandler.END

    await _notify_admins(context, user, charge_id, method, amount_usd, tx_hash=tx_hash)
    await update.message.reply_text(
        f"✅ *{t('charge_submitted', lang)}*\n\n—————————————————\n\n"
        f"🔖 Request ID: `#{charge_id}`\n💵 ${amount_usd:.2f}\n\n"
        f"_{t('charge_pending', lang)}_\n\n—————————————————\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────
# Step 3 — Photo (Syriatel)
# ─────────────────────────────────────────

async def charge_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo      = update.message.photo[-1]
    file_id    = photo.file_id
    user       = update.effective_user
    lang       = get_user_lang(context, user.id)
    method     = context.user_data.get("charge_method", "syriatel")
    amount_usd = context.user_data.get("charge_amount_usd", 0)
    amount_raw = context.user_data.get("charge_amount_raw", 0)

    charge_id = db.create_charge_request(
        user_id=user.id, username=user.username or "", full_name=user.full_name or "",
        method=method, amount_usd=amount_usd, amount_raw=amount_raw,
        tx_hash=None, proof=file_id,
    )
    if charge_id is None:
        await update.message.reply_text(
            "⚠️ تم إرسال هذا الإيصال مسبقاً.\n_This receipt was already submitted._",
            reply_markup=kb.main_menu(lang)
        )
        context.user_data.clear()
        return ConversationHandler.END

    await _notify_admins(context, user, charge_id, method, amount_usd, proof_type="photo")
    await update.message.reply_text(
        f"✅ *{t('charge_submitted', lang)}*\n\n—————————————————\n\n"
        f"🔖 Request ID: `#{charge_id}`\n💵 ${amount_usd:.2f}\n\n"
        f"_{t('charge_pending', lang)}_\n\n—————————————————\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────
# Cancel
# ─────────────────────────────────────────

async def charge_cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """زر إلغاء العملية داخل الـ conversation."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    lang = get_user_lang(context, update.effective_user.id)
    await query.edit_message_text(
        t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
    )
    return ConversationHandler.END


async def charge_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/cancel command fallback."""
    context.user_data.clear()
    lang = get_user_lang(context, update.effective_user.id)
    await update.message.reply_text(
        t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
    )
    return ConversationHandler.END


# ─────────────────────────────────────────
# Admin notification
# ─────────────────────────────────────────

async def _notify_admins(context, user, charge_id, method, amount_usd,
                         tx_hash=None, proof_type=None):
    method_label = "USDT BEP-20" if method == "usdt" else "Syriatel Cash"
    proof_line   = f"\n🔗 TX: `{tx_hash}`" if tx_hash else "\n🖼️ صورة إيصال"
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💰 *طلب شحن جديد | New Charge*\n\n—————————————————\n\n"
                    f"🔖 ID: `#{charge_id}`\n👤 {user.full_name} (@{user.username or '—'})\n"
                    f"🆔 `{user.id}`\n💵 ${amount_usd:.2f}\n💳 {method_label}{proof_line}\n\n—————————————————"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
