"""Data access for the `usuarios` table. Passwords are always stored
already-hashed by the caller (see controllers.user_controller) - this
module never hashes or compares passwords itself.

`UserRepository` receives its `DatabaseConnection` via the constructor
(built once in `app.py`'s composition root) instead of importing a
module-level singleton getter.
"""


def _row_to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "senha": row["senha"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def to_public_dict(user):
    """Shapes a user dict for any response path that must never leak the
    password hash (e.g. `GET /usuarios`, `GET /usuarios/<id>`). The only
    call site allowed to keep `senha` is the internal `authenticate()`
    lookup in `controllers.user_controller`, which needs the hash to call
    `check_password_hash`. Pure data shaping, no DB access - no need for
    constructor injection here.
    """
    if user is None:
        return None
    return {key: value for key, value in user.items() if key != "senha"}


class UserRepository:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def get_all(self, limit=None, offset=0):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        query = "SELECT * FROM usuarios ORDER BY id"
        params = ()
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = (limit, offset)
        cursor.execute(query, params)
        return [_row_to_dict(row) for row in cursor.fetchall()]

    def get_by_id(self, user_id):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None

    def get_by_email(self, email):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None

    def create(self, nome, email, senha_hash, tipo="cliente"):
        db = self.db_connection.get_connection()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
        db.commit()
        return cursor.lastrowid
