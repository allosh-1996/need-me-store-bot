"""
database.py — NexVault Bot
Turso (libsql-experimental) cloud database.

Required env vars:
  TURSO_DATABASE_URL  — libsql://nexvault-store-xxxx.turso.io
  TURSO_AUTH_TOKEN    — token from Turso dashboard
"""

import os
import logging
import threading
import time as _time
import libsql_experimental as libsql

logger = logging.getLogger(__name__)

TURSO_URL   = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

# ════════════════════════════════════════
# Thread-local Connection Pool
# ════════════════════════════════════════

_local = threading.local()


def get_conn():
    """
    Returns a thread-local connection.
    Validates env vars here (not at import time) so the module
    can be imported safely before env vars are set.
    """
    if not TURSO_URL or not TURSO_TOKEN:
        raise RuntimeError(
            "TURSO_DATABASE_URL or TURSO_AUTH_TOKEN not set. "
            "Add them to your environment variables."
        )
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)
        _local.conn = conn
    return conn


def close_thread_conn():
    """Close the current thread's connection. Call when a thread exits."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None


# ════════════════════════════════════════
# Row Helpers
# ════════════════════════════════════════

def _row_to_dict(description, row):
    return {description[i][0]: row[i] for i in range(len(description))}


def _fetchall_dict(cursor):
    desc = cursor.description
    return [_row_to_dict(desc, row) for row in cursor.fetchall()]


def _fetchone_dict(cursor):
    desc = cursor.description
    row = cursor.fetchone()
    return _row_to_dict(desc, row) if row else None


# ════════════════════════════════════════
# Init DB
# ════════════════════════════════════════

def init_db():
    conn = get_conn()

    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        description TEXT,
        price_usd   REAL,
        price_syp   REAL,
        category    TEXT,
        platform    TEXT DEFAULT 'iOS',
        stock       TEXT,
        active      INTEGER DEFAULT 1,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL,
        username       TEXT,
        full_name      TEXT,
        product_id     INTEGER,
        product_name   TEXT,
        quantity       INTEGER DEFAULT 1,
        price_usd      REAL,
        price_syp      REAL,
        currency       TEXT DEFAULT 'USD',
        payment_method TEXT,
        payment_proof  TEXT,
        status         TEXT DEFAULT 'pending',
        notes          TEXT,
        delivered_item TEXT,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id        INTEGER PRIMARY KEY,
        username  TEXT,
        full_name TEXT,
        lang      TEXT DEFAULT 'ar',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_blocked INTEGER DEFAULT 0
    )""")

    # Migrations — safe to run every startup
    for migration in [
        "ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'ar'",
        "ALTER TABLE appsflyer_orders ADD COLUMN levels TEXT",
    ]:
        try:
            conn.execute(migration)
            conn.commit()
        except Exception:
            pass  # column already exists

    conn.execute("""CREATE TABLE IF NOT EXISTS broadcasts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        message    TEXT,
        sent_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_count INTEGER DEFAULT 0,
        is_sent    INTEGER DEFAULT 0
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS balances (
        user_id       INTEGER PRIMARY KEY,
        balance_usd   REAL DEFAULT 0.0,
        total_charged REAL DEFAULT 0.0,
        total_spent   REAL DEFAULT 0.0,
        updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS charge_requests (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        username   TEXT,
        full_name  TEXT,
        amount_usd REAL NOT NULL,
        method     TEXT DEFAULT 'usdt',
        tx_hash    TEXT,
        proof      TEXT,
        status     TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS proxy_orders (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        username         TEXT,
        full_name        TEXT,
        proxy_type       TEXT,
        proxy_type_label TEXT,
        quantity         INTEGER,
        country          TEXT,
        notes            TEXT,
        status           TEXT DEFAULT 'pending',
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""CREATE TABLE IF NOT EXISTS appsflyer_orders (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        username     TEXT,
        full_name    TEXT,
        game_key     TEXT NOT NULL,
        game_name    TEXT NOT NULL,
        price_usd    REAL NOT NULL,
        idfa         TEXT,
        idfv         TEXT,
        ios_version  TEXT,
        appsflyer_id TEXT,
        levels       TEXT,
        status       TEXT DEFAULT 'pending',
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()


# ════════════════════════════════════════
# Products Cache
# ════════════════════════════════════════

_cache_lock    = threading.Lock()
_products_cache: dict = {"data": None, "ts": 0}
_single_cache:  dict  = {}
_CACHE_TTL = 60


def invalidate_products_cache():
    with _cache_lock:
        _products_cache["data"] = None
        _products_cache["ts"]   = 0
        _single_cache.clear()


def get_all_products(active_only=True):
    now = _time.time()
    with _cache_lock:
        if (
            active_only
            and _products_cache["data"] is not None
            and (now - _products_cache["ts"]) < _CACHE_TTL
        ):
            return _products_cache["data"]

    conn = get_conn()
    query = (
        "SELECT * FROM products WHERE active=1 ORDER BY category, name"
        if active_only
        else "SELECT * FROM products ORDER BY category, name"
    )
    rows = _fetchall_dict(conn.execute(query))

    if active_only:
        with _cache_lock:
            _products_cache["data"] = rows
            _products_cache["ts"]   = now
    return rows


def get_product(product_id):
    now = _time.time()
    with _cache_lock:
        cached = _single_cache.get(product_id)
        if cached and (now - cached["ts"]) < _CACHE_TTL:
            return cached["data"]

    conn = get_conn()
    row = _fetchone_dict(conn.execute("SELECT * FROM products WHERE id=?", (product_id,)))
    if row:
        with _cache_lock:
            _single_cache[product_id] = {"data": row, "ts": now}
    return row


def get_product_with_stock(product_id):
    product = get_product(product_id)
    if not product:
        return None, 0
    stock = product.get("stock") or ""
    count = len([l for l in stock.strip().splitlines() if l.strip()])
    return product, count


def add_product(name, description, price_usd, price_syp, category, stock, platform="iOS"):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO products (name, description, price_usd, price_syp, category, platform, stock) "
        "VALUES (?,?,?,?,?,?,?)",
        (name, description, price_usd, price_syp, category, platform, stock),
    )
    conn.commit()
    invalidate_products_cache()
    return cur.lastrowid


def update_product_stock(product_id, stock):
    conn = get_conn()
    conn.execute("UPDATE products SET stock=? WHERE id=?", (stock, product_id))
    conn.commit()
    invalidate_products_cache()


def delete_product(product_id):
    conn = get_conn()
    conn.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
    conn.commit()
    invalidate_products_cache()


def pop_stock_item(product_id):
    """
    Atomic stock pop — pulls the first item from stock.
    Returns (item_text, remaining_count) or (None, 0) if empty.
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()

        if not row or not row[0]:
            conn.execute("ROLLBACK")
            return None, 0

        lines = [l.strip() for l in row[0].strip().splitlines() if l.strip()]
        if not lines:
            conn.execute("ROLLBACK")
            return None, 0

        item, remaining = lines[0], lines[1:]
        conn.execute("UPDATE products SET stock=? WHERE id=?", ("\n".join(remaining), product_id))
        conn.execute("COMMIT")
        invalidate_products_cache()
        return item, len(remaining)

    except Exception as e:
        logger.error(f"pop_stock_item error product={product_id}: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return None, 0


def get_stock_count(product_id):
    conn = get_conn()
    row = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
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
         price_usd, price_syp, currency, payment_method, delivered_item),
    )
    conn.commit()
    return cur.lastrowid


