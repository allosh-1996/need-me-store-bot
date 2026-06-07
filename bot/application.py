from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from app.settings import get_settings
from bot.handlers import start as start_h
from bot.handlers import catalog as catalog_h
from bot.handlers import wallet as wallet_h
from bot.handlers import admin as admin_h
from bot.handlers.charge import build_conversation as build_charge_conv
from bot.handlers.appsflyer import build_conversation as build_af_conv


def build_app() -> Application:
    app = Application.builder().token(get_settings().telegram_bot_token).build()

    # Commands
    app.add_handler(CommandHandler("start", start_h.start))
    app.add_handler(CommandHandler("admin", admin_h.admin_panel))

    # Navigation
    app.add_handler(CallbackQueryHandler(start_h.home,            pattern=r"^home$"))
    app.add_handler(CallbackQueryHandler(start_h.toggle_language, pattern=r"^user:toggle_lang$"))

    # Catalog
    app.add_handler(CallbackQueryHandler(catalog_h.open_catalog,  pattern=r"^catalog:open$"))
    app.add_handler(CallbackQueryHandler(catalog_h.show_product,  pattern=r"^catalog:product:\d+$"))
    app.add_handler(CallbackQueryHandler(catalog_h.buy_product,   pattern=r"^catalog:buy:\d+$"))

    # Wallet
    app.add_handler(CallbackQueryHandler(wallet_h.show_balance,   pattern=r"^wallet:balance$"))

    # Conversations (charge + appsflyer)
    app.add_handler(build_charge_conv())
    app.add_handler(build_af_conv())

    # Admin panel
    app.add_handler(CallbackQueryHandler(admin_h.admin_panel,         pattern=r"^admin:panel$"))
    app.add_handler(CallbackQueryHandler(admin_h.list_pending_charges, pattern=r"^admin:charges(:\d+)?$"))
    app.add_handler(CallbackQueryHandler(admin_h.list_pending_af,      pattern=r"^admin:af_orders(:\d+)?$"))
    app.add_handler(CallbackQueryHandler(admin_h.list_accepted_af,     pattern=r"^admin:af_accepted(:\d+)?$"))

    # Admin actions
    app.add_handler(CallbackQueryHandler(admin_h.charge_action, pattern=r"^charge:(confirm|reject):\d+$"))
    app.add_handler(CallbackQueryHandler(admin_h.af_action,     pattern=r"^af:(accept|reject|fulfill):\d+$"))

    return app
