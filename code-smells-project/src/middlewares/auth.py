"""Minimum-viable admin gate for the two destructive endpoints that used
to have no authentication at all (`/admin/reset-db`, `/admin/query`).

There is no session/user auth system in this project to hang a real
role-check off of, so this validates a static admin token passed via the
`X-Admin-Token` header against the `ADMIN_TOKEN` environment variable. If
`ADMIN_TOKEN` is not configured, the routes fail closed (nobody gets in)
rather than falling back to a hardcoded value. A real auth system
(sessions/JWT + roles) is a follow-up beyond this refactor's scope.
"""
from functools import wraps

from flask import jsonify, request

from config.settings import ADMIN_TOKEN


def require_admin(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token")
        if not ADMIN_TOKEN or token != ADMIN_TOKEN:
            return jsonify({"erro": "Não autorizado"}), 401
        return view_func(*args, **kwargs)
    return wrapper
