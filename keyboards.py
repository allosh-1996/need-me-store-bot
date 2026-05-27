from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# ============ Main Menu ============
def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("🛍️ المنتجات  |  Shop", callback_data="products"),
            InlineKeyboardButton("🛒 طلباتي  |  Orders", callback_data="my_orders"),
        ],
        [
            InlineKeyboardButton("💰 رصيدي  |  Balance", callback_data="show_balance"),
            InlineKeyboardButton("🔒 بروكسي  |  Proxy", callback_data="proxy_menu"),
        ],
        [
            InlineKeyboardButton("📞 تواصل  |  Contact", callback_data="contact"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Categories Menu ============
def categories_menu(categories):
    keyboard = []
    icons = ["🍎", "📧", "📋", "📚", "🎮", "💎", "🔑", "🌐"]
    row = []
    for i, cat in enumerate(categories):
        icon = icons[i % len(icons)]
        row.append(InlineKeyboardButton(f"{icon} {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ============ Products Menu ============
def products_menu(products):
    keyboard = []
    for p in products:
        stock_icon = "✅" if p['stock'] else "🔴"
        price_text = f"${p['price_usd']}" if p['price_usd'] else ""
        keyboard.append([InlineKeyboardButton(
            f"{stock_icon}  {p['name']}  —  {price_text}",
            callback_data=f"prod_{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="products")])
    return InlineKeyboardMarkup(keyboard)

# ============ Product Detail Menu ============
def product_detail_menu(product_id, has_stock=True):
    keyboard = []
    if has_stock:
        keyboard.append([
            InlineKeyboardButton("🛒 شراء الآن  |  Buy Now", callback_data=f"buy_{product_id}"),
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="products")])
    return InlineKeyboardMarkup(keyboard)

# ============ Payment Method Menu ============
def payment_method_menu(product_id, currency):
    keyboard = [
        [InlineKeyboardButton("🪙 USDT  (BEP-20)", callback_data=f"pay_{product_id}_{currency}_usdt")],
        [InlineKeyboardButton("📱 Syriatel Cash  |  سيريتيل كاش", callback_data=f"pay_{product_id}_{currency}_syriatel")],
        [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data=f"prod_{product_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Admin Main Menu ============
def admin_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📦 Products  |  المنتجات", callback_data="adm_products"),
            InlineKeyboardButton("📋 Orders  |  الطلبات", callback_data="adm_orders"),
        ],
        [
            InlineKeyboardButton("➕ Add Product  |  إضافة", callback_data="adm_add_product"),
            InlineKeyboardButton("📊 Stats  |  إحصائيات", callback_data="adm_stats"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast  |  رسالة جماعية", callback_data="adm_broadcast"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Order Confirm Menu ============
def order_confirm_menu(order_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm & Send  |  تأكيد", callback_data=f"adm_confirm_{order_id}"),
            InlineKeyboardButton("❌ Reject  |  رفض", callback_data=f"adm_reject_{order_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Admin Product Menu ============
def admin_product_menu(product_id):
    keyboard = [
        [
            InlineKeyboardButton("✏️ Update Stock  |  تحديث المخزون", callback_data=f"adm_stock_{product_id}"),
            InlineKeyboardButton("🗑️ Delete  |  حذف", callback_data=f"adm_del_{product_id}"),
        ],
        [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="adm_products")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ Persistent Bottom Menu ============
def persistent_menu():
    keyboard = [
        [
            KeyboardButton("🚀 Start  |  ابدأ"),
            KeyboardButton("💬 Support"),
            KeyboardButton("ℹ️ About"),
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder="🔍 اكتب أو اختر من القائمة..."
    )
