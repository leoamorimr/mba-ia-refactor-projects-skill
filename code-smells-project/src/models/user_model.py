"""Data access for the `usuarios` table. Passwords are always stored
already-hashed by the caller (see controllers.user_controller) - this
module never hashes or compares passwords itself.
"""
from database.connection import get_db


def _row_to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "senha": row["senha"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def get_all(limit=None, offset=0):
    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM usuarios ORDER BY id"
    params = ()
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params = (limit, offset)
    cursor.execute(query, params)
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_by_id(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def get_by_email(email):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def create(nome, email, senha_hash, tipo="cliente"):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, senha_hash, tipo),
    )
    db.commit()
    return cursor.lastrowid
