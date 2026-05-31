"""
utils.py — NexVault Bot
Rate limiting, input validation, shared helpers.
"""
import time
import logging
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)

# ════════════════════════════════════════
# Rate Limiting
# ════════════════════════════════════════

_last_call: dict = defaultdict(float)

def rate_limit(seconds: int = 3):
    """
    Decorator — يمنع المستخدم من استدعاء نفس الـ handler
    أكثر من مرة كل `seconds` ثانية.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            uid  = update.effective_user.id if update.effective_user else 0
            key  = f"{func.__name__}:{uid}"
            now  = time.monotonic()
            wait = seconds - (now - _last_call[key])
            if wait > 0:
                query = getattr(update, "callback_query", None)
                if query:
                    await query.answer("⏳ انتظر لحظة...", show_alert=False)
                return
            _last_call[key] = now
            return await func(update, context)
        return wrapper
    return decorator


# ════════════════════════════════════════
# Input Validation
# ════════════════════════════════════════

MAX_FIELD_LENGTH = {
    "name":        80,
    "description": 300,
    "category":    60,
    "stock_item":  500,
    "message":     4000,
}

def validate_text(value: str, field: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    يتحقق من طول النص وأنه غير فارغ.
    """
    value = value.strip()
    if not value:
        return False, "⚠️ الحقل لا يمكن أن يكون فارغاً."
    max_len = MAX_FIELD_LENGTH.get(field, 500)
    if len(value) > max_len:
        return False, f"⚠️ النص طويل جداً — الحد الأقصى {max_len} حرف."
    return True, ""


def validate_amount(value: str, min_val: float = 0.5, max_val: float = 10000.0) -> tuple[bool, float, str]:
    """
    Returns (is_valid, amount_float, error_message).
    يتحقق أن المبلغ رقم ضمن النطاق المسموح.
    """
    try:
        amount = float(value.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return False, 0.0, "⚠️ أدخل رقماً صحيحاً."
    if amount < min_val:
        return False, 0.0, f"⚠️ الحد الأدنى ${min_val:.2f}."
    if amount > max_val:
        return False, 0.0, f"⚠️ الحد الأقصى ${max_val:,.0f}."
    return True, amount, ""
