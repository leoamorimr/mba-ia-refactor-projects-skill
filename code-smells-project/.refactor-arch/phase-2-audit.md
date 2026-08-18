================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (raw sqlite3, no ORM)
Files:   31 analyzed | ~1228 lines of code

## Summary
CRITICAL: 3 | HIGH: 3 | MEDIUM: 5 | LOW: 2

## Findings

### [CRITICAL] SQL Injection / Arbitrary SQL Execution (Admin Query Endpoint)
File: src/controllers/admin_controller.py:27-35
Description: `execute_query(sql)` takes the `sql` string passed straight through from the `/admin/query` request body (`src/views/admin_routes.py:24`, `dados.get("sql", "")`) and hands it verbatim to `cursor.execute(sql)` with no parameterization, statement whitelist, or read-only restriction. Any syntactically valid SQL — `DROP TABLE`, `UPDATE usuarios SET tipo='admin'`, `SELECT senha FROM usuarios`, etc. — runs exactly as submitted.
Impact: The endpoint is gated by `require_admin` (`src/middlewares/auth.py`), so this is no longer a fully open door, but it remains a full, unrestricted SQL console: possession of the single shared `ADMIN_TOKEN` (or a token leak/log exposure) grants complete read/write/delete access to every table, including dumping every user's password hash or arbitrarily rewriting data, with no audit trail beyond a single `logger.warning` on the reset endpoint (not on this one).
Recommendation: Remove raw-SQL execution from the API surface entirely. If ad-hoc admin querying is genuinely needed, replace it with a small set of named, parameterized read-only operations (e.g. `SELECT` against an explicit allow-list of tables/columns) exposed only to an internal tool, never as "run this string as SQL" over HTTP.

### [CRITICAL] Hardcoded Credentials / Secrets Exposure (Password Hash Returned in API Response)
File: src/models/user_model.py:8-16
Description: `_row_to_dict` includes the raw `senha` column (the password hash) in every dict it returns. `user_controller.list_users`/`get_user` pass this dict through unfiltered, and `src/views/user_routes.py:11-24` (`GET /usuarios` and `GET /usuarios/<id>`) serialize it straight into the JSON response with no authentication on either route.
Impact: Any anonymous caller can retrieve every user's password hash via `GET /usuarios`. Although the hash is salted (`werkzeug.security.generate_password_hash`), exposing it at all hands attackers an offline dictionary/brute-force target for every account in the system, including the seeded `admin@loja.com` account.
Recommendation: Give `user_model` a separate public-facing shaping function (or a `to_public_dict`) that omits `senha`, and use it in every response path except the internal `authenticate()` lookup in `user_controller.py` that needs the hash to call `check_password_hash`.

### [CRITICAL] Unauthenticated Destructive/Admin Endpoint (DELETE /produtos/<id>)
File: src/views/product_routes.py:101-107
Description: `deletar_produto` (backing `DELETE /produtos/<id>`) calls `product_controller.delete_product(id)` with no authentication or authorization decorator of any kind — unlike `/admin/*`, which is correctly gated by `require_admin`, this catalog-mutating route is reachable by anyone.
Impact: Any anonymous client can deactivate (remove from all listings) any product in the catalog, a direct write/destroy capability with zero access control, mirroring the exact "DELETE with no auth check" pattern the admin routes were already fixed for.
Recommendation: Apply the same `require_admin` (or a proper role-based) guard used on `/admin/*` to this route, and audit `POST /produtos` / `PUT /produtos/<id>` for the same gap — a public storefront API should not let arbitrary clients mutate the product catalog.

