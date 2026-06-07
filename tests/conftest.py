"""
Test fixtures using in-memory SQLite.

Root cause of previous failures:
  repositories do `from infra.db import execute` — they hold a direct reference
  to the function object, not a lookup through the module. monkeypatch on
  infra.db.execute does NOT affect those already-bound references.

Fix: patch `execute` in every repository module directly.
"""
from __future__ import annotations

import sqlite3
import threading
import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

class _SqliteResult:
    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._rows = [tuple(r) for r in cursor.fetchall()]
        self.lastrowid: int | None = cursor.lastrowid
        self.rowcount: int = cursor.rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list:
        return self._rows


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture()
def db(monkeypatch):
    """
    Fresh in-memory SQLite per test.
    Patches `execute` in every repository module AND in infra.db,
    and patches `transactional` in every service module.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.isolation_level = None  # manual transaction control
    _lock = threading.Lock()
    _tl   = threading.local()

    # ── SQLite execute ──────────────────────────────────────────────────────
    def sqlite_execute(sql: str, params: tuple = ()) -> _SqliteResult:
        cur = getattr(_tl, "txn_cursor", None)
        if cur is not None:
            cur.execute(sql, params)
            return _SqliteResult(cur)
        with _lock:
            c = conn.cursor()
            c.execute(sql, params)
            return _SqliteResult(c)

    # ── SQLite transactional ────────────────────────────────────────────────
    from contextlib import contextmanager

    @contextmanager
    def sqlite_transactional():
        if getattr(_tl, "active", False):
            yield
            return
        with _lock:
            cur = conn.cursor()
            cur.execute("BEGIN")
            _tl.active = True
            _tl.txn_cursor = cur
            try:
                yield
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                _tl.active = False
                _tl.txn_cursor = None

    # ── Patch infra.db.execute (for init_db and any direct callers) ─────────
    import infra.db as db_module
    monkeypatch.setattr(db_module, "execute", sqlite_execute)

    # ── Patch execute in every repository module ────────────────────────────
    import repositories.users        as r_users
    import repositories.wallet       as r_wallet
    import repositories.products     as r_products
    import repositories.stock        as r_stock
    import repositories.orders       as r_orders
    import repositories.charges      as r_charges
    import repositories.appsflyer    as r_af
    import repositories.admin_audit  as r_audit

    for mod in [r_users, r_wallet, r_products, r_stock,
                r_orders, r_charges, r_af, r_audit]:
        monkeypatch.setattr(mod, "execute", sqlite_execute)

    # ── Patch transactional in every service module ─────────────────────────
    import infra.transactions  as tx_module
    import services.orders     as svc_orders
    import services.wallet     as svc_wallet
    import services.charges    as svc_charges
    import services.appsflyer  as svc_af
    import services.admin      as svc_admin

    for mod in [tx_module, svc_orders, svc_wallet, svc_charges, svc_af, svc_admin]:
        monkeypatch.setattr(mod, "transactional", sqlite_transactional)

    # ── Build schema ────────────────────────────────────────────────────────
    from infra.db import init_db
    init_db()

    yield conn
    conn.close()


# ── Test helpers ───────────────────────────────────────────────────────────────

def _insert_user(conn: sqlite3.Connection, user_id: int, balance: float = 10.0) -> None:
    conn.execute(
        "INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)",
        (user_id, "testuser", "Test User"),
    )
    conn.execute(
        "INSERT INTO wallet_balances (user_id, balance_usd) VALUES (?, ?)",
        (user_id, balance),
    )


def _insert_product(
    conn: sqlite3.Connection, price: float = 5.0, stock_count: int = 1
) -> int:
    conn.execute(
        "INSERT INTO products (name, description, price_usd, category, platform, active) "
        "VALUES (?,?,?,?,?,1)",
        ("TestProd", "desc", price, "cat", "iOS"),
    )
    product_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i in range(stock_count):
        conn.execute(
            "INSERT INTO stock_items (product_id, content, status) VALUES (?, ?, 'available')",
            (product_id, f"KEY-{i}"),
        )
    return product_id
