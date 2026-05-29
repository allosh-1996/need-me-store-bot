from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from lang import t


def main_menu(lang="ar"):
    keyboard = [
        [
            InlineKeyboardButton(t("btn_icloud", lang),   callback_data="icloud_menu"),
            InlineKeyboardButton(t("btn_emails", lang),   callback_data="emails_menu"),
        ],
        [
            InlineKeyboardButton(t("btn_balance", lang),  callback_data="show_balance"),
            InlineKeyboardButton(t("btn_proxy", lang),    callback_data="proxy_menu"),
        ],
        [
            InlineKeyboardButton(t("btn_surveys", lang),  callback_data="surveys_menu"),
            InlineKeyboardButton(t("btn_appsflyer", lang),callback_data="win_appsflyer"),
        ],
        [
            InlineKeyboardButton(t("btn_contact", lang),  callback_data="contact"),
            InlineKeyboardButton(t("btn_lang", lang),     callback_data="toggle_lang"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def categories_menu(categories, back_cb="products", lang="ar"):
    keyboard = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data=back_cb)])
    return InlineKeyboardMarkup(keyboard)


def products_menu(products, lang="ar", back_cb="products"):
    keyboard = []
    for p in products:
        stock_count = len([l for l in (p['stock'] or '').strip().splitlines() if l.strip()])
        status = t("in_stock", lang) if stock_count > 0 else t("out_of_stock", lang)
        price_text = f"${p['price_usd']}" if p['price_usd'] else ""
        keyboard.append([InlineKeyboardButton(
            f"{p['name']}  —  {price_text}  ({status})",
            callback_data=f"prod_{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data=back_cb)])
    return InlineKeyboardMarkup(keyboard)


def product_detail_menu(product_id, has_stock=True, lang="ar", back_cb="products"):
    keyboard = []
    if has_stock:
        keyboard.append([
            InlineKeyboardButton(t("buy_from_balance", lang), callback_data=f"buy_{product_id}_USD"),
        ])
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data=back_cb)])
    return InlineKeyboardMarkup(keyboard)


def admin_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("المنتجات",    callback_data="adm_products"),
            InlineKeyboardButton("الطلبات",     callback_data="adm_orders"),
        ],
        [
            InlineKeyboardButton("اضافة منتج", callback_data="adm_add_product"),
            InlineKeyboardButton("الاحصائيات", callback_data="adm_stats"),
        ],
        [
            InlineKeyboardButton("رسالة جماعية", callback_data="adm_broadcast"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def order_confirm_menu(order_id):
    keyboard = [[
        InlineKeyboardButton("تاكيد وارسال", callback_data=f"adm_confirm_{order_id}"),
        InlineKeyboardButton("رفض",           callback_data=f"adm_reject_{order_id}"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def admin_product_menu(product_id):
    keyboard = [
        [
            InlineKeyboardButton("تحديث المخزون", callback_data=f"adm_stock_{product_id}"),
            InlineKeyboardButton("حذف",            callback_data=f"adm_del_{product_id}"),
        ],
        [InlineKeyboardButton("رجوع", callback_data="adm_products")],
    ]
    return InlineKeyboardMarkup(keyboard)


def persistent_menu(lang="ar"):
    return ReplyKeyboardRemove()
