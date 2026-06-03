from __future__ import annotations
from functools import wraps
from typing import Callable
from flask import session, redirect, url_for, request
from werkzeug.security import check_password_hash
from app.settings import get_settings

SESSION_KEY = "dashboard_auth"


def verify_password(password: str) -> bool:
    return check_password_hash(get_settings().dashboard_password_hash, password)


def login_required(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get(SESSION_KEY):
            return redirect(url_for("dashboard.login", next=request.path))
        return func(*args, **kwargs)
    return wrapper
