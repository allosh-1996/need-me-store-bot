from infra.db import execute, get_conn


def reserve_first_available(product_id: int):
    return execute(
        "SELECT id, content FROM stock_items WHERE product_id = ? AND status = 'available' ORDER BY id ASC LIMIT 1",
        (product_id,),
    ).fetchone()


def mark_reserved(stock_item_id: int, order_id: int) -> None:
    execute(
        "UPDATE stock_items SET status = 'reserved', reserved_by_order_id = ?, reserved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (order_id, stock_item_id),
    )


def mark_sold(stock_item_id: int) -> None:
    execute(
        "UPDATE stock_items SET status = 'sold', sold_at = CURRENT_TIMESTAMP WHERE id = ?",
        (stock_item_id,),
    )


def release_reserved(stock_item_id: int) -> None:
    execute(
        "UPDATE stock_items SET status = 'available', reserved_by_order_id = NULL, reserved_at = NULL WHERE id = ?",
        (stock_item_id,),
    )


def add_stock_items(product_id: int, lines: list[str]) -> None:
    import libsql_client
    client = get_conn()
    statements = [
        libsql_client.Statement(
            "INSERT INTO stock_items (product_id, content, status) VALUES (?, ?, 'available')",
            [product_id, line],
        )
        for line in lines if line.strip()
    ]
    if statements:
        client.batch(statements)