def update_order_status(order_id, status, notes=None):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=?, notes=? WHERE id=?", (status, notes, order_id))
    conn.commit()


def update_order_proof(order_id, proof):
    conn = get_conn()
    conn.execute("UPDATE orders SET payment_proof=? WHERE id=?", (proof, order_id))
    conn.commit()


def update_order_delivered_item(order_id, item):
    conn = get_conn()
    conn.execute("UPDATE orders SET delivered_item=? WHERE id=?", (item, order_id))
    conn.commit()


def get_pending_orders():
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        "SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC"
    ))


def get_order(order_id):
    conn = get_conn()
    return _fetchone_dict(conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)))


def get_user_orders(user_id):
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (user_id,),
    ))


# ════════════════════════════════════════
# Users
# ════════════════════════════════════════

def upsert_user(user_id, username, full_name):
    conn = get_conn()
    conn.execute(
        """INSERT INTO users (id, username, full_name) VALUES (?,?,?)
           ON CONFLICT(id) DO UPDATE SET
           username=excluded.username, full_name=excluded.full_name""",
        (user_id, username, full_name),
    )
    conn.commit()


def get_user_lang(user_id):
    conn = get_conn()
    row = conn.execute("SELECT lang FROM users WHERE id=?", (user_id,)).fetchone()
    return (row[0] or "ar") if row else "ar"


