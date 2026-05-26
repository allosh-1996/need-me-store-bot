import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# معلومات الدفع
USDT_WALLET = os.environ.get("USDT_WALLET", "ضع_محفظة_USDT_هنا")
SYRIATEL_CASH = os.environ.get("SYRIATEL_CASH", "ضع_رقم_سيريتيل_كاش_هنا")

# رسالة الترحيب
WELCOME_MSG = """
🛍️ *أهلاً بك في Need Me Store!*

نوفر لك:
• 🍎 حسابات Apple iCloud
• 📧 إيميلات جاهزة
• 📋 حسابات استبيانات Survey
• 📚 شروحات وطرق حصرية

اختر من القائمة أدناه 👇
"""

# رسالة الدفع
PAYMENT_MSG = """
💳 *طرق الدفع المتاحة:*

1️⃣ *USDT (BEP-20)*
`{usdt_wallet}`

2️⃣ *Syriatel Cash*
`{syriatel_cash}`

⚠️ بعد الدفع، أرسل إيصال الدفع (صورة أو رقم العملية)
"""

