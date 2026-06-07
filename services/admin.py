from __future__ import annotations

from infra.transactions import transactional
from infra.db import sync_replica
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
            new_balance = wallet_repo.credit_atomic(
                user_id=user_id, amount=amount, entry_type="credit",
                reference_type="charge", reference_id=str(charge_id),
                reason="charge confirmed",
            )
            charges_repo.mark_confirmed(charge_id)
            audit_repo.log_action(admin_actor, "confirm_charge", "charge", str(charge_id), f"credited={amount}")
        sync_replica()
        return new_balance

    def reject_charge(self, admin_actor: str, charge_id: int) -> None:
        with transactional():
            charge = charges_repo.get_charge(charge_id)
            if not charge:
                raise NotFoundError("charge not found")
            if str(charge[4]) != "pending":
                raise InvalidStateTransitionError("charge already processed")
            charges_repo.mark_rejected(charge_id)
            audit_repo.log_action(admin_actor, "reject_charge", "charge", str(charge_id))
        sync_replica()

    def accept_appsflyer(self, admin_actor: str, order_id: int) -> None:
        with transactional():
            order = af_repo.get_order(order_id)
            if not order:
                raise NotFoundError("appsflyer order not found")
            if str(order[4]) != "pending":
                raise InvalidStateTransitionError("appsflyer order already processed")
            af_repo.update_status(order_id, "accepted")
            audit_repo.log_action(admin_actor, "accept_appsflyer", "appsflyer_order", str(order_id))
        sync_replica()

    def fulfill_appsflyer(self, admin_actor: str, order_id: int) -> None:
        with transactional():
            order = af_repo.get_order(order_id)
            if not order:
                raise NotFoundError("appsflyer order not found")
            if str(order[4]) != "accepted":
                raise InvalidStateTransitionError(f"can only fulfill accepted orders, current status: {order[4]}")
            af_repo.update_status(order_id, "fulfilled")
            audit_repo.log_action(admin_actor, "fulfill_appsflyer", "appsflyer_order", str(order_id))
        sync_replica()

    def reject_appsflyer(self, admin_actor: str, order_id: int) -> float:
        with transactional():
            order = af_repo.get_order(order_id)
            if not order:
                raise NotFoundError("appsflyer order not found")
            if str(order[4]) not in ("pending", "accepted"):
                raise InvalidStateTransitionError("appsflyer order already finalized")
            user_id = int(order[1])
            amount = float(order[3])
            new_balance = wallet_repo.credit_atomic(
                user_id=user_id, amount=amount, entry_type="refund",
                reference_type="appsflyer_order", reference_id=str(order_id),
                reason="appsflyer rejected",
            )
            af_repo.update_status(order_id, "rejected")
            audit_repo.log_action(admin_actor, "reject_appsflyer", "appsflyer_order", str(order_id), f"refunded={amount}")
        sync_replica()
        return new_balance
