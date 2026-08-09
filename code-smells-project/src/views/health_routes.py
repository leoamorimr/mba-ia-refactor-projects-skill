"""Routing only for `/health`."""
from flask import Blueprint, jsonify

from controllers import health_controller

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    status = health_controller.get_health_status()
    return jsonify(status), 200
