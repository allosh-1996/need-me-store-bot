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
🌑 *Need Me Store*

مرحباً بك في متجرنا الرقمي الموثوق
_Welcome to your trusted digital store_

▬▬▬▬▬▬▬▬▬▬▬▬▬▬

🔒 Apple iCloud Accounts
_حسابات آبل آي كلاود_

📩 Ready\-made Emails
_إيميلات جاهزة_

📄 Survey Accounts
_حسابات استبيانات_

📖 Exclusive Methods & Guides
_شروحات وطرق حصرية_

▬▬▬▬▬▬▬▬▬▬▬▬▬▬

اختر من القائمة أدناه
_Choose from the menu below_ 👇
"""

# ═══════════════════════════════════════
# رسالة الدفع | Payment Message
# ═══════════════════════════════════════
PAYMENT_MSG = """
💳 *Payment Methods  |  طرق الدفع*

━━━━━━━━━━━━━━━━
🪙 *USDT — BEP-20*
`{usdt_wallet}`

📱 *Syriatel Cash  |  سيريتيل كاش*
`{syriatel_cash}`
━━━━━━━━━━━━━━━━

⚠️ بعد الدفع أرسل إيصال التحويل
_After payment, send your receipt_
"""
