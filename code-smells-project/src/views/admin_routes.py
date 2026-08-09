"""Routing only for `/admin/*`. Both routes are gated by `require_admin` -
previously they had no authentication at all (a fully open DB wipe and an
open raw-SQL console). A previously-open endpoint now correctly requiring
auth is the intended, expected change here.
"""
from flask import Blueprint, jsonify, request

from controllers import admin_controller
from middlewares.auth import require_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/reset-db", methods=["POST"])
@require_admin
def reset_database():
    resultado = admin_controller.reset_database()
    return jsonify(resultado), 200


@admin_bp.route("/admin/query", methods=["POST"])
@require_admin
def executar_query():
    dados = request.get_json(silent=True) or {}
    query = dados.get("sql", "")
    if not query:
        return jsonify({"erro": "Query não informada"}), 400

    try:
        resultado = admin_controller.execute_query(query)
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
