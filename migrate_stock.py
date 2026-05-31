"""
migrate_stock.py — NexVault Bot
يحول stock TEXT القديم لجدول stock_items المنفصل.
شغّله مرة وحدة بعد deploy الكود الجديد:
    python migrate_stock.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import database as db

def migrate():
    db.init_db()
    conn = db.get_conn()

    # تحقق إذا في عمود stock قديم
    cur = conn.execute("PRAGMA table_info(products)")
    columns = [row[1] for row in cur.fetchall()]
    if "stock" not in columns:
        print("✅ لا يوجد عمود stock قديم — لا حاجة للـ migration.")
        return

    products = conn.execute(
        "SELECT id, name, stock FROM products WHERE stock IS NOT NULL AND stock != ''"
    ).fetchall()
    total_items = 0
    total_products = 0

    for product_id, name, stock_text in products:
        lines = [l.strip() for l in stock_text.splitlines() if l.strip()]
        if not lines:
            continue

        existing = conn.execute(
            "SELECT COUNT(*) FROM stock_items WHERE product_id = ?",
            (product_id,)
        ).fetchone()[0]
        if existing > 0:
            print(f"⏭️  #{product_id} {name} — تم migration مسبقاً ({existing} items)")
            continue

        conn.executemany(
            "INSERT INTO stock_items (product_id, content) VALUES (?, ?)",
            [(product_id, line) for line in lines]
        )
        conn.execute("UPDATE products SET stock = '' WHERE id = ?", (product_id,))
        total_items    += len(lines)
        total_products += 1
        print(f"✅ #{product_id} {name} — {len(lines)} items migrated")

    conn.commit()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products_new (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                description TEXT,
                price_usd   REAL,
                price_syp   REAL,
                category    TEXT,
                platform    TEXT    DEFAULT 'iOS',
                active      INTEGER DEFAULT 1,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO products_new
                (id, name, description, price_usd, price_syp, category, platform, active, created_at)
            SELECT id, name, description, price_usd, price_syp, category, platform, active, created_at
            FROM products
        """)
        conn.execute("DROP TABLE products")
        conn.execute("ALTER TABLE products_new RENAME TO products")
        conn.commit()
        print("✅ عمود stock القديم حُذف من جدول products")
    except Exception as e:
        print(f"⚠️ لم يتم حذف العمود القديم (غير ضروري): {e}")

    print(f"\n🎉 اكتمل الـ migration:")
    print(f"   - {total_products} منتج")
    print(f"   - {total_items} item في stock_items")

if __name__ == "__main__":
    migrate()
