import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from infra.db import init_db, execute, get_conn

PRODUCTS = [
    ("Toluna",          "Survey account",     2.0, "Survey Accounts",  "iOS"),
    ("Qmee",            "Survey account",     2.0, "Survey Accounts",  "iOS"),
    ("Coin Master",     "AppsFlyer track",    4.0, "AppsFlyer Track",  "iOS"),
    ("Disney Solitaire","AppsFlyer track",    4.0, "AppsFlyer Track",  "iOS"),
    ("Cash Giraffe",    "Games App",          2.0, "Games App",        "iOS"),
]


def main() -> None:
    init_db()
    added = 0
    for name, description, price_usd, category, platform in PRODUCTS:
        exists = execute("SELECT 1 FROM products WHERE name = ?", (name,)).fetchone()
        if exists:
            print(f"⏭️  Skip: {name}")
            continue
        execute(
            "INSERT INTO products (name, description, price_usd, category, platform, active) VALUES (?, ?, ?, ?, ?, 1)",
            (name, description, price_usd, category, platform),
        )
        print(f"✅ Added: {name}")
        added += 1
    get_conn().commit()
    print(f"\nDone — {added} added")


if __name__ == "__main__":
    main()
