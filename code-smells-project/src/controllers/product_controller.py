"""Orchestration + business rules for products. Routes call these
functions with already-parsed input and translate the result into an
HTTP response - no SQL and no `request`/`jsonify` in here.
"""
from models import product_model

PRODUCT_NAME_MIN_LENGTH = 2
PRODUCT_NAME_MAX_LENGTH = 200
VALID_CATEGORIES = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]


def _validate_product_fields(nome, preco, estoque, categoria):
    """Shared by create and update so both enforce identical rules -
    previously `atualizar_produto` skipped the name-length/category checks
    that `criar_produto` applied, letting invalid data in through PUT.
    """
    if preco is None or preco < 0:
        return "Preço não pode ser negativo"
    if estoque is None or estoque < 0:
        return "Estoque não pode ser negativo"
    if not isinstance(nome, str) or len(nome) < PRODUCT_NAME_MIN_LENGTH:
        return "Nome muito curto"
    if len(nome) > PRODUCT_NAME_MAX_LENGTH:
        return "Nome muito longo"
    if categoria not in VALID_CATEGORIES:
        return f"Categoria inválida. Válidas: {VALID_CATEGORIES}"
    return None


def list_products(limit=None, offset=0):
    return product_model.get_all(limit=limit, offset=offset)


def get_product(product_id):
    return product_model.get_by_id(product_id)


def create_product(nome, descricao, preco, estoque, categoria):
    """Returns (erro, novo_id)."""
    erro = _validate_product_fields(nome, preco, estoque, categoria)
    if erro:
        return erro, None
    novo_id = product_model.create(nome, descricao, preco, estoque, categoria)
    return None, novo_id


def update_product(product_id, nome, descricao, preco, estoque, categoria):
    """Returns erro or None on success."""
    erro = _validate_product_fields(nome, preco, estoque, categoria)
    if erro:
        return erro
    product_model.update(product_id, nome, descricao, preco, estoque, categoria)
    return None


def delete_product(product_id):
    return product_model.deactivate(product_id)


def search_products(termo, categoria=None, preco_min=None, preco_max=None, limit=None, offset=0):
    return product_model.search(
        termo, categoria=categoria, preco_min=preco_min, preco_max=preco_max,
        limit=limit, offset=offset,
    )
