"""
Web Dashboard Backend
Flask server for the admin dashboard
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import database as db
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


app.secret_key = os.environ.get("DASHBOARD_SECRET", "needmestore2026")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

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
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/orders/<int:oid>/status', methods=['POST'])
@auth_required
def api_order_status(oid):
    status = request.json.get('status')
    order = db.get_order(oid)
    db.update_order_status(oid, status)

    if order:
        if status == 'completed':
            product = db.get_product(order['product_id'])
            stock_text = f"\n✅ *تفاصيل المنتج:*\n`{product['stock']}`" if product and product['stock'] else ""
            tg_send(order['user_id'],
                f"🎉 *تم تأكيد طلبك!  |  Order Confirmed!*\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔖 Order ID: `#{oid}`\n"
                f"📦 {order['product_name']}\n"
                f"💵 ${order['price_usd']}"
                + stock_text +
                f"\n━━━━━━━━━━━━━━━━\n"
                f"شكراً لثقتك 🙏  |  _Thank you!_"
            )
        elif status == 'rejected':
            tg_send(order['user_id'],
                f"🔴 *تم رفض طلبك  |  Order Rejected*\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔖 Order ID: `#{oid}`\n"
                f"📦 {order['product_name']}\n"
                f"💵 ${order['price_usd']}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"_للاستفسار تواصل مع الأدمن_"
            )

    return jsonify({"ok": True})

@app.route('/api/charges')
@auth_required
def api_charges():
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM charge_requests ORDER BY created_at DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/charges/<int:cid>/confirm', methods=['POST'])
@auth_required
def api_confirm_charge(cid):
    charge = db.get_charge_request(cid)
    db.confirm_charge(cid)
    if charge:
        method_label = "USDT BEP-20" if charge['method'] == 'usdt' else "Syriatel Cash"
        tg_send(charge['user_id'],
            f"✅ *تم قبول طلب الشحن!  |  Top Up Accepted!*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 المبلغ  |  Amount: `${charge['amount_usd']}`\n"
            f"💳 {method_label}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⏳ _سيتم إضافة الرصيد لحسابك قريباً_\n"
            f"_Your balance will be added shortly_ 🚀"
        )
    return jsonify({"ok": True})

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
    c.execute("""SELECT u.*, COALESCE(b.balance_usd, 0) as balance 
                 FROM users u LEFT JOIN balances b ON u.id=b.user_id 
                 ORDER BY u.joined_at DESC""")
    rows = [dict(r) for r in c.fetchall()]
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
    c.execute("INSERT INTO broadcasts (message) VALUES (?)", (msg,))
    broadcast_id = c.lastrowid
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
    return jsonify({"ok": True, "new_balance": new_balance})

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
    rows = [dict(r) for r in c.fetchall()]
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
