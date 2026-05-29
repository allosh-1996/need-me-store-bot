"""
database.py — NexVault Bot
يستخدم Turso (libsql-experimental) كقاعدة بيانات cloud دائمة.
البيانات لا تُفقد أبداً مع restart أو redeploy.

متغيرات البيئة المطلوبة:
  TURSO_DATABASE_URL  — libsql://nexvault-store-xxxx.turso.io
  TURSO_AUTH_TOKEN    — التوكن من Turso dashboard
"""

import os
import logging
import libsql_experimental as libsql

logger = logging.getLogger(__name__)

TURSO_URL   = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

if not TURSO_URL or not TURSO_TOKEN:
    raise RuntimeError(
        "❌ TURSO_DATABASE_URL أو TURSO_AUTH_TOKEN غير محددين!\n"
        "أضفهم في Railway Variables."
    )

def get_conn():
    """يفتح اتصال جديد بـ Turso — thread-safe"""
    return libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)

def _row_to_dict(description, row):
    """يحول row إلى dict باستخدام column names"""
    return {description[i][0]: row[i] for i in range(len(description))}

def _fetchall_dict(cursor):
    desc = cursor.description
    return [_row_to_dict(desc, row) for row in cursor.fetchall()]

def _fetchone_dict(cursor):
    desc = cursor.description
    row = cursor.fetchone()
    return _row_to_dict(desc, row) if row else None