### [HIGH] Tight Coupling / No Dependency Injection (NotificationService)
File: src/controllers/order_controller.py:6-9
Description: `order_controller` imports the concrete `NotificationService` class and instantiates it directly at module import time (`notification_service = NotificationService()`), rather than receiving it as a constructor/function argument.
Impact: Nothing can substitute a test double or an alternate notification backend without monkeypatching the module-level singleton; every consumer of `order_controller` is silently and permanently coupled to this one concrete implementation.
Recommendation: Pass a `notification_service` instance into the functions that need it (or build it once in `app.py`'s composition root and thread it through), so `order_controller` depends on an injected collaborator instead of constructing its own.

### [HIGH] Mutable Global State (Database Connection Singleton)
File: src/database/connection.py:118-126
Description: `_db_instance = DatabaseConnection(DB_PATH)` is a module-level object whose internal `_connection` is lazily mutated on first use, and every model file (`order_model.py`, `product_model.py`, `user_model.py`) plus two controllers reach it directly through the module-level `get_db()` function.
Impact: This is a real improvement over a bare global (the state is at least encapsulated in a class, as the module's own docstring notes), but it is still one shared, implicitly-constructed connection that every unrelated handler reads through without any way to substitute a different connection (e.g. an in-memory test DB) except by monkeypatching `database.connection._db_instance`.
Recommendation: Construct the `DatabaseConnection` once in the composition root (`app.py`) and pass it (or a request-scoped connection from Flask's `g`) into models/controllers via dependency injection, rather than importing a module-level singleton getter from every data-access function.

### [MEDIUM] Overly Permissive CORS Configuration
File: src/app.py:24
Description: `CORS(app)` is applied with default settings, which enables cross-origin requests from any origin to every route in the application, including the mutating `/produtos`, `/pedidos`, and `/usuarios` endpoints.
Impact: Any website can issue cross-origin requests against this API from a victim's browser; combined with the unauthenticated `DELETE /produtos/<id>` finding above, a malicious page could trigger destructive calls on a visitor's behalf.
Recommendation: Scope CORS to the specific origins that legitimately need it (`CORS(app, origins=[...])`) instead of the wide-open default, especially once any session/cookie-based auth is added.

### [MEDIUM] Overly Broad Exception Handling / Duplicated Error-Handling Logic
File: src/views/admin_routes.py:29-33
Description: `executar_query` wraps its call in its own `try/except Exception as e: return jsonify({"erro": str(e)}), 500`, reintroducing exactly the per-handler "log and return 500" pattern that `middlewares/error_handler.py`'s centralized `@app.errorhandler(Exception)` was built to eliminate elsewhere in the codebase.
Impact: This is the one route in the app that bypasses the shared error-handling strategy, and it also leaks raw SQLite error text (`str(e)`, e.g. table/column names in a syntax error) straight to the client instead of the generic message the rest of the app returns.
Recommendation: Let exceptions from `admin_controller.execute_query` propagate to the centralized handler in `middlewares/error_handler.py` like every other controller does, adding a dedicated typed exception (e.g. `QueryExecutionError`) if a distinct 400 response is wanted for malformed SQL.

### [MEDIUM] Missing Input Validation at the Route Boundary (Non-Numeric Price/Stock)
File: src/controllers/product_controller.py:17-20
Description: `_validate_product_fields` compares `preco < 0` and `estoque < 0` without first checking that `preco`/`estoque` are numeric. A non-numeric JSON value (e.g. `"preco": "abc"`) raises an uncaught `TypeError` when compared to `0` in Python 3, which is caught only by the generic 500 handler instead of returning a clean 400.
Impact: Malformed input produces an opaque "Erro interno no servidor" response instead of a clear validation error, and the type error is indistinguishable from a real bug in monitoring.
Recommendation: Validate `isinstance(preco, (int, float))` and `isinstance(estoque, int)` (rejecting bools, as `validate_items` already does for order items) before the numeric comparisons, returning the existing validation-error message on failure.

### [MEDIUM] Missing Input Validation at the Route Boundary (Order usuario_id Not Verified)
File: src/controllers/order_controller.py:30-44
Description: `create_order` uses the client-supplied `usuario_id` to insert a new `pedidos` row (line 44) without ever checking that a user with that id exists in `usuarios`.
Impact: A client can create orders attributed to any arbitrary (including nonexistent) user id; `GET /pedidos/usuario/<id>` and sales reports will silently include orders with no real owner, and there is no referential check preventing orphaned `usuario_id` values.
Recommendation: Look up the user via `user_model.get_by_id(usuario_id)` at the top of `create_order` and return a validation error (e.g. `"Usuário não encontrado"`) if it doesn't exist, before creating the order.

### [MEDIUM] Missing Input Validation at the Route Boundary (Duplicate Email Not Checked)
File: src/controllers/user_controller.py:23-36
Description: Neither `validate_new_user` nor `create_user` checks whether `email` already exists via `user_model.get_by_email` before inserting, and the `usuarios` table itself has no `UNIQUE` constraint on `email` (`src/database/connection.py:66-74`).
Impact: Multiple accounts can be created with the same email address, which breaks the implicit one-account-per-email assumption `authenticate()`/`get_by_email` relies on (it will silently match whichever row `SELECT ... WHERE email = ?` returns first).
Recommendation: Call `user_model.get_by_email(email)` in `validate_new_user` and return a validation error when a row already exists, and add a `UNIQUE` constraint on `usuarios.email` at the schema level as a second line of defense.

### [LOW] Predictable/Insecure Token Comparison (Non-Constant-Time Admin Token Check)
File: src/middlewares/auth.py:22
Description: `require_admin` compares the submitted header value to `ADMIN_TOKEN` with a plain `!=` string comparison, which short-circuits on the first differing byte and is not constant-time.
Impact: In principle this opens a timing side-channel that could help an attacker narrow down the admin token character-by-character; the practical exploitability is low over a real network but the fix is essentially free.
Recommendation: Compare with `hmac.compare_digest(token or "", ADMIN_TOKEN)` instead of `!=`.

### [LOW] Duplicated Code (Product Create/Update Field Extraction)
File: src/views/product_routes.py:49-98
Description: `criar_produto` (49-70) and `atualizar_produto` (73-98) both repeat the identical block that checks for `"nome"`/`"preco"`/`"estoque"` presence in the JSON body and extracts `nome`/`descricao`/`preco`/`estoque`/`categoria` with the same defaults.
Impact: Any future change to required fields or defaults must be made in two places and can drift, exactly the kind of duplication the controller layer already avoided by sharing `_validate_product_fields`.
Recommendation: Extract a shared `_parse_product_payload(dados)` helper (returning the required-field error or the parsed tuple) used by both route handlers.

================================
Total: 13 findings
================================
