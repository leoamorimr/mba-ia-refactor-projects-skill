"""Health-check status. Deliberately returns no secrets and no internal
configuration (no SECRET_KEY, no debug flag, no DB path) - only a status
and non-sensitive counts, per the audit finding on the old `/health`
response.

`HealthController` receives the shared `DatabaseConnection` via the
constructor instead of importing a module-level singleton getter. A raw
connection (rather than the three domain repositories) is injected here
because this check is intentionally cross-entity and read-only - adding a
`count()` method to every repository just for this would be more
indirection than the endpoint needs.
"""


class HealthController:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def get_health_status(self):
        db = self.db_connection.get_connection()
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
