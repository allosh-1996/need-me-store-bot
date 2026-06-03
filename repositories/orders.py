from infra.db import execute


def create_order(user_id: int, product_id: int, amount_usd: float) -> int:
    cur = execute(
        "INSERT INTO orders (user_id, product_id, status, amount_usd) VALUES (?, ?, 'reserved', ?)",
        (user_id, product_id, amount_usd),
    )
    return cur.lastrowid


def attach_stock_and_payload(order_id: int, stock_item_id: int, payload: str) -> None:
    execute(
        "UPDATE orders SET stock_item_id = ?, delivery_payload = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (stock_item_id, payload, order_id),
    )


def mark_delivered(order_id: int) -> None:
    execute(
        "UPDATE orders SET status = 'delivered', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (order_id,),
    )


def mark_rejected(order_id: int) -> None:
    execute(
        "UPDATE orders SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (order_id,),
    )


def get_order(order_id: int):
    return execute(
        "SELECT id, user_id, product_id, stock_item_id, status, amount_usd, delivery_payload FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()


def get_recent_orders(limit: int = 100) -> list:
    return execute(
        "SELECT id, user_id, product_id, status, amount_usd, created_at FROM orders ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
