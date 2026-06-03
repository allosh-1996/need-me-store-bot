from __future__ import annotations
from flask import Blueprint, jsonify
from dashboard.auth import login_required
from services.admin import AdminService
from domain.errors import NotFoundError, InvalidStateTransitionError

bp_admin = Blueprint("dashboard_admin", __name__, url_prefix="/admin-api")
service = AdminService()


@bp_admin.post("/charges/<int:charge_id>/confirm")
@login_required
def confirm_charge(charge_id: int):
    try:
        balance = service.confirm_charge("dashboard", charge_id)
        return jsonify({"ok": True, "balance": balance})
    except (NotFoundError, InvalidStateTransitionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp_admin.post("/charges/<int:charge_id>/reject")
@login_required
def reject_charge(charge_id: int):
    try:
        service.reject_charge("dashboard", charge_id)
        return jsonify({"ok": True})
    except (NotFoundError, InvalidStateTransitionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp_admin.post("/appsflyer/<int:order_id>/accept")
@login_required
def accept_appsflyer(order_id: int):
    try:
        service.accept_appsflyer("dashboard", order_id)
        return jsonify({"ok": True})
    except (NotFoundError, InvalidStateTransitionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp_admin.post("/appsflyer/<int:order_id>/reject")
@login_required
def reject_appsflyer(order_id: int):
    try:
        balance = service.reject_appsflyer("dashboard", order_id)
        return jsonify({"ok": True, "balance": balance})
    except (NotFoundError, InvalidStateTransitionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
