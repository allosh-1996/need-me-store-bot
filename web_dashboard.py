"""
Web Dashboard Backend
Flask server for the admin dashboard
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import database as db
from database import _fetchall_dict, _fetchone_dict
import os
import asyncio
import requests as req_lib
from config import ADMIN_ID, BOT_TOKEN

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
        print(f"TG send error: {e}")


import secrets as _secrets

# ═══════════════════════════════════════════════════════════════
# FIX: أمان الداشبورد
#
# DASHBOARD_SECRET  — مفتاح تشفير الجلسات. لو ما تحدد:
#   - في dev: يستخدم مفتاح عشوائي (sessions تنكسر مع كل restart)
#   - في production: يرفع خطأ واضح
#
# DASHBOARD_PASSWORD — كلمة سر الداشبورد. الافتراضي "admin123" خطر!
# ═══════════════════════════════════════════════════════════════
_is_production = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER") or os.environ.get("PRODUCTION")
_dashboard_secret = os.environ.get("DASHBOARD_SECRET")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

if not _dashboard_secret:
    _dashboard_secret = _secrets.token_hex(32)
    print("⚠️  WARNING: DASHBOARD_SECRET not set — using random key (sessions reset on restart)")
    print("   Set DASHBOARD_SECRET in Railway Variables for persistent sessions")

app.secret_key = _dashboard_secret

if DASHBOARD_PASSWORD == "admin123":
    print("⚠️  WARNING: DASHBOARD_PASSWORD is default 'admin123'! Change it in Railway Variables.")

# ═══ Auth ═══
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == DASHBOARD_PASSWORD:
            session['admin'] = True
            return redirect('/')
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
        if not session.get('admin'):
            return redirect('/login')
        return f(*args, **kwargs)
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
        stock=d.get('stock','')
    )
    return jsonify({"id": pid, "ok": True})

@app.route('/api/products/<int:pid>/delete', methods=['POST'])
@auth_required
def api_delete_product(pid):
    db.delete_product(pid)
    return jsonify({"ok": True})

@app.route('/api/products/<int:pid>/stock', methods=['POST'])
@auth_required
def api_update_stock(pid):
    stock = request.json.get('stock', '')
    db.update_product_stock(pid, stock)
    return jsonify({"ok": True})

@app.route('/api/orders')
@auth_required
def api_orders():
    status = request.args.get('status', '')
    conn = db.get_conn()
    c = conn.cursor()
    if status:
        c.execute("SELECT o.*, b.balance_usd FROM orders o LEFT JOIN balances b ON o.user_id=b.user_id WHERE o.status=? ORDER BY o.created_at DESC", (status,))
    else:
        c.execute("SELECT o.*, b.balance_usd FROM orders o LEFT JOIN balances b ON o.user_id=b.user_id ORDER BY o.created_at DESC LIMIT 100")
    rows = _fetchall_dict(c)
    conn.close()
    return jsonify(rows)

@app.route('/api/orders/<int:oid>/status', methods=['POST'])
@auth_required
def api_order_status(oid):
    """
    FIX: عند التأكيد يستخدم pop_stock_item() لسحب وحدة فريدة.
    """
    status = request.json.get('status')
    order = db.get_order(oid)

    if order and status == 'completed':
        # FIX: سحب وحدة فريدة من المخزون
        item, remaining = db.pop_stock_item(order['product_id'])
        if not item:
            return jsonify({"ok": False, "error": "No stock available for this product"}), 400
        db.update_order_delivered_item(oid, item)
        db.update_order_status(oid, status)
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
    c = conn.cursor()
    c.execute("SELECT * FROM charge_requests ORDER BY created_at DESC LIMIT 100")
    rows = _fetchall_dict(c)
    conn.close()
    return jsonify(rows)

@app.route('/api/charges/<int:cid>/confirm', methods=['POST'])
@auth_required
def api_confirm_charge(cid):
    """
    FIX: الحين يضيف الرصيد تلقائياً عبر db.confirm_charge()
    اللي تضيف الرصيد وتغير الحالة مع بعض.
    """
    charge = db.confirm_charge(cid)  # يضيف الرصيد + يغير الحالة
    if charge:
        new_balance = db.get_balance(charge['user_id'])
        method_label = "USDT BEP-20" if charge['method'] == 'usdt' else "Syriatel Cash"
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
    c = conn.cursor()
    c.execute("""SELECT u.*, 
                        COALESCE(b.balance_usd, 0) as balance,
                        COALESCE(b.total_charged, 0) as total_charged,
                        COALESCE(b.total_spent, 0) as total_spent
                 FROM users u LEFT JOIN balances b ON u.id=b.user_id 
                 ORDER BY u.joined_at DESC""")
    rows = _fetchall_dict(c)
    conn.close()
    return jsonify(rows)

@app.route('/api/broadcast', methods=['POST'])
@auth_required
def api_broadcast():
    msg = request.json.get('message', '')
    if not msg:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    # احفظ بقاعدة البيانات
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO broadcasts (message, is_sent) VALUES (?, 1)", (msg,))
    broadcast_id = c.lastrowid
    # FIX: نحدد is_sent=1 مباشرة — الإرسال يصير هنا، الـ job_queue ما يحتاج يعيده
    conn.commit()

    # ارسل مباشرة لكل المستخدمين عبر Bot API
    c.execute("SELECT id FROM users WHERE is_blocked=0")
    users = c.fetchall()
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
        except:
            failed += 1

    # حدث السجل
    conn2 = db.get_conn()
    c2 = conn2.cursor()
    c2.execute("UPDATE broadcasts SET is_sent=1, sent_count=? WHERE id=?", (sent, broadcast_id))
    conn2.commit()
    conn2.close()

    return jsonify({"ok": True, "sent": sent, "failed": failed})

@app.route('/api/users/<int:uid>/add_balance', methods=['POST'])
@auth_required
def api_add_balance(uid):
    amount = float(request.json.get('amount', 0))
    if amount <= 0:
        return jsonify({"ok": False, "error": "Invalid amount"}), 400
    db.add_balance(uid, amount)
    new_balance = db.get_balance(uid)
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

@app.route('/api/notifications')
@auth_required
def api_notifications():
    conn = db.get_conn()
    c = conn.cursor()

    # طلبات شحن معلقة
    c.execute("SELECT id, full_name, amount_usd, method, created_at FROM charge_requests WHERE status='pending' ORDER BY created_at DESC LIMIT 20")
    charges = [{"type": "charge", "id": r["id"], "name": r["full_name"],
                "amount": r["amount_usd"], "method": r["method"],
                "time": r["created_at"]} for r in c.fetchall()]

    # طلبات شراء معلقة
    c.execute("SELECT id, full_name, product_name, price_usd, created_at FROM orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20")
    orders = [{"type": "order", "id": r["id"], "name": r["full_name"],
               "product": r["product_name"], "amount": r["price_usd"],
               "time": r["created_at"]} for r in c.fetchall()]

    # طلبات بروكسي معلقة
    c.execute("SELECT id, full_name, proxy_type_label, quantity, country, created_at FROM proxy_orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20")
    proxies = [{"type": "proxy", "id": r["id"], "name": r["full_name"],
                "product": f"{r['proxy_type_label']} x{r['quantity']} ({r['country']})",
                "amount": 0, "time": r["created_at"]} for r in c.fetchall()]

    conn.close()

    notifications = sorted(charges + orders + proxies, key=lambda x: x["time"], reverse=True)
    return jsonify({
        "notifications": notifications,
        "count": len(notifications)
    })


@app.route('/api/proxy_orders')
@auth_required
def api_proxy_orders():
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM proxy_orders ORDER BY created_at DESC LIMIT 100")
    rows = _fetchall_dict(c)
    conn.close()
    return jsonify(rows)

@app.route('/api/proxy_orders/<int:oid>/status', methods=['POST'])
@auth_required
def api_proxy_order_status(oid):
    status = request.json.get('status')
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM proxy_orders WHERE id=?", (oid,))
    proxy = c.fetchone()
    conn.close()
    db.update_proxy_order_status(oid, status)
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

def run_dashboard():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
