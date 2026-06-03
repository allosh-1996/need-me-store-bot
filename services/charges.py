from infra.transactions import transactional
from repositories import charges as charges_repo
from repositories import wallet as wallet_repo
from domain.errors import DuplicateProofError, NotFoundError, InvalidStateTransitionError


class ChargeService:
    def create_charge(
        self,
        user_id: int,
        method: str,
        amount_usd: float,
        amount_raw: float | None,
        tx_hash: str | None,
        proof: str | None,
    ) -> int:
        try:
            with transactional():
                return charges_repo.create_charge(
                    user_id, method, amount_usd, amount_raw, tx_hash, proof
                )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise DuplicateProofError("duplicate proof or tx hash") from exc
            raise
