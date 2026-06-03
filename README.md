# NexVault Bot

بوت تيليغرام للمتجر الرقمي مع داشبورد ويب — نسخة مُعاد كتابتها بالكامل.

## المميزات
- شراء منتجات فوري مع حجز مخزون ذري
- محفظة رصيد مع سجل ledger لكل عملية
- شحن رصيد عبر USDT أو Syriatel Cash
- خدمة Win AppsFlyer
- داشبورد ويب محمي بكلمة مرور
- استضافة على Railway

## إعداد البيئة

```bash
pip install -r requirements.txt
cp .env.example .env
# عدّل .env بقيمك الحقيقية
```

## توليد كلمة مرور الداشبورد

```bash
python scripts/make_dashboard_hash.py
# انسخ الناتج وضعه في DASHBOARD_PASSWORD_HASH داخل .env
```

## تشغيل محلي

```bash
python main.py
```

## متغيرات البيئة المطلوبة

| المتغير | الوصف |
|---|---|
| TELEGRAM_BOT_TOKEN | توكن البوت من @BotFather |
| ADMIN_TELEGRAM_IDS | أرقام الأدمن مفصولة بفاصلة |
| TURSO_DATABASE_URL | رابط قاعدة بيانات Turso |
| TURSO_AUTH_TOKEN | توكن Turso |
| DASHBOARD_SECRET | مفتاح تشفير الجلسة (عشوائي طويل) |
| DASHBOARD_PASSWORD_HASH | هاش كلمة مرور الداشبورد |
| USDT_WALLET | عنوان محفظة USDT BEP-20 |
| SYRIATEL_CASH | رقم سيريتيل كاش |
| SYP_RATE | سعر صرف الليرة (افتراضي 140) |

## النشر على Railway

1. أضف كل المتغيرات في Settings → Variables
2. النشر تلقائي عند push
