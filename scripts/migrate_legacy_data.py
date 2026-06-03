"""
Legacy data migration scaffold.
Export data from old DB, then implement mappings here.
Order: users -> balances -> products -> stock -> orders -> charges -> appsflyer
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from infra.db import init_db


def main() -> None:
    init_db()
    print("Implement legacy migration field mappings here.")


if __name__ == "__main__":
    main()
