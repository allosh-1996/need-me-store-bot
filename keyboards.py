from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from lang import t

# ============ Main Menu ============
def main_menu(lang="ar"):
    keyboard = [
        [
            InlineKeyboardButton(t("btn_products", lang), callback_data="products"),
            InlineKeyboardButton(t("btn_emails", lang), callback_data="emails_menu"),
        ],
        [
            InlineKeyboardButton(t("btn_balance", lang), callback_data="show_balance"),
            InlineKeyboardButton(t("btn_proxy", lang), callback_data="proxy_menu"),
        ],
        [
            InlineKeyboardButton(t("btn_appsflyer", lang), callback_data="win_appsflyer"),
        ],
        [
            InlineKeyboardButton(t("btn_contact", lang), callback_data="contact"),
            InlineKeyboardButton(t("btn_lang", lang), callback_data="toggle_lang"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Categories Menu ============
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

# ============ Products Menu ============
def products_menu(products, lang="ar"):
    keyboard = []
    for p in products:
        status = t("in_stock", lang) if p['stock'] else t("out_of_stock", lang)
        price_text = f"${p['price_usd']}" if p['price_usd'] else ""
        keyboard.append([InlineKeyboardButton(
            f"{p['name']}  —  {price_text}  ({status})",
            callback_data=f"prod_{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="products")])
    return InlineKeyboardMarkup(keyboard)

# ============ Product Detail Menu ============
def product_detail_menu(product_id, has_stock=True, lang="ar"):
    keyboard = []
    if has_stock:
        keyboard.append([
            InlineKeyboardButton(t("buy_usd", lang), callback_data=f"buy_{product_id}_USD"),
            InlineKeyboardButton(t("buy_syp", lang), callback_data=f"buy_{product_id}_SYP"),
        ])
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="products")])
    return InlineKeyboardMarkup(keyboard)

# ============ Payment Method Menu ============
def payment_method_menu(product_id, currency, lang="ar"):
    keyboard = [
        [InlineKeyboardButton("USDT  (BEP-20)", callback_data=f"pay_{product_id}_{currency}_usdt")],
        [InlineKeyboardButton("Syriatel Cash", callback_data=f"pay_{product_id}_{currency}_syriatel")],
        [InlineKeyboardButton(t("buy_from_balance", lang), callback_data=f"confirm_buy_{product_id}")],
        [InlineKeyboardButton(t("back", lang), callback_data=f"prod_{product_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Admin Main Menu ============
def admin_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("المنتجات", callback_data="adm_products"),
            InlineKeyboardButton("الطلبات", callback_data="adm_orders"),
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

# ============ Order Confirm Menu ============
def order_confirm_menu(order_id):
    keyboard = [
        [
            InlineKeyboardButton("تاكيد وارسال", callback_data=f"adm_confirm_{order_id}"),
            InlineKeyboardButton("رفض", callback_data=f"adm_reject_{order_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Admin Product Menu ============
def admin_product_menu(product_id):
    keyboard = [
        [
            InlineKeyboardButton("تحديث المخزون", callback_data=f"adm_stock_{product_id}"),
            InlineKeyboardButton("حذف", callback_data=f"adm_del_{product_id}"),
        ],
        [InlineKeyboardButton("رجوع", callback_data="adm_products")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Persistent Bottom Menu ============
def persistent_menu(lang="ar"):
    if lang == "en":
        keys = [["Start", "Support", "About"]]
    else:
        keys = [["ابدأ", "دعم", "عن المتجر"]]
    return ReplyKeyboardMarkup(
        keys,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
    )
