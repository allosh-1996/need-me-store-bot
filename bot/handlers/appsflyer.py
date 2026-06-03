import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, CommandHandler, filters,
)
from repositories.users import get_user_language
from repositories.wallet import get_balance
from services.appsflyer import AppsflyerService
from domain.errors import InsufficientBalanceError
from bot.render.keyboards import back_home, cancel_button
from bot.render.strings import t
from bot.render.formatters import safe
from app.settings import get_settings

UUID_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)

WAIT_GAME, WAIT_IDFA, WAIT_IDFV, WAIT_IOS, WAIT_AFID, WAIT_LEVELS = range(40, 46)
service = AppsflyerService()

GAMES = {
    "domino_dream":    ("Domino Dreams",    "AF_PRICE_DOMINO"),
    "disney_dream":    ("Disney Dream",     "AF_PRICE_DISNEY"),
    "coin_master":     ("Coin Master",      "AF_PRICE_COIN"),
    "travel_town":     ("Travel Town",      "AF_PRICE_TRAVEL"),
    "yarn_loop":       ("Yarn Loop",        "AF_PRICE_YARN"),
    "dice_dream":      ("Dice Dreams",      "AF_PRICE_DICE"),
    "toy_blast":       ("Toy Blast",        "AF_PRICE_TOY"),
    "toon_blast":      ("Toon Blast",       "AF_PRICE_TOON"),
    "match_factory":   ("Match Factory",    "AF_PRICE_MATCH"),
    "royal_kingdom":   ("Royal Kingdom",    "AF_PRICE_ROYAL"),
    "board_adventure": ("Board Adventure",  "AF_PRICE_BOARD"),
    "disney_solitaire":("Disney Solitaire", "AF_PRICE_DSOL"),
    "homescapes":      ("Homescapes",       "AF_PRICE_HOME"),
    "screw_guru":      ("Screw Guru",       "AF_PRICE_SCREW"),
    "empires":         ("Empires",          "AF_PRICE_EMPIRES"),
    "zombie_miner":    ("Zombie Miner",     "AF_PRICE_ZOMBIE"),
    "family_island":   ("Family Island",    "AF_PRICE_FAMILY"),
}


def _game_price(env_key: str) -> float:
    import os
    return float(os.getenv(env_key, "4"))


async def show_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query.from_user.id)
    buttons = []
    for key, (name, env_key) in GAMES.items():
        price = _game_price(env_key)
        buttons.append([InlineKeyboardButton(
            f"{name} — ${price:.0f}",
            callback_data=f"af:game:{key}",
        )])
    buttons.append([InlineKeyboardButton(t("back", lang), callback_data="home")])
    await query.edit_message_text(
        "🎮 اختر اللعبة:" if lang == "ar" else "🎮 Choose a game:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return WAIT_GAME


async def select_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query.from_user.id)
    game_key = query.data.replace("af:game:", "")
    if game_key not in GAMES:
        await query.answer("❌", show_alert=True)
        return WAIT_GAME
    name, env_key = GAMES[game_key]
    price = _game_price(env_key)
    balance = get_balance(query.from_user.id)
    if balance < price:
        await query.edit_message_text(
            f"{t('insufficient_balance', lang)}\n\n💰 ${balance:.2f} / 💵 ${price:.0f}",
            reply_markup=back_home(lang),
        )
        return ConversationHandler.END
    context.user_data.update({"af_game_key": game_key, "af_game_name": name, "af_price": price})
    await query.edit_message_text(
        f"🎮 <b>{safe(name)}</b> — ${price:.0f}\n\n{'—'*20}\n\n{t('af_step_idfa', lang)}",
        parse_mode="HTML",
        reply_markup=cancel_button(lang),
    )
    return WAIT_IDFA


