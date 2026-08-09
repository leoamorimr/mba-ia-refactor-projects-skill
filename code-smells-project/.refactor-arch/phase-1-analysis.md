================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:     Flask 3.1.1 (pinned in requirements.txt, imported in app.py)
Dependencies:  flask-cors==5.0.1 (CORS applied globally in app.py); sqlite3 (Python stdlib, no ORM)
Domain:        E-commerce API (produtos/products, usuarios/users, pedidos/orders with itens_pedido/order items, login, relatorio de vendas/sales report)
Architecture:  Flat monolith — all logic lives in 4 root-level files (app.py, controllers.py, models.py, database.py) with no subfolders for models/routes/controllers/services; app.py itself also embeds two raw route handlers directly (reset-db, arbitrary SQL execution) alongside its url_rule registrations
Source files:  4 files analyzed (app.py, controllers.py, database.py, models.py — verified via `find . -maxdepth 3 -name '*.py'`)
DB tables:     produtos, usuarios, pedidos, itens_pedido (all defined via CREATE TABLE IF NOT EXISTS in database.py)
================================
