from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.render.strings import t


def main_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("iCloud",       callback_data="catalog:open:icloud"),
            InlineKeyboardButton("ايميلات",      callback_data="catalog:open:emails"),
        ],
        [
            InlineKeyboardButton("رصيدي 💰",     callback_data="wallet:balance"),
            InlineKeyboardButton("بروكسي",       callback_data="catalog:open:proxy"),
        ],
        [
            InlineKeyboardButton("Surveys",      callback_data="catalog:open:surveys"),
        ],
        [
            InlineKeyboardButton("🟢 Win AppsFlyer 🟢", callback_data="af:start"),
        ],
        [
            InlineKeyboardButton("تواصل 💬",     url="https://t.me/Allosh96ha"),
            InlineKeyboardButton("English 🌐" if lang == "ar" else "العربية 🌐", callback_data="user:toggle_lang"),
        ],
    ])


def back_home(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("home", lang), callback_data="home")]
    ])


def back_button(lang: str, cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("back", lang), callback_data=cb)]
    ])


def charge_methods(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 USDT BEP-20",   callback_data="charge:method:usdt")],
        [InlineKeyboardButton("📱 Syriatel Cash", callback_data="charge:method:syriatel")],
        [InlineKeyboardButton(t("back", lang),    callback_data="home")],
    ])


def cancel_button(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ " + t("cancelled", lang).replace(" ✅", ""), callback_data="cancel")]
    ])


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Pending Charges",    callback_data="admin:charges:0")],
        [InlineKeyboardButton("🎮 AF Pending Orders",  callback_data="admin:af_orders:0")],
        [InlineKeyboardButton("✅ AF Accepted Orders", callback_data="admin:af_accepted:0")],
    ])
