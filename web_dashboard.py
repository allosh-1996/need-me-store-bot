"""
web_dashboard.py — NexVault Bot
Flask dashboard backend. Includes /health endpoint (port 5000).
"""
import time
import logging
import os
import hashlib
import secrets as _secrets
import threading
import uuid

from functools import wraps
import requests as req_lib
from flask import Flask, render_template, request, jsonify, session, redirect, send_from_directory

import database as db
from config import ADMIN_ID, BOT_TOKEN

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=".")

# ════════════════════════════════════════
# Telegram Send — Retry + Exponential Backoff
# ════════════════════════════════════════

def tg_send(chat_id, text, retries=3):
    """Send a Telegram message with automatic retry on 429."""
    url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

    for attempt in range(retries + 1):
        try:
            resp = req_lib.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                return True
            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 2 ** attempt)
                logger.warning(f"tg_send 429 — retry after {retry_after}s (attempt {attempt + 1})")
                time.sleep(retry_after)
                continue
            logger.warning(f"tg_send {resp.status_code} for chat_id={chat_id}")
            return False
        except Exception as e:
            logger.error(f"tg_send error (attempt {attempt + 1}): {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)

    return False


# ════════════════════════════════════════
# Security Config
# ════════════════════════════════════════

_is_production = bool(
    os.environ.get("RAILWAY_ENVIRONMENT")
    or os.environ.get("RAILWAY_PROJECT_ID")
    or os.environ.get("RENDER")
    or os.environ.get("PRODUCTION")
)

_dashboard_secret = os.environ.get("DASHBOARD_SECRET")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")

if _is_production:
    if not DASHBOARD_PASSWORD:
        raise RuntimeError(
            "DASHBOARD_PASSWORD is not set. Add it to Railway Variables."
        )
    if not _dashboard_secret:
        raise RuntimeError(
            "DASHBOARD_SECRET is not set. Add it to Railway Variables."
        )
else:
    if not DASHBOARD_PASSWORD:
        DASHBOARD_PASSWORD = "dev_only_change_in_production"
        logger.warning("DASHBOARD_PASSWORD not set — using dev default.")
    if not _dashboard_secret:
        _dashboard_secret = _secrets.token_hex(32)
        logger.warning("DASHBOARD_SECRET not set — using random key (sessions won't persist).")

app.secret_key = _dashboard_secret
app.config["SESSION_COOKIE_SECURE"]   = _is_production
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"]     = "nx_session"

_auth_token = hashlib.sha256(
    (DASHBOARD_PASSWORD or "dev").encode() + (_dashboard_secret or "dev").encode()
).hexdigest()[:32]
app.config["AUTH_TOKEN"] = _auth_token


# ════════════════════════════════════════
# Auth
# ════════════════════════════════════════

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Auth-Token") or request.args.get("_t")
        if session.get("admin") or (token and token == app.config.get("AUTH_TOKEN")):
            return f(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"error": "unauthorized"}), 401
        return redirect("/login")
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["admin"] = True
            logger.info(f"Dashboard login from IP: {request.remote_addr}")
            token = app.config.get("AUTH_TOKEN", "")
            return redirect(f"/?_t={token}")
        logger.warning(f"Dashboard login failed from IP: {request.remote_addr}")
        error = "❌ كلمة السر غلط"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ════════════════════════════════════════
# Health & Static
# ════════════════════════════════════════

@app.route("/health")
def health():
    return {"status": "alive", "bot": "NexVault"}, 200


@app.route("/ping")
def ping():
    return "🌙 NexVault Bot — Online ✅"


@app.route("/")
@auth_required
def dashboard():
    return send_from_directory(".", "dashboard.html")


@app.route("/styles.css")
def styles():
    return send_from_directory(".", "styles.css")


@app.route("/theme.js")
def theme():
    return send_from_directory(".", "theme.js")


# ════════════════════════════════════════
# Stats & Products
# ════════════════════════════════════════

@app.route("/api/stats")
@auth_required
def api_stats():
    return jsonify(db.get_stats())


@app.route("/api/products")
@auth_required
def api_products():
    return jsonify([dict(p) for p in db.get_all_products(active_only=False)])


