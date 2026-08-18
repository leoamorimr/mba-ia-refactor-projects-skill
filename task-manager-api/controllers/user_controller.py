"""User business logic: validation, auth token issuance, and orchestration."""
import logging
from datetime import timedelta

import jwt
from sqlalchemy import func

from config.settings import JWT_EXPIRATION_HOURS, SECRET_KEY
from database import db
from models.task import Task
from models.user import User
from utils.helpers import (
    DEFAULT_PAGE,
    DEFAULT_PER_PAGE,
    MIN_PASSWORD_LENGTH,
    VALID_ROLES,
    clamp_pagination,
    format_date,
    is_valid_password,
    utc_now,
    validate_email,
)

logger = logging.getLogger(__name__)


def list_users(page=DEFAULT_PAGE, per_page=DEFAULT_PER_PAGE):
    page, per_page = clamp_pagination(page, per_page)

    users = (
        User.query.order_by(User.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    user_ids = [user.id for user in users]
    task_counts = dict(
        db.session.query(Task.user_id, func.count(Task.id))
        .filter(Task.user_id.in_(user_ids))
        .group_by(Task.user_id)
        .all()
    )

    result = []
    for user in users:
        user_data = user.to_public_dict()
        user_data['task_count'] = task_counts.get(user.id, 0)
        result.append(user_data)

    return result


def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return None, 'Usuário não encontrado', 404

    data = user.to_public_dict()
    tasks = Task.query.filter_by(user_id=user_id).all()
    data['tasks'] = [task.to_dict() for task in tasks]
    return data, None, 200


def create_user(data, caller=None):
    """Create a user.

    `caller` is the authenticated `g.current_user` performing the request.
    Only an admin caller may assign an elevated `role` -- for anyone else
    (including self-service creation), any `role` in the payload is
    ignored and the new account is always created as `role='user'`.
    """
    if not data:
        return None, 'Dados inválidos', 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    requested_role = data.get('role', 'user')

    if not name:
        return None, 'Nome é obrigatório', 400
    if not email:
        return None, 'Email é obrigatório', 400
    if not password:
        return None, 'Senha é obrigatória', 400

    if not validate_email(email):
        return None, 'Email inválido', 400

    if not is_valid_password(password):
        return None, (
            f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres '
            'e conter ao menos uma letra e um número'
        ), 400

    if User.query.filter_by(email=email).first():
        return None, 'Email já cadastrado', 409

    caller_is_admin = bool(caller and caller.is_admin())

    if caller_is_admin:
        if requested_role not in VALID_ROLES:
            return None, 'Role inválido', 400
        role = requested_role
    else:
        # Non-admin callers (including self-service signup) can never set
        # their own or anyone else's role -- force it server-side.
        role = 'user'

    user = User(name=name, email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('User created: id=%s name=%s', user.id, user.name)
    return user.to_public_dict(), None, 201


def update_user(user_id, data, caller=None):
    """Update a user.

    `caller` is the authenticated `g.current_user` performing the request.
    Only the account owner or an admin may update a user at all; only an
    admin may change the `role` field (their own or anyone else's).
    """
    user = db.session.get(User, user_id)
    if not user:
        return None, 'Usuário não encontrado', 404

    if not data:
        return None, 'Dados inválidos', 400

    caller_is_admin = bool(caller and caller.is_admin())
    is_owner = bool(caller and caller.id == user_id)

    if not (is_owner or caller_is_admin):
        return None, 'Permissão insuficiente', 403

    if 'role' in data:
        if not caller_is_admin:
            return None, 'Apenas administradores podem alterar o role', 403
        if data['role'] not in VALID_ROLES:
            return None, 'Role inválido', 400
        user.role = data['role']

    if 'name' in data:
        user.name = data['name']

    if 'email' in data:
        if not validate_email(data['email']):
            return None, 'Email inválido', 400

        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != user_id:
            return None, 'Email já cadastrado', 409
        user.email = data['email']

    if 'password' in data:
        if not is_valid_password(data['password']):
            return None, (
                f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres '
                'e conter ao menos uma letra e um número'
            ), 400
        user.set_password(data['password'])

    if 'active' in data:
        user.active = data['active']

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return user.to_public_dict(), None, 200


def delete_user(user_id, caller=None):
    """Delete a user. Only the account owner or an admin may do this."""
    user = db.session.get(User, user_id)
    if not user:
        return None, 'Usuário não encontrado', 404

    caller_is_admin = bool(caller and caller.is_admin())
    is_owner = bool(caller and caller.id == user_id)
    if not (is_owner or caller_is_admin):
        return None, 'Permissão insuficiente', 403

    Task.query.filter_by(user_id=user_id).delete()

    db.session.delete(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('User deleted: id=%s', user_id)
    return {'message': 'Usuário deletado com sucesso'}, None, 200


def get_user_tasks(user_id, page=DEFAULT_PAGE, per_page=DEFAULT_PER_PAGE):
    user = db.session.get(User, user_id)
    if not user:
        return None, 'Usuário não encontrado', 404

    page, per_page = clamp_pagination(page, per_page)

    tasks = (
        Task.query.filter_by(user_id=user_id)
        .order_by(Task.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )
    result = []
    for task in tasks:
        result.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'created_at': format_date(task.created_at),
            'due_date': format_date(task.due_date),
            'overdue': task.is_overdue(),
        })

    return result, None, 200


def login(data):
    if not data:
        return None, 'Dados inválidos', 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return None, 'Email e senha são obrigatórios', 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return None, 'Credenciais inválidas', 401

    if not user.active:
        return None, 'Usuário inativo', 403

    token = _issue_token(user)

    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_public_dict(),
        'token': token,
    }, None, 200


def _issue_token(user):
    now = utc_now()
    payload = {
        'user_id': user.id,
        'role': user.role,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
