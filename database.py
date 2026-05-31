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
import libsql_experimental as libsql

logger = logging.getLogger(__name__)

TURSO_URL   = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN",   "")

_local = threading.local()

def get_conn():
    if not TURSO_URL or not TURSO_TOKEN:
        raise RuntimeError("TURSO_DATABASE_URL or TURSO_AUTH_TOKEN not set.")
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)
        _local.conn = conn
    return conn

def close_thread_conn():
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None

def _row_to_dict(description, row):
    return {description[i][0]: row[i] for i in range(len(description))}

def _fetchall_dict(cursor):
    desc = cursor.description
    return [_row_to_dict(desc, row) for row in cursor.fetchall()]

def _fetchone_dict(cursor):
    desc = cursor.description
    row  = cursor.fetchone()
    return _row_to_dict(desc, row) if row else None

def init_db():
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        description TEXT,
        price_usd   REAL,
        price_syp   REAL,
        category    TEXT,
        platform    TEXT    DEFAULT 'iOS',
        active      INTEGER DEFAULT 1,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS stock_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(id),
        content    TEXT    NOT NULL,
        sold       INTEGER DEFAULT 0,
        sold_to    INTEGER,
        sold_at    TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        currency       TEXT    DEFAULT 'USD',
        payment_method TEXT    DEFAULT 'balance',
        status         TEXT    DEFAULT 'pending',
        delivered_item TEXT,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id         INTEGER PRIMARY KEY,
        username   TEXT,
        full_name  TEXT,
        balance    REAL    DEFAULT 0,
        lang       TEXT    DEFAULT 'ar',
        blocked    INTEGER DEFAULT 0,
        joined_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS charge_requests (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        username   TEXT,
        full_name  TEXT,
        method     TEXT,
        amount_usd REAL,
        amount_raw REAL,
        tx_hash    TEXT    UNIQUE,
        proof      TEXT,
        status     TEXT    DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS proxy_orders (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        username         TEXT,
        full_name        TEXT,
        proxy_type       TEXT,
        proxy_type_label TEXT,
        quantity         INTEGER DEFAULT 1,
        country          TEXT,
        notes            TEXT,
        status           TEXT DEFAULT 'pending',
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS appsflyer_orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER NOT NULL,
        username      TEXT,
        full_name     TEXT,
        game_key      TEXT,
        game_name     TEXT,
        price_usd     REAL,
        idfa          TEXT,
        idfv          TEXT,
        ios_version   TEXT,
        appsflyer_id  TEXT,
        levels        TEXT,
        status        TEXT DEFAULT 'pending',
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS broadcasts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        message    TEXT,
        is_sent    INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    logger.info("✅ DB schema ready")

# ── Users ──

def upsert_user(user_id: int, username: str, full_name: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            username  = excluded.username,
            full_name = excluded.full_name
    """, [user_id, username, full_name])
    conn.commit()

def set_user_lang(user_id: int, lang: str):
    conn = get_conn()
    conn.execute("UPDATE users SET lang = ? WHERE id = ?", (lang, user_id))
    conn.commit()

def get_user_lang_db(user_id: int) -> str:
    conn = get_conn()
    cur  = conn.execute("SELECT lang FROM users WHERE id = ?", (user_id,))
    row  = cur.fetchone()
    return row[0] if row else "ar"

# alias للتوافق مع lang.py الذي يستدعي _db.get_user_lang()
get_user_lang = get_user_lang_db

def get_balance(user_id: int) -> float:
    conn = get_conn()
    cur  = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    row  = cur.fetchone()
    return float(row[0]) if row else 0.0

def get_balance_by_user(user_id: int) -> dict:
    return {"balance": get_balance(user_id)}

def add_balance(user_id: int, amount: float):
    conn = get_conn()
    conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    conn.commit()

def deduct_balance_atomic(user_id: int, amount: float):
    """
    خصم الرصيد مع التحقق من الكفاية — atomic.
    يرفع ValueError('insufficient_balance:X.XX') إذا الرصيد غير كافٍ.
    """
    conn = get_conn()
    conn.execute("BEGIN")
    try:
        cur     = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        row     = cur.fetchone()
        balance = float(row[0]) if row else 0.0
        if balance < amount:
            conn.execute("ROLLBACK")
            raise ValueError(f"insufficient_balance:{balance:.2f}")
        conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
        conn.execute("COMMIT")
    except ValueError:
        raise
    except Exception as e:
        conn.execute("ROLLBACK")
        raise

def get_all_users() -> list:
    conn = get_conn()
    cur  = conn.execute("SELECT id, username, full_name FROM users WHERE blocked = 0")
    return _fetchall_dict(cur)

def get_users_with_balances() -> list:
    conn = get_conn()
    cur  = conn.execute("""
        SELECT
            u.id, u.username, u.full_name, u.balance, u.joined_at,
            COALESCE(SUM(CASE WHEN c.status='confirmed' THEN c.amount_usd ELSE 0 END), 0) AS total_charged,
            COALESCE(SUM(CASE WHEN o.status='completed' THEN o.price_usd ELSE 0 END), 0) AS total_spent
        FROM users u
        LEFT JOIN charge_requests c ON c.user_id = u.id
        LEFT JOIN orders           o ON o.user_id = u.id
        WHERE u.blocked = 0
        GROUP BY u.id
        ORDER BY u.joined_at DESC
    """)
    return _fetchall_dict(cur)

def block_user(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET blocked = 1 WHERE id = ?", (user_id,))
    conn.commit()

# ── Products ──

def get_all_products(active_only: bool = True) -> list:
    conn  = get_conn()
    query = "SELECT * FROM products"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id ASC"
    cur      = conn.execute(query)
    products = _fetchall_dict(cur)
    for p in products:
        p["stock_count"] = get_stock_count(p["id"])
    return products

def get_product(product_id: int) -> dict | None:
    conn = get_conn()
    cur  = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    p    = _fetchone_dict(cur)
    if p:
        p["stock_count"] = get_stock_count(product_id)
    return p

def add_product(name: str, description: str, price_usd: float, price_syp: float,
                category: str, stock: str, platform: str = "iOS") -> int:
    conn = get_conn()
    cur  = conn.execute("""
        INSERT INTO products (name, description, price_usd, price_syp, category, platform)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [name, description, price_usd, price_syp, category, platform])
    product_id = cur.lastrowid
    conn.commit()
    lines = [l.strip() for l in stock.splitlines() if l.strip()]
    if lines:
        _bulk_add_stock(product_id, lines)
    return product_id

def delete_product(product_id: int):
    conn = get_conn()
    conn.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
    conn.commit()

def get_products_by_platform(platform: str) -> list:
    conn     = get_conn()
    cur      = conn.execute("""
        SELECT * FROM products WHERE active = 1 AND platform = ?
        ORDER BY category, name
    """, (platform,))
    products = _fetchall_dict(cur)
    for p in products:
        p["stock_count"] = get_stock_count(p["id"])
    return products

def get_products_by_category(category: str) -> list:
    conn     = get_conn()
    cur      = conn.execute("""
        SELECT * FROM products WHERE active = 1 AND category = ?
        ORDER BY name
    """, (category,))
    products = _fetchall_dict(cur)
    for p in products:
        p["stock_count"] = get_stock_count(p["id"])
    return products

def get_categories(platform: str = None) -> list:
    conn = get_conn()
    if platform:
        cur = conn.execute("""
            SELECT DISTINCT category FROM products
            WHERE active = 1 AND platform = ? AND category IS NOT NULL
            ORDER BY category
        """, (platform,))
    else:
        cur = conn.execute("""
            SELECT DISTINCT category FROM products
            WHERE active = 1 AND category IS NOT NULL
            ORDER BY category
        """)
    return [row[0] for row in cur.fetchall()]

# ── Stock Items ──

def _bulk_add_stock(product_id: int, lines: list):
    conn = get_conn()
    conn.executemany(
        "INSERT INTO stock_items (product_id, content) VALUES (?, ?)",
        [(product_id, line) for line in lines]
    )
    conn.commit()

def get_stock_count(product_id: int) -> int:
    conn = get_conn()
    cur  = conn.execute(
        "SELECT COUNT(*) FROM stock_items WHERE product_id = ? AND sold = 0",
        [product_id]
    )
    return cur.fetchone()[0]

def pop_stock_item(product_id: int) -> tuple:
    conn = get_conn()
    conn.execute("BEGIN")
    try:
        cur = conn.execute("""
            SELECT id, content FROM stock_items
            WHERE product_id = ? AND sold = 0
            ORDER BY id ASC LIMIT 1
        """, (product_id,))
        row = cur.fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return None, 0
        item_id, content = row
        conn.execute("""
            UPDATE stock_items SET sold = 1, sold_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (item_id,))
        conn.execute("COMMIT")
        remaining = get_stock_count(product_id)
        return content, remaining
    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"pop_stock_item error: {e}")
        raise

def mark_stock_sold(item_id: int, user_id: int):
    conn = get_conn()
    conn.execute("""
        UPDATE stock_items
        SET sold = 1, sold_to = ?, sold_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (user_id, item_id))
    conn.commit()

def set_stock_items(product_id: int, lines: list) -> None:
    conn = get_conn()
    conn.execute("BEGIN")
    try:
        conn.execute(
            "DELETE FROM stock_items WHERE product_id = ? AND sold = 0",
            (product_id,)
        )
        if lines:
            conn.executemany(
                "INSERT INTO stock_items (product_id, content) VALUES (?, ?)",
                [(product_id, line) for line in lines]
            )
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"set_stock_items error: {e}")
        raise

def update_product_stock(product_id: int, stock_text: str):
    """Wrapper للتوافق مع web_dashboard."""
    lines = [l.strip() for l in stock_text.splitlines() if l.strip()]
    set_stock_items(product_id, lines)

# ── Orders ──

def create_order_atomic(user_id: int, username: str, full_name: str,
                        product_id: int, product_name: str,
                        price_usd: float, price_syp: float,
                        currency: str = "USD") -> int:
    conn = get_conn()
    conn.execute("BEGIN")
    try:
        cur     = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        row     = cur.fetchone()
        balance = float(row[0]) if row else 0.0
        if balance < price_usd:
            conn.execute("ROLLBACK")
            raise ValueError("insufficient_balance")
        conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (price_usd, user_id))
        cur = conn.execute("""
            INSERT INTO orders
                (user_id, username, full_name, product_id, product_name,
                 price_usd, price_syp, currency, payment_method, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'balance', 'pending')
        """, [user_id, username, full_name, product_id, product_name,
              price_usd, price_syp, currency])
        order_id = cur.lastrowid
        conn.execute("COMMIT")
        return order_id
    except ValueError:
        raise
    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"create_order_atomic error: {e}")
        raise

