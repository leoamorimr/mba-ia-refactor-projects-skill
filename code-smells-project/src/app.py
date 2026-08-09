"""Composition root: the only file that imports config, initializes the
DB connection, registers all blueprints, and starts the server. It
contains wiring only - no business logic, no SQL, no route handlers.
"""
from flask import Flask
from flask_cors import CORS

from config.settings import DEBUG, HOST, PORT, SECRET_KEY
from database.connection import init_db
from middlewares.error_handler import register_error_handlers
from views.admin_routes import admin_bp
from views.health_routes import health_bp
from views.main_routes import main_bp
from views.order_routes import order_bp
from views.product_routes import product_bp
from views.report_routes import report_bp
from views.user_routes import user_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG
    CORS(app)

    init_db()

    app.register_blueprint(main_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(admin_bp)

    register_error_handlers(app)

    return app


if __name__ == "__main__":
    app = create_app()
    print("=" * 50)
    print("SERVIDOR INICIADO")
    print(f"Rodando em http://localhost:{PORT}")
    print("=" * 50)
    app.run(host=HOST, port=PORT, debug=DEBUG)