@app.route("/api/products/add", methods=["POST"])
@auth_required
def api_add_product():
    d   = request.json
    pid = db.add_product(
        name=d.get("name", ""),
        description=d.get("description", ""),
        price_usd=float(d.get("price_usd", 0)),
        price_syp=float(d.get("price_syp", 0)),
        category=d.get("category", ""),
        stock=d.get("stock", ""),
        platform=d.get("platform", "iOS"),
    )
    logger.info(f"Dashboard: product #{pid} added")
    return jsonify({"id": pid, "ok": True})


@app.route("/api/products/<int:pid>/delete", methods=["POST"])
@auth_required
def api_delete_product(pid):
    db.delete_product(pid)
    logger.info(f"Dashboard: product #{pid} deleted")
    return jsonify({"ok": True})


@app.route("/api/products/<int:pid>/stock", methods=["POST"])
@auth_required
def api_update_stock(pid):
    stock = request.json.get("stock", "")
    db.update_product_stock(pid, stock)
    count = db.get_stock_count(pid)
    logger.info(f"Dashboard: stock updated for product #{pid}: {count} units")
    return jsonify({"ok": True, "count": count})


# ════════════════════════════════════════
# Orders
# ════════════════════════════════════════

@app.route("/api/orders")
@auth_required
def api_orders():
    status = request.args.get("status", "")
    limit  = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    return jsonify(db.get_orders_paginated(status=status, limit=limit, offset=offset))


@app.route("/api/orders/<int:oid>/status", methods=["POST"])
@auth_required
def api_order_status(oid):
    status = request.json.get("status")
    order  = db.get_order(oid)

    if order and status == "completed":
        item, remaining = db.pop_stock_item(order["product_id"])
        if not item:
            return jsonify({"ok": False, "error": "No stock available for this product"}), 400
        db.update_order_delivered_item(oid, item)
        db.update_order_status(oid, status)
        logger.info(f"Dashboard: order #{oid} confirmed, stock remaining={remaining}")
        tg_send(order["user_id"],
            f"✅ *تم تأكيد طلبك!  |  Order Confirmed!*\n\n"
            f"\n—————————————————\n\n"
            f"🔖 Order ID: `#{oid}`\n"
            f"📦 {order['product_name']}\n"
            f"💵 ${order['price_usd']}\n"
            f"\n—————————————————\n\n"
            f"شكراً لثقتك 🙏  |  _Thank you!_"
        )
        tg_send(order["user_id"],
            f"🎁 *تفاصيل المنتج  |  Product Details*\n"
            f"\n—————————————————\n\n"
            f"`{item}`\n"
            f"\n—————————————————\n\n"
            f"_احفظ هذه المعلومات بأمان_"
        )
    elif order and status == "rejected":
        db.update_order_status(oid, status)
        logger.info(f"Dashboard: order #{oid} rejected")
        tg_send(order["user_id"],
            f"🔴 *تم رفض طلبك  |  Order Rejected*\n\n"
            f"\n—————————————————\n\n"
            f"🔖 Order ID: `#{oid}`\n"
            f"📦 {order['product_name']}\n"
            f"💵 ${order['price_usd']}\n"
            f"\n—————————————————\n\n"
            f"_للاستفسار تواصل مع الأدمن_"
        )
    else:
        db.update_order_status(oid, status)

    return jsonify({"ok": True})


# ════════════════════════════════════════
# Charges
# ════════════════════════════════════════

@app.route("/api/charges")
@auth_required
def api_charges():
    return jsonify(db.get_charges_recent())


