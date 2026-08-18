# Refactoring Playbook (Phase 3)

Concrete before/after transformations, one per anti-pattern family from `anti-pattern-catalog.md`. Apply the pattern that matches each finding; adapt the exact syntax to the project's language, but keep the shape of the transformation the same. After applying these, re-read `architecture-guidelines.md` to confirm the result still respects layer boundaries.

## 1. Extract hardcoded secrets into config

**Before (Python):**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
```

**After:**
```python
# config/settings.py
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# app.py
from config.settings import SECRET_KEY, DEBUG
app.config["SECRET_KEY"] = SECRET_KEY
app.config["DEBUG"] = DEBUG
```

**Before (Node):**
```javascript
const config = {
    dbPass: "senha_super_secreta_prod_123",
    paymentGatewayKey: "pk_live_1234567890abcdef",
};
```

**After:**
```javascript
// config/index.js
require('dotenv').config();
module.exports = {
    dbPass: process.env.DB_PASS,
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
};
```
Never echo any config value back in an API response (e.g. a `/health` endpoint) — drop that field entirely.

## 2. Parameterize SQL / stop concatenating strings

**Before:**
```python
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
cursor.execute(
    "INSERT INTO produtos (nome, preco) VALUES ('" + nome + "', " + str(preco) + ")"
)
```

**After:**
```python
cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
cursor.execute(
    "INSERT INTO produtos (nome, preco) VALUES (?, ?)", (nome, preco)
)
```

**Before (Node, string template into a driver call):**
```javascript
db.run("DELETE FROM users WHERE id = " + req.params.id);
```

**After:**
```javascript
db.run("DELETE FROM users WHERE id = ?", [req.params.id]);
```
If the project uses an ORM (SQLAlchemy, Sequelize), prefer its query builder (`Model.query.filter_by(id=id)`) over raw parameterized SQL where a model already exists for the table.

## 3. Split a God File into Model + Controller + Routes

**Before:** one `models.py` with SQL, formatting, and validation for four unrelated entities, and one `controllers.py` calling into it — no per-domain boundaries.

**After:**
```python
# models/product_model.py — data access only
def get_by_id(product_id):
    db = get_db()
    row = db.execute("SELECT * FROM produtos WHERE id = ?", (product_id,)).fetchone()
    return dict(row) if row else None

# controllers/product_controller.py — orchestration + business rules
from models import product_model

def get_product(product_id):
    product = product_model.get_by_id(product_id)
    if not product:
        return None, "Product not found"
    return product, None

# views/routes.py — routing + response shaping only
@app.route("/produtos/<int:id>")
def buscar_produto(id):
    product, error = product_controller.get_product(id)
    if error:
        return jsonify({"erro": error}), 404
    return jsonify({"dados": product, "sucesso": True}), 200
```
Do this domain by domain (products, users, orders, ...) rather than one big-bang rewrite of the whole file at once — it keeps each step verifiable.

## 4. Move business logic out of controllers/routes into a model or service

**Before:** a route handler computing an order's total and applying a discount inline.

**After:**
```python
# controllers/order_controller.py
def calculate_discount(revenue):
    if revenue > REVENUE_THRESHOLD_HIGH:
        return revenue * DISCOUNT_RATE_HIGH
    if revenue > REVENUE_THRESHOLD_MID:
        return revenue * DISCOUNT_RATE_MID
    return 0

# views/routes.py
@app.route("/relatorios/vendas")
def relatorio_vendas():
    report = order_controller.build_sales_report()
    return jsonify({"dados": report, "sucesso": True}), 200
```
The route now has zero business logic — it delegates and shapes the response.

## 5. Replace weak/custom password hashing with a standard library

**Before:**
```python
import hashlib
self.password = hashlib.md5(pwd.encode()).hexdigest()
```

**After:**
```python
from werkzeug.security import generate_password_hash, check_password_hash
self.password = generate_password_hash(pwd)
# verification:
check_password_hash(self.password, candidate_pwd)
```

**Before (Node, homegrown "crypto"):**
```javascript
function badCrypto(pwd) {
    let hash = "";
    for (let i = 0; i < 10000; i++) hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    return hash.substring(0, 10);
}
```

**After:**
```javascript
const bcrypt = require('bcrypt');
const passwordHash = await bcrypt.hash(pwd, 10);
// verification:
await bcrypt.compare(candidatePwd, passwordHash);
```

## 6. Centralize error handling

**Before:** every controller function wraps itself in `try/except` and repeats the same `jsonify({"erro": str(e)}), 500`.

**After:**
```python
# middlewares/error_handler.py
from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error("Unhandled error: %s", e)
        return jsonify({"erro": "Internal server error"}), 500

