from __future__ import annotations

from infra.db import execute


def create_order(
    user_id: int,
    game_key: str,
    game_name: str,
    price_usd: float,
    idfa: str,
    idfv: str,
    ios_version: str,
    appsflyer_id: str,
    levels: str,
) -> int:
    cur = execute(
        """
        INSERT INTO appsflyer_orders
            (user_id, game_key, game_name, price_usd, idfa, idfv, ios_version, appsflyer_id, levels, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (user_id, game_key, game_name, price_usd, idfa, idfv, ios_version, appsflyer_id, levels),
    )
    return cur.lastrowid


def get_order(order_id: int):
    return execute(
        "SELECT id, user_id, game_name, price_usd, status, game_key, idfa, idfv, ios_version, appsflyer_id, levels "
        "FROM appsflyer_orders WHERE id = ?",
        (order_id,),
    ).fetchone()


def get_pending_orders(limit: int = 5, offset: int = 0) -> list:
    return execute(
        "SELECT id, user_id, game_name, price_usd, status, created_at "
        "FROM appsflyer_orders WHERE status = 'pending' "
        "ORDER BY id ASC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()


def get_accepted_orders(limit: int = 5, offset: int = 0) -> list:
    return execute(
        "SELECT id, user_id, game_name, price_usd, status, created_at "
        "FROM appsflyer_orders WHERE status = 'accepted' "
        "ORDER BY id ASC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()


def count_pending_orders() -> int:
    row = execute(
        "SELECT COUNT(*) FROM appsflyer_orders WHERE status = 'pending'"
    ).fetchone()
    return row[0] if row else 0


def count_accepted_orders() -> int:
    row = execute(
        "SELECT COUNT(*) FROM appsflyer_orders WHERE status = 'accepted'"
    ).fetchone()
    return row[0] if row else 0


def update_status(order_id: int, status: str) -> None:
    execute(
        "UPDATE appsflyer_orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, order_id),
    )
