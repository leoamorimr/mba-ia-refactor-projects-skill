"""Data access for the `produtos` table. No HTTP concepts, no business
rules - only parameterized SQL and row-to-dict shaping.

`ProductRepository` takes its `DatabaseConnection` via the constructor
instead of reaching for a module-level singleton - the composition root
(`app.py`) builds one `DatabaseConnection` and passes that same instance
into every repository, so a test or an alternate backend can inject a
different connection without monkeypatching this module.
"""


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


class ProductRepository:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def get_all(self, limit=None, offset=0):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        query = "SELECT * FROM produtos WHERE ativo = 1 ORDER BY id"
        params = ()
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = (limit, offset)
        cursor.execute(query, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]

    def get_by_id(self, product_id):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM produtos WHERE id = ? AND ativo = 1", (product_id,))
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None

    def get_by_ids(self, product_ids):
        """Batch fetch used by order creation to avoid one SELECT per item."""
        if not product_ids:
            return {}
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        placeholders = ",".join("?" * len(product_ids))
        cursor.execute(
            f"SELECT * FROM produtos WHERE id IN ({placeholders})",
            tuple(product_ids),
        )
        return {row["id"]: _row_to_dict(row) for row in cursor.fetchall()}

    def create(self, nome, descricao, preco, estoque, categoria):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        db.commit()
        return cursor.lastrowid

    def update(self, product_id, nome, descricao, preco, estoque, categoria):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, "
            "categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, product_id),
        )
        db.commit()
        return True

    def deactivate(self, product_id):
        """Soft-delete: keeps historical order items pointing at a real row
        instead of orphaning them, while still making the product disappear
        from lookups/listings exactly like a hard delete would from the API's
        point of view.
        """
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (product_id,))
        db.commit()
        return True

    def decrement_stock_bulk(self, items):
        """items: iterable of (quantidade, produto_id) tuples."""
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.executemany(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ?", items
        )
        db.commit()

    def restore_stock_bulk(self, items):
        """items: iterable of (quantidade, produto_id) tuples."""
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.executemany(
            "UPDATE produtos SET estoque = estoque + ? WHERE id = ?", items
        )
        db.commit()

    def search(self, termo=None, categoria=None, preco_min=None, preco_max=None, limit=None, offset=0):
        db = self.db_connection.get_connection()
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
