================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (raw sqlite3, no ORM)
Files:   4 analyzed | ~781 lines of code

## Summary
CRITICAL: 8 | HIGH: 4 | MEDIUM: 10 | LOW: 8

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: app.py:7
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` is a literal secret committed to source, not read from an environment variable or secret manager.
Impact: Anyone with source access (or a leaked repo/backup) gets Flask's session-signing key, enabling session/cookie forgery and CSRF-token bypass.
Recommendation: Load `SECRET_KEY` from an environment variable (e.g. `os.environ["SECRET_KEY"]`) or a secrets manager, with no hardcoded fallback in source.

### [CRITICAL] Unauthenticated Destructive/Admin Endpoint
File: app.py:47-57
Description: `POST /admin/reset-db` (`reset_database`) deletes every row from `itens_pedido`, `pedidos`, `produtos`, and `usuarios` with no authentication/authorization check of any kind before running.
Impact: Any anonymous caller can wipe the entire database in one request.
Recommendation: Remove this endpoint from the public API, or gate it behind an authenticated admin role plus a confirmation mechanism; move the handler out of `app.py` into a properly authorized admin controller.

### [CRITICAL] Unauthenticated Destructive/Admin Endpoint
File: app.py:59-78
Description: `POST /admin/query` (`executar_query`) takes a raw `sql` string straight from the request body (`dados.get("sql", "")`) and executes it verbatim via `cursor.execute(query)`, with no authentication and no restriction on statement type.
Impact: This is a fully open SQL console exposed to the internet — an attacker can read, modify, or drop any table, or exfiltrate the whole database, with a single POST request.
Recommendation: Delete this endpoint entirely; it has no legitimate use in a production API. If ad-hoc admin querying is genuinely needed, expose it only through an authenticated internal tool that never accepts raw SQL from an HTTP client.

### [CRITICAL] Unauthenticated Destructive/Admin Endpoint
File: controllers.py:98-109
Description: `deletar_produto` (backing `DELETE /produtos/<id>`) fetches the product and deletes it via `models.deletar_produto(id)` with no authentication or authorization check — any client can delete any product by id.
Impact: Any anonymous user can permanently delete catalog data.
Recommendation: Add an authentication/authorization layer (e.g. a decorator or middleware requiring an admin session) in front of all mutating endpoints, enforced centrally rather than per-handler.

### [CRITICAL] Hardcoded Credentials / Secrets
File: controllers.py:264-292
Description: `health_check` returns `"secret_key": "minha-chave-super-secreta-123"` (line 289) directly in the JSON response body, along with `"debug": True` and the internal `"db_path": "loja.db"`.
Impact: Any unauthenticated caller hitting `/health` receives the Flask secret key and internal configuration details in plaintext, handing an attacker everything needed to forge signed sessions.
Recommendation: Strip all secrets and internal configuration from health-check responses; return only a boolean/status and, if desired, non-sensitive counts.

### [CRITICAL] God Class / God File
File: models.py:1-314
Description: A single file mixes raw SQL string-building, response-shaping (hand-built dicts) for four unrelated domains (`produtos`, `usuarios`, `pedidos`, `itens_pedido`), and business logic (stock checks, order-total calculation, sales-discount tiers) with no separation between data access and domain rules.
Impact: Nothing in this file can be unit-tested without a live SQLite connection; a change to order logic risks breaking product or user queries, and vice versa.
Recommendation: Split into one repository/module per entity (`produtos_repository.py`, `usuarios_repository.py`, `pedidos_repository.py`) plus a separate service layer for cross-entity business rules (stock/pricing/discounts), following the MVC/repository pattern.

### [CRITICAL] SQL Injection via String Concatenation
File: models.py:28-299
Description: Nearly every query in this file is built by string concatenation of request-derived values instead of parameterized placeholders, e.g. `"SELECT * FROM produtos WHERE id = " + str(id)` (line 28), the `INSERT INTO produtos` built from raw `nome`/`descricao`/`categoria` strings (lines 47-50), `atualizar_produto`'s `UPDATE` (lines 57-61), `deletar_produto` (line 68), `get_usuario_por_id` (line 92), `login_usuario`'s `email`/`senha` splice (lines 109-111), `criar_usuario`'s `INSERT` (lines 126-129), every query inside `criar_pedido` (lines 140, 148-151, 155, 158-161, 163-166), `get_pedidos_usuario` (lines 174, 188, 192), `get_todos_pedidos` (lines 220, 224), `atualizar_status_pedido` (lines 279-281), and the dynamic filter-building in `buscar_produtos` (lines 291, 293, 295, 297, executed at 299).
Impact: Any of these values reachable from `request.args`/`request.get_json()` (product name/description/category, email/password, search term, status) lets an attacker read, modify, or delete arbitrary data — including authenticating as any user or bypassing the login check entirely via a crafted `senha`/`email`.
Recommendation: Replace every string-built query with parameterized `?` placeholders (`cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))`) throughout the file; never interpolate request-derived values into SQL text.

### [CRITICAL] Weak or Homegrown Password Encryption (Plaintext Storage)
File: models.py:105-131
Description: `login_usuario` (105-120) compares the submitted password directly against the stored value inside the SQL `WHERE` clause, and `criar_usuario` (122-131) inserts the password exactly as received — there is no hashing at all, not even a weak one; passwords are stored and compared in plaintext (confirmed by the seed data in database.py:76-79, e.g. `"admin123"`).
Impact: A database leak (or the SQL-injection/admin-query holes above) instantly exposes every user's real password in cleartext; because people reuse passwords, this compromises accounts on other services too.
Recommendation: Hash passwords on write with a proper algorithm (`werkzeug.security.generate_password_hash` / `bcrypt`), and verify on login with the matching `check_password_hash`/`checkpw` — never compare or store raw passwords, and never use the password as part of a SQL predicate.

### [HIGH] Fat Controller / Business Logic in the Route Layer
File: controllers.py:188-220
Description: `criar_pedido` embeds notification/side-effect business process logic directly in the HTTP handler (`print("ENVIANDO EMAIL: ...")`, `print("ENVIANDO SMS: ...")`, `print("ENVIANDO PUSH: ...")`, lines 208-210) instead of delegating to a notification service.
Impact: Notification behavior can't be tested, swapped, or reused independently of the HTTP layer, and every future order-related endpoint will be tempted to re-implement the same "print and hope" side effects.
Recommendation: Extract a `NotificationService` (or event/queue publisher) called from a service layer after order creation; the controller should only translate the service's result into an HTTP response.

### [HIGH] Fat Controller / Business Logic in the Route Layer
File: controllers.py:237-255
Description: `atualizar_status_pedido` embeds status-transition business rules and side effects directly in the controller — deciding to log "prepare shipment" on `aprovado` and "return stock" on `cancelado` (lines 247-250) — without actually performing the stock-return logic, just printing about it.
Impact: Business rules for order-status transitions live in the HTTP layer, can't be unit tested without Flask, and the "cancelado" path claims to restock inventory but never actually does it (silently incorrect behavior).
Recommendation: Move status-transition rules (including the real stock-restoration logic on cancellation) into a service/model method; have the controller only call it and shape the response.

### [HIGH] Mutable Global State
File: database.py:4-11
Description: `db_connection` is a module-level variable (line 4) that `get_db()` reads and lazily reassigns via `global db_connection` (lines 8-11); every request handler across the app shares this one mutable global connection object.
Impact: Concurrent requests share one SQLite connection with unpredictable interleaving of cursors/transactions, and no code path can substitute a different connection (e.g. a test database) without monkeypatching the module.
Recommendation: Wrap connection creation in a factory/class that is constructed once at app startup and passed (or attached to Flask's `app.config`/`g` object) into controllers/models via dependency injection, instead of a bare module global.

### [HIGH] Tight Coupling / No Dependency Injection
File: models.py:1-314
Description: Every single function in this file calls `db = get_db()` (e.g. lines 5-6, 25-26, 44-45, 55-56, 66-67, 73-74, 90-91, 106-107, 123-124, 134-135, 172-173, 204-205, 236-237, 276-277, 286-287) to reach directly for the global singleton connection defined in `database.py`, rather than receiving a connection/repository as a parameter or constructor argument.
Impact: No model function can be unit-tested with a fake/in-memory connection without patching the global; every function is silently coupled to exactly one concrete SQLite singleton.
Recommendation: Introduce a repository class that receives its connection via `__init__` (constructor injection), and have controllers depend on the repository interface rather than importing `database.get_db` transitively through `models`.

### [MEDIUM] Deprecated API Usage (Flask Debug Mode in Production Entry Point)
File: app.py:8,88
Description: `app.config["DEBUG"] = True` (line 8) and `app.run(host="0.0.0.0", port=5000, debug=True)` (line 88) leave Werkzeug's interactive debugger enabled on what is the application's only entry point.
Impact: If this ever runs reachable from an untrusted network, the Werkzeug debugger allows arbitrary remote code execution via its console; it also leaks stack traces with source snippets to clients.
Recommendation: Default `debug` to `False` and gate it on an explicit environment variable (e.g. `FLASK_DEBUG`); run production via a WSGI server (gunicorn/uwsgi) rather than the Flask dev server.

### [MEDIUM] No Structured Logging / No Centralized Error Handling
File: controllers.py:1-292
Description: Every handler wraps its body in its own `try/except Exception as e` that duplicates the same "print and return 500" logic (e.g. lines 6-12, 10-22, 60-62, 108-109, 254-255), and diagnostics are emitted via bare `print(...)` calls (e.g. lines 8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250) instead of a logging framework.
Impact: Errors aren't queryable, leveled, or aggregable in production (stdout `print` is the only trace), and the ~19 duplicated try/except blocks are copy-paste debt that will drift as handlers evolve.
Recommendation: Register a single Flask `errorhandler` for uncaught exceptions that logs via the `logging` module and returns a consistent error envelope; remove the per-handler try/except boilerplate.

### [MEDIUM] Missing Input Validation at the Route Boundary
File: controllers.py:64-96
Description: `atualizar_produto` validates presence of `nome`/`preco`/`estoque` and that `preco`/`estoque` aren't negative, but — unlike `criar_produto` — never checks `len(nome)` bounds or that `categoria` is one of the valid values, so a PUT can silently set an out-of-range name or an invalid category that POST would have rejected.
Impact: Data written via update bypasses rules enforced on create, producing inconsistent, un-queryable category values and empty/oversized names.
Recommendation: Extract the validation rules (name length, category whitelist, non-negative numbers) into one shared validator/schema used by both `criar_produto` and `atualizar_produto`.

### [MEDIUM] Missing Input Validation at the Route Boundary
File: controllers.py:146-165
Description: `criar_usuario` only checks that `nome`, `email`, and `senha` are truthy (line 157) — there is no email-format check and no minimum length/strength requirement on the password.
Impact: Malformed emails and trivially weak passwords (e.g. a single character) are accepted and stored as-is.
Recommendation: Validate email format (regex or a library) and enforce a minimum password length/complexity before calling `models.criar_usuario`.

### [MEDIUM] Missing Input Validation at the Route Boundary
File: controllers.py:188-220
Description: `criar_pedido` checks only that `itens` is a non-empty list (lines 200-201); it never validates that each item has a valid `produto_id` type or that `quantidade` is a positive number before passing the list to `models.criar_pedido`.
Impact: A negative `quantidade` passes the model's `estoque < quantidade` check (a negative is always "enough stock") and then `UPDATE produtos SET estoque = estoque - (negative)` actually *increases* stock — a genuine data-corruption bug enabled purely by missing validation.
Recommendation: Validate each item's shape (`produto_id` is an int, `quantidade` is a positive integer) at the route boundary before it ever reaches the model layer.

### [MEDIUM] Missing Pagination on List Endpoints
File: models.py:4-22,72-87,203-233,285-314
Description: `get_todos_produtos` (4-22), `get_todos_usuarios` (72-87), `get_todos_pedidos` (203-233), and `buscar_produtos` (285-314) all run `SELECT *` (with filters, in the last case) and return every matching row with no `LIMIT`/`OFFSET`/page parameter.
Impact: Response size and query cost for `/produtos`, `/produtos/busca`, `/usuarios`, and `/pedidos` grow unbounded as the tables grow — invisible with 10 seed rows, painful at production scale.
Recommendation: Add `limit`/`offset` (or cursor-based) pagination parameters to each of these queries and thread them through the corresponding controller functions.

### [MEDIUM] Deletes That Break Referential Integrity
File: models.py:65-70
Description: `deletar_produto` runs `DELETE FROM produtos WHERE id = ...` with no corresponding cleanup or reassignment of `itens_pedido` rows that reference the deleted product by `produto_id`.
Impact: Existing orders end up pointing at a non-existent product; `get_pedidos_usuario`/`get_todos_pedidos` already have to defensively handle this via `"Desconhecido"` (lines 196/228), which is a symptom of the orphaned-row problem rather than a fix for it.
Recommendation: Either soft-delete products (`ativo = 0`, which the schema already supports) instead of hard-deleting, or explicitly handle/forbid deletion of products still referenced by existing order items.

### [MEDIUM] N+1 Queries
File: models.py:133-169
Description: `criar_pedido` loops over `itens` and runs a separate `SELECT` per item to validate stock (line 140), then loops again and runs another `SELECT` per item to re-fetch the price (line 155) plus an `INSERT` (158-161) and `UPDATE` (163-166) per item — all individually round-tripped instead of batched.
Impact: Order creation time grows linearly with the number of line items, with 3-4x the necessary round trips per item.
Recommendation: Fetch all needed products in one query using `WHERE id IN (...)`, validate stock in memory, then use `executemany` for the item inserts and a single batched stock-decrement update.

### [MEDIUM] N+1 Queries
File: models.py:171-201
Description: `get_pedidos_usuario` fetches all orders for a user (line 174), then for each order runs a separate query for its items (line 188) and, for each item, another separate query for the product name (line 192).
Impact: Response time for a single user's order history grows as O(orders × items) round trips instead of a small constant number of queries.
Recommendation: Replace the nested per-row queries with a single `JOIN` across `pedidos`, `itens_pedido`, and `produtos`, grouping the results in application code.

### [MEDIUM] N+1 Queries
File: models.py:203-233
Description: `get_todos_pedidos` has the identical nested-query structure as `get_pedidos_usuario` — one query for all orders (line 206), then a per-order query for items (line 220) and a per-item query for the product name (line 224).
Impact: Same linear round-trip growth as above, but on the full unfiltered order list, making it the worst offender as data grows.
Recommendation: Same fix as `get_pedidos_usuario` — a single `JOIN` query instead of nested loops; consider factoring the shared logic into one parametrized function (see Duplicated Code finding below).

### [LOW] Overly Broad Exception Handling
File: controllers.py:10-12
Description: Nearly every handler (this is the first instance, in `listar_produtos`) catches the generic `Exception` class and returns a bare 500 with `str(e)`, indiscriminately swallowing programming errors (`TypeError`, `KeyError`) the same way it handles expected failures.
Impact: Bugs (e.g. a typo'd dict key) surface identically to legitimate runtime errors, masking real defects behind a generic "something went wrong" response and making them harder to detect in monitoring.
Recommendation: Catch specific, expected exception types where recoverable, and let unexpected exceptions propagate to one centralized error handler (see the related MEDIUM finding) that logs the full traceback.

### [LOW] Duplicated Code
File: controllers.py:24-96
Description: `criar_produto` (24-62) and `atualizar_produto` (64-96) share near-identical field-extraction and `preco`/`estoque` negative-value validation logic, differing only in a couple of extra checks and the final model call.
Impact: Any future rule change (e.g. a new required field) must be remembered and applied in two places, and the two have already drifted (see the Missing Input Validation finding above).
Recommendation: Extract the shared field-extraction and validation into one helper function parametrized by mode (create vs. update).

### [LOW] Magic Numbers
File: controllers.py:47-50
Description: The product name length bounds `2` and `200` (`len(nome) < 2`, `len(nome) > 200`) are unexplained literals with no named constant.
Impact: A future reader can't tell whether `2`/`200` are arbitrary or load-bearing business rules, and changing them means hunting for the literal.
Recommendation: Extract `PRODUCT_NAME_MIN_LENGTH = 2` and `PRODUCT_NAME_MAX_LENGTH = 200` constants (or a validation schema) referenced by name.

### [LOW] Dead Code / Unused Imports
File: database.py:2
Description: `import os` is never used anywhere in the file — no `os.*` call appears (the database path is a plain string literal).
Impact: Minor noise; a reader may assume the module reads the DB path from an environment variable via `os`, which it does not.
Recommendation: Remove the unused import (or, better, actually use `os.environ` to make the DB path configurable).

### [LOW] Dead Code / Unused Imports
File: models.py:2
Description: `import sqlite3` is never referenced in the file — all database access goes through the `db`/`cursor` objects returned by `database.get_db()`, never through the `sqlite3` module directly.
Impact: Minor noise/confusion about the module's actual dependencies.
Recommendation: Remove the unused import.

### [LOW] Duplicated Code
File: models.py:171-233
Description: `get_pedidos_usuario` (171-201) and `get_todos_pedidos` (203-233) have virtually identical bodies — same nested-loop shape building the same `pedido`/`itens` dict structure — differing only in the presence of a `WHERE usuario_id = ...` filter.
Impact: The N+1 fix and any future change to the order-shaping logic must be applied twice, and the two have already been kept in sync only by luck.
Recommendation: Parametrize one function with an optional `usuario_id` filter (or, once JOIN-based, one query with an optional WHERE clause) instead of maintaining two near-identical copies.

### [LOW] Poor Naming
File: models.py:187-199,219-231
Description: Sequentially-numbered cursor variables `cursor2` and `cursor3` (declared at 187/219 and 191/223 respectively) carry no semantic meaning about what they query.
Impact: Readers must trace each cursor back to its `execute()` call to understand what it represents, slowing down comprehension of already-nested logic.
Recommendation: Name cursors for what they fetch (e.g. `itens_cursor`, `produto_nome_cursor`), or eliminate them entirely once the N+1 queries are replaced by a single JOIN.

### [LOW] Magic Numbers
File: models.py:256-262
Description: The sales-report discount tiers — thresholds `10000`, `5000`, `1000` and rates `0.1`, `0.05`, `0.02` — are unexplained literals with no named constants.
Impact: The discount business rule can't be located, referenced, or changed without reading and re-deriving this exact block; a rate change risks a typo going unnoticed.
Recommendation: Extract named constants (e.g. `TIER1_THRESHOLD = 10000`, `TIER1_RATE = 0.10`) or a small lookup table of `(threshold, rate)` pairs.

================================
Total: 30 findings
================================
