import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# معلومات الدفع
USDT_WALLET = os.environ.get("USDT_WALLET", "ضع_محفظة_USDT_هنا")
SYRIATEL_CASH = os.environ.get("SYRIATEL_CASH", "ضع_رقم_سيريتيل_كاش_هنا")

# ═══════════════════════════════════════
# رسالة الترحيب | Welcome Message
# ═══════════════════════════════════════
WELCOME_MSG = """
*اهلا بك في NexVault*

نوفر لك كل ما تحتاجه من منتجات رقمية
باسعار تنافسية وتسليم فوري.

حسابات Apple  |  ايميلات جاهزة
بروكسيات  |  Survey Accounts  |  Games

اختر ما تريد من القائمة ادناه.
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
