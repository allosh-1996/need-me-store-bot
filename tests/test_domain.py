import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from domain.enums import OrderStatus, ChargeStatus, AppsflyerStatus, Language
from domain.errors import InsufficientBalanceError, OutOfStockError


def test_order_statuses():
    assert OrderStatus.DELIVERED == "delivered"
    assert OrderStatus.REJECTED  == "rejected"


def test_charge_statuses():
    assert ChargeStatus.PENDING   == "pending"
    assert ChargeStatus.CONFIRMED == "confirmed"


def test_appsflyer_statuses():
    assert AppsflyerStatus.PENDING  == "pending"
    assert AppsflyerStatus.ACCEPTED == "accepted"


def test_languages():
    assert Language.AR == "ar"
    assert Language.EN == "en"


def test_errors_are_exceptions():
    with __import__("pytest").raises(InsufficientBalanceError):
        raise InsufficientBalanceError("test")
    with __import__("pytest").raises(OutOfStockError):
        raise OutOfStockError("test")
