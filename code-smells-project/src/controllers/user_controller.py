"""Orchestration + business rules for users, including password hashing
and authentication. Plaintext passwords never touch the model layer or a
SQL predicate.

`UserController` receives its `UserRepository` via the constructor instead
of importing the data module directly.
"""
import re

from werkzeug.security import check_password_hash, generate_password_hash

from models.user_model import to_public_dict

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 6


class UserController:
    def __init__(self, user_repository):
        self.user_repository = user_repository

    def list_users(self, limit=None, offset=0):
        """Public listing - never includes the password hash."""
        usuarios = self.user_repository.get_all(limit=limit, offset=offset)
        return [to_public_dict(usuario) for usuario in usuarios]

    def get_user(self, user_id):
        """Public lookup - never includes the password hash."""
        return to_public_dict(self.user_repository.get_by_id(user_id))

    def validate_new_user(self, nome, email, senha):
        """Returns an error message, or None if the payload is valid."""
        if not nome or not email or not senha:
            return "Nome, email e senha são obrigatórios"
        if not EMAIL_PATTERN.match(email):
            return "Email inválido"
        if len(senha) < PASSWORD_MIN_LENGTH:
            return f"Senha deve ter ao menos {PASSWORD_MIN_LENGTH} caracteres"
        if self.user_repository.get_by_email(email):
            return "Email já cadastrado"
        return None

    def create_user(self, nome, email, senha, tipo="cliente"):
        senha_hash = generate_password_hash(senha)
        return self.user_repository.create(nome, email, senha_hash, tipo)

    def authenticate(self, email, senha):
        """Returns the public user dict on success (never includes the hash),
        or None if the credentials are invalid.
        """
        usuario = self.user_repository.get_by_email(email)
        if usuario and check_password_hash(usuario["senha"], senha):
            return {
                "id": usuario["id"],
                "nome": usuario["nome"],
                "email": usuario["email"],
                "tipo": usuario["tipo"],
            }
        return None
