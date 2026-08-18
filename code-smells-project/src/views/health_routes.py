"""Routing only for `/health`.

`create_health_blueprint` closes over the already-constructed
`HealthController` (built once in `app.py`'s composition root) instead of
importing a controller module and calling its functions directly.
"""
from flask import Blueprint, jsonify


def create_health_blueprint(health_controller):
    health_bp = Blueprint("health", __name__)

    @health_bp.route("/health", methods=["GET"])
    def health_check():
        status = health_controller.get_health_status()
        return jsonify(status), 200

    return health_bp
