from __future__ import annotations

import logging
import libsql_client
from app.settings import get_settings

logger = logging.getLogger(__name__)

_client: libsql_client.ClientSync | None = None


def _open() -> libsql_client.ClientSync:
    s = get_settings()
    url = s.turso_database_url
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://"):]
    elif url.startswith("wss://"):
        url = "https://" + url[len("wss://"):]
    logger.info("Connecting to Turso via HTTP: %s", url.split("@")[-1])
    return libsql_client.create_client_sync(
        url=url,
        auth_token=s.turso_auth_token,
    )


def get_client() -> libsql_client.ClientSync:
    global _client
    if _client is None or _client.closed:
        _client = _open()
    return _client


def _reset() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


class _Result:
    def __init__(self, rs: libsql_client.ResultSet) -> None:
        self._rows = [tuple(r) for r in rs.rows]
        self.lastrowid: int | None = rs.last_insert_rowid
        self.rowcount: int = rs.rows_affected

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list:
        return self._rows


def execute(sql: str, params: tuple = ()) -> _Result:
    args = list(params) if params else None
    try:
        rs = get_client().execute(sql, args)
        return _Result(rs)
    except Exception as exc:
        logger.warning("Query failed (%s) — reconnecting once", exc)
        _reset()
        rs = get_client().execute(sql, args)
        return _Result(rs)


def execute_batch(statements: list[tuple[str, list]]) -> list[_Result]:
    """Execute multiple statements atomically via Turso batch."""
    stmts = [
        libsql_client.Statement(sql, args if args else None)
        for sql, args in statements
    ]
    try:
        results = get_client().batch(stmts)
        return [_Result(rs) for rs in results]
    except Exception as exc:
        logger.warning("Batch failed (%s) — reconnecting once", exc)
        _reset()
        results = get_client().batch(stmts)
        return [_Result(rs) for rs in results]


def init_db() -> None:
    stmts = [
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL DEFAULT '',
            full_name TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'ar',
            blocked INTEGER NOT NULL DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS wallet_balances (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            balance_usd REAL NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS ledger_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            entry_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            reference_type TEXT,
            reference_id TEXT,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price_usd REAL NOT NULL,
            category TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'iOS',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            reserved_by_order_id INTEGER,
            reserved_at TIMESTAMP,
            sold_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            stock_item_id INTEGER REFERENCES stock_items(id),
            status TEXT NOT NULL,
            amount_usd REAL NOT NULL,
            delivery_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS charge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            method TEXT NOT NULL,
            amount_usd REAL NOT NULL,
            amount_raw REAL,
            tx_hash TEXT UNIQUE,
            proof TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS appsflyer_orders (
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
        )""",
        """CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    for stmt in stmts:
        execute(stmt)
    logger.info("DB schema ready")
