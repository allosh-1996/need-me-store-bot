# NexVault Bot 🛍️

بوت متجر رقمي على تيليغرام مع داشبورد ويب.

---

## المتغيرات المطلوبة (Railway Variables)

### أساسية
```
TELEGRAM_BOT_TOKEN=       # توكن البوت من @BotFather
ADMIN_TELEGRAM_ID=        # رقم حسابك على تيليغرام
```

### قاعدة البيانات (Turso)
```
TURSO_DATABASE_URL=       # libsql://your-db.turso.io
TURSO_AUTH_TOKEN=         # التوكن من Turso dashboard
```

### الدفع
```
USDT_WALLET=              # عنوان محفظة USDT BEP-20
SYRIATEL_CASH=            # رقم سيريتيل كاش
SYP_RATE=140              # سعر صرف الليرة السورية (ل.س لكل دولار)
```

### الداشبورد
```
DASHBOARD_PASSWORD=       # كلمة سر الداشبورد (مطلوبة في production)
DASHBOARD_SECRET=         # مفتاح تشفير الجلسات (مطلوب في production)
```

لتوليد DASHBOARD_SECRET:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### أسعار ألعاب AppsFlyer (اختيارية — الافتراضي $4)
```
AF_PRICE_DOMINO=4
AF_PRICE_DISNEY=4
AF_PRICE_COIN=4
# ... الخ (راجع config.py للقائمة الكاملة)
```

---

## التشغيل المحلي

```bash
pip install -r requirements.txt
python run_all.py
```

البوت يشتغل على الـ foreground، الداشبورد على http://localhost:5000

---

## الاستضافة على Railway

1. أضف كل المتغيرات في Settings → Variables
2. Deploy تلقائي عند push
3. `railway.toml` مضبوط مسبقاً

---

## بنية الملفات

| الملف | الوظيفة |
|---|---|
| `main.py` | نقطة دخول البوت |
| `run_all.py` | يشغل البوت + الداشبورد معاً |
| `database.py` | كل عمليات قاعدة البيانات (Turso) |
| `config.py` | متغيرات البيئة |
| `lang.py` | نصوص عربي/إنجليزي |
| `keyboards.py` | أزرار inline |
| `handlers_user.py` | أوامر المستخدم |
| `handlers_admin.py` | لوحة الأدمن |
| `handlers_charge.py` | شحن الرصيد |
| `handlers_appsflyer.py` | خدمة Win AppsFlyer |
| `web_dashboard.py` | Flask dashboard (port 5000) |
| `keep_alive.py` | Self-ping كل 4 دقائق |
