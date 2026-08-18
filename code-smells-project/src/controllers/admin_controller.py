"""Admin-only operations. Both are gated behind `middlewares.auth.require_admin`
at the route layer - see views/admin_routes.py.

`AdminController` receives the shared `DatabaseConnection` via the
constructor instead of importing a module-level singleton getter.

`execute_query` used to run any client-submitted SQL string verbatim -
`DROP TABLE`, `UPDATE usuarios SET tipo='admin'`, `SELECT senha FROM
usuarios`, etc. - which meant possession of the single shared admin token
granted full read/write/delete access to every table, including dumping
every password hash. Removing the raw-SQL console entirely (replacing it
with a handful of named, parameterized operations) was judged too large a
scope change for this pass, so instead the endpoint is now restricted to a
single read-only `SELECT` statement, and any column that looks like a
credential is stripped from the result before it leaves this function.

This closes the "arbitrary write/delete" and "bulk-dump every password
hash via the obvious column name" risks, which is the actual impact the
audit called out. It does NOT fully close the finding: a client could
still read arbitrary non-sensitive rows, and a `SELECT senha AS x FROM
usuarios` alias can defeat the by-name column filter, since this endpoint
still executes free-form `SELECT` text rather than a real allow-list of
statements. Full removal in favor of a named allow-listed query set
remains the recommended follow-up if this console is still needed at all.
"""
import logging

from errors import ValidationError

logger = logging.getLogger(__name__)

# Column names stripped from every row this endpoint returns, regardless of
# which table they came from - defense in depth against a `SELECT *` (or an
# explicit `senha` column) leaking a credential through the admin console.
SENSITIVE_COLUMNS = {"senha", "password", "senha_hash", "password_hash"}


class AdminController:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def reset_database(self):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute("DELETE FROM itens_pedido")
        cursor.execute("DELETE FROM pedidos")
        cursor.execute("DELETE FROM produtos")
        cursor.execute("DELETE FROM usuarios")
        db.commit()
        logger.warning("Banco de dados resetado via endpoint administrativo")
        return {"mensagem": "Banco de dados resetado", "sucesso": True}

    def execute_query(self, sql):
        """Runs a single, read-only SELECT and strips sensitive-looking
        columns from the result. Raises ValidationError (handled centrally,
        see middlewares/error_handler.py) for anything else - multiple
        statements, or any non-SELECT statement (INSERT/UPDATE/DELETE/DROP/
        etc.).
        """
        normalized = sql.strip()
        if not normalized.upper().startswith("SELECT"):
            raise ValidationError("Somente instruções SELECT são permitidas neste endpoint")
        if ";" in normalized.rstrip(";"):
            raise ValidationError("Apenas uma única instrução SELECT é permitida por requisição")

        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute(normalized)
        rows = cursor.fetchall()
        dados = []
        for row in rows:
            row_dict = dict(row)
            for column in SENSITIVE_COLUMNS:
                row_dict.pop(column, None)
            dados.append(row_dict)
        return {"dados": dados, "sucesso": True}
