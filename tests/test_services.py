"""
Integration tests for OrderService, WalletService, ChargeService, AppsflyerService, AdminService.
All tests run against an in-memory SQLite DB via the `db` fixture in conftest.py.
"""
from __future__ import annotations

import threading
import pytest

from tests.conftest import _insert_user, _insert_product
from services.orders import OrderService
from services.wallet import WalletService
from services.charges import ChargeService
from services.appsflyer import AppsflyerService
from services.admin import AdminService
from domain.errors import (
    InsufficientBalanceError, OutOfStockError, NotFoundError,
    InvalidStateTransitionError, DuplicateProofError,
)


# ─── WalletService ────────────────────────────────────────────────────────────

class TestWalletService:
    def test_get_balance(self, db):
        _insert_user(db, 1, balance=25.0)
        svc = WalletService()
        assert svc.get_balance(1) == pytest.approx(25.0)

    def test_credit_increases_balance(self, db):
        _insert_user(db, 1, balance=10.0)
        svc = WalletService()
        new_bal = svc.credit(1, 5.0, "test credit", "test", "ref1")
        assert new_bal == pytest.approx(15.0)

    def test_debit_decreases_balance(self, db):
        _insert_user(db, 1, balance=10.0)
        svc = WalletService()
        new_bal = svc.debit(1, 3.0, "test debit", "test", "ref1")
        assert new_bal == pytest.approx(7.0)

    def test_debit_raises_on_insufficient_balance(self, db):
        _insert_user(db, 1, balance=2.0)
        svc = WalletService()
        with pytest.raises(InsufficientBalanceError):
            svc.debit(1, 5.0, "test", "test", "ref1")

    def test_credit_raises_on_zero_amount(self, db):
        _insert_user(db, 1, balance=10.0)
        svc = WalletService()
        from domain.errors import ValidationError
        with pytest.raises(ValidationError):
            svc.credit(1, 0, "test", "test", "ref1")


# ─── OrderService ─────────────────────────────────────────────────────────────

class TestOrderService:
    def test_buy_instant_product_success(self, db):
        _insert_user(db, 1, balance=20.0)
        product_id = _insert_product(db, price=5.0, stock_count=1)
        svc = OrderService()
        result = svc.buy_instant_product(1, product_id)
        assert result["amount_usd"] == pytest.approx(5.0)
        assert result["balance_after"] == pytest.approx(15.0)
        assert result["payload"].startswith("KEY-")

    def test_buy_product_deducts_balance(self, db):
        _insert_user(db, 1, balance=10.0)
        product_id = _insert_product(db, price=4.0, stock_count=2)
        svc = OrderService()
        svc.buy_instant_product(1, product_id)
        from repositories.wallet import get_balance
        assert get_balance(1) == pytest.approx(6.0)

    def test_buy_product_insufficient_balance(self, db):
        _insert_user(db, 1, balance=2.0)
        product_id = _insert_product(db, price=5.0, stock_count=1)
        svc = OrderService()
        with pytest.raises(InsufficientBalanceError):
            svc.buy_instant_product(1, product_id)

    def test_buy_product_out_of_stock(self, db):
        _insert_user(db, 1, balance=20.0)
        product_id = _insert_product(db, price=5.0, stock_count=0)
        svc = OrderService()
        with pytest.raises(OutOfStockError):
            svc.buy_instant_product(1, product_id)

    def test_buy_product_marks_stock_sold(self, db):
        _insert_user(db, 1, balance=20.0)
        product_id = _insert_product(db, price=5.0, stock_count=1)
        svc = OrderService()
        svc.buy_instant_product(1, product_id)
        row = db.execute("SELECT status FROM stock_items WHERE product_id = ?", (product_id,)).fetchone()
        assert row[0] == "sold"

    def test_race_condition_only_one_purchase_succeeds(self, db):
        """
        Two concurrent buy attempts with balance for only one purchase.
        Exactly one must succeed and one must fail with InsufficientBalanceError.
        """
        _insert_user(db, 1, balance=5.0)
        product_id = _insert_product(db, price=5.0, stock_count=2)
        svc = OrderService()

        results = []
        errors = []

        def attempt():
            try:
                r = svc.buy_instant_product(1, product_id)
                results.append(r)
            except InsufficientBalanceError:
                errors.append("insufficient")
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=attempt)
        t2 = threading.Thread(target=attempt)
        t1.start(); t2.start()
        t1.join(); t2.join()

        # Exactly one success, one failure
        assert len(results) == 1
        assert len(errors) == 1
        # Balance must be exactly 0, not negative
        from repositories.wallet import get_balance
        assert get_balance(1) == pytest.approx(0.0)


# ─── ChargeService ────────────────────────────────────────────────────────────

