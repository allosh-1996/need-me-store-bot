import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# معلومات الدفع
USDT_WALLET = os.environ.get("USDT_WALLET", "ضع_محفظة_USDT_هنا")
SYRIATEL_CASH = os.environ.get("SYRIATEL_CASH", "ضع_رقم_سيريتيل_كاش_هنا")

# سعر صرف الليرة السورية | SYP Exchange Rate (SYP per 1 USD)
# سعر صرف الليرة السورية (العملة الجديدة) | SYP Exchange Rate (new currency)
# القيمة الافتراضية 140 — عدّلها في Railway Variables متى احتجت
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
# ══════════════════════════════════════════════════════
APPSFLYER_GAMES = {
    "domino_dream":        {"name": "Domino Dreams",         "price_usd": float(os.environ.get("AF_PRICE_DOMINO",   "4"))},
    "disney_dream":        {"name": "Disney Dream",          "price_usd": float(os.environ.get("AF_PRICE_DISNEY",   "4"))},
    "coin_master":         {"name": "Coin Master",           "price_usd": float(os.environ.get("AF_PRICE_COIN",     "4"))},
    "travel_town":         {"name": "Travel Town",           "price_usd": float(os.environ.get("AF_PRICE_TRAVEL",   "4"))},
    "yarn_loop":           {"name": "Yarn Loop",             "price_usd": float(os.environ.get("AF_PRICE_YARN",     "4"))},
    "dice_dream":          {"name": "Dice Dreams",           "price_usd": float(os.environ.get("AF_PRICE_DICE",     "4"))},
    "toy_blast":           {"name": "Toy Blast",             "price_usd": float(os.environ.get("AF_PRICE_TOY",      "4"))},
    "toon_blast":          {"name": "Toon Blast",            "price_usd": float(os.environ.get("AF_PRICE_TOON",     "4"))},
    "match_factory":       {"name": "Match Factory",         "price_usd": float(os.environ.get("AF_PRICE_MATCH",    "4"))},
    "royal_kingdom":       {"name": "Royal Kingdom",         "price_usd": float(os.environ.get("AF_PRICE_ROYAL",    "4"))},
    "board_adventure":     {"name": "Board Adventure",       "price_usd": float(os.environ.get("AF_PRICE_BOARD",    "4"))},
    "disney_solitaire":    {"name": "Disney Solitaire",      "price_usd": float(os.environ.get("AF_PRICE_DSOL",     "4"))},
    "homescapes":          {"name": "Homescapes",            "price_usd": float(os.environ.get("AF_PRICE_HOME",     "4"))},
    "screw_guru":          {"name": "Screw Guru",            "price_usd": float(os.environ.get("AF_PRICE_SCREW",    "4"))},
    "empires":             {"name": "⚔️ Empires",            "price_usd": float(os.environ.get("AF_PRICE_EMPIRES",  "4"))},
    "zombie_miner":        {"name": "Zombie Miner",          "price_usd": float(os.environ.get("AF_PRICE_ZOMBIE",   "4"))},
    "family_island":       {"name": "Family Island",         "price_usd": float(os.environ.get("AF_PRICE_FAMILY",   "4"))},
    "fishdom":             {"name": "Fishdom",               "price_usd": float(os.environ.get("AF_PRICE_FISH",     "4"))},
    "goods_master_3d":     {"name": "Goods Master 3D",       "price_usd": float(os.environ.get("AF_PRICE_GOODS",    "4"))},
    "matching_story":      {"name": "Matching Story",        "price_usd": float(os.environ.get("AF_PRICE_MSTORY",   "4"))},
    "solitaire_harvest":   {"name": "Solitaire Grand Harvest","price_usd": float(os.environ.get("AF_PRICE_SHARVEST","4"))},
    "farmville_3":         {"name": "FarmVille 3",           "price_usd": float(os.environ.get("AF_PRICE_FARM",     "4"))},
}