def set_user_lang(user_id, lang):
    conn = get_conn()
    conn.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
    conn.commit()


def get_all_users():
    conn = get_conn()
    return _fetchall_dict(conn.execute("SELECT * FROM users WHERE is_blocked=0"))


def get_stats():
    conn = get_conn()
    return {
        "users":            conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "total_orders":     conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "pending_orders":   conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0],
        "completed_orders": conn.execute("SELECT COUNT(*) FROM orders WHERE status='completed'").fetchone()[0],
        "products":         conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0],
    }


def block_user(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_blocked=1 WHERE id=?", (user_id,))
    conn.commit()


# ════════════════════════════════════════
# Balances
# ════════════════════════════════════════

def get_balance(user_id):
    conn = get_conn()
    row = conn.execute("SELECT balance_usd FROM balances WHERE user_id=?", (user_id,)).fetchone()
    return row[0] if row else 0.0


def get_balance_details(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT balance_usd, total_charged, total_spent FROM balances WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if row:
        return {"balance_usd": row[0], "total_charged": row[1], "total_spent": row[2]}
    return {"balance_usd": 0.0, "total_charged": 0.0, "total_spent": 0.0}


def get_balance_by_user(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT balance_usd, total_charged, total_spent FROM balances WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if row:
        return {"balance": row[0], "total_charged": row[1], "total_spent": row[2]}
    return {"balance": 0.0, "total_charged": 0.0, "total_spent": 0.0}


def add_balance(user_id, amount: float):
    """
    Add (positive) or subtract (negative) from a user's balance.
    Raises ValueError if a subtraction would result in a negative balance.
    """
    if amount == 0:
        return

    conn = get_conn()

    if amount > 0:
        conn.execute(
            """INSERT INTO balances (user_id, balance_usd, total_charged)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               balance_usd   = balance_usd + excluded.balance_usd,
               total_charged = total_charged + excluded.total_charged,
               updated_at    = CURRENT_TIMESTAMP""",
            (user_id, amount, amount),
        )
        conn.commit()
    else:
        # Negative amount — verify sufficient balance first
        deduct_balance_atomic(user_id, abs(amount))


def deduct_balance(user_id, amount: float):
    """Convenience wrapper — same as deduct_balance_atomic."""
    deduct_balance_atomic(user_id, amount)


def deduct_balance_atomic(user_id, price: float):
    """
    Atomic balance deduction.
    Returns new_balance on success.
    Raises ValueError('insufficient_balance:<current>') if balance is too low.
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT balance_usd FROM balances WHERE user_id=?", (user_id,)).fetchone()
        current = row[0] if row else 0.0

        if current < price:
            conn.execute("ROLLBACK")
            raise ValueError(f"insufficient_balance:{current:.2f}")

        conn.execute(
            """UPDATE balances SET
               balance_usd = balance_usd - ?,
               total_spent = total_spent + ?,
               updated_at  = CURRENT_TIMESTAMP
               WHERE user_id=?""",
            (price, price, user_id),
        )
        conn.execute("COMMIT")
        return current - price

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"deduct_balance_atomic error user={user_id}: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise ValueError(f"transaction_error:{e}")


def buy_with_balance(user_id, product_id, price):
    """
    Atomic purchase — deduct balance and pop stock in one transaction.
    Returns (item_text, new_balance, remaining_count) or raises ValueError.
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute("SELECT balance_usd FROM balances WHERE user_id=?", (user_id,)).fetchone()
        current = row[0] if row else 0.0

        if current < price:
            conn.execute("ROLLBACK")
            raise ValueError(f"insufficient_balance:{current:.2f}")

        row2 = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        if not row2 or not row2[0]:
            conn.execute("ROLLBACK")
            raise ValueError("out_of_stock")

        lines = [l.strip() for l in row2[0].strip().splitlines() if l.strip()]
        if not lines:
            conn.execute("ROLLBACK")
            raise ValueError("out_of_stock")

        item, remaining = lines[0], lines[1:]

        conn.execute(
            """UPDATE balances SET
               balance_usd = balance_usd - ?,
               total_spent = total_spent + ?,
               updated_at  = CURRENT_TIMESTAMP
               WHERE user_id=?""",
            (price, price, user_id),
        )
        conn.execute("UPDATE products SET stock=? WHERE id=?", ("\n".join(remaining), product_id))
        conn.execute("COMMIT")
        invalidate_products_cache()
        return item, current - price, len(remaining)

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"buy_with_balance error user={user_id} product={product_id}: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise ValueError(f"transaction_error:{e}")


# ════════════════════════════════════════
# Charge Requests
# ════════════════════════════════════════

def create_charge_request(user_id, username, full_name, amount_usd, tx_hash="", method="usdt"):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO charge_requests (user_id, username, full_name, amount_usd, method, tx_hash)
           VALUES (?,?,?,?,?,?)""",
        (user_id, username, full_name, amount_usd, method, tx_hash),
    )
    conn.commit()
    return cur.lastrowid


def update_charge_proof(req_id, proof):
    conn = get_conn()
    conn.execute("UPDATE charge_requests SET proof=? WHERE id=?", (proof, req_id))
    conn.commit()


def get_charge_request(req_id):
    conn = get_conn()
    return _fetchone_dict(conn.execute("SELECT * FROM charge_requests WHERE id=?", (req_id,)))


def confirm_charge(req_id):
    """
    Atomic confirm — updates status and adds balance in one transaction.
    Returns the request dict on success, None if not found or already processed.
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        req = _fetchone_dict(conn.execute("SELECT * FROM charge_requests WHERE id=?", (req_id,)))

        if not req or req["status"] != "pending":
            conn.execute("ROLLBACK")
            return None

        conn.execute("UPDATE charge_requests SET status='confirmed' WHERE id=?", (req_id,))
        conn.execute(
            """INSERT INTO balances (user_id, balance_usd, total_charged)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               balance_usd   = balance_usd + excluded.balance_usd,
               total_charged = total_charged + excluded.total_charged,
               updated_at    = CURRENT_TIMESTAMP""",
            (req["user_id"], req["amount_usd"], req["amount_usd"]),
        )
        conn.execute("COMMIT")
        return req

    except Exception as e:
        logger.error(f"confirm_charge error req_id={req_id}: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return None


def reject_charge(req_id):
    conn = get_conn()
    conn.execute("UPDATE charge_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit()


# ════════════════════════════════════════
# Broadcasts
# ════════════════════════════════════════

def get_pending_broadcasts():
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        """SELECT * FROM broadcasts
           WHERE is_sent=0
              OR (is_sent=2 AND sent_at < datetime('now', '-10 minutes'))
           ORDER BY sent_at ASC"""
    ))


def mark_broadcast_sent(broadcast_id, sent_count):
    conn = get_conn()
    conn.execute(
        "UPDATE broadcasts SET is_sent=1, sent_count=? WHERE id=?",
        (sent_count, broadcast_id),
    )
    conn.commit()


def claim_broadcast_for_job(broadcast_id):
    """Atomic claim — prevents double-sending."""
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT is_sent FROM broadcasts WHERE id=?", (broadcast_id,)).fetchone()
        if not row or row[0] == 1:
            conn.execute("ROLLBACK")
            return False
        conn.execute("UPDATE broadcasts SET is_sent=2 WHERE id=?", (broadcast_id,))
        conn.execute("COMMIT")
        return True
    except Exception as e:
        logger.error(f"claim_broadcast_for_job error: {e}")
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return False


# ════════════════════════════════════════
# Proxy Orders
# ════════════════════════════════════════

def create_proxy_order(user_id, username, full_name, proxy_type, proxy_type_label,
                       quantity, country, notes):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO proxy_orders
           (user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes)
           VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes),
    )
    conn.commit()
    return cur.lastrowid


def get_pending_proxy_orders():
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        "SELECT * FROM proxy_orders WHERE status='pending' ORDER BY created_at DESC"
    ))


