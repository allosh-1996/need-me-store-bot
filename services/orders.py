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
            current_balance = wallet_repo.get_balance(user_id)
            if current_balance < amount_usd:
                raise InsufficientBalanceError("insufficient balance")

            stock_row = stock_repo.reserve_first_available(product_id)
            if not stock_row:
                raise OutOfStockError("out of stock")

            order_id = orders_repo.create_order(user_id, product_id, amount_usd)
            stock_item_id = int(stock_row[0])
            payload = str(stock_row[1])

            stock_repo.mark_reserved(stock_item_id, order_id)
            orders_repo.attach_stock_and_payload(order_id, stock_item_id, payload)
            wallet_repo.set_balance(user_id, current_balance - amount_usd)
            wallet_repo.insert_ledger_entry(
                user_id, "debit", amount_usd, "order", str(order_id), "product purchase"
            )
            stock_repo.mark_sold(stock_item_id)
            orders_repo.mark_delivered(order_id)

            return {
                "order_id": order_id,
                "product_name": str(product[1]),
                "amount_usd": amount_usd,
                "payload": payload,
                "balance_after": current_balance - amount_usd,
            }
