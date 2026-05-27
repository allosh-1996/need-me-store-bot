"""
تشغيل مرة وحدة لإضافة المنتجات الأساسية
Run once to seed initial products
"""
import database as db
import os

db.init_db()

products = [
    # iOS - Survey Accounts
    {"name": "Toluna",          "description": "", "price_usd": 2.0, "price_syp": 200000, "category": "Survey Accounts", "platform": "iOS", "stock": ""},
    {"name": "Qmee",            "description": "", "price_usd": 2.0, "price_syp": 200000, "category": "Survey Accounts", "platform": "iOS", "stock": ""},
    # iOS - AppsFlyer Track
    {"name": "Coin Master",     "description": "", "price_usd": 2.0, "price_syp": 200000, "category": "AppsFlyer Track", "platform": "iOS", "stock": ""},
    {"name": "Disney Solitaire","description": "", "price_usd": 2.0, "price_syp": 200000, "category": "AppsFlyer Track", "platform": "iOS", "stock": ""},
    # iOS - Games App
    {"name": "Cash Giraffe",    "description": "", "price_usd": 2.0, "price_syp": 200000, "category": "Games App",       "platform": "iOS", "stock": ""},
]

for p in products:
    pid = db.add_product(
        name=p["name"], description=p["description"],
        price_usd=p["price_usd"], price_syp=p["price_syp"],
        category=p["category"], stock=p["stock"],
        platform=p["platform"]
    )
    print(f"✅ Added #{pid}: {p['name']} — {p['category']} ({p['platform']})")

print("\n🎉 All products seeded!")