@app.route("/api/charges/<int:cid>/confirm", methods=["POST"])
@auth_required
def api_confirm_charge(cid):
    charge = db.confirm_charge(cid)
    if charge:
        new_balance  = db.get_balance(charge["user_id"])
        method_label = "USDT BEP-20" if charge["method"] == "usdt" else "Syriatel Cash"
        logger.info(f"Dashboard: charge #{cid} confirmed, user={charge['user_id']}, amount=${charge['amount_usd']}")
        tg_send(charge["user_id"],
            f"✅ *تم شحن رصيدك!  |  Balance Added!*\n\n"
            f"\n—————————————————\n\n"
            f"💵 المبلغ المضاف  |  Added: `${charge['amount_usd']}`\n"
            f"💳 {method_label}\n"
            f"💰 رصيدك الحالي  |  New Balance: `${new_balance:.2f}`\n"
            f"\n—————————————————\n\n"
            f"_يمكنك الشراء الآن_ 🛍️"
        )
        return jsonify({"ok": True, "new_balance": new_balance})
    return jsonify({"ok": False, "error": "Not found or already processed"}), 404


@app.route("/api/charges/<int:cid>/reject", methods=["POST"])
@auth_required
def api_reject_charge(cid):
    charge = db.get_charge_request(cid)
    db.reject_charge(cid)
    if charge:
        method_label = "USDT BEP-20" if charge["method"] == "usdt" else "Syriatel Cash"
        logger.info(f"Dashboard: charge #{cid} rejected, user={charge['user_id']}")
        tg_send(charge["user_id"],
            f"🔴 *تم رفض طلب الشحن  |  Top Up Rejected*\n\n"
            f"\n—————————————————\n\n"
            f"💵 المبلغ  |  Amount: `${charge['amount_usd']}`\n"
            f"💳 {method_label}\n"
            f"\n—————————————————\n\n"
            f"_للاستفسار تواصل مع الأدمن_"
        )
    return jsonify({"ok": True})


@app.route("/api/charges/<int:cid>/proof_image")
@auth_required
def api_charge_proof_image(cid):
    charge = db.get_charge_request(cid)
    if not charge or not charge.get("proof"):
        return jsonify({"ok": False, "error": "No proof found"}), 404

    file_id = charge["proof"]
    try:
        resp    = req_lib.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=5,
        )
        result = resp.json()
        if not result.get("ok"):
            return jsonify({"ok": False, "error": "Telegram API error",
                            "is_file_id": True, "file_id": file_id}), 200
        file_path = result["result"]["file_path"]
        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        return jsonify({"ok": True, "url": image_url, "file_id": file_id})
    except Exception as e:
        logger.error(f"Proof image error: {e}")
        return jsonify({"ok": False, "error": str(e), "file_id": file_id}), 200


# ════════════════════════════════════════
# Users
# ════════════════════════════════════════

@app.route("/api/users")
@auth_required
def api_users():
    return jsonify(db.get_users_with_balances())


@app.route("/api/users/<int:uid>/add_balance", methods=["POST"])
@auth_required
def api_add_balance(uid):
    amount = float(request.json.get("amount", 0))
    if amount <= 0:
        return jsonify({"ok": False, "error": "Invalid amount"}), 400
    db.add_balance(uid, amount)
    new_balance = db.get_balance(uid)
    logger.info(f"Dashboard: added ${amount} to user {uid}, new balance=${new_balance}")
    tg_send(uid,
        f"✅ *تم إضافة رصيد إلى حسابك!*\n\n"
        f"💵 المبلغ المضاف: `${amount:.2f}`\n"
        f"💰 رصيدك الحالي: `${new_balance:.2f}`"
    )
    return jsonify({"ok": True, "new_balance": new_balance})


@app.route("/api/users/<int:uid>/deduct_balance", methods=["POST"])
@auth_required
def api_deduct_balance(uid):
    amount  = float(request.json.get("amount", 0))
    if amount <= 0:
        return jsonify({"ok": False, "error": "Invalid amount"}), 400
    current = db.get_balance(uid)
    if amount > current:
        return jsonify({"ok": False, "error": f"رصيد غير كافٍ — الرصيد الحالي: ${current:.2f}"}), 400
    db.deduct_balance_atomic(uid, amount)
    new_balance = db.get_balance(uid)
    logger.info(f"Dashboard: deducted ${amount} from user {uid}, new balance=${new_balance}")
    tg_send(uid,
        f"🔴 *تم خصم رصيد من حسابك*\n\n"
        f"💵 المبلغ المخصوم: `${amount:.2f}`\n"
        f"💰 رصيدك الحالي: `${new_balance:.2f}`"
    )
    return jsonify({"ok": True, "new_balance": new_balance})


