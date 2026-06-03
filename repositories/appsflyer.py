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
        "SELECT id, user_id, game_name, price_usd, status, game_key, idfa, idfv, ios_version, appsflyer_id, levels FROM appsflyer_orders WHERE id = ?",
        (order_id,),
    ).fetchone()


def get_pending_orders(limit: int = 100) -> list:
    return execute(
        "SELECT id, user_id, game_name, price_usd, status, created_at FROM appsflyer_orders WHERE status = 'pending' ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def update_status(order_id: int, status: str) -> None:
    execute(
        "UPDATE appsflyer_orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, order_id),
    )
