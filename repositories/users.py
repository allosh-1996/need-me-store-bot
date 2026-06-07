from __future__ import annotations

import threading
from infra.db import execute

# ── Simple in-memory language cache ──────────────────────────────────────────
# Avoids a DB round-trip on every single message just to read the language.
# TTL-less: language changes are written through immediately via set_user_language.
_lang_cache: dict[int, str] = {}
_cache_lock = threading.Lock()


def _cache_set(user_id: int, lang: str) -> None:
    with _cache_lock:
        _lang_cache[user_id] = lang


def _cache_get(user_id: int) -> str | None:
    with _cache_lock:
        return _lang_cache.get(user_id)


# ── User operations ───────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str, full_name: str) -> None:
    """Upsert user + ensure wallet row — 2 queries but batched."""
    execute(
        """
        INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            username  = excluded.username,
            full_name = excluded.full_name
        """,
        (user_id, username, full_name),
    )
    execute(
        "INSERT OR IGNORE INTO wallet_balances (user_id, balance_usd) VALUES (?, 0)",
        (user_id,),
    )


def ensure_user(user_id: int, username: str = "", full_name: str = "") -> None:
    """
    Lightweight upsert — INSERT OR IGNORE so it's a no-op if user exists.
    Guarantees users + wallet_balances rows exist before any DB operation.
    """
    execute(
        "INSERT OR IGNORE INTO users (id, username, full_name) VALUES (?, ?, ?)",
        (user_id, username or "", full_name or ""),
    )
    execute(
        "INSERT OR IGNORE INTO wallet_balances (user_id, balance_usd) VALUES (?, 0)",
        (user_id,),
    )


def get_user_language(user_id: int) -> str:
    """Return language from cache if available, otherwise hit DB once."""
    cached = _cache_get(user_id)
    if cached is not None:
        return cached
    row = execute(
        "SELECT language FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    lang = row[0] if row else "ar"
    _cache_set(user_id, lang)
    return lang


def set_user_language(user_id: int, language: str) -> None:
    execute(
        "UPDATE users SET language = ? WHERE id = ?", (language, user_id)
    )
    # Write-through: update cache immediately
    _cache_set(user_id, language)


def get_all_users() -> list:
    return execute(
        "SELECT id, username, full_name FROM users WHERE blocked = 0"
    ).fetchall()
