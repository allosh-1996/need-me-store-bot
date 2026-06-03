from infra.db import execute


def get_balance(user_id: int) -> float:
    row = execute(
        "SELECT balance_usd FROM wallet_balances WHERE user_id = ?", (user_id,)
    ).fetchone()
    return float(row[0]) if row else 0.0


def set_balance(user_id: int, new_balance: float) -> None:
    execute(
        "UPDATE wallet_balances SET balance_usd = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
        (new_balance, user_id),
    )


def insert_ledger_entry(
    user_id: int,
    entry_type: str,
    amount: float,
    reference_type: str,
    reference_id: str,
    reason: str,
) -> None:
    execute(
        """
        INSERT INTO ledger_entries
            (user_id, entry_type, amount, reference_type, reference_id, reason)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, entry_type, amount, reference_type, reference_id, reason),
    )
