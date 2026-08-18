"""Routing only for `/relatorios/vendas`.

`create_report_blueprint` closes over the already-constructed
`ReportController` (built once in `app.py`'s composition root) instead of
importing a controller module and calling its functions directly.
"""
from flask import Blueprint, jsonify


def create_report_blueprint(report_controller):
    report_bp = Blueprint("reports", __name__)

    @report_bp.route("/relatorios/vendas", methods=["GET"])
    def relatorio_vendas():
        relatorio = report_controller.build_sales_report()
        return jsonify({"dados": relatorio, "sucesso": True}), 200

    return report_bp