@app.route("/api/users/<int:uid>/balance")
@auth_required
def api_get_balance(uid):
    return jsonify(db.get_balance_by_user(uid))


@app.route("/api/users/<int:uid>/delete", methods=["POST"])
@auth_required
def api_delete_user(uid):
    db.block_user(uid)
    logger.info(f"Dashboard: user {uid} blocked")
    return jsonify({"ok": True})


# ════════════════════════════════════════
# Notifications
# ════════════════════════════════════════

@app.route("/api/notifications")
@auth_required
def api_notifications():
    notifications = db.get_pending_notifications()
    return jsonify({"notifications": notifications, "count": len(notifications)})


@app.route("/api/notifications/all")
@auth_required
def api_notifications_all():
    return jsonify(db.get_all_notifications_full())


@app.route("/api/notifications/user/<int:uid>")
@auth_required
def api_user_notifications(uid):
    return jsonify(db.get_user_notifications(uid))


# ════════════════════════════════════════
# Broadcast — Non-Blocking Background Job
# ════════════════════════════════════════

# In-memory job tracker  {job_id: {"status": "running"|"done", "sent": int, "failed": int, "total": int}}
_broadcast_jobs: dict = {}
_broadcast_jobs_lock  = threading.Lock()


def _broadcast_worker(job_id: str, message: str, users: list):
    """
    Runs in a daemon thread. Sends to all users with a small delay
    between batches to stay under Telegram's 30 msg/s limit.
    Updates _broadcast_jobs[job_id] in place.
    """
    BATCH_SIZE  = 25
    BATCH_DELAY = 1.0  # seconds between batches

    sent   = 0
    failed = 0
    total  = len(users)

    for i in range(0, total, BATCH_SIZE):
        batch = users[i : i + BATCH_SIZE]
        for user in batch:
            ok = tg_send(user["id"], message)
            if ok:
                sent += 1
            else:
                failed += 1

        with _broadcast_jobs_lock:
            _broadcast_jobs[job_id]["sent"]   = sent
            _broadcast_jobs[job_id]["failed"] = failed

        if i + BATCH_SIZE < total:
            time.sleep(BATCH_DELAY)

    with _broadcast_jobs_lock:
        _broadcast_jobs[job_id]["status"] = "done"

    logger.info(f"Broadcast job {job_id}: sent={sent}, failed={failed}, total={total}")


@app.route("/api/broadcast", methods=["POST"])
@auth_required
def api_broadcast():
    msg = request.json.get("message", "")
    if not msg:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    users = db.get_all_users()
    total = len(users)

    # Persist in DB (is_sent=0 so the bot job_queue won't re-send it)
    conn = db.get_conn()
    cur  = conn.execute("INSERT INTO broadcasts (message, is_sent) VALUES (?, 1)", (msg,))
    broadcast_id = cur.lastrowid
    conn.commit()

    job_id = str(uuid.uuid4())
    with _broadcast_jobs_lock:
        _broadcast_jobs[job_id] = {"status": "running", "sent": 0, "failed": 0, "total": total}

    t = threading.Thread(
        target=_broadcast_worker,
        args=(job_id, msg, users),
        daemon=True,
    )
    t.start()

    logger.info(f"Broadcast job {job_id} started — {total} users, broadcast_id={broadcast_id}")
    return jsonify({"ok": True, "job_id": job_id, "total": total})


@app.route("/api/broadcast/status/<job_id>")
@auth_required
def api_broadcast_status(job_id):
    """Poll this endpoint to track broadcast progress."""
    with _broadcast_jobs_lock:
        job = _broadcast_jobs.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job not found"}), 404
    return jsonify({"ok": True, **job})


# ════════════════════════════════════════
# Proxy Orders
# ════════════════════════════════════════

@app.route("/api/proxy_orders")
@auth_required
def api_proxy_orders():
    return jsonify(db.get_proxy_orders())


