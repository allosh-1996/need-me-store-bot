from telegram import Update
from telegram.ext import ContextTypes
from repositories.users import upsert_user, get_user_language, set_user_language
from bot.render.keyboards import main_menu
from bot.render.strings import t


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_language(user.id)
    await update.effective_message.reply_text(
        t("welcome", lang), parse_mode="HTML", reply_markup=main_menu(lang)
    )


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_language(user.id)
    await query.edit_message_text(
        t("welcome", lang), parse_mode="HTML", reply_markup=main_menu(lang)
    )


async def toggle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    upsert_user(user.id, user.username or "", user.full_name or "")
    current = get_user_language(user.id)
    new_lang = "en" if current == "ar" else "ar"
    set_user_language(user.id, new_lang)
    await query.edit_message_text(
        t("welcome", new_lang), parse_mode="HTML", reply_markup=main_menu(new_lang)
    )
