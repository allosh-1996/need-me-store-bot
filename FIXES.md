# NexVault Bot — Change Log

> Last updated: 2026-05-31

---

## v2 — Full Clean Rewrite (2026-05-31)

All files below were rewritten from scratch, not patched.

---

### database.py

**Problem 1 — RuntimeError at import time**
The env-var validation (`TURSO_URL / TURSO_TOKEN`) ran at module level, meaning
any `import database` would crash before the bot even started if the vars were missing.

**Fix:** Validation moved inside `get_conn()`. The module now imports safely in all
environments; the error is raised only when a DB call is actually attempted.

---

**Problem 2 — Negative balance possible via `add_balance()`**
`add_balance(user_id, -100)` would silently subtract without checking the current
balance, leaving users with negative balances.

**Fix:** `add_balance()` now delegates negative amounts to `deduct_balance_atomic()`,
which wraps the deduction in `BEGIN IMMEDIATE` and raises `ValueError` if the balance
is insufficient. A negative balance is now impossible.

---

**Problem 3 — Thread-local connections never closed**
`threading.local()` connections were created per-thread but never closed. Over time
(many threads, long uptime) this silently accumulated open connections.

**Fix:** `close_thread_conn()` was already present but never called. The function is
retained and documented. Callers (Flask teardown, thread cleanup) should invoke it.
The connection is now also re-created if the thread-local slot is `None`, so there is
no stale-connection risk on reconnect.

---

**Problem 4 — `deduct_balance()` was a loose wrapper**
The old `deduct_balance()` issued a plain `UPDATE` with no balance check, bypassing
the atomic guard in `deduct_balance_atomic()`.

**Fix:** `deduct_balance()` is now a thin alias for `deduct_balance_atomic()`.
One code path, one guarantee.

---

### web_dashboard.py

**Problem — Broadcast was a blocking HTTP request**
`api_broadcast()` looped over all users synchronously inside the Flask request.
With 1 000+ users at ~1 s per `tg_send`, the HTTP request would hang for 1 000 s
and time out before completing.

**Fix:** Broadcast now runs in a daemon `threading.Thread` (`_broadcast_worker`).
The API endpoint returns immediately with a `job_id`. The caller can poll
`GET /api/broadcast/status/<job_id>` to track `sent / failed / total` in real time.

Batch size: 25 messages per batch, 1 s delay between batches — stays under
Telegram's 30 msg/s limit.

---

### handlers_admin.py

**Problem — Notifications used a hardcoded Arabic language**
`reject_order()` and `confirm_order()` always sent messages in Arabic, even when
the user had selected English.

**Fix:** Both handlers now call `db.get_user_lang(order["user_id"])` before sending
and pass the result to `t()`. Same fix applied to `appsflyer_accept()` and
`appsflyer_reject()`.

---

### handlers_user.py

**Problem — Hardcoded Arabic string in `initiate_buy()`**
The product-delivery message ended with a hardcoded Arabic string
`"احفظ هذه المعلومات بأمان"` regardless of the user's language setting.

**Fix:** The string is now conditional on `lang`:
```python
save_note = "Keep this information safe" if lang == "en" else "احفظ هذه المعلومات بأمان"
```

`proxy_menu_simple()` had the same issue — all button labels and body text are now
driven by `lang`.

---

## v1 — Initial Fixes (2026-05-27)

| Fix | File | Description |
|-----|------|-------------|
| DB persistence | database.py | Migrated from SQLite `/tmp` to Turso cloud DB |
| Stock pop | database.py | `pop_stock_item()` — atomic, unique per buyer |
| Broadcast dedup | web_dashboard.py | `is_sent=1` set immediately; job_queue skips sent rows |
| Dashboard security | web_dashboard.py | `DASHBOARD_SECRET` + `DASHBOARD_PASSWORD` required in production |
