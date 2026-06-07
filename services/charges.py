from __future__ import annotations

from infra.transactions import transactional
from infra.db import sync_replica
from repositories import charges as charges_repo
from domain.errors import DuplicateProofError


class ChargeService:
    def create_charge(self, user_id, method, amount_usd, amount_raw, tx_hash, proof) -> int:
        try:
            with transactional():
                charge_id = charges_repo.create_charge(
                    user_id, method, amount_usd, amount_raw, tx_hash, proof
                )
            sync_replica()
            return charge_id
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise DuplicateProofError("duplicate proof or tx hash") from exc
            raise
