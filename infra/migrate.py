from __future__ import annotations
import logging
from infra.db import execute

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "users":            ["id", "username", "full_name", "language", "blocked", "joined_at"],
    "wallet_balances":  ["user_id", "balance_usd", "updated_at"],
    "ledger_entries":   ["id", "user_id", "entry_type", "amount", "currency", "reference_type", "reference_id", "reason", "created_at"],
    "products":         ["id", "name", "description", "price_usd", "category", "platform", "active", "created_at"],
    "stock_items":      ["id", "product_id", "content", "status", "reserved_by_order_id", "reserved_at", "sold_at", "created_at"],
    "orders":           ["id", "user_id", "product_id", "stock_item_id", "status", "amount_usd", "delivery_payload", "created_at", "updated_at"],
    "charge_requests":  ["id", "user_id", "method", "amount_usd", "amount_raw", "tx_hash", "proof", "status", "created_at", "updated_at"],
    "appsflyer_orders": ["id", "user_id", "game_key", "game_name", "price_usd", "idfa", "idfv", "ios_version", "appsflyer_id", "levels", "status", "created_at", "updated_at"],
    "admin_audit_logs": ["id", "actor", "action", "target_type", "target_id", "details", "created_at"],
}

AUTO_MIGRATIONS: list[tuple[str, str, str]] = [
    # (table, column, alter_sql)
    ("users",            "language",             "ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'ar'"),
    ("users",            "blocked",              "ALTER TABLE users ADD COLUMN blocked INTEGER NOT NULL DEFAULT 0"),
    ("users",            "joined_at",            "ALTER TABLE users ADD COLUMN joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("stock_items",      "status",               "ALTER TABLE stock_items ADD COLUMN status TEXT NOT NULL DEFAULT 'available'"),
    ("stock_items",      "reserved_by_order_id", "ALTER TABLE stock_items ADD COLUMN reserved_by_order_id INTEGER"),
    ("stock_items",      "reserved_at",          "ALTER TABLE stock_items ADD COLUMN reserved_at TIMESTAMP"),
    ("orders",           "stock_item_id",        "ALTER TABLE orders ADD COLUMN stock_item_id INTEGER"),
    ("orders",           "amount_usd",           "ALTER TABLE orders ADD COLUMN amount_usd REAL NOT NULL DEFAULT 0"),
    ("orders",           "delivery_payload",     "ALTER TABLE orders ADD COLUMN delivery_payload TEXT"),
    ("orders",           "updated_at",           "ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("charge_requests",  "updated_at",           "ALTER TABLE charge_requests ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("appsflyer_orders", "updated_at",           "ALTER TABLE appsflyer_orders ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
]


def run_migrations() -> None:
    """Run all pending schema migrations at startup. Safe to call multiple times."""
    for table, column, sql in AUTO_MIGRATIONS:
        rows = execute(f"PRAGMA table_info({table})").fetchall()
        live_cols = [r[1] for r in rows]
        if column not in live_cols:
            try:
                execute(sql)
                logger.info("Migration applied: %s.%s", table, column)
            except Exception as exc:
                logger.error("Migration failed for %s.%s: %s", table, column, exc)


def verify_schema() -> None:
    """Verify all required columns exist after migrations. Raises RuntimeError if not."""
    errors = []
    for table, cols in REQUIRED_COLUMNS.items():
        rows = execute(f"PRAGMA table_info({table})").fetchall()
        live_cols = [r[1] for r in rows]
        missing = [c for c in cols if c not in live_cols]
        if missing:
            errors.append(f"{table}: missing {missing}")
    if errors:
        raise RuntimeError("Schema incompatible with code: " + "; ".join(errors))
    logger.info("Schema verification passed")
