from __future__ import annotations

import logging
import threading
import libsql_experimental as libsql
from app.settings import get_settings

logger = logging.getLogger(__name__)

_local = threading.local()


def _open_conn() -> libsql.Connection:
    settings = get_settings()
    return libsql.connect(
        database=settings.turso_database_url,
        auth_token=settings.turso_auth_token,
    )


def get_conn() -> libsql.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        logger.info("Opening Turso connection")
        conn = _open_conn()
        _local.conn = conn
    return conn


def close_conn() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None


def execute(sql: str, params: tuple = ()):
    """
    Execute SQL. On any exception, drop the connection and retry once
    on a fresh one — handles Turso silently closing idle connections.
    """
    try:
        return get_conn().execute(sql, params)
    except Exception as exc:
        logger.warning("Query failed (%s) — reconnecting and retrying", exc)
        close_conn()
        return get_conn().execute(sql, params)


def init_db() -> None:
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL DEFAULT '',
            full_name TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'ar',
            blocked INTEGER NOT NULL DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wallet_balances (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            balance_usd REAL NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            entry_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            reference_type TEXT,
            reference_id TEXT,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price_usd REAL NOT NULL,
            category TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'iOS',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            reserved_by_order_id INTEGER,
            reserved_at TIMESTAMP,
            sold_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            stock_item_id INTEGER REFERENCES stock_items(id),
            status TEXT NOT NULL,
            amount_usd REAL NOT NULL,
            delivery_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS charge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            method TEXT NOT NULL,
            amount_usd REAL NOT NULL,
            amount_raw REAL,
            tx_hash TEXT UNIQUE,
            proof TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS appsflyer_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            game_key TEXT NOT NULL,
            game_name TEXT NOT NULL,
            price_usd REAL NOT NULL,
            idfa TEXT NOT NULL,
            idfv TEXT NOT NULL,
            ios_version TEXT NOT NULL,
            appsflyer_id TEXT NOT NULL,
            levels TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    logger.info("DB schema ready")
