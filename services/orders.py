from __future__ import annotations

from infra.transactions import transactional
from infra.db import sync_replica
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
            stock_row = stock_repo.reserve_first_available(product_id)
            if not stock_row:
                raise OutOfStockError("out of stock")
            stock_item_id = int(stock_row[0])
            payload = str(stock_row[1])
            order_id = orders_repo.create_order(user_id, product_id, amount_usd)
            stock_repo.mark_reserved(stock_item_id, order_id)
            balance_after = wallet_repo.debit_atomic(
                user_id=user_id, amount=amount_usd, entry_type="debit",
                reference_type="order", reference_id=str(order_id),
                reason="product purchase",
            )
            orders_repo.attach_stock_and_payload(order_id, stock_item_id, payload)
            stock_repo.mark_sold(stock_item_id)
            orders_repo.mark_delivered(order_id)
        sync_replica()
        return {
            "order_id": order_id,
            "product_name": str(product[1]),
            "amount_usd": amount_usd,
            "payload": payload,
            "balance_after": balance_after,
        }
