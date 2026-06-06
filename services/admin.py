from infra.transactions import transactional
from repositories import charges as charges_repo
from repositories import appsflyer as af_repo
from repositories import wallet as wallet_repo
from repositories import admin_audit as audit_repo
from domain.errors import NotFoundError, InvalidStateTransitionError


class AdminService:
    def confirm_charge(self, admin_actor: str, charge_id: int) -> float:
        with transactional():
            charge = charges_repo.get_charge(charge_id)
            if not charge:
                raise NotFoundError("charge not found")
            if str(charge[4]) != "pending":
                raise InvalidStateTransitionError("charge already processed")
            user_id = int(charge[1])
            amount = float(charge[3])
            balance = wallet_repo.get_balance(user_id)
            new_balance = round(balance + amount, 8)
            wallet_repo.set_balance(user_id, new_balance)
            wallet_repo.insert_ledger_entry(
                user_id, "credit", amount, "charge", str(charge_id), "charge confirmed"
            )
            charges_repo.mark_confirmed(charge_id)
            audit_repo.log_action(
                admin_actor, "confirm_charge", "charge", str(charge_id), f"credited={amount}"
            )
            return new_balance

    def reject_charge(self, admin_actor: str, charge_id: int) -> None:
        with transactional():
            charge = charges_repo.get_charge(charge_id)
            if not charge:
                raise NotFoundError("charge not found")
            if str(charge[4]) != "pending":
                raise InvalidStateTransitionError("charge already processed")
            charges_repo.mark_rejected(charge_id)
            audit_repo.log_action(
                admin_actor, "reject_charge", "charge", str(charge_id)
            )

    def accept_appsflyer(self, admin_actor: str, order_id: int) -> None:
        with transactional():
            order = af_repo.get_order(order_id)
            if not order:
                raise NotFoundError("appsflyer order not found")
            if str(order[4]) != "pending":
                raise InvalidStateTransitionError("appsflyer order already processed")
            af_repo.update_status(order_id, "accepted")
            audit_repo.log_action(
                admin_actor, "accept_appsflyer", "appsflyer_order", str(order_id)
            )

    def reject_appsflyer(self, admin_actor: str, order_id: int) -> float:
        with transactional():
            order = af_repo.get_order(order_id)
            if not order:
                raise NotFoundError("appsflyer order not found")
            if str(order[4]) != "pending":
                raise InvalidStateTransitionError("appsflyer order already processed")
            user_id = int(order[1])
            amount = float(order[3])
            balance = wallet_repo.get_balance(user_id)
            new_balance = round(balance + amount, 8)
            wallet_repo.set_balance(user_id, new_balance)
            wallet_repo.insert_ledger_entry(
                user_id, "refund", amount,
                "appsflyer_order", str(order_id), "appsflyer rejected",
            )
            af_repo.update_status(order_id, "rejected")
            audit_repo.log_action(
                admin_actor, "reject_appsflyer", "appsflyer_order",
                str(order_id), f"refunded={amount}",
            )
            return new_balance
