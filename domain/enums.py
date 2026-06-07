from enum import Enum


class Language(str, Enum):
    AR = "ar"
    EN = "en"


class OrderStatus(str, Enum):
    RESERVED  = "reserved"
    DELIVERED = "delivered"
    REJECTED  = "rejected"
    REFUNDED  = "refunded"


class ChargeStatus(str, Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    REJECTED  = "rejected"


class AppsflyerStatus(str, Enum):
    PENDING   = "pending"
    ACCEPTED  = "accepted"
    REJECTED  = "rejected"
    FULFILLED = "fulfilled"   # service has been delivered


class StockStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED  = "reserved"
    SOLD      = "sold"


class LedgerEntryType(str, Enum):
    CREDIT     = "credit"
    DEBIT      = "debit"
    REFUND     = "refund"
    ADJUSTMENT = "adjustment"
