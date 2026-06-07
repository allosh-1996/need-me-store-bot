from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from repositories.users import ensure_user, get_user_language
from services.wallet import WalletService
from bot.render.strings import t

service = WalletService()


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    ensure_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_language(user.id)
    balance = service.get_balance(user.id)
    await query.edit_message_text(
        f"{t('balance', lang)}

<b>${balance:.2f}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("top_up", lang), callback_data="charge:start")],
            [InlineKeyboardButton(t("home", lang),   callback_data="home")],
        ]),
    )
