import logging
from keep_alive import keep_alive
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

import database as db
from config import BOT_TOKEN, ADMIN_ID
import handlers_user as hu
import handlers_admin as ha
import handlers_charge as hc
import handlers_proxy as hp
import handlers_appsflyer as haf

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    keep_alive()  # Self-ping فقط — لا Flask server منفصل

    # محاولة الاتصال بالـ DB مع retry
    import time
    for attempt in range(10):
        try:
            db.init_db()
            logger.info("✅ قاعدة البيانات جاهزة")
            break
        except Exception as e:
            logger.error(f"❌ DB connection failed (attempt {attempt+1}/10): {e}")
            if attempt < 9:
                time.sleep(5)
            else:
                logger.critical("❌ فشل الاتصال بقاعدة البيانات بعد 10 محاولات")
                raise

    app = Application.builder().token(BOT_TOKEN).build()

    # ========== ConversationHandler: شراء منتج ==========
    buy_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(hu.show_payment_details, pattern=r'^pay_\d+_\w+_\w+$')],
        states={
            hu.WAITING_PROOF: [
                MessageHandler(
                    filters.PHOTO | filters.Document.ALL | (filters.TEXT & ~filters.COMMAND),
                    hu.receive_proof
                )
            ],
        },
        fallbacks=[
            CommandHandler('cancel', lambda u, c: ConversationHandler.END),
            CommandHandler('start', hu.persistent_start),
            MessageHandler(filters.Regex("ابدأ|Start"), hu.persistent_start),
        ],
        per_user=True,
        per_chat=True,
        per_message=False,
    )

    # ========== ConversationHandler: إضافة منتج ==========
    add_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ha.add_product_start, pattern='^adm_add_product$')],
        states={
            ha.ADM_PROD_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_name)],
            ha.ADM_PROD_DESC:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_desc)],
            ha.ADM_PROD_PRICE_USD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_price_usd)],
            ha.ADM_PROD_PRICE_SYP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_price_syp)],
            ha.ADM_PROD_CATEGORY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_category)],
            ha.ADM_PROD_PLATFORM:  [CallbackQueryHandler(ha.add_product_platform, pattern=r'^adm_platform_')],
            ha.ADM_PROD_STOCK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.add_product_stock)],
        },
        fallbacks=[CommandHandler('cancel', ha.cancel), MessageHandler(filters.Regex("ابدأ|Start"), hu.persistent_start)],
        per_user=True,
        per_chat=True,
        per_message=False,
    )

    # ========== ConversationHandler: تحديث مخزون ==========
    stock_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ha.update_stock_start, pattern=r'^adm_stock_\d+$')],
        states={
            ha.ADM_STOCK_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ha.update_stock_receive)],
        },
        fallbacks=[CommandHandler('cancel', ha.cancel), MessageHandler(filters.Regex("ابدأ|Start"), hu.persistent_start)],
        per_user=True,
        per_chat=True,
        per_message=False,
    )

    # ========== ConversationHandler: رسالة جماعية ==========
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ha.broadcast_start, pattern='^adm_broadcast$')],
        states={
            ha.ADM_BROADCAST_MSG: [
                MessageHandler(
                    (filters.TEXT & ~filters.COMMAND) | filters.PHOTO,
                    ha.broadcast_send
                )
            ],
        },
        fallbacks=[CommandHandler('cancel', ha.cancel), MessageHandler(filters.Regex("ابدأ|Start"), hu.persistent_start)],
        per_user=True,
        per_chat=True,
        per_message=False,
    )

    # ========== ConversationHandler: شحن رصيد ==========
    charge_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(hc.charge_start, pattern='^charge_start$'),
            CommandHandler('charge', hc.charge_start),
        ],
        states={
            hc.WAITING_METHOD: [
                CallbackQueryHandler(hc.charge_method_selected, pattern=r'^chg_method_'),
                CallbackQueryHandler(hc.charge_back_to_main, pattern='^back_main$'),
            ],
            hc.WAITING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, hc.charge_amount),
                CallbackQueryHandler(hc.charge_back_to_main, pattern='^back_main$'),
            ],
            hc.WAITING_TXHASH: [
                MessageHandler(
                    filters.PHOTO | filters.Document.ALL | (filters.TEXT & ~filters.COMMAND),
                    hc.charge_proof
                ),
                CallbackQueryHandler(hc.charge_back_to_main, pattern='^back_main$'),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', hc.charge_cancel),
            CommandHandler('start', hc.charge_back_to_main),
            MessageHandler(filters.Regex("ابدأ|Start"), hu.persistent_start),
        ],
        per_user=True, per_chat=True, per_message=False,
    )

    # ========== أوامر ==========
    app.add_handler(CommandHandler("start",    hu.start))
    app.add_handler(CommandHandler("help",     hu.help_cmd))
    app.add_handler(CommandHandler("products", hu.show_products))
    app.add_handler(CommandHandler("orders",   hu.my_orders))
    app.add_handler(CommandHandler("admin",    ha.admin_panel))

    # ========== Conversations ==========
    app.add_handler(add_product_conv)
    app.add_handler(stock_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(charge_conv)
    app.add_handler(buy_conv)

    # ========== ConversationHandler: Win AppsFlyer ==========
    appsflyer_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(haf.appsflyer_menu, pattern='^win_appsflyer$'),
        ],
        states={
            haf.AF_GAME: [
                CallbackQueryHandler(haf.af_game_selected, pattern=r'^af_game_\w+$'),
                CallbackQueryHandler(haf.af_cancel, pattern='^af_cancel$'),
            ],
            haf.AF_IDFA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, haf.af_receive_idfa),
                CallbackQueryHandler(haf.af_cancel, pattern='^af_cancel$'),
            ],
            haf.AF_IDFV: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, haf.af_receive_idfv),
                CallbackQueryHandler(haf.af_cancel, pattern='^af_cancel$'),
            ],
            haf.AF_IOS_VER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, haf.af_receive_ios_ver),
                CallbackQueryHandler(haf.af_cancel, pattern='^af_cancel$'),
            ],
            haf.AF_AF_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, haf.af_receive_af_id),
                CallbackQueryHandler(haf.af_cancel, pattern='^af_cancel$'),
            ],
            haf.AF_CONFIRM: [
                CallbackQueryHandler(haf.af_confirm_send, pattern='^af_confirm_send$'),
                CallbackQueryHandler(haf.af_cancel, pattern='^af_cancel$'),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', haf.af_cancel_text),
            CommandHandler('start', hu.persistent_start),
            MessageHandler(filters.Regex("ابدأ|Start"), hu.persistent_start),
        ],
        per_user=True,
        per_chat=True,
        per_message=False,
    )
    app.add_handler(appsflyer_conv)

    # ========== Callbacks الرصيد ==========
    app.add_handler(CallbackQueryHandler(hc.show_balance,         pattern='^show_balance$'))
    app.add_handler(CallbackQueryHandler(hu.confirm_buy,          pattern=r'^confirm_buy_\d+$'))
    app.add_handler(CallbackQueryHandler(hc.admin_confirm_charge, pattern=r'^chg_confirm_\d+$'))
    app.add_handler(CallbackQueryHandler(hc.admin_reject_charge,  pattern=r'^chg_reject_\d+$'))

    # ========== Callbacks المستخدم ==========
    app.add_handler(CallbackQueryHandler(hu.show_products,       pattern='^products$'))
    app.add_handler(CallbackQueryHandler(hu.show_platform_categories, pattern=r'^platform_(iOS|Android)$'))
    app.add_handler(CallbackQueryHandler(hu.show_category,       pattern=r'^cat_'))
    app.add_handler(CallbackQueryHandler(hu.show_product_detail, pattern=r'^prod_\d+$'))
    app.add_handler(CallbackQueryHandler(hu.initiate_buy,        pattern=r'^buy_\d+_\w+$'))
    app.add_handler(CallbackQueryHandler(hu.toggle_lang,         pattern='^toggle_lang$'))
    app.add_handler(CallbackQueryHandler(hu.emails_menu,         pattern='^emails_menu$'))
    app.add_handler(CallbackQueryHandler(hu.icloud_menu,          pattern='^icloud_menu$'))
    app.add_handler(CallbackQueryHandler(hu.proxy_menu_simple,     pattern='^proxy_menu$'))
    app.add_handler(CallbackQueryHandler(hu.payment_info,        pattern='^payment_info$'))
    app.add_handler(CallbackQueryHandler(hu.contact,             pattern='^contact$'))
    app.add_handler(CallbackQueryHandler(hu.back_main,           pattern='^back_main$'))

    # ========== Callbacks AppsFlyer Admin ==========
    app.add_handler(CallbackQueryHandler(ha.appsflyer_accept, pattern=r'^af_accept_\d+$'))
    app.add_handler(CallbackQueryHandler(ha.appsflyer_reject, pattern=r'^af_reject_\d+$'))

    # ========== Callbacks الأدمن ==========
    app.add_handler(CallbackQueryHandler(ha.admin_panel,          pattern='^adm_back$'))
    app.add_handler(CallbackQueryHandler(ha.admin_stats,          pattern='^adm_stats$'))
    app.add_handler(CallbackQueryHandler(ha.show_pending_orders,  pattern='^adm_orders$'))
    app.add_handler(CallbackQueryHandler(ha.confirm_order,        pattern=r'^adm_confirm_\d+$'))
    app.add_handler(CallbackQueryHandler(ha.reject_order,         pattern=r'^adm_reject_\d+$'))
    app.add_handler(CallbackQueryHandler(ha.admin_show_products,  pattern='^adm_products$'))
    app.add_handler(CallbackQueryHandler(ha.admin_product_detail, pattern=r'^adm_prod_detail_\d+$'))
    app.add_handler(CallbackQueryHandler(ha.delete_product,       pattern=r'^adm_del_\d+$'))

    # ========== Callbacks البروكسي ==========
    app.add_handler(CallbackQueryHandler(hp.proxy_admin_done,   pattern=r'^prx_done_\d+'))
    app.add_handler(CallbackQueryHandler(hp.proxy_admin_reject, pattern=r'^prx_reject_\d+'))

    # ========== القائمة الثابتة ==========
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        hu.handle_persistent_menu
    ))

    # ========== Broadcast Job ==========
    # FIX: يستخدم claim_broadcast_for_job() لمنع الإرسال المزدوج مع الداشبورد
    async def send_pending_broadcasts(context):
        broadcasts = db.get_pending_broadcasts()
        for bc in broadcasts:
            # FIX: atomic claim — لو فشل يعني الداشبورد سبق وأرسلها
            if not db.claim_broadcast_for_job(bc["id"]):
                logger.info(f"Broadcast #{bc['id']} already sent by dashboard, skipping")
                continue

            users = db.get_all_users()
            sent = 0
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user["id"],
                        text=bc["message"],
                        parse_mode="Markdown"
                    )
                    sent += 1
                except Exception:
                    pass
            db.mark_broadcast_sent(bc["id"], sent)
            logger.info(f"📢 Broadcast #{bc['id']} sent to {sent} users")

    app.job_queue.run_repeating(send_pending_broadcasts, interval=30, first=10)

    # ========== Auto-Register ==========
    async def auto_register(update: Update, context):
        user = update.effective_user
        if user and not user.is_bot:
            db.upsert_user(user.id, user.username or "", user.full_name or "")

    app.add_handler(
        MessageHandler(filters.ALL, auto_register),
        group=-1
    )
    app.add_handler(
        CallbackQueryHandler(auto_register),
        group=-1
    )

    logger.info(f"🚀 البوت شغال! Admin ID: {ADMIN_ID}")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        read_timeout=10,
        write_timeout=10,
        connect_timeout=10,
        pool_timeout=5,
        drop_pending_updates=True,
    )

if __name__ == '__main__':
    main()
