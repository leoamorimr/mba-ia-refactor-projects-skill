"""Composition root: the only file that imports config, constructs the
database connection, builds every repository/service/controller and wires
them together via constructor injection, registers all blueprints, and
starts the server. It contains wiring only - no business logic, no SQL, no
route handlers.

Every repository takes the same `DatabaseConnection` instance in its
constructor, every controller takes its repositories (and, for
`OrderController`, the `NotificationService`) in its constructor, and
every blueprint factory takes its controller in its constructor - nothing
below reaches for a module-level singleton to find its dependencies.
"""
from flask import Flask
from flask_cors import CORS

from config.settings import CORS_ORIGINS, DB_PATH, DEBUG, HOST, PORT, SECRET_KEY
from controllers.admin_controller import AdminController
from controllers.health_controller import HealthController
from controllers.order_controller import OrderController
from controllers.product_controller import ProductController
from controllers.report_controller import ReportController
from controllers.user_controller import UserController
from database.connection import DatabaseConnection
from middlewares.error_handler import register_error_handlers
from models.order_model import OrderRepository
from models.product_model import ProductRepository
from models.user_model import UserRepository
from services.notification_service import NotificationService
from views.admin_routes import create_admin_blueprint
from views.health_routes import create_health_blueprint
from views.main_routes import main_bp
from views.order_routes import create_order_blueprint
from views.product_routes import create_product_blueprint
from views.report_routes import create_report_blueprint
from views.user_routes import create_user_blueprint


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG
    # Scoped to explicit origins (config.settings.CORS_ORIGINS) instead of
    # the previous default-open CORS(app), which allowed any origin to hit
    # every route including the mutating /produtos, /pedidos and /usuarios
    # endpoints.
    CORS(app, origins=CORS_ORIGINS)

    # Single DatabaseConnection for the whole process, constructed here and
    # threaded into every repository below - nothing imports a module-level
    # singleton to get one.
    db_connection = DatabaseConnection(DB_PATH)
    db_connection.get_connection()  # creates schema + seeds data on first boot

    product_repository = ProductRepository(db_connection)
    user_repository = UserRepository(db_connection)
    order_repository = OrderRepository(db_connection)

    notification_service = NotificationService()

    product_controller = ProductController(product_repository)
    user_controller = UserController(user_repository)
    order_controller = OrderController(
        order_repository, product_repository, user_repository, notification_service
    )
    report_controller = ReportController(order_repository)
    health_controller = HealthController(db_connection)
    admin_controller = AdminController(db_connection)

    app.register_blueprint(main_bp)
    app.register_blueprint(create_product_blueprint(product_controller))
    app.register_blueprint(create_user_blueprint(user_controller))
    app.register_blueprint(create_order_blueprint(order_controller))
    app.register_blueprint(create_report_blueprint(report_controller))
    app.register_blueprint(create_health_blueprint(health_controller))
    app.register_blueprint(create_admin_blueprint(admin_controller))

    register_error_handlers(app)

    return app


if __name__ == "__main__":
    app = create_app()
    print("=" * 50)
    print("SERVIDOR INICIADO")
    print(f"Rodando em http://localhost:{PORT}")
    print("=" * 50)
    app.run(host=HOST, port=PORT, debug=DEBUG)
