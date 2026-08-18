"""Data access for `pedidos` / `itens_pedido`. Order-total math, discount
tiers and stock-restoration rules live in controllers.order_controller /
controllers.report_controller - this module only reads and writes rows.

`OrderRepository` receives its `DatabaseConnection` via the constructor
instead of importing a module-level singleton getter.
"""


class OrderRepository:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def create(self, usuario_id, total):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
            (usuario_id, total),
        )
        db.commit()
        return cursor.lastrowid

    def insert_items_bulk(self, items):
        """items: iterable of (pedido_id, produto_id, quantidade, preco_unitario)."""
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.executemany(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
            "VALUES (?, ?, ?, ?)",
            items,
        )
        db.commit()

    def get_items_by_order(self, pedido_id):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
        return [dict(row) for row in cursor.fetchall()]

    def list_orders(self, usuario_id=None, limit=None, offset=0):
        """Single JOIN query replacing the old per-order/per-item N+1 loops.
        Grouping happens in memory since sqlite has no native "array_agg".
        """
        db = self.db_connection.get_connection()
        cursor = db.cursor()

        query = """
            SELECT p.id AS pedido_id, p.usuario_id, p.status, p.total, p.criado_em,
                   i.produto_id AS item_produto_id, i.quantidade, i.preco_unitario,
                   pr.nome AS produto_nome
            FROM pedidos p
            LEFT JOIN itens_pedido i ON i.pedido_id = p.id
            LEFT JOIN produtos pr ON pr.id = i.produto_id
        """
        params = []
        if usuario_id is not None:
            query += " WHERE p.usuario_id = ?"
            params.append(usuario_id)
        query += " ORDER BY p.id"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        orders_by_id = {}
        ordered_ids = []
        for row in rows:
            pedido_id = row["pedido_id"]
            if pedido_id not in orders_by_id:
                orders_by_id[pedido_id] = {
                    "id": pedido_id,
                    "usuario_id": row["usuario_id"],
                    "status": row["status"],
                    "total": row["total"],
                    "criado_em": row["criado_em"],
                    "itens": [],
                }
                ordered_ids.append(pedido_id)
            if row["item_produto_id"] is not None:
                orders_by_id[pedido_id]["itens"].append({
                    "produto_id": row["item_produto_id"],
                    "produto_nome": row["produto_nome"] or "Desconhecido",
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                })

        result = [orders_by_id[pid] for pid in ordered_ids]
        if limit is not None:
            result = result[offset:offset + limit]
        return result

    def update_status(self, pedido_id, novo_status):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
        db.commit()
        return True

    def get_stats(self):
        db = self.db_connection.get_connection()
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM pedidos")
        total_pedidos, faturamento = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = ?", ("pendente",))
        pendentes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = ?", ("aprovado",))
        aprovados = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = ?", ("cancelado",))
        cancelados = cursor.fetchone()[0]

        return {
            "total_pedidos": total_pedidos,
            "faturamento": faturamento,
            "pendentes": pendentes,
            "aprovados": aprovados,
            "cancelados": cancelados,
        }
