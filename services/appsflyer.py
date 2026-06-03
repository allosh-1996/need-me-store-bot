from infra.transactions import transactional
from repositories import appsflyer as af_repo
from repositories import wallet as wallet_repo
from domain.errors import InsufficientBalanceError, NotFoundError, InvalidStateTransitionError


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
            balance = wallet_repo.get_balance(user_id)
            if balance < price_usd:
                raise InsufficientBalanceError("insufficient balance")
            order_id = af_repo.create_order(
                user_id, game_key, game_name, price_usd,
                idfa, idfv, ios_version, appsflyer_id, levels,
            )
            wallet_repo.set_balance(user_id, balance - price_usd)
            wallet_repo.insert_ledger_entry(
                user_id, "debit", price_usd,
                "appsflyer_order", str(order_id), "appsflyer purchase",
            )
            return order_id
