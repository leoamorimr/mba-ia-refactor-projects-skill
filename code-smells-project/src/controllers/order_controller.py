"""Orchestration + business rules for orders: stock validation, total
calculation, notification side effects, and status-transition rules
(including the stock restoration on cancellation that the old controller
only logged about but never actually performed).
"""
from models import order_model, product_model
from services.notification_service import NotificationService

notification_service = NotificationService()


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


def create_order(usuario_id, itens):
    """Returns a dict: either {"erro": ...} or {"pedido_id": ..., "total": ...}."""
    produto_ids = [item["produto_id"] for item in itens]
    produtos_por_id = product_model.get_by_ids(produto_ids)

    total = 0
    for item in itens:
        produto = produtos_por_id.get(item["produto_id"])
        if produto is None:
            return {"erro": f"Produto {item['produto_id']} não encontrado"}
        if produto["estoque"] < item["quantidade"]:
            return {"erro": f"Estoque insuficiente para {produto['nome']}"}
        total += produto["preco"] * item["quantidade"]

    pedido_id = order_model.create(usuario_id, total)

    itens_para_inserir = []
    baixas_de_estoque = []
    for item in itens:
        produto = produtos_por_id[item["produto_id"]]
        itens_para_inserir.append(
            (pedido_id, item["produto_id"], item["quantidade"], produto["preco"])
        )
        baixas_de_estoque.append((item["quantidade"], item["produto_id"]))

    order_model.insert_items_bulk(itens_para_inserir)
    product_model.decrement_stock_bulk(baixas_de_estoque)

    notification_service.notify_order_created(pedido_id, usuario_id)

    return {"pedido_id": pedido_id, "total": total}


def list_orders_by_user(usuario_id, limit=None, offset=0):
    return order_model.list_orders(usuario_id=usuario_id, limit=limit, offset=offset)


def list_all_orders(limit=None, offset=0):
    return order_model.list_orders(limit=limit, offset=offset)


def update_order_status(pedido_id, novo_status):
    if novo_status == "cancelado":
        itens = order_model.get_items_by_order(pedido_id)
        if itens:
            devolucoes = [(item["quantidade"], item["produto_id"]) for item in itens]
            product_model.restore_stock_bulk(devolucoes)
        notification_service.notify_order_cancelled(pedido_id)

    order_model.update_status(pedido_id, novo_status)

    if novo_status == "aprovado":
        notification_service.notify_order_approved(pedido_id)

    return True
