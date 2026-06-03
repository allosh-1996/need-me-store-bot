# NexVault Bot

بوت تيليغرام للمتجر الرقمي مع داشبورد ويب.

## المميزات
- شراء منتجات فوري مع حجز مخزون ذري
- محفظة رصيد مع سجل ledger لكل عملية
- شحن رصيد عبر USDT BEP-20 أو Syriatel Cash
- خدمة Win AppsFlyer (17 لعبة)
- داشبورد ويب محمي بكلمة مرور
- استضافة على Railway

## بنية المشروع

```
app/            إعدادات وlogging
bot/
  handlers/     منطق الأوامر والمحادثات
  render/       keyboards, strings, formatters
dashboard/      Flask dashboard (port 5000)
domain/         enums, errors, models
infra/          اتصال قاعدة البيانات والمعاملات
repositories/   طبقة الوصول للبيانات
services/       منطق الأعمال
scripts/        أدوات مساعدة (تشغيل يدوي فقط)
tests/          اختبارات الوحدة
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

### متغيرات أسعار AppsFlyer (اختيارية — الافتراضي $4)

```
AF_PRICE_DOMINO, AF_PRICE_DISNEY, AF_PRICE_COIN, AF_PRICE_TRAVEL,
AF_PRICE_YARN, AF_PRICE_DICE, AF_PRICE_TOY, AF_PRICE_TOON,
AF_PRICE_MATCH, AF_PRICE_ROYAL, AF_PRICE_BOARD, AF_PRICE_DSOL,
AF_PRICE_HOME, AF_PRICE_SCREW, AF_PRICE_EMPIRES, AF_PRICE_ZOMBIE,
AF_PRICE_FAMILY
```

## الإعداد

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

البوت يشتغل على الـ foreground، الداشبورد على http://localhost:5000

## النشر على Railway

1. أضف كل المتغيرات في Settings → Variables
2. Deploy تلقائي عند push
3. `railway.toml` مضبوط مسبقاً

## إضافة منتجات (اختياري)

```bash
python scripts/seed_products.py
```
