from infra.db import execute


def reserve_first_available(product_id: int):
    """
    Atomically reserve the first available stock item using a single UPDATE statement.
    This eliminates the SELECT → UPDATE race condition where two concurrent buyers
    could read the same row before either marks it reserved.

    Returns (id, content) tuple or None if out of stock.
    """
    # SQLite supports RETURNING; this is a single atomic operation.
    result = execute(
        """
        UPDATE stock_items
           SET status             = 'reserved',
               reserved_at        = CURRENT_TIMESTAMP
         WHERE id = (
               SELECT id FROM stock_items
                WHERE product_id = ? AND status = 'available'
                ORDER BY id ASC
                LIMIT 1
         )
        RETURNING id, content
        """,
        (product_id,),
    ).fetchone()
    return result  # (id, content) or None


def mark_reserved(stock_item_id: int, order_id: int) -> None:
    """Attach the order_id to an already-reserved stock item."""
    execute(
        "UPDATE stock_items SET reserved_by_order_id = ? WHERE id = ?",
        (order_id, stock_item_id),
    )


def mark_sold(stock_item_id: int) -> None:
    execute(
        "UPDATE stock_items SET status = 'sold', sold_at = CURRENT_TIMESTAMP WHERE id = ?",
        (stock_item_id,),
    )


def release_reserved(stock_item_id: int) -> None:
    execute(
        "UPDATE stock_items SET status = 'available', "
        "reserved_by_order_id = NULL, reserved_at = NULL WHERE id = ?",
        (stock_item_id,),
    )


def add_stock_items(product_id: int, lines: list[str]) -> None:
    for line in lines:
        if line.strip():
            execute(
                "INSERT INTO stock_items (product_id, content, status) "
                "VALUES (?, ?, 'available')",
                (product_id, line.strip()),
            )
