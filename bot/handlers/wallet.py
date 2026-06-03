from telegram import Update
from telegram.ext import ContextTypes
from repositories.users import get_user_language
from services.wallet import WalletService
from bot.render.keyboards import back_home
from bot.render.strings import t

service = WalletService()


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query.from_user.id)
    balance = service.get_balance(query.from_user.id)
    await query.edit_message_text(
        f"{t('balance', lang)}\n\n<b>${balance:.2f}</b>",
        parse_mode="HTML",
        reply_markup=back_home(lang),
    )