# app.py
from middlewares.error_handler import register_error_handlers
register_error_handlers(app)
```
Controllers can now let exceptions propagate for unexpected cases and only catch what they can meaningfully recover from.

**Node equivalent:**
```javascript
// middlewares/errorHandler.js
module.exports = (err, req, res, next) => {
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
};

// app.js — registered last, after all routes
app.use(errorHandler);
```

## 7. Fix N+1 queries

**Before:**
```python
for row in orders:
    items = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (row["id"],)).fetchall()
```

**After (batch fetch, then group in memory):**
```python
order_ids = [row["id"] for row in orders]
placeholders = ",".join("?" * len(order_ids))
all_items = db.execute(
    f"SELECT * FROM itens_pedido WHERE pedido_id IN ({placeholders})", order_ids
).fetchall()
items_by_order = {}
for item in all_items:
    items_by_order.setdefault(item["pedido_id"], []).append(dict(item))
```

**ORM equivalent (SQLAlchemy eager loading):**
```python
tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
# t.user and t.category are now already loaded — no per-row query
```

## 8. Add auth/authorization middleware on every CRITICAL-flagged mutable route

This applies to **any** route the audit marked CRITICAL for missing authentication — `/admin/*` or not. A `DELETE`/`POST`/`PUT`/`PATCH` handler with no auth guard is equally CRITICAL whether it lives under `/admin/` or under a plain resource path like `/produtos/<id>`; gate all of them the same way, not just the admin-prefixed ones.

**Before:**
```python
@app.route("/admin/reset-db", methods=["POST"])
def reset_database():
    ...  # anyone can call this
```

**After:**
```python
# middlewares/auth.py
from functools import wraps
from flask import request, jsonify

def require_admin(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not is_valid_admin_token(token):
            return jsonify({"erro": "Unauthorized"}), 401
        return view_func(*args, **kwargs)
    return wrapper

# app.py
@app.route("/admin/reset-db", methods=["POST"])
@require_admin
def reset_database():
    ...
```

**Same pattern, non-admin destructive route — before:**
```python
@app.route("/produtos/<int:id>", methods=["DELETE"])
def deletar_produto(id):
    ...  # anyone can delete any product, no admin path involved
```

**After:**
```python
@app.route("/produtos/<int:id>", methods=["DELETE"])
@require_admin
def deletar_produto(id):
    ...
```
The route's path, method, and response shape are unchanged — only unauthenticated requests now get a 401 instead of succeeding. That is the fix, not a scope violation.

If the project has no auth system at all yet, this is the minimum viable gate — flag in the audit report that a real auth system (sessions/JWT) is a follow-up beyond this refactor's scope, but every CRITICAL-flagged mutable endpoint, admin-prefixed or not, cannot stay wide open.

## 9. Replace a deprecated API with its modern equivalent

**Before:**
```python
created_at = datetime.utcnow()
```

**After:**
```python
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc)
```
Apply this one mechanically everywhere the deprecated call appears — it's a pure substitution, not a design change, so batch it across the whole codebase in one pass rather than one file at a time.

## 10. Replace `print()`/`console.log()` with structured logging

**Before:**
```python
print("ERRO ao criar produto: " + str(e))
```

**After:**
```python
import logging
logger = logging.getLogger(__name__)
logger.error("Failed to create product: %s", e)
```

## 11. Extract magic numbers into named constants

**Before:**
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
elif faturamento > 5000:
    desconto = faturamento * 0.05
```

**After:**
```python
REVENUE_THRESHOLD_HIGH = 10000
REVENUE_THRESHOLD_MID = 5000
DISCOUNT_RATE_HIGH = 0.10
DISCOUNT_RATE_MID = 0.05

if faturamento > REVENUE_THRESHOLD_HIGH:
    desconto = faturamento * DISCOUNT_RATE_HIGH
elif faturamento > REVENUE_THRESHOLD_MID:
    desconto = faturamento * DISCOUNT_RATE_MID
```

## 12. Establish a single composition root

**Before:** the entry point both defines routes inline *and* contains handler logic *and* creates the DB connection lazily on first access from anywhere in the codebase.

**After:**
```python
# app.py — wiring only
from flask import Flask
from config.settings import SECRET_KEY, DEBUG
from database import init_db
from views.routes import register_routes
from middlewares.error_handler import register_error_handlers

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    init_db()
    register_routes(app)
    register_error_handlers(app)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
```
Nothing here computes a discount, validates a payload, or writes to the DB directly — it only assembles the pieces built in steps 1-11.
