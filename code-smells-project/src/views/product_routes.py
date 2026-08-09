"""Routing + request/response shaping only for the `/produtos` domain -
no SQL, no business rules. Required-field presence is checked here (the
"is this endpoint even the right shape" concern); business validation
(lengths, categories, negative numbers) lives in product_controller.
"""
from flask import Blueprint, jsonify, request

from controllers import product_controller

product_bp = Blueprint("products", __name__)


def _parse_pagination():
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    return limit, offset


@product_bp.route("/produtos", methods=["GET"])
def listar_produtos():
    limit, offset = _parse_pagination()
    produtos = product_controller.list_products(limit=limit, offset=offset)
    return jsonify({"dados": produtos, "sucesso": True}), 200


@product_bp.route("/produtos/busca", methods=["GET"])
def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria") or None
    preco_min = request.args.get("preco_min", type=float)
    preco_max = request.args.get("preco_max", type=float)
    limit, offset = _parse_pagination()

    resultados = product_controller.search_products(
        termo, categoria=categoria, preco_min=preco_min, preco_max=preco_max,
        limit=limit, offset=offset,
    )
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


@product_bp.route("/produtos/<int:id>", methods=["GET"])
def buscar_produto(id):
    produto = product_controller.get_product(id)
    if produto:
        return jsonify({"dados": produto, "sucesso": True}), 200
    return jsonify({"erro": "Produto não encontrado", "sucesso": False}), 404


@product_bp.route("/produtos", methods=["POST"])
def criar_produto():
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Dados inválidos"}), 400
    if "nome" not in dados:
        return jsonify({"erro": "Nome é obrigatório"}), 400
    if "preco" not in dados:
        return jsonify({"erro": "Preço é obrigatório"}), 400
    if "estoque" not in dados:
        return jsonify({"erro": "Estoque é obrigatório"}), 400

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", "geral")

    erro, novo_id = product_controller.create_product(nome, descricao, preco, estoque, categoria)
    if erro:
        return jsonify({"erro": erro}), 400
    return jsonify({"dados": {"id": novo_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


@product_bp.route("/produtos/<int:id>", methods=["PUT"])
def atualizar_produto(id):
    produto_existente = product_controller.get_product(id)
    if not produto_existente:
        return jsonify({"erro": "Produto não encontrado"}), 404

    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Dados inválidos"}), 400
    if "nome" not in dados:
        return jsonify({"erro": "Nome é obrigatório"}), 400
    if "preco" not in dados:
        return jsonify({"erro": "Preço é obrigatório"}), 400
    if "estoque" not in dados:
        return jsonify({"erro": "Estoque é obrigatório"}), 400

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", "geral")

    erro = product_controller.update_product(id, nome, descricao, preco, estoque, categoria)
    if erro:
        return jsonify({"erro": erro}), 400
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@product_bp.route("/produtos/<int:id>", methods=["DELETE"])
def deletar_produto(id):
    produto = product_controller.get_product(id)
    if not produto:
        return jsonify({"erro": "Produto não encontrado"}), 404
    product_controller.delete_product(id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
