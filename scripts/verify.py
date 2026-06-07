#!/usr/bin/env python3
"""
Pre-deploy verification gate.
Run before every push: python scripts/verify.py
Fails fast on syntax errors, import failures, or callback mismatches.
"""
import sys
import os
import re
import py_compile
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

errors = []

# ── 1. Syntax check all Python files ────────────────────────────────────────
print("1. Syntax check...")
for f in sorted(ROOT.rglob("*.py")):
    if ".git" in str(f):
        continue
    try:
        py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"SYNTAX: {f.relative_to(ROOT)}: {e}")

if not errors:
    print("   ✅ All files pass syntax check")

# ── 2. Import check ──────────────────────────────────────────────────────────
print("2. Import check...")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "x")
os.environ.setdefault("ADMIN_TELEGRAM_IDS", "1")
os.environ.setdefault("TURSO_DATABASE_URL", "libsql://x.turso.io")
os.environ.setdefault("TURSO_AUTH_TOKEN", "x")
os.environ.setdefault("DASHBOARD_SECRET", "x")
os.environ.setdefault("DASHBOARD_PASSWORD_HASH", "x")
os.environ.setdefault("USDT_WALLET", "x")
os.environ.setdefault("SYRIATEL_CASH", "x")

MODULES = [
    "app.settings", "domain.models", "domain.enums", "domain.errors",
    "bot.render.strings", "bot.render.keyboards", "bot.render.formatters",
    "bot.handlers.start", "bot.handlers.catalog", "bot.handlers.wallet",
    "bot.handlers.charge", "bot.handlers.appsflyer", "bot.handlers.admin",
    "repositories.users", "repositories.wallet", "repositories.products",
    "services.orders", "services.wallet", "services.charges",
    "services.appsflyer", "services.admin",
    "dashboard.routes", "dashboard.routes_admin",
]

for m in MODULES:
    try:
        __import__(m)
    except Exception as e:
        errors.append(f"IMPORT: {m}: {e}")

if not any(e.startswith("IMPORT") for e in errors):
    print("   ✅ All modules import OK")

# ── 3. Callback contract check ───────────────────────────────────────────────
print("3. Callback contract check...")

EMITTED = [
    "catalog:open:icloud", "catalog:open:emails", "catalog:open:proxy", "catalog:open:surveys",
    "wallet:balance", "af:start", "user:toggle_lang", "home",
    "charge:start", "charge:method:usdt", "charge:method:syriatel", "cancel",
    "admin:charges:0", "admin:af_orders:0", "admin:af_accepted:0", "admin:panel",
    "charge:confirm:1", "charge:reject:1",
    "af:accept:1", "af:reject:1", "af:fulfill:1", "af:game:coin_master",
    "catalog:product:1", "catalog:buy:1",
    "admin:charges:5", "admin:af_orders:5", "admin:af_accepted:5",
]

PATTERNS = [
    r"^home$", r"^user:toggle_lang$",
    r"^catalog:open(:[a-z]+)?$", r"^catalog:product:\d+$", r"^catalog:buy:\d+$",
    r"^wallet:balance$",
    r"^admin:panel$", r"^admin:charges(:\d+)?$",
    r"^admin:af_orders(:\d+)?$", r"^admin:af_accepted(:\d+)?$",
    r"^charge:(confirm|reject):\d+$", r"^af:(accept|reject|fulfill):\d+$",
    r"^charge:start$", r"^charge:method:", r"^cancel$",
    r"^af:start$", r"^af:game:",
]

for cb in EMITTED:
    if not any(re.match(p, cb) for p in PATTERNS):
        errors.append(f"CALLBACK: no handler for \'{cb}\'")

if not any(e.startswith("CALLBACK") for e in errors):
    print("   ✅ All callbacks matched")

# ── Result ───────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"❌ {len(errors)} error(s) found:")
    for e in errors:
        print(f"   {e}")
    sys.exit(1)
else:
    print("✅ All checks passed — safe to deploy")
    sys.exit(0)
