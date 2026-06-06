"""
Idempotent product seeder — safe to run multiple times.
Usage: python scripts/seed_products.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from infra.db import init_db, execute

PRODUCTS = [
    ("Netflix Premium", "اشتراك نتفليكس بريميوم شهر", 8.0, "streaming", "All"),
    ("Spotify Premium", "اشتراك سبوتيفاي شهر", 5.0, "streaming", "All"),
    ("ChatGPT Plus", "اشتراك ChatGPT Plus شهر", 20.0, "ai", "All"),
]

def seed():
    init_db()
    for name, desc, price, cat, platform in PRODUCTS:
        existing = execute(
            "SELECT id FROM products WHERE name = ? AND active = 1", (name,)
        ).fetchone()
        if existing:
            print(f"⏭  Skipped (exists): {name}")
            continue
        execute(
            "INSERT INTO products (name, description, price_usd, category, platform, active) VALUES (?, ?, ?, ?, ?, 1)",
            (name, desc, price, cat, platform),
        )
        print(f"✅ Added: {name}")

if __name__ == "__main__":
    seed()
