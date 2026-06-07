from __future__ import annotations

from infra.transactions import transactional
from repositories import wallet as wallet_repo
from domain.errors import InsufficientBalanceError, ValidationError


class WalletService:
    def get_balance(self, user_id: int) -> float:
        return wallet_repo.get_balance(user_id)

    def credit(
        self,
        user_id: int,
        amount: float,
        reason: str,
        reference_type: str,
        reference_id: str,
    ) -> float:
        if amount <= 0:
            raise ValidationError("credit amount must be positive")
        with transactional():
            return wallet_repo.credit_atomic(
                user_id=user_id,
                amount=amount,
                entry_type="credit",
                reference_type=reference_type,
                reference_id=reference_id,
                reason=reason,
            )

    def debit(
        self,
        user_id: int,
        amount: float,
        reason: str,
        reference_type: str,
        reference_id: str,
    ) -> float:
        if amount <= 0:
            raise ValidationError("debit amount must be positive")
        with transactional():
            # debit_atomic now raises InsufficientBalanceError directly
            return wallet_repo.debit_atomic(
                user_id=user_id,
                amount=amount,
                entry_type="debit",
                reference_type=reference_type,
                reference_id=reference_id,
                reason=reason,
            )
