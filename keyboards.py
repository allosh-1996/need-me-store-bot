from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# ============ كيبورد المستخدم الرئيسي ============
def main_menu():
    keyboard = [
        [InlineKeyboardButton("🛍️ المنتجات", callback_data="products"),
         InlineKeyboardButton("🛒 طلباتي", callback_data="my_orders")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="show_balance"),
         InlineKeyboardButton("💳 شحن رصيد", callback_data="charge_start")],
        [InlineKeyboardButton("📞 تواصل معنا", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ كيبورد الفئات ============
def categories_menu(categories):
    keyboard = []
    row = []
    for i, cat in enumerate(categories):
        row.append(InlineKeyboardButton(f"📦 {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ============ كيبورد المنتجات ============
def products_menu(products):
    keyboard = []
    for p in products:
        price_text = f"${p['price_usd']}" if p['price_usd'] else ""
        keyboard.append([InlineKeyboardButton(
            f"{'✅' if p['stock'] else '❌'} {p['name']} — {price_text}",
            callback_data=f"prod_{p['id']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ============ كيبورد تفاصيل المنتج ============
def product_detail_menu(product_id, has_stock=True):
    keyboard = []
    if has_stock:
        keyboard.append([
            InlineKeyboardButton("🛒 شراء", callback_data=f"buy_{product_id}"),
        ])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="products")])
    return InlineKeyboardMarkup(keyboard)

# ============ كيبورد اختيار طريقة الدفع ============
def payment_method_menu(product_id, currency):
    keyboard = [
        [InlineKeyboardButton("💰 USDT (BEP-20)", callback_data=f"pay_{product_id}_{currency}_usdt")],
        [InlineKeyboardButton("📱 Syriatel Cash", callback_data=f"pay_{product_id}_{currency}_syriatel")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"prod_{product_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ كيبورد الأدمن الرئيسي ============
def admin_main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 المنتجات", callback_data="adm_products"),
         InlineKeyboardButton("📋 الطلبات المعلقة", callback_data="adm_orders")],
        [InlineKeyboardButton("➕ إضافة منتج", callback_data="adm_add_product"),
         InlineKeyboardButton("📊 الإحصائيات", callback_data="adm_stats")],
        [InlineKeyboardButton("📢 رسالة جماعية", callback_data="adm_broadcast")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ كيبورد تأكيد الطلب ============
def order_confirm_menu(order_id):
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد وإرسال المنتج", callback_data=f"adm_confirm_{order_id}"),
         InlineKeyboardButton("❌ رفض الطلب", callback_data=f"adm_reject_{order_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ كيبورد إدارة منتج ============
def admin_product_menu(product_id):
    keyboard = [
        [InlineKeyboardButton("✏️ تعديل المخزون", callback_data=f"adm_stock_{product_id}"),
         InlineKeyboardButton("🗑️ حذف المنتج", callback_data=f"adm_del_{product_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="adm_products")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ القائمة الثابتة (تظهر دايماً تحت المحادثة) ============
from telegram import ReplyKeyboardMarkup, KeyboardButton

def persistent_menu():
    keyboard = [
        [
            KeyboardButton("🚀 ابدأ"),
            KeyboardButton("💬 Support"),
            KeyboardButton("ℹ️ About"),
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder="اختر أو اكتب رسالة..."
    )
