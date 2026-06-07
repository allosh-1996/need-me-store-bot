"""
Test fixtures using in-memory libsql (sqlite3-compatible).
Patches `execute` in every repository module directly.
"""
from __future__ import annotations

import threading
import pytest
import libsql_experimental as libsql

import infra.db as db_module
from infra.db import init_db


class _LibsqlResult:
    def __init__(self, cursor) -> None:
        rows = cursor.fetchall(); self._rows = [tuple(r) for r in rows] if rows is not None else []
        self.lastrowid: int | None = cursor.lastrowid
        self.rowcount: int = cursor.rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list:
        return self._rows


@pytest.fixture()
def db(monkeypatch):
    """
    Fresh in-memory libsql DB per test.
    Patches `execute` in every repository module.
    """
    conn = libsql.connect(":memory:")
    _lock = threading.Lock()
    _tl   = threading.local()

    def sqlite_execute(sql: str, params: tuple = ()) -> _LibsqlResult:
        cur = getattr(_tl, "txn_cursor", None)
        if cur is not None:
            cur.execute(sql, params)
            return _LibsqlResult(cur)
        with _lock:
            c = conn.cursor()
            c.execute(sql, params)
            conn.commit()
            return _LibsqlResult(c)

    from contextlib import contextmanager

    @contextmanager
    def sqlite_transactional():
        if getattr(_tl, "active", False):
            yield
            return
        with _lock:
            cur = conn.cursor()
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

    monkeypatch.setattr(db_module, "execute", sqlite_execute)

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

    import infra.transactions  as tx_module
    import services.orders     as svc_orders
    import services.wallet     as svc_wallet
    import services.charges    as svc_charges
    import services.appsflyer  as svc_af
    import services.admin      as svc_admin

    for mod in [tx_module, svc_orders, svc_wallet, svc_charges, svc_af, svc_admin]:
        monkeypatch.setattr(mod, "transactional", sqlite_transactional)

    init_db()
    yield conn
    conn.close()


def _insert_user(conn, user_id: int, balance: float = 10.0) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)",
        (user_id, "testuser", "Test User"),
    )
    cur.execute(
        "INSERT INTO wallet_balances (user_id, balance_usd) VALUES (?, ?)",
        (user_id, balance),
    )
    conn.commit()


def _insert_product(conn, price: float = 5.0, stock_count: int = 1) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (name, description, price_usd, category, platform, active) "
        "VALUES (?,?,?,?,?,1)",
        ("TestProd", "desc", price, "cat", "iOS"),
    )
    conn.commit()
    product_id = cur.lastrowid
    for i in range(stock_count):
        cur.execute(
            "INSERT INTO stock_items (product_id, content, status) VALUES (?, ?, 'available')",
            (product_id, f"KEY-{i}"),
        )
    conn.commit()
    return product_id
