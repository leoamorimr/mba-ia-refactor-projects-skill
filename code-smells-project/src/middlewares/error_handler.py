"""Single centralized error-handling strategy for the whole app, replacing
the ~19 duplicated `try/except Exception as e: return jsonify({"erro":
str(e)}), 500` blocks that used to live in every controller function.

Expected/known failure modes get their own typed exception + status code;
anything unexpected is logged with a full traceback and returns a generic
500 instead of leaking exception internals to the client.
"""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from errors import NotFoundError, UnauthorizedError, ValidationError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({"erro": str(e)}), 400

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(e):
        return jsonify({"erro": str(e)}), 404

    @app.errorhandler(UnauthorizedError)
    def handle_unauthorized_error(e):
        return jsonify({"erro": str(e)}), 401

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        # Let Flask/Werkzeug's own HTTP errors (404 on unknown routes, 405
        # on wrong methods, etc.) pass through unchanged instead of being
        # swallowed by the catch-all handler below.
        return e

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        logger.exception("Unhandled error")
        return jsonify({"erro": "Erro interno no servidor"}), 500
