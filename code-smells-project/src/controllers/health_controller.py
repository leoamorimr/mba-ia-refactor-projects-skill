"""Health-check status. Deliberately returns no secrets and no internal
configuration (no SECRET_KEY, no debug flag, no DB path) - only a status
and non-sensitive counts, per the audit finding on the old `/health`
response.
"""
from database.connection import get_db


def get_health_status():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
    produtos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    usuarios = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pedidos")
    pedidos = cursor.fetchone()[0]

    return {
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": produtos,
            "usuarios": usuarios,
            "pedidos": pedidos,
        },
        "versao": "1.0.0",
    }
