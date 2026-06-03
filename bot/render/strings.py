STRINGS: dict[str, dict[str, str]] = {
    "welcome": {
        "ar": "أهلاً بك في <b>NexVault</b> 🛍️\nاختر من القائمة أدناه.",
        "en": "Welcome to <b>NexVault</b> 🛍️\nChoose from the menu below.",
    },
    "back":        {"ar": "رجوع ◀️",      "en": "Back ◀️"},
    "home":        {"ar": "الرئيسية 🏠",  "en": "Home 🏠"},
    "balance":     {"ar": "رصيدي 💰",     "en": "My Balance 💰"},
    "buy":         {"ar": "✅ شراء",       "en": "✅ Buy"},
    "contact":     {"ar": "تواصل 💬",     "en": "Contact 💬"},
    "language":    {"ar": "English 🌐",   "en": "العربية 🌐"},
    "products":    {"ar": "المنتجات 📦",  "en": "Products 📦"},
    "top_up":      {"ar": "شحن الرصيد 💳","en": "Top Up 💳"},
    "appsflyer":   {"ar": "🟢 Win AppsFlyer 🟢", "en": "🟢 Win AppsFlyer 🟢"},
    "admin_only":  {"ar": "للأدمن فقط 🔐","en": "Admins only 🔐"},
    "admin_panel": {"ar": "لوحة الأدمن 🔐","en": "Admin Panel 🔐"},
    "insufficient_balance": {
        "ar": "❌ رصيدك غير كافٍ",
        "en": "❌ Insufficient balance",
    },
    "out_of_stock": {
        "ar": "❌ غير متوفر حالياً",
        "en": "❌ Out of stock",
    },
    "purchase_success": {
        "ar": "✅ تم الشراء بنجاح!",
        "en": "✅ Purchase completed!",
    },
    "product_details": {
        "ar": "🎁 تفاصيل المنتج",
        "en": "🎁 Product Details",
    },
    "save_info": {
        "ar": "احفظ هذه المعلومات بأمان 🔒",
        "en": "Keep this information safe 🔒",
    },
    "charge_methods": {
        "ar": "اختر طريقة الشحن 💳",
        "en": "Choose top-up method 💳",
    },
    "send_amount_usdt": {
        "ar": "أرسل المبلغ بالدولار (USDT):",
        "en": "Send amount in USD (USDT):",
    },
    "send_amount_syp": {
        "ar": "أرسل المبلغ بالليرة السورية:",
        "en": "Send amount in SYP:",
    },
    "send_tx_hash": {
        "ar": "أرسل TX Hash بعد التحويل:",
        "en": "Send TX Hash after transfer:",
    },
    "send_proof": {
        "ar": "أرسل صورة الإيصال:",
        "en": "Send receipt photo:",
    },
    "charge_submitted": {
        "ar": "✅ تم إرسال طلب الشحن",
        "en": "✅ Top-up request submitted",
    },
    "charge_pending": {
        "ar": "سيتم مراجعة طلبك وإضافة الرصيد قريباً.",
        "en": "Your request will be reviewed and balance added shortly.",
    },
    "duplicate_proof": {
        "ar": "⚠️ هذا الإيصال أو TX Hash مستخدم مسبقاً.",
        "en": "⚠️ This proof or TX Hash was already used.",
    },
    "invalid_amount": {
        "ar": "⚠️ أدخل رقماً صحيحاً.",
        "en": "⚠️ Please enter a valid number.",
    },
    "af_step_idfa": {
        "ar": "📋 الخطوة 1/5 — أرسل <b>IDFA</b> جهازك:\n\n<i>مثال:</i> <code>6D92078A-8246-4BA4-AE75-79F1B2D67052</code>",
        "en": "📋 Step 1/5 — Send your device <b>IDFA</b>:\n\n<i>Example:</i> <code>6D92078A-8246-4BA4-AE75-79F1B2D67052</code>",
    },
    "af_step_idfv": {
        "ar": "📋 الخطوة 2/5 — أرسل <b>IDFV</b> جهازك:\n\n<i>مثال:</i> <code>599F9C00-92DC-4B5C-9464-7971F01F8370</code>",
        "en": "📋 Step 2/5 — Send your device <b>IDFV</b>:\n\n<i>Example:</i> <code>599F9C00-92DC-4B5C-9464-7971F01F8370</code>",
    },
    "af_step_ios": {
        "ar": "📋 الخطوة 3/5 — أرسل إصدار <b>iOS</b>:\n\n<i>مثال:</i> <code>17.4.1</code>",
        "en": "📋 Step 3/5 — Send your <b>iOS version</b>:\n\n<i>Example:</i> <code>17.4.1</code>",
    },
    "af_step_afid": {
        "ar": "📋 الخطوة 4/5 — أرسل <b>AppsFlyer ID</b>:",
        "en": "📋 Step 4/5 — Send your <b>AppsFlyer ID</b>:",
    },
    "af_step_levels": {
        "ar": "📋 الخطوة 5/5 — أرسل الليفلات المطلوبة (مفصولة بفاصلة):\n<i>مثال:</i> <code>5, 60, 400</code>",
        "en": "📋 Step 5/5 — Send required levels (comma-separated):\n<i>Example:</i> <code>5, 60, 400</code>",
    },
    "af_submitted": {
        "ar": "✅ تم إرسال طلب AppsFlyer بنجاح!\n\nرقم الطلب: <code>#{order_id}</code>\nاللعبة: {game_name}\nالليفلات: <code>{levels}</code>\nالمبلغ المخصوم: <b>${price_usd}</b>\nرصيدك الحالي: <b>${balance}</b>",
        "en": "✅ AppsFlyer order submitted!\n\nOrder: <code>#{order_id}</code>\nGame: {game_name}\nLevels: <code>{levels}</code>\nCharged: <b>${price_usd}</b>\nBalance: <b>${balance}</b>",
    },
    "af_invalid_uuid": {
        "ar": "❌ UUID غير صحيح، أعد الإرسال.",
        "en": "❌ Invalid UUID format, try again.",
    },
    "cancelled": {
        "ar": "تم الإلغاء ✅",
        "en": "Cancelled ✅",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    text = STRINGS.get(key, {}).get(lang) or STRINGS.get(key, {}).get("en") or key
    if kwargs:
        text = text.format(**kwargs)
    return text