class TestChargeService:
    def test_create_charge_returns_id(self, db):
        _insert_user(db, 1)
        svc = ChargeService()
        charge_id = svc.create_charge(1, "usdt", 10.0, None, "TXHASH123", None)
        assert isinstance(charge_id, int)
        assert charge_id > 0

    def test_duplicate_tx_hash_raises(self, db):
        _insert_user(db, 1)
        svc = ChargeService()
        svc.create_charge(1, "usdt", 10.0, None, "SAMEHASH", None)
        with pytest.raises(DuplicateProofError):
            svc.create_charge(1, "usdt", 10.0, None, "SAMEHASH", None)


# ─── AppsflyerService ─────────────────────────────────────────────────────────

class TestAppsflyerService:
    def test_create_order_deducts_balance(self, db):
        _insert_user(db, 1, balance=10.0)
        svc = AppsflyerService()
        order_id = svc.create_order(1, "coin_master", "Coin Master", 4.0,
                                    "idfa-uuid", "idfv-uuid", "17.0", "af-id", "5,10")
        assert order_id > 0
        from repositories.wallet import get_balance
        assert get_balance(1) == pytest.approx(6.0)

    def test_create_order_insufficient_balance(self, db):
        _insert_user(db, 1, balance=1.0)
        svc = AppsflyerService()
        with pytest.raises(InsufficientBalanceError):
            svc.create_order(1, "coin_master", "Coin Master", 4.0,
                             "idfa-uuid", "idfv-uuid", "17.0", "af-id", "5,10")


# ─── AdminService ─────────────────────────────────────────────────────────────

class TestAdminService:
    def _create_charge(self, db, user_id: int, amount: float = 5.0) -> int:
        db.execute(
            "INSERT INTO charge_requests (user_id, method, amount_usd, status) VALUES (?,?,?,'pending')",
            (user_id, "usdt", amount),
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def _create_af_order(self, db, user_id: int, price: float = 4.0) -> int:
        db.execute(
            "INSERT INTO appsflyer_orders (user_id, game_key, game_name, price_usd, idfa, idfv, ios_version, appsflyer_id, levels, status) "
            "VALUES (?,?,?,?,?,?,?,?,'5,10','pending')",
            (user_id, "coin_master", "Coin Master", price, "idfa", "idfv", "17.0", "af-id"),
        )
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def test_confirm_charge_credits_balance(self, db):
        _insert_user(db, 1, balance=0.0)
        charge_id = self._create_charge(db, 1, amount=10.0)
        svc = AdminService()
        new_bal = svc.confirm_charge("admin", charge_id)
        assert new_bal == pytest.approx(10.0)

    def test_confirm_charge_already_processed(self, db):
        _insert_user(db, 1, balance=0.0)
        charge_id = self._create_charge(db, 1, amount=5.0)
        svc = AdminService()
        svc.confirm_charge("admin", charge_id)
        with pytest.raises(InvalidStateTransitionError):
            svc.confirm_charge("admin", charge_id)

    def test_reject_charge_not_found(self, db):
        svc = AdminService()
        with pytest.raises(NotFoundError):
            svc.reject_charge("admin", 9999)

    def test_accept_appsflyer(self, db):
        _insert_user(db, 1, balance=10.0)
        order_id = self._create_af_order(db, 1)
        svc = AdminService()
        svc.accept_appsflyer("admin", order_id)
        row = db.execute("SELECT status FROM appsflyer_orders WHERE id = ?", (order_id,)).fetchone()
        assert row[0] == "accepted"

    def test_fulfill_appsflyer(self, db):
        _insert_user(db, 1, balance=10.0)
        order_id = self._create_af_order(db, 1)
        svc = AdminService()
        svc.accept_appsflyer("admin", order_id)
        svc.fulfill_appsflyer("admin", order_id)
        row = db.execute("SELECT status FROM appsflyer_orders WHERE id = ?", (order_id,)).fetchone()
        assert row[0] == "fulfilled"

    def test_fulfill_pending_raises(self, db):
        _insert_user(db, 1, balance=10.0)
        order_id = self._create_af_order(db, 1)
        svc = AdminService()
        with pytest.raises(InvalidStateTransitionError):
            svc.fulfill_appsflyer("admin", order_id)

    def test_reject_appsflyer_refunds_balance(self, db):
        _insert_user(db, 1, balance=0.0)
        order_id = self._create_af_order(db, 1, price=4.0)
        # Manually set balance to 0 (simulating already-deducted)
        db.execute("UPDATE wallet_balances SET balance_usd = 0 WHERE user_id = 1")
        svc = AdminService()
        new_bal = svc.reject_appsflyer("admin", order_id)
        assert new_bal == pytest.approx(4.0)
