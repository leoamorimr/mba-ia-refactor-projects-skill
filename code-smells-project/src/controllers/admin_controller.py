"""Admin-only operations. Both are gated behind `middlewares.auth.require_admin`
at the route layer - see views/admin_routes.py. This module still allows
raw SQL execution for `execute_query`, which is a genuinely dangerous
capability; the fix applied here is closing the "no authentication at all"
hole per the audit's recommendation (gate behind an authenticated admin
check), not changing what the endpoint does once authorized.
"""
import logging

from database.connection import get_db

logger = logging.getLogger(__name__)


def reset_database():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM itens_pedido")
    cursor.execute("DELETE FROM pedidos")
    cursor.execute("DELETE FROM produtos")
    cursor.execute("DELETE FROM usuarios")
    db.commit()
    logger.warning("Banco de dados resetado via endpoint administrativo")
    return {"mensagem": "Banco de dados resetado", "sucesso": True}


def execute_query(sql):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql)
    if sql.strip().upper().startswith("SELECT"):
        rows = cursor.fetchall()
        return {"dados": [dict(row) for row in rows], "sucesso": True}
    db.commit()
    return {"mensagem": "Query executada", "sucesso": True}
