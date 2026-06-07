from infra.db import execute


def get_active_products() -> list:
    return execute(
        "SELECT id, name, description, price_usd, category, platform "
        "FROM products WHERE active = 1 ORDER BY id ASC"
    ).fetchall()


def get_active_products_by_category(category: str) -> list:
    return execute(
        "SELECT id, name, description, price_usd, category, platform "
        "FROM products WHERE active = 1 AND category = ? ORDER BY id ASC",
        (category,),
    ).fetchall()


def get_product(product_id: int):
    return execute(
        "SELECT id, name, description, price_usd, category, platform, active "
        "FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()


def get_product_with_stock(product_id: int):
    """
    Returns (id, name, description, price_usd, category, platform, active, stock_count)
    in a single query — avoids two round-trips to get product + stock.
    """
    return execute(
        """
        SELECT p.id, p.name, p.description, p.price_usd, p.category, p.platform, p.active,
               COUNT(s.id) as stock_count
          FROM products p
          LEFT JOIN stock_items s ON s.product_id = p.id AND s.status = 'available'
         WHERE p.id = ?
         GROUP BY p.id
        """,
        (product_id,),
    ).fetchone()


def get_active_products_with_stock(category: str | None = None) -> list:
    """
    Returns products with stock count in a single query.
    Each row: (id, name, description, price_usd, category, platform, stock_count)
    """
    if category:
        return execute(
            """
            SELECT p.id, p.name, p.description, p.price_usd, p.category, p.platform,
                   COUNT(s.id) as stock_count
              FROM products p
              LEFT JOIN stock_items s ON s.product_id = p.id AND s.status = 'available'
             WHERE p.active = 1 AND p.category = ?
             GROUP BY p.id
             ORDER BY p.id ASC
            """,
            (category,),
        ).fetchall()
    return execute(
        """
        SELECT p.id, p.name, p.description, p.price_usd, p.category, p.platform,
               COUNT(s.id) as stock_count
          FROM products p
          LEFT JOIN stock_items s ON s.product_id = p.id AND s.status = 'available'
         WHERE p.active = 1
         GROUP BY p.id
         ORDER BY p.id ASC
        """,
    ).fetchall()


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
