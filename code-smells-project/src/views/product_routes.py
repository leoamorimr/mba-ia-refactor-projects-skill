"""Routing + request/response shaping only for the `/produtos` domain -
no SQL, no business rules. Required-field presence is checked here (the
"is this endpoint even the right shape" concern); business validation
(lengths, categories, negative numbers) lives in product_controller.

`create_product_blueprint` takes the already-constructed `ProductController`
as an argument (built once in `app.py`'s composition root) and closes over
it in every route handler, instead of the module importing a controller
module and calling its functions directly - this is what lets the
controller's own dependencies (its repository) be injected all the way
down from a single place.

`DELETE /produtos/<id>` is gated by the same `require_admin` guard used on
`/admin/*` - it used to have no authentication at all, letting any
anonymous client deactivate any product. A previously-open destructive
route now correctly requiring auth is the intended fix, not a contract
break.
"""
from flask import Blueprint, jsonify, request

from middlewares.auth import require_admin


def _parse_pagination():
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    return limit, offset


def _parse_product_payload(dados):
    """Shared by `criar_produto`/`atualizar_produto` so the required-field
    check and field extraction live in exactly one place. Returns
    `(erro, campos)` where `campos` is `(nome, descricao, preco, estoque,
    categoria)` on success, or `(erro, None)` on a missing-field error.
    """
    if "nome" not in dados:
        return "Nome é obrigatório", None
    if "preco" not in dados:
        return "Preço é obrigatório", None
    if "estoque" not in dados:
        return "Estoque é obrigatório", None

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", "geral")
    return None, (nome, descricao, preco, estoque, categoria)


def create_product_blueprint(product_controller):
    product_bp = Blueprint("products", __name__)

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

        erro, campos = _parse_product_payload(dados)
        if erro:
            return jsonify({"erro": erro}), 400
        nome, descricao, preco, estoque, categoria = campos

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

        erro, campos = _parse_product_payload(dados)
        if erro:
            return jsonify({"erro": erro}), 400
        nome, descricao, preco, estoque, categoria = campos

        erro = product_controller.update_product(id, nome, descricao, preco, estoque, categoria)
        if erro:
            return jsonify({"erro": erro}), 400
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    @product_bp.route("/produtos/<int:id>", methods=["DELETE"])
    @require_admin
    def deletar_produto(id):
        produto = product_controller.get_product(id)
        if not produto:
            return jsonify({"erro": "Produto não encontrado"}), 404
        product_controller.delete_product(id)
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200

    return product_bp