def update_proxy_order_status(order_id, status):
    conn = get_conn()
    conn.execute("UPDATE proxy_orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()


def get_proxy_orders(limit=100):
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        "SELECT * FROM proxy_orders ORDER BY created_at DESC LIMIT ?", (limit,)
    ))


# ════════════════════════════════════════
# AppsFlyer Orders
# ════════════════════════════════════════

def create_appsflyer_order(user_id, username, full_name, game_key, game_name,
                           price_usd, idfa, idfv, ios_version, appsflyer_id, levels=""):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO appsflyer_orders
           (user_id, username, full_name, game_key, game_name, price_usd,
            idfa, idfv, ios_version, appsflyer_id, levels, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (user_id, username, full_name, game_key, game_name, price_usd,
         idfa, idfv, ios_version, appsflyer_id, levels),
    )
    conn.commit()
    return cur.lastrowid


def get_appsflyer_order(order_id):
    conn = get_conn()
    return _fetchone_dict(conn.execute(
        "SELECT * FROM appsflyer_orders WHERE id=?", (order_id,)
    ))


def update_appsflyer_order_status(order_id, status):
    conn = get_conn()
    conn.execute("UPDATE appsflyer_orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()


def get_pending_appsflyer_orders():
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        "SELECT * FROM appsflyer_orders WHERE status='pending' ORDER BY created_at DESC"
    ))


