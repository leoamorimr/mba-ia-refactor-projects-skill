"""Data access for the `produtos` table. No HTTP concepts, no business
rules - only parameterized SQL and row-to-dict shaping.
"""
from database.connection import get_db


def _row_to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def get_all(limit=None, offset=0):
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM produtos WHERE ativo = 1 ORDER BY id"
    params = ()
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params = (limit, offset)
    cursor.execute(query, params)
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_by_id(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ? AND ativo = 1", (product_id,))
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def get_by_ids(product_ids):
    """Batch fetch used by order creation to avoid one SELECT per item."""
    if not product_ids:
        return {}
    db = get_db()
    cursor = db.cursor()
    placeholders = ",".join("?" * len(product_ids))
    cursor.execute(
        f"SELECT * FROM produtos WHERE id IN ({placeholders})",
        tuple(product_ids),
    )
    return {row["id"]: _row_to_dict(row) for row in cursor.fetchall()}


def create(nome, descricao, preco, estoque, categoria):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
        "VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    db.commit()
    return cursor.lastrowid


def update(product_id, nome, descricao, preco, estoque, categoria):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, "
        "categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, product_id),
    )
    db.commit()
    return True


def deactivate(product_id):
    """Soft-delete: keeps historical order items pointing at a real row
    instead of orphaning them, while still making the product disappear
    from lookups/listings exactly like a hard delete would from the API's
    point of view.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (product_id,))
    db.commit()
    return True


def decrement_stock_bulk(items):
    """items: iterable of (quantidade, produto_id) tuples."""
    db = get_db()
    cursor = db.cursor()
    cursor.executemany(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ?", items
    )
    db.commit()


def restore_stock_bulk(items):
    """items: iterable of (quantidade, produto_id) tuples."""
    db = get_db()
    cursor = db.cursor()
    cursor.executemany(
        "UPDATE produtos SET estoque = estoque + ? WHERE id = ?", items
    )
    db.commit()


def search(termo=None, categoria=None, preco_min=None, preco_max=None, limit=None, offset=0):
    db = get_db()
    cursor = db.cursor()

    query = "SELECT * FROM produtos WHERE ativo = 1"
    params = []
    if termo:
        query += " AND (nome LIKE ? OR descricao LIKE ?)"
        like_termo = f"%{termo}%"
        params.extend([like_termo, like_termo])
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    if preco_min is not None:
        query += " AND preco >= ?"
        params.append(preco_min)
    if preco_max is not None:
        query += " AND preco <= ?"
        params.append(preco_max)
    query += " ORDER BY id"
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    cursor.execute(query, tuple(params))
    return [_row_to_dict(row) for row in cursor.fetchall()]
