from __future__ import annotations

from infra.transactions import transactional
from repositories import products as products_repo
from repositories import orders as orders_repo
from repositories import stock as stock_repo
from repositories import wallet as wallet_repo
from domain.errors import InsufficientBalanceError, NotFoundError, OutOfStockError


class OrderService:
    def buy_instant_product(self, user_id: int, product_id: int) -> dict:
        with transactional():
            product = products_repo.get_product(product_id)
            if not product or int(product[6]) != 1:
                raise NotFoundError("product not found")

            amount_usd = float(product[3])

            # Reserve stock first (before touching money)
            stock_row = stock_repo.reserve_first_available(product_id)
            if not stock_row:
                raise OutOfStockError("out of stock")

            stock_item_id = int(stock_row[0])
            payload = str(stock_row[1])

            # Create the order record
            order_id = orders_repo.create_order(user_id, product_id, amount_usd)

            # Mark stock reserved
            stock_repo.mark_reserved(stock_item_id, order_id)

            # Atomic debit — raises ValueError if balance insufficient
            try:
                balance_after = wallet_repo.debit_atomic(
                    user_id=user_id,
                    amount=amount_usd,
                    entry_type="debit",
                    reference_type="order",
                    reference_id=str(order_id),
                    reason="product purchase",
                )
            except ValueError:
                raise InsufficientBalanceError("insufficient balance")

            # Finalize order and stock
            orders_repo.attach_stock_and_payload(order_id, stock_item_id, payload)
            stock_repo.mark_sold(stock_item_id)
            orders_repo.mark_delivered(order_id)

            return {
                "order_id": order_id,
                "product_name": str(product[1]),
                "amount_usd": amount_usd,
                "payload": payload,
                "balance_after": balance_after,
            }