def get_appsflyer_orders(status="", limit=100):
    conn = get_conn()
    if status:
        return _fetchall_dict(conn.execute(
            "SELECT * FROM appsflyer_orders WHERE status=? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ))
    return _fetchall_dict(conn.execute(
        "SELECT * FROM appsflyer_orders ORDER BY created_at DESC LIMIT ?", (limit,)
    ))


# ════════════════════════════════════════
# Dashboard Helpers
# ════════════════════════════════════════

def get_orders_paginated(status="", limit=50, offset=0):
    conn = get_conn()
    if status:
        return _fetchall_dict(conn.execute(
            """SELECT o.*, b.balance_usd FROM orders o
               LEFT JOIN balances b ON o.user_id=b.user_id
               WHERE o.status=? ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
            (status, limit, offset),
        ))
    return _fetchall_dict(conn.execute(
        """SELECT o.*, b.balance_usd FROM orders o
           LEFT JOIN balances b ON o.user_id=b.user_id
           ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
        (limit, offset),
    ))


def get_users_with_balances():
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        """SELECT u.*,
                  COALESCE(b.balance_usd, 0)   AS balance,
                  COALESCE(b.total_charged, 0)  AS total_charged,
                  COALESCE(b.total_spent, 0)    AS total_spent
           FROM users u LEFT JOIN balances b ON u.id=b.user_id
           ORDER BY u.joined_at DESC"""
    ))


def get_charges_recent(limit=100):
    conn = get_conn()
    return _fetchall_dict(conn.execute(
        "SELECT * FROM charge_requests ORDER BY created_at DESC LIMIT ?", (limit,)
    ))


def get_pending_notifications():
    conn = get_conn()

    charges = [
        {"type": "charge", "id": r["id"], "name": r["full_name"],
         "amount": r["amount_usd"], "method": r["method"], "time": r["created_at"]}
        for r in _fetchall_dict(conn.execute(
            "SELECT id, full_name, amount_usd, method, created_at "
            "FROM charge_requests WHERE status='pending' ORDER BY created_at DESC LIMIT 20"
        ))
    ]

    orders = [
        {"type": "order", "id": r["id"], "name": r["full_name"],
         "product": r["product_name"], "amount": r["price_usd"], "time": r["created_at"]}
        for r in _fetchall_dict(conn.execute(
            "SELECT id, full_name, product_name, price_usd, created_at "
            "FROM orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20"
        ))
    ]

    proxies = [
        {"type": "proxy", "id": r["id"], "name": r["full_name"],
         "product": f"{r['proxy_type_label']} x{r['quantity']} ({r['country']})",
         "amount": 0, "time": r["created_at"]}
        for r in _fetchall_dict(conn.execute(
            "SELECT id, full_name, proxy_type_label, quantity, country, created_at "
            "FROM proxy_orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20"
        ))
    ]

    appsflyer = [
        {"type": "appsflyer", "id": r["id"], "name": r["full_name"],
         "product": r["game_name"], "amount": r["price_usd"],
         "levels": r["levels"] or "", "time": r["created_at"]}
        for r in _fetchall_dict(conn.execute(
            "SELECT id, full_name, game_name, price_usd, levels, created_at "
            "FROM appsflyer_orders WHERE status='pending' ORDER BY created_at DESC LIMIT 20"
        ))
    ]

    return sorted(charges + orders + proxies + appsflyer, key=lambda x: x["time"], reverse=True)


