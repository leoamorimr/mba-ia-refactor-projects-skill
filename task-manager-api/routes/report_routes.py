from flask import Blueprint, jsonify

from controllers import report_controller

report_bp = Blueprint('reports', __name__)


@report_bp.route('/reports/summary', methods=['GET'])
def summary_report():
    report = report_controller.summary_report()
    return jsonify(report), 200


@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
def user_report(user_id):
    report, error, status_code = report_controller.user_report(user_id)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(report), status_code