def get_order(order_id: int) -> dict | None:
    conn = get_conn()
    cur  = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    return _fetchone_dict(cur)

def update_order_status(order_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()

def update_order_delivered_item(order_id: int, item: str):
    conn = get_conn()
    conn.execute("UPDATE orders SET delivered_item = ? WHERE id = ?", (item, order_id))
    conn.commit()

def get_orders_paginated(status: str = "", limit: int = 100, offset: int = 0) -> list:
    conn = get_conn()
    if status:
        cur = conn.execute("""
            SELECT * FROM orders WHERE status = ?
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (status, limit, offset))
    else:
        cur = conn.execute("""
            SELECT * FROM orders
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
    return _fetchall_dict(cur)

# ── Charge Requests ──

def create_charge_request(user_id: int, username: str, full_name: str,
                          method: str, amount_usd: float, amount_raw: float,
                          tx_hash, proof) -> int | None:
    conn = get_conn()
    try:
        cur = conn.execute("""
            INSERT INTO charge_requests
                (user_id, username, full_name, method, amount_usd, amount_raw, tx_hash, proof)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [user_id, username, full_name, method, amount_usd, amount_raw, tx_hash, proof])
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return None
        raise

def get_charge_request(charge_id: int) -> dict | None:
    conn = get_conn()
    cur  = conn.execute("SELECT * FROM charge_requests WHERE id = ?", (charge_id,))
    return _fetchone_dict(cur)

def get_charges_recent(limit: int = 100) -> list:
    conn = get_conn()
    cur  = conn.execute("""
        SELECT * FROM charge_requests ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    return _fetchall_dict(cur)

def confirm_charge(charge_id: int) -> dict | None:
    conn = get_conn()
    conn.execute("BEGIN")
    try:
        cur    = conn.execute("SELECT * FROM charge_requests WHERE id = ?", (charge_id,))
        charge = _fetchone_dict(cur)
        if not charge or charge["status"] != "pending":
            conn.execute("ROLLBACK")
            return None
        conn.execute(
            "UPDATE charge_requests SET status = 'confirmed' WHERE id = ?", (charge_id,)
        )
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (charge["amount_usd"], charge["user_id"])
        )
        conn.execute("COMMIT")
        return charge
    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"confirm_charge error: {e}")
        raise

def reject_charge(charge_id: int):
    conn = get_conn()
    conn.execute("UPDATE charge_requests SET status = 'rejected' WHERE id = ?", (charge_id,))
    conn.commit()

# ── Proxy Orders ──

def create_proxy_order(user_id: int, username: str, full_name: str,
                       proxy_type: str, proxy_type_label: str,
                       quantity: int, country: str, notes: str) -> int:
    conn = get_conn()
    cur  = conn.execute("""
        INSERT INTO proxy_orders
            (user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [user_id, username, full_name, proxy_type, proxy_type_label, quantity, country, notes])
    conn.commit()
    return cur.lastrowid

def get_proxy_orders(status: str = "") -> list:
    conn = get_conn()
    if status:
        cur = conn.execute(
            "SELECT * FROM proxy_orders WHERE status = ? ORDER BY created_at DESC", (status,)
        )
    else:
        cur = conn.execute("SELECT * FROM proxy_orders ORDER BY created_at DESC")
    return _fetchall_dict(cur)

def update_proxy_order_status(order_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE proxy_orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()

# ── AppsFlyer Orders ──

def create_appsflyer_order(user_id: int, username: str, full_name: str,
                           game_key: str, game_name: str, price_usd: float,
                           idfa: str, idfv: str, ios_version: str,
                           appsflyer_id: str, levels: str) -> int:
    conn = get_conn()
    cur  = conn.execute("""
        INSERT INTO appsflyer_orders
            (user_id, username, full_name, game_key, game_name, price_usd,
             idfa, idfv, ios_version, appsflyer_id, levels)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [user_id, username, full_name, game_key, game_name, price_usd,
          idfa, idfv, ios_version, appsflyer_id, levels])
    conn.commit()
    return cur.lastrowid

def get_appsflyer_order(order_id: int) -> dict | None:
    conn = get_conn()
    cur  = conn.execute("SELECT * FROM appsflyer_orders WHERE id = ?", (order_id,))
    return _fetchone_dict(cur)

def get_appsflyer_orders(status: str = "") -> list:
    conn = get_conn()
    if status:
        cur = conn.execute(
            "SELECT * FROM appsflyer_orders WHERE status = ? ORDER BY created_at DESC", (status,)
        )
    else:
        cur = conn.execute("SELECT * FROM appsflyer_orders ORDER BY created_at DESC")
    return _fetchall_dict(cur)

def update_appsflyer_order_status(order_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE appsflyer_orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()

# ── Stats & Notifications ──

def get_stats() -> dict:
    conn = get_conn()
    def count(q, *args):
        return conn.execute(q, tuple(args)).fetchone()[0]
    return {
        "users":            count("SELECT COUNT(*) FROM users WHERE blocked=0"),
        "products":         count("SELECT COUNT(*) FROM products WHERE active=1"),
        "total_orders":     count("SELECT COUNT(*) FROM orders"),
        "pending_orders":   count("SELECT COUNT(*) FROM orders WHERE status='pending'"),
        "completed_orders": count("SELECT COUNT(*) FROM orders WHERE status='completed'"),
    }

def get_pending_notifications() -> list:
    conn   = get_conn()
    notifs = []
    cur = conn.execute("""
        SELECT c.id, u.full_name, u.username, c.amount_usd, c.method, c.created_at
        FROM charge_requests c JOIN users u ON u.id = c.user_id
        WHERE c.status = 'pending' ORDER BY c.created_at DESC
    """)
    for row in _fetchall_dict(cur):
        notifs.append({"type": "charge", "id": row["id"], "name": row["full_name"],
                       "amount": row["amount_usd"], "method": row["method"], "time": row["created_at"]})
    cur = conn.execute("""
        SELECT o.id, u.full_name, u.username, o.price_usd, o.product_name, o.created_at
        FROM orders o JOIN users u ON u.id = o.user_id
        WHERE o.status = 'pending' ORDER BY o.created_at DESC
    """)
    for row in _fetchall_dict(cur):
        notifs.append({"type": "order", "id": row["id"], "name": row["full_name"],
                       "amount": row["price_usd"], "product": row["product_name"], "time": row["created_at"]})
    return notifs

def get_all_notifications_full() -> list:
    conn   = get_conn()
    notifs = []
    cur = conn.execute("""
        SELECT c.*, u.full_name, u.username FROM charge_requests c
        JOIN users u ON u.id = c.user_id ORDER BY c.created_at DESC LIMIT 200
    """)
    for row in _fetchall_dict(cur):
        notifs.append({**row, "type": "charge", "icon": "💰",
                       "title": f"شحن رصيد — ${row['amount_usd']}", "subtitle": row["full_name"]})
    cur = conn.execute("""
        SELECT o.*, u.full_name, u.username FROM orders o
        JOIN users u ON u.id = o.user_id ORDER BY o.created_at DESC LIMIT 200
    """)
    for row in _fetchall_dict(cur):
        notifs.append({**row, "type": "order", "icon": "🛍️",
                       "title": f"طلب — {row['product_name']}", "subtitle": row["full_name"]})
    cur = conn.execute("""
        SELECT p.*, u.full_name, u.username FROM proxy_orders p
        JOIN users u ON u.id = p.user_id ORDER BY p.created_at DESC LIMIT 100
    """)
    for row in _fetchall_dict(cur):
        notifs.append({**row, "type": "proxy", "icon": "🌐",
                       "title": f"بروكسي — {row['proxy_type_label']}", "subtitle": row["full_name"]})
    cur = conn.execute("""
        SELECT a.*, u.full_name, u.username FROM appsflyer_orders a
        JOIN users u ON u.id = a.user_id ORDER BY a.created_at DESC LIMIT 100
    """)
    for row in _fetchall_dict(cur):
        notifs.append({**row, "type": "appsflyer", "icon": "🎮",
                       "title": f"AppsFlyer — {row['game_name']}", "subtitle": row["full_name"]})
    notifs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return notifs

def get_user_notifications(user_id: int) -> list:
    return [n for n in get_all_notifications_full() if n.get("user_id") == user_id]
