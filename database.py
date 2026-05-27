import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # جدول المنتجات
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price_usd REAL,
        price_syp REAL,
        category TEXT,
        platform TEXT DEFAULT 'iOS',
        stock TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # إضافة عمود platform للجداول القديمة
    try:
        c.execute("ALTER TABLE products ADD COLUMN platform TEXT DEFAULT 'iOS'")
    except:
        pass

    # جدول الطلبات
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        full_name TEXT,
        product_id INTEGER,
        product_name TEXT,
        quantity INTEGER DEFAULT 1,
        price_usd REAL,
        price_syp REAL,
        currency TEXT DEFAULT 'USD',
        payment_method TEXT,
        payment_proof TEXT,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )''')

    # جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_blocked INTEGER DEFAULT 0
    )''')

    # جدول الرسائل الجماعية
    c.execute('''CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_count INTEGER DEFAULT 0,
        is_sent INTEGER DEFAULT 0
    )''')

    # جدول الرصيد
    c.execute('''CREATE TABLE IF NOT EXISTS balances (
        user_id INTEGER PRIMARY KEY,
        balance_usd REAL DEFAULT 0.0,
        total_charged REAL DEFAULT 0.0,
        total_spent REAL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # جدول طلبات الشحن
    c.execute('''CREATE TABLE IF NOT EXISTS charge_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        full_name TEXT,
        amount_usd REAL NOT NULL,
        method TEXT DEFAULT 'usdt',
        tx_hash TEXT,
        proof TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # جدول طلبات البروكسي
    c.execute('''CREATE TABLE IF NOT EXISTS proxy_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        full_name TEXT,
        proxy_type TEXT,
        proxy_type_label TEXT,
        quantity INTEGER,
        country TEXT,
        notes TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

# ============ المنتجات ============
def get_all_products(active_only=True):
    conn = get_conn()
    c = conn.cursor()
    if active_only:
        c.execute("SELECT * FROM products WHERE active=1 ORDER BY category, name")
    else:
        c.execute("SELECT * FROM products ORDER BY category, name")
    rows = c.fetchall()
    conn.close()
    return rows

def get_product(product_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?", (product_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_product(name, description, price_usd, price_syp, category, stock, platform='iOS'):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO products (name, description, price_usd, price_syp, category, platform, stock) VALUES (?,?,?,?,?,?,?)",
              (name, description, price_usd, price_syp, category, platform, stock))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return pid

def update_product_stock(product_id, stock):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE products SET stock=? WHERE id=?", (stock, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

# ============ الطلبات ============
def create_order(user_id, username, full_name, product_id, product_name, price_usd, price_syp, currency, payment_method):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO orders 
        (user_id, username, full_name, product_id, product_name, price_usd, price_syp, currency, payment_method)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, username, full_name, product_id, product_name, price_usd, price_syp, currency, payment_method))
    conn.commit()
    oid = c.lastrowid
    conn.close()
    return oid

def update_order_status(order_id, status, notes=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE orders SET status=?, notes=? WHERE id=?", (status, notes, order_id))
    conn.commit()
    conn.close()

def update_order_proof(order_id, proof):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE orders SET payment_proof=? WHERE id=?", (proof, order_id))
    conn.commit()
    conn.close()

def get_pending_orders():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_order(order_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_user_orders(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# ============ المستخدمين ============
def upsert_user(user_id, username, full_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO users (id, username, full_name) VALUES (?,?,?)
                 ON CONFLICT(id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name""",
              (user_id, username, full_name))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE is_blocked=0")
    rows = c.fetchall()
    conn.close()
    return rows

def get_stats():
    conn = get_conn()
    c = conn.cursor()
    stats = {}
    c.execute("SELECT COUNT(*) FROM users")
    stats['users'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders")
    stats['total_orders'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    stats['pending_orders'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='completed'")
    stats['completed_orders'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products WHERE active=1")
    stats['products'] = c.fetchone()[0]
    conn.close()
    return stats

# ============ الرصيد ============
def get_balance(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT balance_usd FROM balances WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row['balance_usd'] if row else 0.0

def add_balance(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO balances (user_id, balance_usd, total_charged)
                 VALUES (?, ?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET
                 balance_usd = balance_usd + excluded.balance_usd,
                 total_charged = total_charged + excluded.total_charged,
                 updated_at = CURRENT_TIMESTAMP""",
              (user_id, amount, amount))
    conn.commit()
    conn.close()

def deduct_balance(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""UPDATE balances SET
                 balance_usd = balance_usd - ?,
                 total_spent = total_spent + ?,
                 updated_at = CURRENT_TIMESTAMP
                 WHERE user_id=?""", (amount, amount, user_id))
    conn.commit()
    conn.close()

def has_enough_balance(user_id, amount):
    return get_balance(user_id) >= amount

# ============ طلبات الشحن ============
def create_charge_request(user_id, username, full_name, amount_usd, tx_hash="", method="usdt"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO charge_requests (user_id, username, full_name, amount_usd, method, tx_hash)
                 VALUES (?,?,?,?,?,?)""",
              (user_id, username, full_name, amount_usd, method, tx_hash))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid

def update_charge_proof(req_id, proof):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE charge_requests SET proof=? WHERE id=?", (proof, req_id))
    conn.commit()
    conn.close()

def get_pending_charges():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM charge_requests WHERE status='pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_charge_request(req_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM charge_requests WHERE id=?", (req_id,))
    row = c.fetchone()
    conn.close()
    return row

def confirm_charge(req_id):
    """
    FIX: كانت تغير الحالة بس بدون إضافة رصيد.
    الحين تغير الحالة وتضيف الرصيد تلقائياً.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM charge_requests WHERE id=?", (req_id,))
    req = c.fetchone()
    if req and req['status'] == 'pending':
        c.execute("UPDATE charge_requests SET status='confirmed' WHERE id=?", (req_id,))
        conn.commit()
        conn.close()
        # أضف الرصيد تلقائياً
        add_balance(req['user_id'], req['amount_usd'])
        return req
    conn.close()
    return None

def reject_charge(req_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE charge_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

# ============ الرسائل الجماعية ============
def get_pending_broadcasts():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM broadcasts WHERE is_sent=0 ORDER BY sent_at ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def mark_broadcast_sent(broadcast_id, sent_count):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE broadcasts SET is_sent=1, sent_count=? WHERE id=?", (sent_count, broadcast_id))
    conn.commit()
    conn.close()

# ============ طلبات البروكسي ============
def create_proxy_order(user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO proxy_orders (user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes))
    conn.commit()
    oid = c.lastrowid
    conn.close()
    return oid

def get_pending_proxy_orders():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM proxy_orders WHERE status='pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def update_proxy_order_status(order_id, status):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE proxy_orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
