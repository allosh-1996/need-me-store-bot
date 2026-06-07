from __future__ import annotations

from infra.transactions import transactional
from repositories import appsflyer as af_repo
from repositories import wallet as wallet_repo
from domain.errors import InsufficientBalanceError


class AppsflyerService:
    def create_order(
        self,
        user_id: int,
        game_key: str,
        game_name: str,
        price_usd: float,
        idfa: str,
        idfv: str,
        ios_version: str,
        appsflyer_id: str,
        levels: str,
    ) -> int:
        with transactional():
            order_id = af_repo.create_order(
                user_id, game_key, game_name, price_usd,
                idfa, idfv, ios_version, appsflyer_id, levels,
            )
            try:
                wallet_repo.debit_atomic(
                    user_id=user_id,
                    amount=price_usd,
                    entry_type="debit",
                    reference_type="appsflyer_order",
                    reference_id=str(order_id),
                    reason="appsflyer purchase",
                )
            except ValueError:
                raise InsufficientBalanceError("insufficient balance")
            return order_id