def get_all_notifications_full():
    conn = get_conn()

    charges = [
        dict(r, type="charge", icon="💰",
             title=f"شحن رصيد — ${r['amount_usd']}",
             subtitle=f"{r['full_name']} · {'USDT' if r['method']=='usdt' else 'Syriatel'}")
        for r in _fetchall_dict(conn.execute(
            "SELECT id, user_id, username, full_name, amount_usd, method, "
            "tx_hash, proof, status, created_at FROM charge_requests "
            "ORDER BY created_at DESC LIMIT 100"
        ))
    ]

    orders = [
        dict(r, type="order", icon="🛍️",
             title=f"طلب شراء — {r['product_name']}",
             subtitle=f"{r['full_name']} · ${r['price_usd']}")
        for r in _fetchall_dict(conn.execute(
            "SELECT id, user_id, username, full_name, product_name, price_usd, currency, "
            "payment_method, payment_proof, status, notes, delivered_item, created_at "
            "FROM orders ORDER BY created_at DESC LIMIT 100"
        ))
    ]

    proxies = [
        dict(r, type="proxy", icon="🌐",
             title=f"بروكسي — {r['proxy_type_label']} x{r['quantity']}",
             subtitle=f"{r['full_name']} · {r['country']}")
        for r in _fetchall_dict(conn.execute(
            "SELECT id, user_id, username, full_name, proxy_type_label, quantity, "
            "country, notes, status, created_at FROM proxy_orders "
            "ORDER BY created_at DESC LIMIT 100"
        ))
    ]

    appsflyer = [
        dict(r, type="appsflyer", icon="🎮",
             title=f"AppsFlyer — {r['game_name']}",
             subtitle=f"{r['full_name']} · ${r['price_usd']} | 🎯 {r['levels'] or '—'}")
        for r in _fetchall_dict(conn.execute(
            "SELECT id, user_id, username, full_name, game_name, price_usd, "
            "idfa, idfv, ios_version, appsflyer_id, levels, status, created_at "
            "FROM appsflyer_orders ORDER BY created_at DESC LIMIT 100"
        ))
    ]

    return sorted(charges + orders + proxies + appsflyer,
                  key=lambda x: x["created_at"], reverse=True)


def get_user_notifications(user_id):
    conn = get_conn()

    charges = [
        dict(r, type="charge", icon="💰",
             title=f"شحن رصيد — ${r['amount_usd']}",
             subtitle="USDT" if r["method"] == "usdt" else "Syriatel Cash")
        for r in _fetchall_dict(conn.execute(
            "SELECT id, user_id, username, full_name, amount_usd, method, "
            "tx_hash, proof, status, created_at FROM charge_requests "
            "WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ))
    ]

    orders = [
        dict(r, type="order", icon="🛍️",
             title=f"طلب شراء — {r['product_name']}",
             subtitle=f"${r['price_usd']}")
        for r in _fetchall_dict(conn.execute(
            "SELECT id, user_id, username, full_name, product_name, price_usd, currency, "
            "payment_method, payment_proof, status, notes, delivered_item, created_at "
            "FROM orders WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ))
    ]

    proxies = [
        dict(r, type="proxy", icon="🌐",
             title=f"بروكسي — {r['proxy_type_label']} x{r['quantity']}",
             subtitle=r["country"])
        for r in _fetchall_dict(conn.execute(
            "SELECT id, user_id, username, full_name, proxy_type_label, quantity, "
            "country, notes, status, created_at FROM proxy_orders "
            "WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ))
    ]

    return sorted(charges + orders + proxies, key=lambda x: x["created_at"], reverse=True)
