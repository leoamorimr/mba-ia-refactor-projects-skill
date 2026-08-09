"""Orchestration + business rules for users, including password hashing
and authentication. Plaintext passwords never touch the model layer or a
SQL predicate.
"""
import re

from werkzeug.security import check_password_hash, generate_password_hash

from models import user_model

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 6


def list_users(limit=None, offset=0):
    return user_model.get_all(limit=limit, offset=offset)


def get_user(user_id):
    return user_model.get_by_id(user_id)


def validate_new_user(nome, email, senha):
    """Returns an error message, or None if the payload is valid."""
    if not nome or not email or not senha:
        return "Nome, email e senha são obrigatórios"
    if not EMAIL_PATTERN.match(email):
        return "Email inválido"
    if len(senha) < PASSWORD_MIN_LENGTH:
        return f"Senha deve ter ao menos {PASSWORD_MIN_LENGTH} caracteres"
    return None


def create_user(nome, email, senha, tipo="cliente"):
    senha_hash = generate_password_hash(senha)
    return user_model.create(nome, email, senha_hash, tipo)


def authenticate(email, senha):
    """Returns the public user dict on success (never includes the hash),
    or None if the credentials are invalid.
    """
    usuario = user_model.get_by_email(email)
    if usuario and check_password_hash(usuario["senha"], senha):
        return {
            "id": usuario["id"],
            "nome": usuario["nome"],
            "email": usuario["email"],
            "tipo": usuario["tipo"],
        }
    return None
