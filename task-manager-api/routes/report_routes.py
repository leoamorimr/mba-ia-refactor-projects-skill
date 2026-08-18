from flask import Blueprint, jsonify

from controllers import report_controller
from middlewares.auth import login_required

report_bp = Blueprint('reports', __name__)


@report_bp.route('/reports/summary', methods=['GET'])
@login_required
def summary_report():
    report = report_controller.summary_report()
    return jsonify(report), 200


@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
@login_required
def user_report(user_id):
    report, error, status_code = report_controller.user_report(user_id)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(report), status_code
