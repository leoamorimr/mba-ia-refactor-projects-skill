"""Orchestration + business rules for products. Routes call these
functions with already-parsed input and translate the result into an
HTTP response - no SQL and no `request`/`jsonify` in here.

`ProductController` receives its `ProductRepository` via the constructor
(built once in `app.py`'s composition root) instead of importing the data
module and reaching for a global connection.
"""

PRODUCT_NAME_MIN_LENGTH = 2
PRODUCT_NAME_MAX_LENGTH = 200
VALID_CATEGORIES = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]


def _validate_product_fields(nome, preco, estoque, categoria):
    """Shared by create and update so both enforce identical rules -
    previously `atualizar_produto` skipped the name-length/category checks
    that `criar_produto` applied, letting invalid data in through PUT.
    """
    if preco is None or isinstance(preco, bool) or not isinstance(preco, (int, float)):
        return "Preço deve ser numérico"
    if preco < 0:
        return "Preço não pode ser negativo"
    if estoque is None or isinstance(estoque, bool) or not isinstance(estoque, int):
        return "Estoque deve ser um número inteiro"
    if estoque < 0:
        return "Estoque não pode ser negativo"
    if not isinstance(nome, str) or len(nome) < PRODUCT_NAME_MIN_LENGTH:
        return "Nome muito curto"
    if len(nome) > PRODUCT_NAME_MAX_LENGTH:
        return "Nome muito longo"
    if categoria not in VALID_CATEGORIES:
        return f"Categoria inválida. Válidas: {VALID_CATEGORIES}"
    return None


class ProductController:
    def __init__(self, product_repository):
        self.product_repository = product_repository

    def list_products(self, limit=None, offset=0):
        return self.product_repository.get_all(limit=limit, offset=offset)

    def get_product(self, product_id):
        return self.product_repository.get_by_id(product_id)

    def create_product(self, nome, descricao, preco, estoque, categoria):
        """Returns (erro, novo_id)."""
        erro = _validate_product_fields(nome, preco, estoque, categoria)
        if erro:
            return erro, None
        novo_id = self.product_repository.create(nome, descricao, preco, estoque, categoria)
        return None, novo_id

    def update_product(self, product_id, nome, descricao, preco, estoque, categoria):
        """Returns erro or None on success."""
        erro = _validate_product_fields(nome, preco, estoque, categoria)
        if erro:
            return erro
        self.product_repository.update(product_id, nome, descricao, preco, estoque, categoria)
        return None

    def delete_product(self, product_id):
        return self.product_repository.deactivate(product_id)

    def search_products(self, termo, categoria=None, preco_min=None, preco_max=None, limit=None, offset=0):
        return self.product_repository.search(
            termo, categoria=categoria, preco_min=preco_min, preco_max=preco_max,
            limit=limit, offset=offset,
        )
