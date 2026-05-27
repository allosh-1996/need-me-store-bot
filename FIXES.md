# NexVault Bot — FIXES

> تاريخ الإصلاح: 2026-05-27

---

## 🔴 FIX 1: فقدان البيانات عند الـ Restart (database.py)

**المشكلة:** `DB_PATH` كان `/tmp/store.db` — على Railway يُحذف مع كل restart أو redeploy.

**الإصلاح:**
- `DB_PATH` الافتراضي أصبح `/data/store.db`
- الكود يحاول إنشاء المجلد تلقائياً لو ما موجود
- لو فشل إنشاء المجلد (dev environment) يرجع لـ `/tmp` مع تحذير واضح

**خطوات Railway:**
1. اذهب لـ Settings → Volumes
2. أضف Volume: Mount Path = `/data`
3. أضف env var: `DB_PATH=/data/store.db`

---

## 🔴 FIX 2: نظام المخزون (database.py + handlers)

**المشكلة:** كل المستخدمين اللي يشتروا نفس المنتج يحصلوا على نفس المحتوى (نفس الحساب/الإيميل).

**الإصلاح:**
- أضيفت دالة `pop_stock_item(product_id)` في `database.py`
- تسحب أول سطر من المخزون وتحذفه — كل مشتري يحصل على وحدة فريدة
- أضيفت دالة `get_stock_count(product_id)` لعرض العدد الحقيقي
- أضيف عمود `delivered_item` في جدول `orders` لحفظ الوحدة المُرسلة
- تم تعديل: `handlers_user.py` (confirm_buy) + `handlers_admin.py` (confirm_order) + `web_dashboard.py` (api_order_status)

**طريقة إضافة المخزون الصحيحة:**
```
account1@email.com:password1
account2@email.com:password2
account3@email.com:password3
```
كل سطر = وحدة مستقلة. عند كل بيع يُسحب سطر واحد ويُحذف.

---

## 🟡 FIX 3: Broadcast مكرر (web_dashboard.py)

**المشكلة:** الداشبورد يرسل broadcast فوراً، والـ job_queue في main.py يراقب كل 30 ثانية ويرسل broadcasts غير مرسلة — النتيجة: كل رسالة تتبعث مرتين.

**الإصلاح:**
- تصحيح INSERT ليستخدم `c.lastrowid` بدل `RETURNING id` (توافق أفضل مع SQLite)
- `is_sent=1` يُحدَّث فوراً بعد الإرسال من الداشبورد
- الـ job_queue يشوف `is_sent=1` فلا يعيد الإرسال

---

## 🟡 FIX 4: أمان الداشبورد (web_dashboard.py)

**المشكلة:** `DASHBOARD_SECRET` عشوائي مع كل restart (sessions تنكسر) + `DASHBOARD_PASSWORD` الافتراضي `admin123`.

**الإصلاح:**
- في **production** (Railway/Render): الكود يرفع `RuntimeError` لو `DASHBOARD_SECRET` أو `DASHBOARD_PASSWORD` ما تحدد
- في **dev**: تحذيرات واضحة بدل صمت

**env vars مطلوبة:**
```
DASHBOARD_SECRET=<random 64 chars>
DASHBOARD_PASSWORD=<strong password>
```

**لتوليد DASHBOARD_SECRET:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## ملخص الملفات المعدّلة

| الملف | التغييرات |
|---|---|
| `database.py` | DB_PATH → /data، pop_stock_item()، get_stock_count()، migration عمود delivered_item |
| `handlers_user.py` | confirm_buy يستخدم pop_stock_item، show_product_detail يعرض العدد الحقيقي |
| `handlers_admin.py` | confirm_order يستخدم pop_stock_item |
| `web_dashboard.py` | api_order_status يستخدم pop_stock_item، broadcast fix، security fix |