def init_db():
    conn = get_conn()

    conn.execute('''CREATE TABLE IF NOT EXISTS products (
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

    conn.execute('''CREATE TABLE IF NOT EXISTS orders (
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
        delivered_item TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_blocked INTEGER DEFAULT 0
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_count INTEGER DEFAULT 0,
        is_sent INTEGER DEFAULT 0
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS balances (
        user_id INTEGER PRIMARY KEY,
        balance_usd REAL DEFAULT 0.0,
        total_charged REAL DEFAULT 0.0,
        total_spent REAL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS charge_requests (
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

    conn.execute('''CREATE TABLE IF NOT EXISTS proxy_orders (
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

# ════════════════════════════════════════
# Products
# ════════════════════════════════════════

# Cache بسيط للمنتجات — يتجدد كل 60 ثانية
import time as _time
_products_cache = {"data": None, "ts": 0}
_CACHE_TTL = 60  # ثانية

def invalidate_products_cache():
    """استدعيها بعد أي تعديل على المنتجات"""
    _products_cache["data"] = None
    _products_cache["ts"] = 0

def get_all_products(active_only=True):
    now = _time.time()
    if active_only and _products_cache["data"] is not None and (now - _products_cache["ts"]) < _CACHE_TTL:
        return _products_cache["data"]
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM products WHERE active=1 ORDER BY category, name"
        if active_only else
        "SELECT * FROM products ORDER BY category, name"
    )
    rows = _fetchall_dict(cur)
    conn.close()
    if active_only:
        _products_cache["data"] = rows
        _products_cache["ts"] = now
    return rows

def get_product(product_id):
    conn = get_conn()
    cur = conn.execute("SELECT * FROM products WHERE id=?", (product_id,))
    row = _fetchone_dict(cur)
    conn.close()
    return row

def add_product(name, description, price_usd, price_syp, category, stock, platform='iOS'):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO products (name, description, price_usd, price_syp, category, platform, stock) VALUES (?,?,?,?,?,?,?)",
        (name, description, price_usd, price_syp, category, platform, stock)
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    invalidate_products_cache()
    return pid

def update_product_stock(product_id, stock):
    conn = get_conn()
    conn.execute("UPDATE products SET stock=? WHERE id=?", (stock, product_id))
    conn.commit()
    conn.close()
    invalidate_products_cache()

def delete_product(product_id):
    conn = get_conn()
    conn.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    invalidate_products_cache()

def pop_stock_item(product_id):
    """
    FIX: Atomic stock pop using BEGIN IMMEDIATE transaction.
    يسحب أول وحدة من المخزون بشكل atomic — لا يمكن لمستخدمين الحصول على نفس الوحدة.
    يرجع: (item_text, remaining_count) أو (None, 0) لو فارغ.
    """
    conn = get_conn()
    try:
        # BEGIN IMMEDIATE يقفل الجدول للكتابة فوراً — يمنع race condition
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,))
        row = cur.fetchone()

        if not row or not row[0]:
            conn.execute("ROLLBACK")
            conn.close()
            return None, 0

        lines = [l.strip() for l in row[0].strip().splitlines() if l.strip()]
        if not lines:
            conn.execute("ROLLBACK")
            conn.close()
            return None, 0

        item = lines[0]
        remaining = lines[1:]
        conn.execute(
            "UPDATE products SET stock=? WHERE id=?",
            ("\n".join(remaining), product_id)
        )
        conn.execute("COMMIT")
        conn.close()
        invalidate_products_cache()
        return item, len(remaining)

    except Exception as e:
        logger.error(f"pop_stock_item error for product {product_id}: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return None, 0

def get_stock_count(product_id):
    conn = get_conn()
    cur = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row[0]:
        return 0
    return len([l for l in row[0].strip().splitlines() if l.strip()])

# ════════════════════════════════════════
# Orders
# ════════════════════════════════════════

def create_order(user_id, username, full_name, product_id, product_name,
                 price_usd, price_syp, currency, payment_method, delivered_item=None):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO orders
           (user_id, username, full_name, product_id, product_name,
            price_usd, price_syp, currency, payment_method, delivered_item)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (user_id, username, full_name, product_id, product_name,
         price_usd, price_syp, currency, payment_method, delivered_item)
    )
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid

def update_order_status(order_id, status, notes=None):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=?, notes=? WHERE id=?", (status, notes, order_id))
    conn.commit()
    conn.close()

def update_order_proof(order_id, proof):
    conn = get_conn()
    conn.execute("UPDATE orders SET payment_proof=? WHERE id=?", (proof, order_id))
    conn.commit()
    conn.close()

def update_order_delivered_item(order_id, item):
    conn = get_conn()
    conn.execute("UPDATE orders SET delivered_item=? WHERE id=?", (item, order_id))
    conn.commit()
    conn.close()

def get_pending_orders():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC")
    rows = _fetchall_dict(cur)
    conn.close()
    return rows

def get_order(order_id):
    conn = get_conn()
    cur = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    row = _fetchone_dict(cur)
    conn.close()
    return row

def get_user_orders(user_id):
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,)
    )
    rows = _fetchall_dict(cur)
    conn.close()
    return rows

# ════════════════════════════════════════
# Users
# ════════════════════════════════════════

def upsert_user(user_id, username, full_name):
    conn = get_conn()
    conn.execute(
        """INSERT INTO users (id, username, full_name) VALUES (?,?,?)
           ON CONFLICT(id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name""",
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM users WHERE is_blocked=0")
    rows = _fetchall_dict(cur)
    conn.close()
    return rows

def get_stats():
    conn = get_conn()
    stats = {}
    stats['users']            = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    stats['total_orders']     = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    stats['pending_orders']   = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    stats['completed_orders'] = conn.execute("SELECT COUNT(*) FROM orders WHERE status='completed'").fetchone()[0]
    stats['products']         = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
    conn.close()
    return stats

# ════════════════════════════════════════
# Balances
# ════════════════════════════════════════

def get_balance(user_id):
    conn = get_conn()
    cur = conn.execute("SELECT balance_usd FROM balances WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0.0

def buy_with_balance(user_id, product_id, price):
    """
    FIX: Atomic purchase — خصم الرصيد وسحب المنتج في transaction واحدة.
    يرجع: (item_text, new_balance) أو يرفع ValueError لو فشل.
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")

        # تحقق من الرصيد
        cur = conn.execute("SELECT balance_usd FROM balances WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        current_balance = row[0] if row else 0.0

        if current_balance < price:
            conn.execute("ROLLBACK")
            conn.close()
            raise ValueError(f"insufficient_balance:{current_balance:.2f}")

        # تحقق من المخزون وسحب وحدة
        cur2 = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,))
        row2 = cur2.fetchone()
        if not row2 or not row2[0]:
            conn.execute("ROLLBACK")
            conn.close()
            raise ValueError("out_of_stock")

        lines = [l.strip() for l in row2[0].strip().splitlines() if l.strip()]
        if not lines:
            conn.execute("ROLLBACK")
            conn.close()
            raise ValueError("out_of_stock")

        item = lines[0]
        remaining = lines[1:]

        # خصم الرصيد
        conn.execute(
            """UPDATE balances SET
               balance_usd = balance_usd - ?,
               total_spent = total_spent + ?,
               updated_at  = CURRENT_TIMESTAMP
               WHERE user_id=?""",
            (price, price, user_id)
        )

        # سحب المنتج من المخزون
        conn.execute(
            "UPDATE products SET stock=? WHERE id=?",
            ("\n".join(remaining), product_id)
        )

        conn.execute("COMMIT")
        new_balance = current_balance - price
        conn.close()
        return item, new_balance, len(remaining)

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"buy_with_balance error user={user_id} product={product_id}: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        raise ValueError(f"transaction_error:{e}")

def add_balance(user_id, amount):
    conn = get_conn()
    if amount >= 0:
        conn.execute(
            """INSERT INTO balances (user_id, balance_usd, total_charged)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               balance_usd   = balance_usd + excluded.balance_usd,
               total_charged = total_charged + excluded.total_charged,
               updated_at    = CURRENT_TIMESTAMP""",
            (user_id, amount, amount)
        )
    else:
        conn.execute(
            """UPDATE balances SET
               balance_usd = balance_usd + ?,
               total_spent = total_spent + ?,
               updated_at  = CURRENT_TIMESTAMP
               WHERE user_id=?""",
            (amount, abs(amount), user_id)
        )
    conn.commit()
    conn.close()

def deduct_balance(user_id, amount):
    conn = get_conn()
    conn.execute(
        """UPDATE balances SET
           balance_usd = balance_usd - ?,
           total_spent = total_spent + ?,
           updated_at  = CURRENT_TIMESTAMP
           WHERE user_id=?""",
        (amount, amount, user_id)
    )
    conn.commit()
    conn.close()

def has_enough_balance(user_id, amount):
    return get_balance(user_id) >= amount

# ════════════════════════════════════════
# Charge Requests
# ════════════════════════════════════════

def create_charge_request(user_id, username, full_name, amount_usd, tx_hash="", method="usdt"):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO charge_requests (user_id, username, full_name, amount_usd, method, tx_hash)
           VALUES (?,?,?,?,?,?)""",
        (user_id, username, full_name, amount_usd, method, tx_hash)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid

def update_charge_proof(req_id, proof):
    conn = get_conn()
    conn.execute("UPDATE charge_requests SET proof=? WHERE id=?", (proof, req_id))
    conn.commit()
    conn.close()

def get_pending_charges():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM charge_requests WHERE status='pending' ORDER BY created_at DESC")
    rows = _fetchall_dict(cur)
    conn.close()
    return rows

def get_charge_request(req_id):
    conn = get_conn()
    cur = conn.execute("SELECT * FROM charge_requests WHERE id=?", (req_id,))
    row = _fetchone_dict(cur)
    conn.close()
    return row

def confirm_charge(req_id):
    conn = get_conn()
    cur = conn.execute("SELECT * FROM charge_requests WHERE id=?", (req_id,))
    req = _fetchone_dict(cur)
    if req and req['status'] == 'pending':
        conn.execute("UPDATE charge_requests SET status='confirmed' WHERE id=?", (req_id,))
        conn.commit()
        conn.close()
        add_balance(req['user_id'], req['amount_usd'])
        return req
    conn.close()
    return None

def reject_charge(req_id):
    conn = get_conn()
    conn.execute("UPDATE charge_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

# ════════════════════════════════════════
# Broadcasts
# ════════════════════════════════════════

def get_pending_broadcasts():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM broadcasts WHERE is_sent=0 ORDER BY sent_at ASC")
    rows = _fetchall_dict(cur)
    conn.close()
    return rows

def mark_broadcast_sent(broadcast_id, sent_count):
    conn = get_conn()
    conn.execute("UPDATE broadcasts SET is_sent=1, sent_count=? WHERE id=?", (sent_count, broadcast_id))
    conn.commit()
    conn.close()

def claim_broadcast_for_job(broadcast_id):
    """
    FIX: Atomic claim — يمنع job_queue من إرسال broadcast سبق للداشبورد إرساله.
    يرجع True لو نجح الـ claim، False لو سبق أحد.
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute("SELECT is_sent FROM broadcasts WHERE id=?", (broadcast_id,))
        row = cur.fetchone()
        if not row or row[0] == 1:
            conn.execute("ROLLBACK")
            conn.close()
            return False
        # احجز الـ broadcast بتغيير is_sent=2 (in-progress)
        conn.execute("UPDATE broadcasts SET is_sent=2 WHERE id=?", (broadcast_id,))
        conn.execute("COMMIT")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"claim_broadcast_for_job error: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return False

# ════════════════════════════════════════
# Proxy Orders
# ════════════════════════════════════════

def create_proxy_order(user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO proxy_orders
           (user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes)
    )
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid

def get_pending_proxy_orders():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM proxy_orders WHERE status='pending' ORDER BY created_at DESC")
    rows = _fetchall_dict(cur)
    conn.close()
    return rows

def update_proxy_order_status(order_id, status):
    conn = get_conn()
    conn.execute("UPDATE proxy_orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

# ════════════════════════════════════════
# Dashboard helpers (raw queries)
# ════════════════════════════════════════

def get_conn_raw():
    """للداشبورد — يرجع connection مع _fetchall_dict و _fetchone_dict"""
    return get_conn()
