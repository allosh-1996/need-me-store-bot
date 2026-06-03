from infra.db import execute


def get_active_products() -> list:
    return execute(
        "SELECT id, name, description, price_usd, category, platform "
        "FROM products WHERE active = 1 ORDER BY id ASC"
    ).fetchall()


def get_product(product_id: int):
    return execute(
        "SELECT id, name, description, price_usd, category, platform, active "
        "FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()


def add_product(
    name: str, description: str, price_usd: float, category: str, platform: str
) -> int:
    result = execute(
        "INSERT INTO products (name, description, price_usd, category, platform, active) "
        "VALUES (?, ?, ?, ?, ?, 1)",
        (name, description, price_usd, category, platform),
    )
    return result.lastrowid


def deactivate_product(product_id: int) -> None:
    execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))


def get_stock_count(product_id: int) -> int:
    row = execute(
        "SELECT COUNT(*) FROM stock_items WHERE product_id = ? AND status = 'available'",
        (product_id,),
    ).fetchone()
    return row[0] if row else 0
