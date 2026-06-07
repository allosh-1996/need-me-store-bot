from __future__ import annotations

import os
from flask import Flask, jsonify
from flask_wtf.csrf import CSRFProtect
from app.settings import get_settings
from dashboard.routes import bp as dashboard_bp
from dashboard.routes_admin import bp_admin

csrf = CSRFProtect()


def create_dashboard() -> Flask:
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = get_settings().dashboard_secret
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("RAILWAY_ENVIRONMENT") is not None,
        WTF_CSRF_TIME_LIMIT=None,  # no expiry — dashboard is long-lived
    )
    csrf.init_app(app)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(bp_admin)

    @app.get("/health")
    @csrf.exempt
    def health():
        return jsonify({"ok": True})

    return app


def run_dashboard() -> None:
    port = int(os.getenv("DASHBOARD_PORT", os.getenv("PORT", "5000")))
    app = create_dashboard()
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)
