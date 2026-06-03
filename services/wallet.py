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
            balance = wallet_repo.get_balance(user_id)
            new_balance = balance + amount
            wallet_repo.set_balance(user_id, new_balance)
            wallet_repo.insert_ledger_entry(
                user_id, "credit", amount, reference_type, reference_id, reason
            )
            return new_balance

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
            balance = wallet_repo.get_balance(user_id)
            if balance < amount:
                raise InsufficientBalanceError("insufficient balance")
            new_balance = balance - amount
            wallet_repo.set_balance(user_id, new_balance)
            wallet_repo.insert_ledger_entry(
                user_id, "debit", amount, reference_type, reference_id, reason
            )
            return new_balance
