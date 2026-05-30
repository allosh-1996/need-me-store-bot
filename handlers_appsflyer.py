import re
"""
handlers_appsflyer.py — NexVault Bot
نظام طلبات Win AppsFlyer الكامل
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
from config import ADMIN_ID, APPSFLYER_GAMES
from lang import get_user_lang
from lang import t


UUID_PATTERN = re.compile(
    r'^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$'
)

# ═══ حالات المحادثة ═══
AF_GAME, AF_IDFA, AF_IDFV, AF_IOS_VER, AF_AF_ID, AF_CONFIRM = range(40, 46)


async def appsflyer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context, update.effective_user.id)

    keyboard = []
    for game_key, game_data in APPSFLYER_GAMES.items():
        keyboard.append([InlineKeyboardButton(
            f"{game_data['name']} — ${game_data['price_usd']:.0f}",
            callback_data=f"af_game_{game_key}"
        )])
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="back_main")])

    text = (
        "🎮 *Win AppsFlyer*\n\n"
        "اختر اللعبة اللي بدك تطلب لها الخدمة:\n"
        "_Choose the game you want the service for:_"
    )
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return AF_GAME


async def af_game_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_key = query.data.replace("af_game_", "")
    if game_key not in APPSFLYER_GAMES:
        await query.answer("❌ لعبة غير موجودة", show_alert=True)
        return AF_GAME

    game_data = APPSFLYER_GAMES[game_key]
    context.user_data["af_game_key"] = game_key
    context.user_data["af_game_name"] = game_data["name"]
    context.user_data["af_price"] = game_data["price_usd"]

    balance = db.get_balance(update.effective_user.id)
    if balance < game_data["price_usd"]:
        await query.edit_message_text(
            f"❌ *رصيدك غير كافٍ*\n\n"
            f"💰 رصيدك الحالي: `${balance:.2f}`\n"
            f"💵 سعر الخدمة: `${game_data['price_usd']:.0f}`\n\n"
            f"_اشحن رصيدك أولاً ثم حاول مجدداً_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 شحن الرصيد", callback_data="charge_start")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="win_appsflyer")],
            ])
        )
        return ConversationHandler.END

    await query.edit_message_text(
        f"🎮 *{game_data['name']}* — `${game_data['price_usd']:.0f}`\n"
        f"\n—————————————————\n\n"
        f"📋 *الخطوة 1 من 4*\n\n"
        f"أرسل لي الـ *IDFA* الخاص بجهازك:\n\n"
        f"_مثال:_ `6D92078A-8246-4BA4-AE75-79F1B2D67052`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="af_cancel")]
        ])
    )
    return AF_IDFA


async def af_receive_idfa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idfa = update.message.text.strip()
    if not UUID_PATTERN.match(idfa):
        await update.message.reply_text(
            "❌ *IDFA غير صحيح*\n\n"
            "_يجب أن يكون بصيغة UUID مثل:_\n"
            "`6D92078A-8246-4BA4-AE75-79F1B2D67052`",
            parse_mode=ParseMode.MARKDOWN
        )
        return AF_IDFA
    context.user_data["af_idfa"] = idfa
    await update.message.reply_text(
        f"✅ *IDFA محفوظ*\n\n"
        f"\n—————————————————\n\n"
        f"📋 *الخطوة 2 من 4*\n\n"
        f"أرسل لي الـ *IDFV* الخاص بجهازك:\n\n"
        f"_مثال:_ `599F9C00-92DC-4B5C-9464-7971F01F8370`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="af_cancel")]
        ])
    )
    return AF_IDFV


async def af_receive_idfv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idfv = update.message.text.strip()
    if not UUID_PATTERN.match(idfv):
        await update.message.reply_text(
            "❌ *IDFV غير صحيح*\n\n"
            "_يجب أن يكون بصيغة UUID مثل:_\n"
            "`599F9C00-92DC-4B5C-9464-7971F01F8370`",
            parse_mode=ParseMode.MARKDOWN
        )
        return AF_IDFV
    context.user_data["af_idfv"] = idfv
    await update.message.reply_text(
        f"✅ *IDFV محفوظ*\n\n"
        f"\n—————————————————\n\n"
        f"📋 *الخطوة 3 من 4*\n\n"
        f"أرسل لي *إصدار iOS* الخاص بجهازك:\n\n"
        f"_مثال:_ `17.4.1`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="af_cancel")]
        ])
    )
    return AF_IOS_VER


async def af_receive_ios_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["af_ios_ver"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ *iOS Version محفوظ*\n\n"
        f"\n—————————————————\n\n"
        f"📋 *الخطوة 4 من 4*\n\n"
        f"أرسل لي الـ *AppsFlyer ID* الخاص بجهازك:\n\n"
        f"_مثال:_ `1234567890123-1234567890123456`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="af_cancel")]
        ])
    )
    return AF_AF_ID


async def af_receive_af_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["af_af_id"] = update.message.text.strip()
    ud = context.user_data
    balance = db.get_balance(update.effective_user.id)

    summary = (
        f"🎮 *تأكيد الطلب | Order Summary*\n"
        f"\n—————————————————\n\n"
        f"🕹 *اللعبة:* {ud['af_game_name']}\n"
        f"💵 *السعر:* `${ud['af_price']:.0f}`\n"
        f"💰 *رصيدك:* `${balance:.2f}`\n"
        f"\n—————————————————\n\n"
        f"📱 *IDFA:* `{ud['af_idfa']}`\n"
        f"📱 *IDFV:* `{ud['af_idfv']}`\n"
        f"📱 *iOS Version:* `{ud['af_ios_ver']}`\n"
        f"📱 *AppsFlyer ID:* `{ud['af_af_id']}`\n"
        f"\n—————————————————\n\n"
        f"_تأكد من المعلومات قبل الإرسال_"
    )
    await update.message.reply_text(
        summary,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ إرسال الطلب", callback_data="af_confirm_send")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="af_cancel")],
        ])
    )
    return AF_CONFIRM


async def af_confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    ud = context.user_data

    price = ud.get("af_price", 0)
    try:
        db.deduct_balance_atomic(user.id, price)
    except ValueError as e:
        err = str(e)
        if err.startswith("insufficient_balance:"):
            current_balance = float(err.split(":")[1])
            await query.edit_message_text(
                f"❌ *رصيدك غير كافٍ*\n\n"
                f"💰 رصيدك: `${current_balance:.2f}`\n"
                f"💵 السعر: `${price:.0f}`\n\n"
                f"_اشحن رصيدك وحاول مجدداً_",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("❌ خطأ في المعالجة، حاول مجدداً", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    order_id = db.create_appsflyer_order(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        game_key=ud["af_game_key"],
        game_name=ud["af_game_name"],
        price_usd=ud["af_price"],
        idfa=ud["af_idfa"],
        idfv=ud["af_idfv"],
        ios_version=ud["af_ios_ver"],
        appsflyer_id=ud["af_af_id"],
    )

    new_balance = db.get_balance(user.id)

    await query.edit_message_text(
        f"✅ *تم إرسال طلبك بنجاح!*\n\n"
        f"🎮 *اللعبة:* {ud['af_game_name']}\n"
        f"🔢 *رقم الطلب:* `#{order_id}`\n"
        f"💵 *المبلغ المخصوم:* `${ud['af_price']:.0f}`\n"
        f"💰 *رصيدك الحالي:* `${new_balance:.2f}`\n\n"
        f"\n—————————————————\n\n"
        f"📩 للمتابعة تواصل مع الأدمن:\n"
        f"👤 @Allosh96ha\n"
        f"\n—————————————————\n",
        parse_mode=ParseMode.MARKDOWN
    )

    admin_text = (
        f"🔔 *طلب AppsFlyer جديد!*\n"
        f"\n—————————————————\n\n"
        f"🔢 *رقم الطلب:* `#{order_id}`\n"
        f"👤 *المستخدم:* {user.full_name} (@{user.username or 'N/A'})\n"
        f"🆔 *User ID:* `{user.id}`\n"
        f"🕹 *اللعبة:* {ud['af_game_name']}\n"
        f"💵 *السعر:* `${ud['af_price']:.0f}` ✅ *خُصم*\n"
        f"\n—————————————————\n\n"
        f"📱 *IDFA:* `{ud['af_idfa']}`\n"
        f"📱 *IDFV:* `{ud['af_idfv']}`\n"
        f"📱 *iOS Ver:* `{ud['af_ios_ver']}`\n"
        f"📱 *AF ID:* `{ud['af_af_id']}`"
    )

    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"af_accept_{order_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"af_reject_{order_id}"),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_kb
        )
    except Exception:
        pass

    for key in ["af_game_key", "af_game_name", "af_price", "af_idfa", "af_idfv", "af_ios_ver", "af_af_id"]:
        context.user_data.pop(key, None)

    return ConversationHandler.END


async def af_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "❌ *تم إلغاء الطلب*\n_Order cancelled._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]
            ])
        )
    return ConversationHandler.END


async def af_cancel_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ *تم إلغاء الطلب*\n_Order cancelled._",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END
