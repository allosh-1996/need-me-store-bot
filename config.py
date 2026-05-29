import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# معلومات الدفع
USDT_WALLET = os.environ.get("USDT_WALLET", "ضع_محفظة_USDT_هنا")
SYRIATEL_CASH = os.environ.get("SYRIATEL_CASH", "ضع_رقم_سيريتيل_كاش_هنا")

# سعر صرف الليرة السورية | SYP Exchange Rate (SYP per 1 USD)
SYP_RATE = float(os.environ.get("SYP_RATE", "140"))

# ═══════════════════════════════════════
# رسالة الترحيب | Welcome Message
# ═══════════════════════════════════════
WELCOME_MSG = """
*أهلاً بك في NexVault*
بوابتك الرقمية المتكاملة! نوفر لك كل ما تحتاجه من منتجات وخدمات رقمية بجودة احترافية.

*لماذا تختارنا؟*
• أداء المهام بجودة احترافية.
• أسعار تنافسية تناسب الجميع.

*قائمة منتجاتنا:*
حسابات Apple
إيميلات جاهزة
بروكسيات عالية السرعة
حسابات استبيانات (Survey Accounts)
ألعاب (Games)

اختر ما تريد من القائمة أدناه لبدء الطلب
"""

# ═══════════════════════════════════════
# رسالة الدفع | Payment Message
# ═══════════════════════════════════════
PAYMENT_MSG = """
 *Payment Methods  |  طرق الدفع*


 *USDT — BEP-20*
`{usdt_wallet}`

 *Syriatel Cash  |  سيريتيل كاش*
`{syriatel_cash}`


 بعد الدفع أرسل إيصال التحويل
_After payment, send your receipt_
"""

# Proxy Config
PROXY_TYPES = {
    "http": " HTTP/HTTPS",
    "socks5": " SOCKS5",
    "residential": " Residential",
    "mobile": " Mobile 4G/5G",
    "modem": " Modem Private",
}


# ══════════════════════════════════════════════════════
# AppsFlyer Games Config
# السعر بالدولار — قابل للتغيير من Railway Variables
# ══════════════════════════════════════════════════════
APPSFLYER_GAMES = {
    "domino_dream": {
        "name": "🎲 Domino Dreams",
        "price_usd": float(os.environ.get("AF_PRICE_DOMINO", "5.0")),
    },
    "disney_dream": {
        "name": "✨ Disney Dreamlight Valley",
        "price_usd": float(os.environ.get("AF_PRICE_DISNEY", "5.0")),
    },
    "coin_master": {
        "name": "🪙 Coin Master",
        "price_usd": float(os.environ.get("AF_PRICE_COIN", "5.0")),
    },
    "travel_town": {
        "name": "🏖️ Travel Town",
        "price_usd": float(os.environ.get("AF_PRICE_TRAVEL", "5.0")),
    },
    "yarn_loop": {
        "name": "🧶 Yarn Loop",
        "price_usd": float(os.environ.get("AF_PRICE_YARN", "5.0")),
    },
    "dice_dream": {
        "name": "🎯 Dice Dreams",
        "price_usd": float(os.environ.get("AF_PRICE_DICE", "5.0")),
    },
    "toy_blast": {
        "name": "🧸 Toy Blast",
        "price_usd": float(os.environ.get("AF_PRICE_TOY", "5.0")),
    },
    "toon_blast": {
        "name": "🎮 Toon Blast",
        "price_usd": float(os.environ.get("AF_PRICE_TOON", "5.0")),
    },
}
