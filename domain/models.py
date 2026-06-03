from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from domain.enums import Language, OrderStatus, ChargeStatus, AppsflyerStatus, StockStatus


@dataclass(slots=True)
class User:
    id: int
    username: str
    full_name: str
    language: Language
    blocked: bool
    joined_at: datetime | None


@dataclass(slots=True)
class Product:
    id: int
    name: str
    description: str
    price_usd: float
    category: str
    platform: str
    active: bool


@dataclass(slots=True)
class Order:
    id: int
    user_id: int
    product_id: int
    stock_item_id: int | None
    status: OrderStatus
    amount_usd: float
    delivery_payload: str | None


@dataclass(slots=True)
class ChargeRequest:
    id: int
    user_id: int
    method: str
    amount_usd: float
    status: ChargeStatus


@dataclass(slots=True)
class AppsflyerOrder:
    id: int
    user_id: int
    game_key: str
    game_name: str
    status: AppsflyerStatus
    price_usd: float


@dataclass(slots=True)
class StockItem:
    id: int
    product_id: int
    content: str
    status: StockStatus
