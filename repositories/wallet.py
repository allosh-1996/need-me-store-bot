from __future__ import annotations

from infra.db import execute


def get_balance(user_id: int) -> float:
    row = execute(
        "SELECT balance_usd FROM wallet_balances WHERE user_id = ?", (user_id,)
    ).fetchone()
    return float(row[0]) if row else 0.0


def credit_atomic(
    user_id: int,
    amount: float,
    entry_type: str,
    reference_type: str,
    reference_id: str,
    reason: str,
) -> float:
    """
    Atomically add `amount` to the user's balance and write a ledger entry.
    Returns the new balance.
    Must be called inside a transactional() context.
    """
    result = execute(
        """
        UPDATE wallet_balances
           SET balance_usd = ROUND(balance_usd + ?, 8),
               updated_at  = CURRENT_TIMESTAMP
         WHERE user_id = ?
        """,
        (amount, user_id),
    )
    if result.rowcount == 0:
        raise RuntimeError(f"wallet_balances row missing for user {user_id}")
    insert_ledger_entry(user_id, entry_type, amount, reference_type, reference_id, reason)
    return get_balance(user_id)


def debit_atomic(
    user_id: int,
    amount: float,
    entry_type: str,
    reference_type: str,
    reference_id: str,
    reason: str,
) -> float:
    """
    Atomically subtract `amount` from the user's balance only if sufficient funds exist.
    Returns the new balance.
    Raises ValueError if balance would go negative.
    Must be called inside a transactional() context.
    """
    result = execute(
        """
        UPDATE wallet_balances
           SET balance_usd = ROUND(balance_usd - ?, 8),
               updated_at  = CURRENT_TIMESTAMP
         WHERE user_id = ?
           AND balance_usd >= ?
        """,
        (amount, user_id, amount),
    )
    if result.rowcount == 0:
        # Either user doesn't exist or insufficient balance
        balance = get_balance(user_id)
        raise ValueError(f"insufficient_balance:{balance:.8f}")
    insert_ledger_entry(user_id, entry_type, amount, reference_type, reference_id, reason)
    return get_balance(user_id)


def set_balance(user_id: int, new_balance: float) -> None:
    """Direct set — use only in admin adjustments, not in purchase flows."""
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
