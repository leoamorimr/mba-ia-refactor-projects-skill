"""Orchestration + business rules for orders: stock validation, total
calculation, notification side effects, and status-transition rules
(including the stock restoration on cancellation that the old controller
only logged about but never actually performed).

`OrderController` receives its repositories and its `NotificationService`
via the constructor instead of importing the data modules and
instantiating a concrete `NotificationService` at module import time -
this is the fix for the audit's "Tight Coupling / No Dependency
Injection" finding: a test can now pass in a fake notification service or
in-memory repositories with no monkeypatching.
"""


def validate_items(itens):
    """Returns an error message, or None if every item is well-formed.

    This is the fix for the stock-corruption bug: a negative `quantidade`
    used to pass the old `estoque < quantidade` check (a negative is
    always "enough stock") and then `estoque = estoque - (negative)`
    silently increased stock instead of decreasing it.
    """
    for item in itens:
        produto_id = item.get("produto_id")
        quantidade = item.get("quantidade")
        if not isinstance(produto_id, int) or isinstance(produto_id, bool):
            return "produto_id inválido"
        if not isinstance(quantidade, int) or isinstance(quantidade, bool) or quantidade <= 0:
            return "quantidade deve ser um número inteiro positivo"
    return None


class OrderController:
    def __init__(self, order_repository, product_repository, user_repository, notification_service):
        self.order_repository = order_repository
        self.product_repository = product_repository
        self.user_repository = user_repository
        self.notification_service = notification_service

    def create_order(self, usuario_id, itens):
        """Returns a dict: either {"erro": ...} or {"pedido_id": ..., "total": ...}."""
        if self.user_repository.get_by_id(usuario_id) is None:
            return {"erro": "Usuário não encontrado"}

        produto_ids = [item["produto_id"] for item in itens]
        produtos_por_id = self.product_repository.get_by_ids(produto_ids)

        total = 0
        for item in itens:
            produto = produtos_por_id.get(item["produto_id"])
            if produto is None:
                return {"erro": f"Produto {item['produto_id']} não encontrado"}
            if produto["estoque"] < item["quantidade"]:
                return {"erro": f"Estoque insuficiente para {produto['nome']}"}
            total += produto["preco"] * item["quantidade"]

        pedido_id = self.order_repository.create(usuario_id, total)

        itens_para_inserir = []
        baixas_de_estoque = []
        for item in itens:
            produto = produtos_por_id[item["produto_id"]]
            itens_para_inserir.append(
                (pedido_id, item["produto_id"], item["quantidade"], produto["preco"])
            )
            baixas_de_estoque.append((item["quantidade"], item["produto_id"]))

        self.order_repository.insert_items_bulk(itens_para_inserir)
        self.product_repository.decrement_stock_bulk(baixas_de_estoque)

        self.notification_service.notify_order_created(pedido_id, usuario_id)

        return {"pedido_id": pedido_id, "total": total}

    def list_orders_by_user(self, usuario_id, limit=None, offset=0):
        return self.order_repository.list_orders(usuario_id=usuario_id, limit=limit, offset=offset)

    def list_all_orders(self, limit=None, offset=0):
        return self.order_repository.list_orders(limit=limit, offset=offset)

    def update_order_status(self, pedido_id, novo_status):
        if novo_status == "cancelado":
            itens = self.order_repository.get_items_by_order(pedido_id)
            if itens:
                devolucoes = [(item["quantidade"], item["produto_id"]) for item in itens]
                self.product_repository.restore_stock_bulk(devolucoes)
            self.notification_service.notify_order_cancelled(pedido_id)

        self.order_repository.update_status(pedido_id, novo_status)

        if novo_status == "aprovado":
            self.notification_service.notify_order_approved(pedido_id)

        return True
