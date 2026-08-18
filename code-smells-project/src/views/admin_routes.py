"""Routing only for `/admin/*`. Both routes are gated by `require_admin` -
previously they had no authentication at all (a fully open DB wipe and an
open raw-SQL console). A previously-open endpoint now correctly requiring
auth is the intended, expected change here.

`create_admin_blueprint` closes over the already-constructed
`AdminController` (built once in `app.py`'s composition root) instead of
importing a controller module and calling its functions directly.

`executar_query` does not wrap `admin_controller.execute_query` in its own
try/except - that would reintroduce exactly the per-route "log and return
500" pattern that `middlewares/error_handler.py`'s centralized
`@app.errorhandler(Exception)` exists to eliminate, and it used to leak
raw SQLite error text straight to the client. Malformed/rejected queries
raise `errors.ValidationError`, handled centrally as a 400; any other
unexpected error propagates to the generic 500 handler like every other
controller in the app.
"""
from flask import Blueprint, jsonify, request

from middlewares.auth import require_admin


def create_admin_blueprint(admin_controller):
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

        resultado = admin_controller.execute_query(query)
        return jsonify(resultado), 200

    return admin_bp
