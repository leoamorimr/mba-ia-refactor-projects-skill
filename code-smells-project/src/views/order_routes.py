"""Routing + request/response shaping only for the `/pedidos` domain.

`create_order_blueprint` closes over the already-constructed
`OrderController` (built once in `app.py`'s composition root) instead of
importing a controller module and calling its functions directly.
"""
from flask import Blueprint, jsonify, request

from controllers.order_controller import validate_items


def create_order_blueprint(order_controller):
    order_bp = Blueprint("orders", __name__)

    @order_bp.route("/pedidos", methods=["POST"])
    def criar_pedido():
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({"erro": "Dados inválidos"}), 400

        usuario_id = dados.get("usuario_id")
        itens = dados.get("itens", [])

        if not usuario_id:
            return jsonify({"erro": "Usuario ID é obrigatório"}), 400
        if not itens or len(itens) == 0:
            return jsonify({"erro": "Pedido deve ter pelo menos 1 item"}), 400

        erro_item = validate_items(itens)
        if erro_item:
            return jsonify({"erro": erro_item}), 400

        resultado = order_controller.create_order(usuario_id, itens)
        if "erro" in resultado:
            return jsonify({"erro": resultado["erro"], "sucesso": False}), 400

        return jsonify({
            "dados": resultado,
            "sucesso": True,
            "mensagem": "Pedido criado com sucesso",
        }), 201

    @order_bp.route("/pedidos", methods=["GET"])
    def listar_todos_pedidos():
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", 0, type=int)
        pedidos = order_controller.list_all_orders(limit=limit, offset=offset)
        return jsonify({"dados": pedidos, "sucesso": True}), 200

    @order_bp.route("/pedidos/usuario/<int:usuario_id>", methods=["GET"])
    def listar_pedidos_usuario(usuario_id):
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", 0, type=int)
        pedidos = order_controller.list_orders_by_user(usuario_id, limit=limit, offset=offset)
        return jsonify({"dados": pedidos, "sucesso": True}), 200

    @order_bp.route("/pedidos/<int:pedido_id>/status", methods=["PUT"])
    def atualizar_status_pedido(pedido_id):
        dados = request.get_json(silent=True) or {}
        novo_status = dados.get("status", "")

        if novo_status not in ["pendente", "aprovado", "enviado", "entregue", "cancelado"]:
            return jsonify({"erro": "Status inválido"}), 400

        order_controller.update_order_status(pedido_id, novo_status)
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200

    return order_bp
