from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _parse_admin_ids(raw: str) -> set[int]:
    result: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if item.isdigit():
            result.add(int(item))
    return result


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    admin_ids: set[int]
    turso_database_url: str
    turso_auth_token: str
    dashboard_secret: str
    dashboard_password_hash: str
    usdt_wallet: str
    syriatel_cash: str
    syp_rate: float

    @classmethod
    def from_env(cls) -> "Settings":
        admin_ids = _parse_admin_ids(os.getenv("ADMIN_TELEGRAM_IDS", ""))
        settings = cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            admin_ids=admin_ids,
            turso_database_url=os.getenv("TURSO_DATABASE_URL", "").strip(),
            turso_auth_token=os.getenv("TURSO_AUTH_TOKEN", "").strip(),
            dashboard_secret=os.getenv("DASHBOARD_SECRET", "").strip(),
            dashboard_password_hash=os.getenv("DASHBOARD_PASSWORD_HASH", "").strip(),
            usdt_wallet=os.getenv("USDT_WALLET", "").strip(),
            syriatel_cash=os.getenv("SYRIATEL_CASH", "").strip(),
            syp_rate=float(os.getenv("SYP_RATE", "140")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        required = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TURSO_DATABASE_URL": self.turso_database_url,
            "TURSO_AUTH_TOKEN": self.turso_auth_token,
            "DASHBOARD_SECRET": self.dashboard_secret,
            "DASHBOARD_PASSWORD_HASH": self.dashboard_password_hash,
            "USDT_WALLET": self.usdt_wallet,
            "SYRIATEL_CASH": self.syriatel_cash,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
        if not self.admin_ids:
            raise RuntimeError("ADMIN_TELEGRAM_IDS must contain at least one Telegram ID")
        if self.syp_rate <= 0:
            raise RuntimeError("SYP_RATE must be greater than 0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
