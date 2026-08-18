"""Authentication middleware.

Verifies real, signed JWTs (issued by controllers/user_controller.login)
against the app's SECRET_KEY. Apply @login_required to every mutating /
destructive route -- there is no session or cookie auth in this app, only
bearer tokens.
"""
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from database import db
from models.user import User


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token de autenticação ausente'}), 401

        token = auth_header[len('Bearer '):].strip()
        if not token:
            return jsonify({'error': 'Token de autenticação ausente'}), 401

        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256'],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401

        user = db.session.get(User, payload.get('user_id'))
        if not user or not user.active:
            return jsonify({'error': 'Usuário inválido ou inativo'}), 401

        g.current_user = user
        return view_func(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    """Authorize by role. Must be applied after (i.e. below) @login_required
    so that `g.current_user` is already set.

    `roles_required('admin')` is the common case; `g.current_user.is_admin()`
    is used directly rather than a plain role-string comparison so the check
    stays in one place if admin ever stops being a single literal role.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({'error': 'Token de autenticação ausente'}), 401
            if 'admin' in roles:
                if not user.is_admin():
                    return jsonify({'error': 'Permissão insuficiente'}), 403
            elif user.role not in roles:
                return jsonify({'error': 'Permissão insuficiente'}), 403
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
