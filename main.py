import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
from telegram.constants import ParseMode

import database as db
from config import BOT_TOKEN, ADMIN_IDS
from keep_alive import keep_alive
import handlers_user     as hu
import handlers_admin    as ha
import handlers_charge   as hc
import handlers_appsflyer as haf

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"⚠️ *خطأ في البوت*\n\n`{type(context.error).__name__}: {context.error}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass


def main():
    keep_alive()

    for attempt in range(10):
        try:
            db.init_db()
            logger.info("✅ DB ready")
            break
        except Exception as e:
            logger.error(f"❌ DB connection failed (attempt {attempt + 1}/10): {e}")
            if attempt < 9:
                time.sleep(5)
            else:
                logger.critical("❌ DB failed after 10 attempts")
                raise

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Add Product ──
    add_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ha.add_product_start, pattern="^adm_add_product$")],
        states={
            ha.ADM_PROD_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_name)],
            ha.ADM_PROD_DESC:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_desc)],
            ha.ADM_PROD_PRICE_USD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_price_usd)],
            ha.ADM_PROD_PRICE_SYP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_price_syp)],
            ha.ADM_PROD_CATEGORY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_category)],
            ha.ADM_PROD_STOCK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_stock)],
        },
        fallbacks=[CommandHandler("cancel", ha.cancel), CommandHandler("start", hu.universal_cancel)],
        per_user=True, per_chat=True, per_message=False,
    )

    # ── Update Stock ──
    stock_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ha.update_stock_start, pattern=r"^adm_stock_\d+$")],
        states={
            ha.ADM_STOCK_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.update_stock_receive)],
        },
        fallbacks=[CommandHandler("cancel", ha.cancel), CommandHandler("start", hu.universal_cancel)],
        per_user=True, per_chat=True, per_message=False,
    )

    # ── Broadcast ──
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ha.broadcast_start, pattern="^adm_broadcast$")],
        states={
            ha.ADM_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", ha.cancel), CommandHandler("start", hu.universal_cancel)],
        per_user=True, per_chat=True, per_message=False,
    )

    # ── Charge ──
    charge_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(hc.charge_start, pattern="^charge_start$")],
        states={
            hc.WAITING_METHOD: [
                CallbackQueryHandler(hc.charge_method_selected,  pattern="^chg_method_"),
                CallbackQueryHandler(hc.charge_cancel_conv,      pattern="^charge_cancel_conv$"),
            ],
            hc.WAITING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,  hc.charge_amount),
                CallbackQueryHandler(hc.charge_cancel_conv,      pattern="^charge_cancel_conv$"),
            ],
            hc.WAITING_TXHASH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,  hc.charge_txhash),
                MessageHandler(filters.PHOTO,                    hc.charge_photo),
                CallbackQueryHandler(hc.charge_cancel_conv,      pattern="^charge_cancel_conv$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", hc.charge_cancel),
            CommandHandler("start",  hc.charge_cancel),
            CallbackQueryHandler(hc.charge_cancel_conv, pattern="^charge_cancel_conv$"),
        ],
        per_user=True, per_chat=True, per_message=False,
    )

    # ── AppsFlyer ──
    af_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(haf.appsflyer_menu, pattern="^win_appsflyer$")],
        states={
            haf.AF_GAME:    [CallbackQueryHandler(haf.af_game_selected,       pattern="^af_game_")],
            haf.AF_IDFA:    [MessageHandler(filters.TEXT & ~filters.COMMAND,  haf.af_receive_idfa)],
            haf.AF_IDFV:    [MessageHandler(filters.TEXT & ~filters.COMMAND,  haf.af_receive_idfv)],
            haf.AF_IOS_VER: [MessageHandler(filters.TEXT & ~filters.COMMAND,  haf.af_receive_ios_ver)],
            haf.AF_AF_ID:   [MessageHandler(filters.TEXT & ~filters.COMMAND,  haf.af_receive_af_id)],
            haf.AF_LEVELS:  [
                CallbackQueryHandler(haf.af_level_toggle,         pattern=r"^af_lvl_\d+$"),
                CallbackQueryHandler(haf.af_level_custom,         pattern="^af_lvl_custom$"),
                CallbackQueryHandler(haf.af_levels_back,          pattern="^af_lvl_back$"),
                CallbackQueryHandler(haf.af_levels_done,          pattern="^af_lvl_done$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND,   haf.af_receive_custom_levels),
            ],
            haf.AF_CONFIRM: [CallbackQueryHandler(haf.af_confirm_send, pattern="^af_confirm_send$")],
        },
        fallbacks=[
            CommandHandler("cancel",  ha.cancel),
            CommandHandler("start",   ha.cancel),
            CallbackQueryHandler(haf.af_cancel, pattern="^af_cancel$"),
        ],
        per_user=True, per_chat=True, per_message=False,
    )

    # ── Commands ──
    app.add_handler(CommandHandler("start",    hu.start))
    app.add_handler(CommandHandler("help",     hu.help_cmd))
    app.add_handler(CommandHandler("products", hu.products_cmd))
    app.add_handler(CommandHandler("charge",   hc.charge_cmd))
    app.add_handler(CommandHandler("lang",     hu.change_language_cmd))
    app.add_handler(CommandHandler("support",  hu.support_cmd))
    app.add_handler(CommandHandler("admin",    ha.admin_panel))

    # ── Conversations ──
    app.add_handler(add_product_conv)
    app.add_handler(stock_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(charge_conv)
    app.add_handler(af_conv)

    # ── Callbacks ──
    app.add_handler(CallbackQueryHandler(hu.persistent_start,    pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(hu.toggle_lang,         pattern="^toggle_lang$"))
    app.add_handler(CallbackQueryHandler(hu.show_products,       pattern="^products$"))
    app.add_handler(CallbackQueryHandler(hu.show_platform,       pattern="^platform_"))
    app.add_handler(CallbackQueryHandler(hu.show_category,       pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(hu.show_product_detail, pattern="^prod_"))
    app.add_handler(CallbackQueryHandler(hu.buy_product,         pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(hu.show_balance,        pattern="^show_balance$"))
    app.add_handler(CallbackQueryHandler(hu.contact_handler,     pattern="^contact$"))
    app.add_handler(CallbackQueryHandler(hu.proxy_menu,          pattern="^proxy_menu$"))
    app.add_handler(CallbackQueryHandler(hu.surveys_menu,        pattern="^surveys_menu$"))
    app.add_handler(CallbackQueryHandler(hu.icloud_menu,         pattern="^icloud_menu$"))
    app.add_handler(CallbackQueryHandler(hu.emails_menu,         pattern="^emails_menu$"))
    app.add_handler(CallbackQueryHandler(ha.admin_panel,         pattern="^adm_panel$"))
    app.add_handler(CallbackQueryHandler(ha.admin_stats,         pattern="^adm_stats$"))
    app.add_handler(CallbackQueryHandler(ha.admin_products,      pattern="^adm_products$"))
    app.add_handler(CallbackQueryHandler(ha.admin_orders,        pattern="^adm_orders$"))
    app.add_handler(CallbackQueryHandler(ha.admin_order_action,  pattern="^adm_order_"))

    app.add_error_handler(error_handler)

    logger.info("🚀 NexVault Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