@app.route("/api/proxy_orders/<int:oid>/status", methods=["POST"])
@auth_required
def api_proxy_order_status(oid):
    status = request.json.get("status")
    proxy  = next((p for p in db.get_proxy_orders() if p["id"] == oid), None)
    db.update_proxy_order_status(oid, status)
    logger.info(f"Dashboard: proxy order #{oid} status={status}")
    if proxy:
        if status == "completed":
            tg_send(proxy["user_id"],
                f"✅ *تم قبول طلب البروكسي!  |  Proxy Order Accepted!*\n\n"
                f"\n—————————————————\n\n"
                f"🔖 Order ID: `#{oid}`\n"
                f"📦 {proxy['proxy_type_label']} x{proxy['quantity']}\n"
                f"🌍 {proxy['country']}\n"
                f"\n—————————————————\n\n"
                f"⏳ _سيتم التواصل معك وإرسال البروكسيات قريباً_ 🚀"
            )
        elif status == "rejected":
            tg_send(proxy["user_id"],
                f"🔴 *تم رفض طلب البروكسي  |  Proxy Order Rejected*\n\n"
                f"\n—————————————————\n\n"
                f"🔖 Order ID: `#{oid}`\n"
                f"📦 {proxy['proxy_type_label']} x{proxy['quantity']}\n"
                f"🌍 {proxy['country']}\n"
                f"\n—————————————————\n\n"
                f"_للاستفسار تواصل مع الأدمن_"
            )
    return jsonify({"ok": True})


# ════════════════════════════════════════
# AppsFlyer Orders
# ════════════════════════════════════════

@app.route("/api/appsflyer_orders")
@auth_required
def api_appsflyer_orders():
    status = request.args.get("status", "")
    return jsonify(db.get_appsflyer_orders(status=status))


@app.route("/api/appsflyer_orders/<int:oid>/status", methods=["POST"])
@auth_required
def api_appsflyer_order_status(oid):
    status = request.json.get("status")
    order  = db.get_appsflyer_order(oid)

    if not order:
        return jsonify({"ok": False, "error": "Not found"}), 404
    if order["status"] != "pending":
        return jsonify({"ok": False, "error": "Already processed"}), 400

    if status == "accepted":
        db.update_appsflyer_order_status(oid, "accepted")
        logger.info(f"Dashboard: AppsFlyer order #{oid} accepted")
        levels_info = f"\n🎯 *الليفلات:* `{order['levels']}`" if order.get("levels") else ""
        tg_send(order["user_id"],
            f"✅ *تم قبول طلبك!*\n\n"
            f"🎮 *اللعبة:* {order['game_name']}\n"
            f"🔢 *رقم الطلب:* `#{oid}`"
            f"{levels_info}\n\n"
            f"🚀 *طلبك الآن قيد التنفيذ*\n\n"
            f"\n—————————————————\n\n"
            f"📩 للمتابعة تواصل مع الأدمن:\n"
            f"👤 @Allosh96ha\n"
            f"\n—————————————————\n"
        )
    elif status == "rejected":
        db.add_balance(order["user_id"], order["price_usd"])
        new_balance = db.get_balance(order["user_id"])
        db.update_appsflyer_order_status(oid, "rejected")
        logger.info(f"Dashboard: AppsFlyer order #{oid} rejected — refunded ${order['price_usd']}")
        tg_send(order["user_id"],
            f"❌ *تم رفض طلبك*\n\n"
            f"🎮 *اللعبة:* {order['game_name']}\n"
            f"🔢 *رقم الطلب:* `#{oid}`\n\n"
            f"💰 *تم إعادة المبلغ:* `${order['price_usd']:.2f}`\n"
            f"💳 *رصيدك الحالي:* `${new_balance:.2f}`\n\n"
            f"\n—————————————————\n\n"
            f"📩 للاستفسار تواصل مع الأدمن:\n"
            f"👤 @Allosh96ha\n"
            f"\n—————————————————\n"
        )
    else:
        return jsonify({"ok": False, "error": "Invalid status"}), 400

    return jsonify({"ok": True})


# ════════════════════════════════════════
# Entry Point
# ════════════════════════════════════════

def run_dashboard():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
