================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:     Flask 3.1.1 (pinned in requirements.txt as flask==3.1.1, imported and instantiated in src/app.py)
Dependencies:  flask-cors==5.0.1 (CORS applied globally in app.py), werkzeug==3.1.8 (password hashing via generate_password_hash in database/connection.py), python-dotenv==1.2.2 (env loading in config/settings.py); sqlite3 (Python stdlib, no ORM)
Domain:        E-commerce API (produtos/products, usuarios/users + login, pedidos/orders with itens_pedido/order line items, relatorios de vendas/sales reports, plus /admin/* maintenance endpoints)
Architecture:  Already restructured into a layered MVC shape — src/views/ (7 route blueprint files, routing + request/response shaping only, no SQL), src/controllers/ (7 files, business logic and validation), src/models/ (4 files, DB access), plus dedicated src/services/ (notification_service), src/middlewares/ (auth, error_handler), src/database/ (connection.py, single DatabaseConnection class), and src/config/ (settings.py, centralized env reads). Spot-checked src/views/*.py for SQL/cursor leakage — none found; DB access (get_db/sqlite3) is confined to src/controllers/admin_controller.py and src/controllers/health_controller.py plus the models layer. app.py is a clean composition root (Flask app + CORS + blueprint registration only, no embedded route handlers). No flat-monolith or god-class smell remains at this structural level.
Source files:  31 .py files analyzed under src/ (verified via `find src -name '*.py' | wc -l`) — breakdown: controllers/ 7, views/ 8 (incl. __init__.py), models/ 4, middlewares/ 3, services/ 2, database/ 2, config/ 2, plus src/app.py and src/errors.py and src/__init__.py at the src root.
DB tables:     produtos, usuarios, pedidos, itens_pedido (all defined via CREATE TABLE IF NOT EXISTS in src/database/connection.py, sqlite3 backend, no ORM)
================================
