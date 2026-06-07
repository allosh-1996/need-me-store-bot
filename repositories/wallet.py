from __future__ import annotations

from infra.db import execute
from domain.errors import InsufficientBalanceError


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
    Must be called inside a transactional() context.
    """
    execute(
        """
        UPDATE wallet_balances
           SET balance_usd = ROUND(balance_usd + ?, 8),
               updated_at  = CURRENT_TIMESTAMP
         WHERE user_id = ?
        """,
        (amount, user_id),
    )
    changed = execute("SELECT changes()").fetchone()
    if not changed or changed[0] == 0:
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
    Raises InsufficientBalanceError directly — no ValueError wrapping needed upstream.
    Must be called inside a transactional() context.
    """
    execute(
        """
        UPDATE wallet_balances
           SET balance_usd = ROUND(balance_usd - ?, 8),
               updated_at  = CURRENT_TIMESTAMP
         WHERE user_id = ?
           AND balance_usd >= ?
        """,
        (amount, user_id, amount),
    )
    changed = execute("SELECT changes()").fetchone()
    if not changed or changed[0] == 0:
        balance = get_balance(user_id)
        raise InsufficientBalanceError(
            f"Insufficient balance: have ${balance:.2f}, need ${amount:.2f}"
        )
    insert_ledger_entry(user_id, entry_type, amount, reference_type, reference_id, reason)
    return get_balance(user_id)


def set_balance(user_id: int, new_balance: float) -> None:
    """Direct set — use only in admin adjustments."""
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
