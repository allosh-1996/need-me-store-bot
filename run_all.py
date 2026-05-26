"""
تشغيل البوت + لوحة التحكم معاً في نفس العملية
البوت: python-telegram-bot (async)
اللوحة: Flask في thread منفصل
"""
import threading
import os
import sys
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def run_dashboard():
    """تشغيل Flask في thread منفصل"""
    from flask import Flask, request, jsonify, render_template_string, redirect, session, send_from_directory
    from functools import wraps
    import database as db

    app = Flask(__name__)
    app.secret_key = os.environ.get('DASHBOARD_SECRET', 'needmestore2026x')
    ADMIN_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', '1996')
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect('/login')
            return f(*args, **kwargs)
        return decorated

    @app.route('/styles.css')
    def styles():
        return send_from_directory(BASE_DIR, 'styles.css')

    @app.route('/theme.js')
    def themejs():
        return send_from_directory(BASE_DIR, 'theme.js')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = ''
        if request.method == 'POST':
            if request.form.get('password') == ADMIN_PASSWORD:
                session['logged_in'] = True
                return redirect('/')
            error = '❌ كلمة السر غلط'
        return render_template_string(open(os.path.join(BASE_DIR, 'login.html')).read(), error=error)

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect('/login')

    @app.route('/')
    @login_required
    def index():
        return open(os.path.join(BASE_DIR, 'dashboard.html')).read()

    @app.route('/api/stats')
    @login_required
    def api_stats():
        return jsonify(db.get_stats())

    @app.route('/api/products')
    @login_required
    def api_products():
        return jsonify([dict(p) for p in db.get_all_products(active_only=False)])

    @app.route('/api/products/add', methods=['POST'])
    @login_required
    def api_add_product():
        d = request.json
        pid = db.add_product(d['name'], d.get('description',''), float(d['price_usd']),
                             float(d['price_syp']), d['category'], d.get('stock',''))
        return jsonify({'id': pid, 'ok': True})

    @app.route('/api/products/<int:pid>/delete', methods=['POST'])
    @login_required
    def api_delete_product(pid):
        db.delete_product(pid)
        return jsonify({'ok': True})

    @app.route('/api/products/<int:pid>/stock', methods=['POST'])
    @login_required
    def api_update_stock(pid):
        db.update_product_stock(pid, request.json.get('stock', ''))
        return jsonify({'ok': True})

    @app.route('/api/orders')
    @login_required
    def api_orders():
        conn = db.get_conn()
        c = conn.cursor()
        status = request.args.get('status', '')
        if status:
            c.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC LIMIT 100", (status,))
        else:
            c.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 100")
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/orders/<int:oid>/status', methods=['POST'])
    @login_required
    def api_order_status(oid):
        db.update_order_status(oid, request.json.get('status'), request.json.get('notes',''))
        return jsonify({'ok': True})

    @app.route('/api/charges')
    @login_required
    def api_charges():
        conn = db.get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM charge_requests ORDER BY created_at DESC LIMIT 100")
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/charges/<int:rid>/confirm', methods=['POST'])
    @login_required
    def api_confirm_charge(rid):
        req = db.confirm_charge(rid)
        return jsonify({'ok': bool(req)})

    @app.route('/api/charges/<int:rid>/reject', methods=['POST'])
    @login_required
    def api_reject_charge(rid):
        db.reject_charge(rid)
        return jsonify({'ok': True})

    @app.route('/api/users')
    @login_required
    def api_users():
        users = db.get_all_users()
        conn = db.get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id, balance_usd FROM balances")
        balances = {r['user_id']: r['balance_usd'] for r in c.fetchall()}
        conn.close()
        result = []
        for u in users:
            ud = dict(u)
            ud['balance'] = balances.get(u['id'], 0.0)
            result.append(ud)
        return jsonify(result)

    @app.route('/api/broadcast', methods=['POST'])
    @login_required
    def api_broadcast():
        msg = request.json.get('message', '')
        conn = db.get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO broadcasts (message) VALUES (?)", (msg,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    logging.info(f"🌐 لوحة التحكم على البورت {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    import database as db
    db.init_db()

    # نشغل اللوحة في thread منفصل
    t = threading.Thread(target=run_dashboard, daemon=True)
    t.start()
    logging.info("✅ لوحة التحكم شغالة")

    # نشغل البوت في الـ main thread
    from main import main
    main()
