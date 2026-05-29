"""
Web Dashboard Backend
Flask server for the admin dashboard
FIX: Health endpoint مدمج هنا (port 5000) — لا حاجة لـ keep_alive Flask server.
FIX: DASHBOARD_PASSWORD الافتراضي None — يرفع RuntimeError في production بدون كلمة سر.
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import database as db
from database import _fetchall_dict, _fetchone_dict
import os
import requests as req_lib
from config import ADMIN_ID, BOT_TOKEN
import secrets as _secrets
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='.')

def tg_send(chat_id, text):
    """إرسال رسالة تيليغرام من الداشبورد"""
    try:
        req_lib.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        logger.error(f"TG send error: {e}")

# ═══════════════════════════════════════════════════════════════
# FIX: أمان الداشبورد
# DASHBOARD_SECRET  — مفتاح تشفير الجلسات (مطلوب في production)
# DASHBOARD_PASSWORD — كلمة سر الداشبورد (مطلوبة دائماً، لا افتراضي)
# ═══════════════════════════════════════════════════════════════
_is_production = bool(
    os.environ.get("RAILWAY_ENVIRONMENT") or
    os.environ.get("RAILWAY_PROJECT_ID") or   # Railway دايماً بيحط هذا
    os.environ.get("RENDER") or
    os.environ.get("PRODUCTION")
)

_dashboard_secret = os.environ.get("DASHBOARD_SECRET")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")  # FIX: لا افتراضي

# في production: ارفض الشغل بدون credentials
if _is_production:
    if not DASHBOARD_PASSWORD:
        raise RuntimeError(
            "❌ DASHBOARD_PASSWORD غير محدد!\n"
            "أضف DASHBOARD_PASSWORD في Railway Variables.\n"
            "مثال: python3 -c \"import secrets; print(secrets.token_urlsafe(16))\""
        )
    if not _dashboard_secret:
        raise RuntimeError(
            "❌ DASHBOARD_SECRET غير محدد!\n"
            "أضف DASHBOARD_SECRET في Railway Variables.\n"
            "مثال: python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )
else:
    # في dev: تحذيرات واضحة لكن لا يوقف
    if not DASHBOARD_PASSWORD:
        DASHBOARD_PASSWORD = "dev_only_change_in_production"
        logger.warning("⚠️  DASHBOARD_PASSWORD not set — using dev default. Set it in production!")
    if not _dashboard_secret:
        _dashboard_secret = _secrets.token_hex(32)
        logger.warning("⚠️  DASHBOARD_SECRET not set — using random key (sessions reset on restart)")

app.secret_key = _dashboard_secret

# FIX: Session cookie على HTTPS — بدونها الـ session ما بتنحفظ على Railway
app.config['SESSION_COOKIE_SECURE'] = _is_production  # FIX: only HTTPS in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'nx_session'

# Token-based auth كبديل للـ session (للموبايل)
import hashlib
_auth_token = hashlib.sha256(
    (DASHBOARD_PASSWORD or 'dev').encode() + 
    (_dashboard_secret or 'dev').encode()
).hexdigest()[:32]
app.config['AUTH_TOKEN'] = _auth_token

# ═══ Health Check (FIX: مدمج هنا بدل keep_alive Flask) ═══
@app.route('/health')
def health():
    return {"status": "alive", "bot": "NexVault"}, 200

@app.route('/ping')
def ping():
    return "🌙 NexVault Bot — Online ✅"

# ═══ Auth ═══
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == DASHBOARD_PASSWORD:
            session['admin'] = True
            logger.info(f"Dashboard login successful from IP: {request.remote_addr}")
            session['admin'] = True
            token = app.config.get('AUTH_TOKEN', '')
            return redirect(f'/?_t={token}')
        logger.warning(f"Dashboard login failed from IP: {request.remote_addr}")
        error = "❌ كلمة السر غلط"
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        # تحقق من session أو X-Auth-Token header
        token = request.headers.get('X-Auth-Token') or request.args.get('_t')
        if session.get('admin') or (token and token == app.config.get('AUTH_TOKEN')):
            return f(*args, **kwargs)
        if request.path.startswith('/api/'):
            return jsonify({'error': 'unauthorized'}), 401
        return redirect('/login')
    return decorated

# ═══ Pages ═══
@app.route('/')
@auth_required
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/styles.css')
def styles():
    return send_from_directory('.', 'styles.css')

@app.route('/theme.js')
def theme():
    return send_from_directory('.', 'theme.js')

# ═══ APIs ═══
@app.route('/api/stats')
@auth_required
def api_stats():
    return jsonify(db.get_stats())

@app.route('/api/products')
@auth_required
def api_products():
    products = db.get_all_products(active_only=False)
    return jsonify([dict(p) for p in products])

@app.route('/api/products/add', methods=['POST'])
@auth_required
def api_add_product():
    d = request.json
    pid = db.add_product(
        name=d.get('name',''),
        description=d.get('description',''),
        price_usd=float(d.get('price_usd', 0)),
        price_syp=float(d.get('price_syp', 0)),
        category=d.get('category',''),
        stock=d.get('stock',''),
        platform=d.get('platform', 'iOS')  # FIX: platform was missing
    )
    logger.info(f"Dashboard: product #{pid} added")
    return jsonify({"id": pid, "ok": True})

@app.route('/api/products/<int:pid>/delete', methods=['POST'])
@auth_required
def api_delete_product(pid):
    db.delete_product(pid)
    logger.info(f"Dashboard: product #{pid} deleted")
    return jsonify({"ok": True})

@app.route('/api/products/<int:pid>/stock', methods=['POST'])
@auth_required
def api_update_stock(pid):
    stock = request.json.get('stock', '')
    db.update_product_stock(pid, stock)
    count = db.get_stock_count(pid)
    logger.info(f"Dashboard: stock updated for product #{pid}: {count} units")
    return jsonify({"ok": True, "count": count})

@app.route('/api/orders')
@auth_required
def api_orders():
    status = request.args.get('status', '')
    conn = db.get_conn()
    if status:
        cur = conn.execute("SELECT o.*, b.balance_usd FROM orders o LEFT JOIN balances b ON o.user_id=b.user_id WHERE o.status=? ORDER BY o.created_at DESC", (status,))
    else:
        cur = conn.execute("SELECT o.*, b.balance_usd FROM orders o LEFT JOIN balances b ON o.user_id=b.user_id ORDER BY o.created_at DESC LIMIT 100")
    rows = _fetchall_dict(cur)
    conn.close()
    return jsonify(rows)

@app.route('/api/orders/<int:oid>/status', methods=['POST'])
@auth_required
def api_order_status(oid):
    """
    FIX: عند التأكيد يستخدم pop_stock_item() لسحب وحدة فريدة atomic.
    """
    status = request.json.get('status')
    order = db.get_order(oid)

    if order and status == 'completed':
        item, remaining = db.pop_stock_item(order['product_id'])
        if not item:
            return jsonify({"ok": False, "error": "No stock available for this product"}), 400
        db.update_order_delivered_item(oid, item)
        db.update_order_status(oid, status)
        logger.info(f"Dashboard: order #{oid} confirmed, stock remaining={remaining}")
        tg_send(order['user_id'],
            f"🎉 *تم تأكيد طلبك!  |  Order Confirmed!*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🔖 Order ID: `#{oid}`\n"
            f"📦 {order['product_name']}\n"
            f"💵 ${order['price_usd']}\n\n"
            f"✅ *تفاصيل المنتج:*\n`{item}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"شكراً لثقتك 🙏  |  _Thank you!_"
        )
    elif order and status == 'rejected':
        db.update_order_status(oid, status)
        logger.info(f"Dashboard: order #{oid} rejected")
        tg_send(order['user_id'],
            f"🔴 *تم رفض طلبك  |  Order Rejected*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🔖 Order ID: `#{oid}`\n"
            f"📦 {order['product_name']}\n"
            f"💵 ${order['price_usd']}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"_للاستفسار تواصل مع الأدمن_"
        )
    else:
        db.update_order_status(oid, status)

    return jsonify({"ok": True})

@app.route('/api/charges')
@auth_required
def api_charges():
    conn = db.get_conn()
    cur = conn.execute("SELECT * FROM charge_requests ORDER BY created_at DESC LIMIT 100")
    rows = _fetchall_dict(cur)
    conn.close()
    return jsonify(rows)

@app.route('/api/charges/<int:cid>/confirm', methods=['POST'])
@auth_required
def api_confirm_charge(cid):
    """
    FIX: يضيف الرصيد تلقائياً عبر db.confirm_charge()
    """
    charge = db.confirm_charge(cid)
    if charge:
        new_balance = db.get_balance(charge['user_id'])
        method_label = "USDT BEP-20" if charge['method'] == 'usdt' else "Syriatel Cash"
        logger.info(f"Dashboard: charge #{cid} confirmed, user={charge['user_id']}, amount=${charge['amount_usd']}")
        tg_send(charge['user_id'],
            f"✅ *تم شحن رصيدك!  |  Balance Added!*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 المبلغ المضاف  |  Added: `${charge['amount_usd']}`\n"
            f"💳 {method_label}\n"
            f"💰 رصيدك الحالي  |  New Balance: `${new_balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"_يمكنك الشراء الآن_ 🛍️"
        )
        return jsonify({"ok": True, "new_balance": new_balance})
    return jsonify({"ok": False, "error": "Not found or already processed"}), 404

@app.route('/api/charges/<int:cid>/reject', methods=['POST'])
@auth_required
def api_reject_charge(cid):
    charge = db.get_charge_request(cid)
    db.reject_charge(cid)
    if charge:
        method_label = "USDT BEP-20" if charge['method'] == 'usdt' else "Syriatel Cash"
        logger.info(f"Dashboard: charge #{cid} rejected, user={charge['user_id']}")
        tg_send(charge['user_id'],
            f"🔴 *تم رفض طلب الشحن  |  Top Up Rejected*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 المبلغ  |  Amount: `${charge['amount_usd']}`\n"
            f"💳 {method_label}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"_للاستفسار تواصل مع الأدمن_"
        )
    return jsonify({"ok": True})

@app.route('/api/users')
@auth_required
def api_users():
    conn = db.get_conn()
    cur = conn.execute("""SELECT u.*,
                        COALESCE(b.balance_usd, 0) as balance,
                        COALESCE(b.total_charged, 0) as total_charged,
                        COALESCE(b.total_spent, 0) as total_spent
                 FROM users u LEFT JOIN balances b ON u.id=b.user_id
                 ORDER BY u.joined_at DESC""")
    rows = _fetchall_dict(cur)
    conn.close()
    return jsonify(rows)

@app.route('/api/broadcast', methods=['POST'])
@auth_required
def api_broadcast():
    """
    FIX: يحدد is_sent=1 فوراً قبل الإرسال — يمنع job_queue من إرسالها مرة ثانية.
    """
    msg = request.json.get('message', '')
    if not msg:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    conn = db.get_conn()
    # FIX: is_sent=1 من البداية — الداشبورد يرسل مباشرة، job_queue لن يراها
    cur = conn.execute("INSERT INTO broadcasts (message, is_sent) VALUES (?, 1)", (msg,))
    broadcast_id = cur.lastrowid
    conn.commit()

    cur2 = conn.execute("SELECT id FROM users WHERE is_blocked=0")
    users = db._fetchall_dict(cur2)
    conn.close()

    sent = 0
    failed = 0
    for user in users:
        try:
            resp = req_lib.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": user["id"], "text": msg, "parse_mode": "Markdown"},
                timeout=5
            )
            if resp.status_code == 200:
                sent += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast error for {user['id']}: {e}")

    conn3 = db.get_conn()
    conn3.execute("UPDATE broadcasts SET sent_count=? WHERE id=?", (sent, broadcast_id))
    conn3.commit()
    conn3.close()

    logger.info(f"Dashboard broadcast #{broadcast_id}: sent={sent}, failed={failed}")
    return jsonify({"ok": True, "sent": sent, "failed": failed})

@app.route('/api/users/<int:uid>/add_balance', methods=['POST'])
@auth_required
def api_add_balance(uid):
    amount = float(request.json.get('amount', 0))
    if amount <= 0:
        return jsonify({"ok": False, "error": "Invalid amount"}), 400
    db.add_balance(uid, amount)
    new_balance = db.get_balance(uid)
    logger.info(f"Dashboard: added ${amount} to user {uid}, new balance=${new_balance}")
    tg_send(uid,
        f"✅ *تم إضافة رصيد إلى حسابك!*\n\n"
        f"💵 المبلغ المضاف: `${amount:.2f}`\n"
        f"💰 رصيدك الحالي: `${new_balance:.2f}`"
    )
    return jsonify({"ok": True, "new_balance": new_balance})

@app.route('/api/users/<int:uid>/deduct_balance', methods=['POST'])
@auth_required
def api_deduct_balance(uid):
    amount = float(request.json.get('amount', 0))
    if amount <= 0:
        return jsonify({"ok": False, "error": "Invalid amount"}), 400
    current = db.get_balance(uid)
    if amount > current:
        return jsonify({"ok": False, "error": f"الرصيد غير كافي — الرصيد الحالي: ${current:.2f}"}), 400
    db.add_balance(uid, -amount)
    new_balance = db.get_balance(uid)
    logger.info(f"Dashboard: deducted ${amount} from user {uid}, new balance=${new_balance}")
    tg_send(uid,
        f"🔴 *تم خصم رصيد من حسابك*\n\n"
        f"💵 المبلغ المخصوم: `${amount:.2f}`\n"
        f"💰 رصيدك الحالي: `${new_balance:.2f}`"
    )
    return jsonify({"ok": True, "new_balance": new_balance})

@app.route('/api/users/<int:uid>/balance', methods=['GET'])
@auth_required
def api_get_balance(uid):
    balance = db.get_balance(uid)
    conn = db.get_conn()
    cur = conn.execute("SELECT total_charged, total_spent FROM balances WHERE user_id=?", (uid,))
    row = _fetchone_dict(cur)
    conn.close()
    return jsonify({
        "balance": balance,
        "total_charged": row['total_charged'] if row else 0,
        "total_spent": row['total_spent'] if row else 0
    })

# ===== Notifications APIs =====

@app.route('/api/notifications/all')
@auth_required
def api_notifications_all():
    conn = db.get_conn()
    cur1 = conn.execute("""SELECT id, user_id, username, full_name, amount_usd, method,
        tx_hash, proof, status, created_at FROM charge_requests ORDER BY created_at DESC LIMIT 100""")
    charges = [dict(r, type='charge', icon='💰',
        title=f"شحن رصيد — ${r['amount_usd']}",
        subtitle=f"{r['full_name']} · {'USDT' if r['method']=='usdt' else 'Syriatel'}")
        for r in _fetchall_dict(cur1)]

    cur2 = conn.execute("""SELECT id, user_id, username, full_name, product_name,
        price_usd, currency, payment_method, payment_proof, status, notes,
        delivered_item, created_at FROM orders ORDER BY created_at DESC LIMIT 100""")
    orders = [dict(r, type='order', icon='🛍️',
        title=f"طلب شراء — {r['product_name']}",
        subtitle=f"{r['full_name']} · ${r['price_usd']}")
        for r in _fetchall_dict(cur2)]

    cur3 = conn.execute("""SELECT id, user_id, username, full_name, proxy_type_label,
        quantity, country, notes, status, created_at FROM proxy_orders ORDER BY created_at DESC LIMIT 100""")
    proxies = [dict(r, type='proxy', icon='🌐',
        title=f"بروكسي — {r['proxy_type_label']} x{r['quantity']}",
        subtitle=f"{r['full_name']} · {r['country']}")
        for r in _fetchall_dict(cur3)]

    cur4 = conn.execute("""SELECT id, user_id, username, full_name, game_name,
        price_usd, idfa, idfv, ios_version, appsflyer_id, status, created_at
        FROM appsflyer_orders ORDER BY created_at DESC LIMIT 100""")
    appsflyer = [dict(r, type='appsflyer', icon='🎮',
        title=f"AppsFlyer — {r['game_name']}",
        subtitle=f"{r['full_name']} · ${r['price_usd']}")
        for r in _fetchall_dict(cur4)]

    conn.close()
    all_notifs = sorted(charges + orders + proxies + appsflyer, key=lambda x: x['created_at'], reverse=True)
    return jsonify(all_notifs)

@app.route('/api/notifications/user/<int:uid>')
@auth_required
def api_user_notifications(uid):
    conn = db.get_conn()
    cur1 = conn.execute("""SELECT id, user_id, username, full_name, amount_usd, method,
        tx_hash, proof, status, created_at FROM charge_requests
        WHERE user_id=? ORDER BY created_at DESC""", (uid,))
    charges = [dict(r, type='charge', icon='💰',
        title=f"شحن رصيد — ${r['amount_usd']}",
        subtitle=f"{'USDT' if r['method']=='usdt' else 'Syriatel Cash'}")
        for r in _fetchall_dict(cur1)]

    cur2 = conn.execute("""SELECT id, user_id, username, full_name, product_name,
        price_usd, currency, payment_method, payment_proof, status, notes,
        delivered_item, created_at FROM orders
        WHERE user_id=? ORDER BY created_at DESC""", (uid,))
    orders = [dict(r, type='order', icon='🛍️',
        title=f"طلب شراء — {r['product_name']}",
        subtitle=f"${r['price_usd']}")
        for r in _fetchall_dict(cur2)]

    cur3 = conn.execute("""SELECT id, user_id, username, full_name, proxy_type_label,
        quantity, country, notes, status, created_at FROM proxy_orders
        WHERE user_id=? ORDER BY created_at DESC""", (uid,))
    proxies = [dict(r, type='proxy', icon='🌐',
        title=f"بروكسي — {r['proxy_type_label']} x{r['quantity']}",
        subtitle=f"{r['country']}")
        for r in _fetchall_dict(cur3)]

    conn.close()
    all_notifs = sorted(charges + orders + proxies, key=lambda x: x['created_at'], reverse=True)
    return jsonify(all_notifs)

@app.route('/api/users/<int:uid>/delete', methods=['POST'])
@auth_required
def api_delete_user(uid):
    conn = db.get_conn()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.execute("DELETE FROM balances WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    logger.info(f"Dashboard: user {uid} deleted")
    return jsonify({"ok": True})

@app.route('/api/notifications')
@auth_required
def api_notifications():
    conn = db.get_conn()
    cur1 = conn.execute("SELECT id, full_name, amount_usd, method, created_at FROM charge_requests WHERE status='pending' ORDER BY created_at DESC LIMIT 20")
    charges = [{"type": "charge", "id": r["id"], "name": r["full_name"],
                "amount": r["amount_usd"], "method": r["method"],
                "time": r["created_at"]} for r in _fetchall_dict(cur1)]

    cur2 = conn.execute("SELECT id, full_name, product_name, price_usd, created_at FROM orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20")
    orders = [{"type": "order", "id": r["id"], "name": r["full_name"],
               "product": r["product_name"], "amount": r["price_usd"],
               "time": r["created_at"]} for r in _fetchall_dict(cur2)]

    cur3 = conn.execute("SELECT id, full_name, proxy_type_label, quantity, country, created_at FROM proxy_orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20")
    proxies = [{"type": "proxy", "id": r["id"], "name": r["full_name"],
                "product": f"{r['proxy_type_label']} x{r['quantity']} ({r['country']})",
                "amount": 0, "time": r["created_at"]} for r in _fetchall_dict(cur3)]

    cur4 = conn.execute("SELECT id, full_name, game_name, price_usd, created_at FROM appsflyer_orders WHERE status=\'pending\' ORDER BY created_at DESC LIMIT 20")
    appsflyer = [{"type": "appsflyer", "id": r["id"], "name": r["full_name"],
                  "product": r["game_name"], "amount": r["price_usd"],
                  "time": r["created_at"]} for r in _fetchall_dict(cur4)]

    conn.close()
    notifications = sorted(charges + orders + proxies + appsflyer, key=lambda x: x["time"], reverse=True)
    return jsonify({"notifications": notifications, "count": len(notifications)})

@app.route('/api/proxy_orders')
@auth_required
def api_proxy_orders():
    conn = db.get_conn()
    cur = conn.execute("SELECT * FROM proxy_orders ORDER BY created_at DESC LIMIT 100")
    rows = _fetchall_dict(cur)
    conn.close()
    return jsonify(rows)

@app.route('/api/proxy_orders/<int:oid>/status', methods=['POST'])
@auth_required
def api_proxy_order_status(oid):
    status = request.json.get('status')
    conn = db.get_conn()
    cur = conn.execute("SELECT * FROM proxy_orders WHERE id=?", (oid,))
    proxy = _fetchone_dict(cur)
    conn.close()
    db.update_proxy_order_status(oid, status)
    logger.info(f"Dashboard: proxy order #{oid} status={status}")
    if proxy:
        if status == 'completed':
            tg_send(proxy['user_id'],
                f"✅ *تم قبول طلب البروكسي!  |  Proxy Order Accepted!*\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔖 Order ID: `#{oid}`\n"
                f"📦 {proxy['proxy_type_label']} x{proxy['quantity']}\n"
                f"🌍 {proxy['country']}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"⏳ _سيتم التواصل معك وإرسال البروكسيات قريباً_ 🚀"
            )
        elif status == 'rejected':
            tg_send(proxy['user_id'],
                f"🔴 *تم رفض طلب البروكسي  |  Proxy Order Rejected*\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔖 Order ID: `#{oid}`\n"
                f"📦 {proxy['proxy_type_label']} x{proxy['quantity']}\n"
                f"🌍 {proxy['country']}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"_للاستفسار تواصل مع الأدمن_"
            )
    return jsonify({"ok": True})


# ═══ AppsFlyer Orders ═══

@app.route('/api/appsflyer_orders')
@auth_required
def api_appsflyer_orders():
    """كل طلبات AppsFlyer مع فلتر اختياري بالحالة"""
    status = request.args.get('status', '')
    conn = db.get_conn()
    if status:
        cur = conn.execute(
            "SELECT * FROM appsflyer_orders WHERE status=? ORDER BY created_at DESC LIMIT 100",
            (status,)
        )
    else:
        cur = conn.execute(
            "SELECT * FROM appsflyer_orders ORDER BY created_at DESC LIMIT 100"
        )
    rows = _fetchall_dict(cur)
    conn.close()
    return jsonify(rows)

@app.route('/api/appsflyer_orders/<int:oid>/status', methods=['POST'])
@auth_required
def api_appsflyer_order_status(oid):
    """قبول أو رفض طلب AppsFlyer من الداشبورد"""
    status = request.json.get('status')
    order = db.get_appsflyer_order(oid)

    if not order:
        return jsonify({"ok": False, "error": "Not found"}), 404

    if order["status"] != "pending":
        return jsonify({"ok": False, "error": "Already processed"}), 400

    if status == 'accepted':
        # الرصيد خُصم مسبقاً — فقط حدّث الحالة وأرسل إشعار
        db.update_appsflyer_order_status(oid, "accepted")
        logger.info(f"Dashboard: AppsFlyer order #{oid} accepted")
        tg_send(order["user_id"],
            f"✅ *تم قبول طلبك!*\n\n"
            f"🎮 *اللعبة:* {order['game_name']}\n"
            f"🔢 *رقم الطلب:* `#{oid}`\n\n"
            f"🚀 *طلبك الآن قيد التنفيذ*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📩 للمتابعة تواصل مع الأدمن:\n"
            f"👤 @Allosh96ha\n"
            f"━━━━━━━━━━━━━━━━"
        )

    elif status == 'rejected':
        # رجّع الرصيد + حدّث الحالة + أرسل إشعار
        db.add_balance(order["user_id"], order["price_usd"])
        new_balance = db.get_balance(order["user_id"])
        db.update_appsflyer_order_status(oid, "rejected")
        logger.info(f"Dashboard: AppsFlyer order #{oid} rejected — refunded ${order['price_usd']}")
        tg_send(order["user_id"],
            f"❌ *تم رفض طلبك*\n\n"
            f"🎮 *اللعبة:* {order['game_name']}\n"
            f"🔢 *رقم الطلب:* `#{oid}`\n\n"
            f"💰 *تم إعادة المبلغ:* `${order['price_usd']:.2f}`\n"
            f"💳 *رصيدك الحالي:* `${new_balance:.2f}`\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📩 للاستفسار تواصل مع الأدمن:\n"
            f"👤 @Allosh96ha\n"
            f"━━━━━━━━━━━━━━━━"
        )
    else:
        return jsonify({"ok": False, "error": "Invalid status"}), 400

    return jsonify({"ok": True})


@app.route('/api/charges/<int:cid>/proof_image')
@auth_required
def api_charge_proof_image(cid):
    """جيب صورة إيصال الشحن من تيليغرام"""
    conn = db.get_conn()
    cur = conn.execute("SELECT proof, method FROM charge_requests WHERE id=?", (cid,))
    row = _fetchone_dict(cur)
    conn.close()

    if not row or not row.get("proof"):
        return jsonify({"ok": False, "error": "No proof found"}), 404

    file_id = row["proof"]

    # جيب رابط الصورة من تيليغرام
    try:
        resp = req_lib.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=5
        )
        result = resp.json()
        if not result.get("ok"):
            return jsonify({"ok": False, "error": "Telegram API error", "is_file_id": True, "file_id": file_id}), 200

        file_path = result["result"]["file_path"]
        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        return jsonify({"ok": True, "url": image_url, "file_id": file_id})
    except Exception as e:
        logger.error(f"Proof image error: {e}")
        return jsonify({"ok": False, "error": str(e), "file_id": file_id}), 200


def run_dashboard():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
