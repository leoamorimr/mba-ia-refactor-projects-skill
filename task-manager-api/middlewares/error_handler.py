"""Centralized error handling.

Registered once at the app level so route/controller code never has to
repeat its own try/except-log-500 boilerplate. Controllers may still catch
exceptions they can meaningfully recover from (e.g. to roll back a
transaction), but should let anything unexpected propagate here.
"""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({'error': error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        logger.exception('Unhandled error: %s', error)
        return jsonify({'error': 'Erro interno do servidor'}), 500
