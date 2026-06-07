from __future__ import annotations

from infra.db import execute


def create_charge(
    user_id: int,
    method: str,
    amount_usd: float,
    amount_raw: float | None,
    tx_hash: str | None,
    proof: str | None,
) -> int:
    cur = execute(
        """
        INSERT INTO charge_requests
            (user_id, method, amount_usd, amount_raw, tx_hash, proof, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (user_id, method, amount_usd, amount_raw, tx_hash, proof),
    )
    return cur.lastrowid


def get_charge(charge_id: int):
    return execute(
        "SELECT id, user_id, method, amount_usd, status FROM charge_requests WHERE id = ?",
        (charge_id,),
    ).fetchone()


def get_pending_charges(limit: int = 5, offset: int = 0) -> list:
    return execute(
        "SELECT id, user_id, method, amount_usd, status, created_at "
        "FROM charge_requests WHERE status = 'pending' "
        "ORDER BY id ASC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()


def count_pending_charges() -> int:
    row = execute(
        "SELECT COUNT(*) FROM charge_requests WHERE status = 'pending'"
    ).fetchone()
    return row[0] if row else 0


def get_recent_charges(limit: int = 100) -> list:
    return execute(
        "SELECT id, user_id, method, amount_usd, status, created_at "
        "FROM charge_requests ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def mark_confirmed(charge_id: int) -> None:
    execute(
        "UPDATE charge_requests SET status = 'confirmed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (charge_id,),
    )


def mark_rejected(charge_id: int) -> None:
    execute(
        "UPDATE charge_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (charge_id,),
    )