async def receive_idfa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    val = update.effective_message.text.strip()
    if not UUID_RE.match(val):
        await update.effective_message.reply_text(t("af_invalid_uuid", lang), reply_markup=cancel_button(lang))
        return WAIT_IDFA
    context.user_data["af_idfa"] = val
    await update.effective_message.reply_text(t("af_step_idfv", lang), parse_mode="HTML", reply_markup=cancel_button(lang))
    return WAIT_IDFV


async def receive_idfv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    val = update.effective_message.text.strip()
    if not UUID_RE.match(val):
        await update.effective_message.reply_text(t("af_invalid_uuid", lang), reply_markup=cancel_button(lang))
        return WAIT_IDFV
    context.user_data["af_idfv"] = val
    await update.effective_message.reply_text(t("af_step_ios", lang), parse_mode="HTML", reply_markup=cancel_button(lang))
    return WAIT_IOS


async def receive_ios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    context.user_data["af_ios"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(t("af_step_afid", lang), parse_mode="HTML", reply_markup=cancel_button(lang))
    return WAIT_AFID


async def receive_afid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    context.user_data["af_afid"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(t("af_step_levels", lang), parse_mode="HTML", reply_markup=cancel_button(lang))
    return WAIT_LEVELS


async def receive_levels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)
    levels = update.effective_message.text.strip()
    ud = context.user_data
    try:
        order_id = service.create_order(
            user_id=user.id,
            game_key=ud["af_game_key"],
            game_name=ud["af_game_name"],
            price_usd=ud["af_price"],
            idfa=ud["af_idfa"],
            idfv=ud["af_idfv"],
            ios_version=ud["af_ios"],
            appsflyer_id=ud["af_afid"],
            levels=levels,
        )
    except InsufficientBalanceError:
        await update.effective_message.reply_text(t("insufficient_balance", lang), reply_markup=back_home(lang))
        context.user_data.clear()
        return ConversationHandler.END

    balance = get_balance(user.id)
    await update.effective_message.reply_text(
        t("af_submitted", lang,
          order_id=order_id,
          game_name=safe(ud["af_game_name"]),
          levels=safe(levels),
          price_usd=f"{ud['af_price']:.0f}",
          balance=f"{balance:.2f}"),
        parse_mode="HTML",
        reply_markup=back_home(lang),
    )

    # إشعار الأدمن
    admin_text = (
        f"🔔 <b>AppsFlyer Order #{order_id}</b>\n"
        f"👤 {safe(user.full_name)} (@{safe(user.username or 'N/A')})\n"
        f"🆔 <code>{user.id}</code>\n"
        f"🎮 {safe(ud['af_game_name'])}\n"
        f"💵 ${ud['af_price']:.0f} ✅ خُصم\n"
        f"🎯 Levels: <code>{safe(levels)}</code>\n"
        f"📱 IDFA: <code>{safe(ud['af_idfa'])}</code>\n"
        f"📱 IDFV: <code>{safe(ud['af_idfv'])}</code>\n"
        f"📱 iOS: <code>{safe(ud['af_ios'])}</code>\n"
        f"📱 AF ID: <code>{safe(ud['af_afid'])}</code>"
    )
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    for admin_id in get_settings().admin_ids:
        try:
            await update.get_bot().send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ قبول", callback_data=f"af:accept:{order_id}"),
                    InlineKeyboardButton("❌ رفض",  callback_data=f"af:reject:{order_id}"),
                ]]),
            )
        except Exception:
            pass

    context.user_data.clear()
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
        entry_points=[CallbackQueryHandler(show_games, pattern=r"^af:start$")],
        states={
            WAIT_GAME:   [CallbackQueryHandler(select_game, pattern=r"^af:game:")],
            WAIT_IDFA:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_idfa)],
            WAIT_IDFV:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_idfv)],
            WAIT_IOS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ios)],
            WAIT_AFID:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_afid)],
            WAIT_LEVELS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_levels)],
        },
        fallbacks=[
            CommandHandler("start", cancel),
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
        ],
        allow_reentry=True,
    )
