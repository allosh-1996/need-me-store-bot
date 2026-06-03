from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from repositories.users import get_user_language
from repositories.products import get_active_products, get_stock_count
from services.orders import OrderService
from domain.errors import InsufficientBalanceError, OutOfStockError, NotFoundError
from bot.render.keyboards import back_home
from bot.render.strings import t
from bot.render.formatters import safe, code

service = OrderService()


async def open_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query.from_user.id)
    products = get_active_products()
    if not products:
        await query.edit_message_text(
            "لا يوجد منتجات متاحة حالياً" if lang == "ar" else "No products available",
            reply_markup=back_home(lang),
        )
        return
    buttons = []
    for row in products:
        product_id, name, _desc, price_usd, _cat, _platform = row
        stock = get_stock_count(product_id)
        status = "🟢" if stock > 0 else "🔴"
        buttons.append([
            InlineKeyboardButton(
                f"{status} {name} — ${price_usd}",
                callback_data=f"catalog:product:{product_id}",
            )
        ])
    buttons.append([InlineKeyboardButton(t("back", lang), callback_data="home")])
    await query.edit_message_text(
        "📦 اختر المنتج:" if lang == "ar" else "📦 Choose a product:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query.from_user.id)
    product_id = int(query.data.split(":")[-1])
    from repositories.products import get_product
    product = get_product(product_id)
    if not product:
        await query.edit_message_text(t("out_of_stock", lang), reply_markup=back_home(lang))
        return
    stock = get_stock_count(product_id)
    stock_label = "🟢 متوفر" if stock > 0 else "🔴 غير متوفر"
    if lang == "en":
        stock_label = "🟢 In Stock" if stock > 0 else "🔴 Out of Stock"
    text = (
        f"<b>{safe(product[1])}</b>\n\n"
        f"{safe(product[2]) or ''}\n\n"
        f"💵 ${product[3]}\n"
        f"{stock_label}"
    )
    buttons = []
    if stock > 0:
        buttons.append([InlineKeyboardButton(t("buy", lang), callback_data=f"catalog:buy:{product_id}")])
    buttons.append([InlineKeyboardButton(t("back", lang), callback_data="catalog:open")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = get_user_language(query.from_user.id)
    product_id = int(query.data.split(":")[-1])
    try:
        result = service.buy_instant_product(query.from_user.id, product_id)
    except InsufficientBalanceError:
        await query.edit_message_text(t("insufficient_balance", lang), reply_markup=back_home(lang))
        return
    except OutOfStockError:
        await query.edit_message_text(t("out_of_stock", lang), reply_markup=back_home(lang))
        return
    except NotFoundError:
        await query.edit_message_text(t("out_of_stock", lang), reply_markup=back_home(lang))
        return

    await query.edit_message_text(
        f"{t('purchase_success', lang)}\n\n"
        f"🔖 #{result['order_id']}\n"
        f"📦 {safe(result['product_name'])}\n"
        f"💵 ${result['amount_usd']:.2f}\n"
        f"💰 Balance: ${result['balance_after']:.2f}",
        parse_mode="HTML",
        reply_markup=back_home(lang),
    )
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=(
            f"{t('product_details', lang)}\n\n"
            f"{'—' * 20}\n\n"
            f"{code(result['payload'])}\n\n"
            f"{'—' * 20}\n\n"
            f"{t('save_info', lang)}"
        ),
        parse_mode="HTML",
    )
