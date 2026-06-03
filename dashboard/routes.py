from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from dashboard.auth import verify_password, login_required, SESSION_KEY
from infra.db import execute

bp = Blueprint("dashboard", __name__)


@bp.get("/login")
def login():
    return render_template("login.html")


@bp.post("/login")
def login_post():
    password = request.form.get("password", "")
    if not verify_password(password):
        flash("Invalid password", "error")
        return redirect(url_for("dashboard.login"))
    session[SESSION_KEY] = True
    return redirect(url_for("dashboard.home"))


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard.login"))


@bp.get("/")
@login_required
def home():
    users    = execute("SELECT COUNT(*) FROM users WHERE blocked = 0").fetchone()[0]
    products = execute("SELECT COUNT(*) FROM products WHERE active = 1").fetchone()[0]
    orders   = execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    charges  = execute("SELECT COUNT(*) FROM charge_requests WHERE status = 'pending'").fetchone()[0]
    af_pend  = execute("SELECT COUNT(*) FROM appsflyer_orders WHERE status = 'pending'").fetchone()[0]
    return render_template("dashboard.html",
        users=users, products=products, orders=orders,
        charges=charges, af_pending=af_pend)


@bp.get("/api/orders")
@login_required
def api_orders():
    rows = execute(
        "SELECT id, user_id, product_id, status, amount_usd, created_at FROM orders ORDER BY id DESC LIMIT 100"
    ).fetchall()
    return jsonify([{"id":r[0],"user_id":r[1],"product_id":r[2],"status":r[3],"amount_usd":r[4],"created_at":r[5]} for r in rows])


@bp.get("/api/charges")
@login_required
def api_charges():
    rows = execute(
        "SELECT id, user_id, method, amount_usd, status, created_at FROM charge_requests ORDER BY id DESC LIMIT 100"
    ).fetchall()
    return jsonify([{"id":r[0],"user_id":r[1],"method":r[2],"amount_usd":r[3],"status":r[4],"created_at":r[5]} for r in rows])


@bp.get("/api/appsflyer")
@login_required
def api_appsflyer():
    rows = execute(
        "SELECT id, user_id, game_name, price_usd, status, created_at FROM appsflyer_orders ORDER BY id DESC LIMIT 100"
    ).fetchall()
    return jsonify([{"id":r[0],"user_id":r[1],"game_name":r[2],"price_usd":r[3],"status":r[4],"created_at":r[5]} for r in rows])
