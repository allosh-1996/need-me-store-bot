"""
Web Dashboard Backend
Flask server for the admin dashboard
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import database as db
import os
import asyncio
from config import ADMIN_ID

app = Flask(__name__, template_folder='.')
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
    db.update_order_status(oid, status)
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
    db.confirm_charge(cid)
    return jsonify({"ok": True})

@app.route('/api/charges/<int:cid>/reject', methods=['POST'])
@auth_required
def api_reject_charge(cid):
    db.reject_charge(cid)
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
    # حفظ الرسالة فقط - الإرسال الفعلي عبر البوت
    msg = request.json.get('message', '')
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO broadcasts (message) VALUES (?)", (msg,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

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
    db.update_proxy_order_status(oid, status)
    return jsonify({"ok": True})

def run_dashboard():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
