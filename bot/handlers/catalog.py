from __future__ import annotations

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from repositories.users import ensure_user, get_user_language
from repositories.products import get_active_products_with_stock, get_product_with_stock
from services.orders import OrderService
from domain.errors import InsufficientBalanceError, OutOfStockError, NotFoundError
from bot.render.keyboards import back_home
from bot.render.strings import t
from bot.render.formatters import safe, code

logger = logging.getLogger(__name__)
service = OrderService()

CATEGORY_LABELS = {
    "icloud":   "📱 iCloud",
    "emails":   "📧 ايميلات",
    "proxy":    "🌐 بروكسي",
    "surveys":  "📊 Surveys",
}

SEP = "—" * 20


async def open_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    ensure_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_language(user.id)

    parts = query.data.split(":")
    category = parts[2] if len(parts) > 2 else None

    # Proxy — contact support only
    if category == "proxy":
        proxy_msg = (
            "🌐 <b>قسم البروكسي</b>\n\n"
            "━━━━━━━━━━━━━━━\n"
            "هذا القسم يتطلب طلباً مخصصاً.\n\n"
            "📩 للطلب والاستفسار تواصل مع الدعم مباشرة:\n\n"
            "👤 <b>@Allosh96ha</b>\n\n"
            "━━━━━━━━━━━━━━━\n"
            "⚡️ سيتم الرد عليك في أقرب وقت ممكن."
        )
        await query.edit_message_text(
            proxy_msg, parse_mode="HTML", reply_markup=back_home(lang),
        )
        return

    cat_filter = category if (category and category in CATEGORY_LABELS) else None
    title = CATEGORY_LABELS.get(cat_filter, "📦 المنتجات" if lang == "ar" else "📦 Products")

    # Single query: products + stock count combined
    products = get_active_products_with_stock(cat_filter)

    if not products:
        await query.edit_message_text(
            "لا يوجد منتجات متاحة حالياً" if lang == "ar" else "No products available",
            reply_markup=back_home(lang),
        )
        return

    buttons = []
    for row in products:
        product_id, name, _desc, price_usd, _cat, _platform, stock_count = row
        status = "🟢" if stock_count > 0 else "🔴"
        buttons.append([
            InlineKeyboardButton(
                f"{status} {name} — ${price_usd}",
                callback_data=f"catalog:product:{product_id}",
            )
        ])
    buttons.append([InlineKeyboardButton(t("back", lang), callback_data="home")])

    await query.edit_message_text(
        f"{title}:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    ensure_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_language(user.id)
    product_id = int(query.data.split(":")[-1])

    # Single query: product + stock count
    product = get_product_with_stock(product_id)
    if not product:
        await query.edit_message_text(t("out_of_stock", lang), reply_markup=back_home(lang))
        return

    _id, name, description, price_usd, _cat, _platform, active, stock_count = product
    if not active:
        await query.edit_message_text(t("out_of_stock", lang), reply_markup=back_home(lang))
        return

    stock_label = (
        ("🟢 متوفر" if stock_count > 0 else "🔴 غير متوفر") if lang == "ar"
        else ("🟢 In Stock" if stock_count > 0 else "🔴 Out of Stock")
    )
    text = (
        f"<b>{safe(name)}</b>\n\n"
        f"{safe(description) or ''}\n\n"
        f"💵 ${price_usd}\n"
        f"{stock_label}"
    )
    buttons = []
    if stock_count > 0:
        buttons.append([InlineKeyboardButton(t("buy", lang), callback_data=f"catalog:buy:{product_id}")])
    buttons.append([InlineKeyboardButton(t("back", lang), callback_data="home")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    ensure_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_language(user.id)
    product_id = int(query.data.split(":")[-1])
    try:
        result = service.buy_instant_product(user.id, product_id)
    except InsufficientBalanceError:
        await query.edit_message_text(t("insufficient_balance", lang), reply_markup=back_home(lang))
        return
    except OutOfStockError:
        await query.edit_message_text(t("out_of_stock", lang), reply_markup=back_home(lang))
        return
    except NotFoundError:
        await query.edit_message_text(t("out_of_stock", lang), reply_markup=back_home(lang))
        return

    payload_sent = False
    try:
        msg_text = (
            t("product_details", lang) + "\n\n" + SEP + "\n\n"
            + code(result["payload"]) + "\n\n" + SEP + "\n\n"
            + t("save_info", lang)
        )
        await context.bot.send_message(
            chat_id=user.id, text=msg_text, parse_mode="HTML",
        )
        payload_sent = True
    except Exception:
        logger.error("Failed to send product payload to user %s for order %s", user.id, result["order_id"])

    suffix = "\n\n⚠️ تعذّر إرسال المنتج، تواصل مع الدعم" if not payload_sent else ""
    await query.edit_message_text(
        f"{t('purchase_success', lang)}\n\n"
        f"🔖 #{result['order_id']}\n"
        f"📦 {safe(result['product_name'])}\n"
        f"💵 ${result['amount_usd']:.2f}\n"
        f"💰 Balance: ${result['balance_after']:.2f}"
        + suffix,
        parse_mode="HTML",
        reply_markup=back_home(lang),
    )
