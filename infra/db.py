from __future__ import annotations

import logging
import threading
import libsql_client
from app.settings import get_settings

logger = logging.getLogger(__name__)

_local = threading.local()


# ──────────────────────────────────────────────
# Cursor wrapper — mimics sqlite3 cursor API
# so all repositories work without changes
# ──────────────────────────────────────────────

class _Result:
    """Wraps libsql_client.ResultSet to expose fetchone/fetchall/lastrowid."""

    def __init__(self, rs: libsql_client.ResultSet) -> None:
        self._rows = [tuple(row) for row in rs.rows]
        self.lastrowid: int | None = rs.last_insert_rowid
        self.rowcount: int = rs.rows_affected

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list:
        return self._rows


# ──────────────────────────────────────────────
# Connection management
# ──────────────────────────────────────────────

def _open_client() -> libsql_client.ClientSync:
    settings = get_settings()
    return libsql_client.create_client_sync(
        url=settings.turso_database_url,
        auth_token=settings.turso_auth_token,
    )


def get_conn() -> libsql_client.ClientSync:
    client = getattr(_local, "client", None)
    if client is None or client.closed:
        logger.info("Opening Turso client")
        client = _open_client()
        _local.client = client
    return client


def close_conn() -> None:
    client = getattr(_local, "client", None)
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
        _local.client = None


# ──────────────────────────────────────────────
# Query helper
# ──────────────────────────────────────────────

def execute(sql: str, params: tuple = ()) -> _Result:
    """
    Execute SQL and return a cursor-compatible _Result.
    On failure, reconnect once and retry.
    """
    args = list(params) if params else None
    try:
        rs = get_conn().execute(sql, args)
        return _Result(rs)
    except Exception as exc:
        logger.warning("Query failed (%s) — reconnecting and retrying", exc)
        close_conn()
        rs = get_conn().execute(sql, args)
        return _Result(rs)


# ──────────────────────────────────────────────
# Transaction helper
# ──────────────────────────────────────────────

def commit() -> None:
    """No-op: libsql_client auto-commits each statement."""
    pass


# ──────────────────────────────────────────────
# Schema initialisation
# ──────────────────────────────────────────────

def init_db() -> None:
    client = get_conn()
    client.batch([
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL DEFAULT '',
            full_name TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'ar',
            blocked INTEGER NOT NULL DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS wallet_balances (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            balance_usd REAL NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ])
    logger.info("DB schema ready")
