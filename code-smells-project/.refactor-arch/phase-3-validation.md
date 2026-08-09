================================
PHASE 3: REFACTORING VALIDATION REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (raw sqlite3, no ORM)

## 1. New directory tree

```
code-smells-project/
├── .env.example              # documents required env vars (no secrets)
├── .gitignore                # ignores .venv/, *.db, .env, __pycache__/
├── README.md                 # updated run instructions + env var table
├── requirements.txt          # flask, flask-cors, werkzeug, python-dotenv (all pinned)
├── reports/
│   └── audit-code-smells-project.md
├── .refactor-arch/
│   ├── phase-1-analysis.md
│   ├── phase-2-audit.md
│   └── phase-3-validation.md (this file)
└── src/
    ├── app.py                    # composition root: wiring only
    ├── errors.py                 # ValidationError / NotFoundError / UnauthorizedError
    ├── config/
    │   └── settings.py           # all env vars read here, nowhere else
    ├── database/
    │   └── connection.py         # DatabaseConnection factory + schema + seed
    ├── models/                   # data access only, one file per entity
    │   ├── product_model.py
    │   ├── user_model.py
    │   └── order_model.py
    ├── controllers/              # orchestration + business rules
    │   ├── product_controller.py
    │   ├── user_controller.py
    │   ├── order_controller.py
    │   ├── report_controller.py
    │   ├── health_controller.py
    │   └── admin_controller.py
    ├── views/                    # routing + response shaping only (Flask Blueprints)
    │   ├── product_routes.py
    │   ├── user_routes.py
    │   ├── order_routes.py
    │   ├── report_routes.py
    │   ├── health_routes.py
    │   ├── main_routes.py
    │   └── admin_routes.py
    ├── middlewares/
    │   ├── auth.py               # require_admin decorator (X-Admin-Token)
    │   └── error_handler.py      # single centralized error handler
    └── services/
        └── notification_service.py   # extracted email/SMS/push side effects
```

The old flat monolith (`app.py`, `controllers.py`, `models.py`, `database.py` at
repo root) was removed entirely and replaced by the tree above. The app now
runs via `python src/app.py` (script directory is added to `sys.path`, so
`config`, `models`, `controllers`, `views`, `middlewares`, `services`,
`database` resolve as top-level packages, exactly as shown in the playbook's
composition-root example).

## 2. Findings fixed (mapped to phase-2-audit.md)

| # | Finding | Fix |
|---|---------|-----|
| 1 | Hardcoded `SECRET_KEY` (app.py:7) | Moved to `config/settings.py`, read from `SECRET_KEY` env var via `python-dotenv`; no hardcoded literal remains — if unset, a random key is generated at boot (fails safe, not a leaked constant). |
| 2 | Open `/admin/reset-db` | Gated behind new `middlewares/auth.require_admin`, checks `X-Admin-Token` header against `ADMIN_TOKEN` env var; fails closed if the env var is unset. |
| 3 | Open `/admin/query` (raw SQL console) | Same `require_admin` gate applied. Endpoint retained (its purpose is ad-hoc admin SQL) but is now unreachable without a valid admin token. |
| 4 | Unauthenticated `DELETE /produtos/<id>` | Left without new auth per explicit task scope (only the two `/admin/*` endpoints were to be gated); SQL injection was fixed and the delete converted to a soft-delete (`ativo=0`) to close the separate referential-integrity finding without changing the route's contract. |
| 5 | Secrets/debug leaked in `/health` | Response no longer includes `secret_key`, `debug`, `db_path`, or `ambiente`; only `status`, `database`, `counts`, `versao` remain. |
| 6 | God File (`models.py`, 314 lines, 4 domains) | Split into `product_model.py`, `user_model.py`, `order_model.py`, each pure data access. |
| 7 | SQL injection via string concatenation (all of models.py) | Every query rewritten to `?` parameterized statements; verified live with a payload containing `'); DROP TABLE produtos;--` in a product name — stored as inert data, table intact (see §4). |
| 8 | Plaintext password storage/comparison | `werkzeug.security.generate_password_hash`/`check_password_hash` used throughout; seed users in `database/connection.py` are hashed at seed time; login verified working against the hashed values with the original plaintext seed passwords (e.g. `admin123`). |
| 9 | Fat controller: print-based "send email/SMS/push" in `criar_pedido` | Extracted to `services/notification_service.NotificationService`, using `logging` instead of `print`. |
| 10 | Fat controller: status-transition logic + fake stock restore in `atualizar_status_pedido` | Moved to `controllers/order_controller.update_order_status`; cancellation now genuinely restores stock (previously only printed about it) — verified live (§4). |
| 11 | Mutable global DB connection | Replaced `global db_connection` pattern with a `DatabaseConnection` class instance in `database/connection.py`, encapsulating connection state; `get_db()`/`init_db()` remain as thin accessors used by the model layer (full constructor-injected repositories were judged out of scope for this pass — see note below). |
| 12 | Tight coupling / no DI in models.py | Each model module now depends only on `database.connection.get_db`, and controllers depend only on their respective model module — no controller reaches for `get_db` directly except `health_controller` and `admin_controller`, which are inherently infrastructure-facing. |
| 13 | Debug mode hardcoded `True` | `DEBUG` now read from `FLASK_DEBUG` env var, defaults to `False`. |
| 14 | No structured logging / duplicated try/except in every controller | Centralized `middlewares/error_handler.register_error_handlers` added (ValidationError→400, NotFoundError→404, UnauthorizedError→401, HTTPException passthrough, generic Exception→500 logged via `logging`). Remaining `print()` calls replaced with `logging` in the notification service and admin controller. |
| 15 | Missing input validation (`atualizar_produto` skipped checks `criar_produto` had) | Both now share `product_controller._validate_product_fields` — verified live: PUT with an invalid category is now rejected (previously would have been accepted). |
| 16 | Missing input validation (`criar_usuario`: no email format/password length check) | Added email regex + `PASSWORD_MIN_LENGTH = 6` in `user_controller.validate_new_user` — verified live. |
| 17 | Missing input validation (negative `quantidade` in `criar_pedido`) | `order_controller.validate_items` rejects non-positive/non-int `quantidade` and non-int `produto_id` before it reaches the model — this is also the fix for finding #21 below. |
| 18 | Missing pagination on list endpoints | `limit`/`offset` optional query params added to `/produtos`, `/produtos/busca`, `/usuarios`, `/pedidos`, `/pedidos/usuario/<id>`; omitted by default so existing callers see identical responses. |
| 19 | Deletes breaking referential integrity | `deletar_produto` now soft-deletes (`ativo = 0`) instead of hard-deleting; all product reads filter `ativo = 1`, so the API-visible behavior (product disappears) is unchanged while order history keeps a valid `produto_id` reference. |
| 20 | N+1 queries in `criar_pedido` | Replaced per-item `SELECT`/`SELECT` with one batched `WHERE id IN (...)` fetch (`product_model.get_by_ids`) plus `executemany` for item inserts and stock decrements. |
| 21 | Negative-quantity stock-corruption bug | Fixed by the same `order_controller.validate_items` guard — verified live: a `quantidade: -5` order is now rejected with 400 and stock is provably unaffected. |
| 22 | N+1 queries in `get_pedidos_usuario` / `get_todos_pedidos` | Both replaced by one parametrized function, `order_model.list_orders(usuario_id=None)`, using a single `LEFT JOIN` across `pedidos`/`itens_pedido`/`produtos` and grouping in memory — also fixes the duplicated-code finding (#27) since both endpoints now call the same function. |
| 23 | Overly broad exception handling | Route handlers no longer wrap every call in `try/except Exception`; expected failures are represented as explicit return values (validation errors) or as typed exceptions caught by the central handler; only `/admin/query`, which executes arbitrary caller-supplied SQL, still catches broadly, since any SQL error there is an expected, reportable outcome. |
| 24 | Duplicated code (`criar_produto`/`atualizar_produto` validation) | Shared via `product_controller._validate_product_fields`. |
| 25 | Magic numbers (name length bounds) | `PRODUCT_NAME_MIN_LENGTH`/`PRODUCT_NAME_MAX_LENGTH` constants in `product_controller.py`. |
| 26 | Dead imports (`database.py: import os`, `models.py: import sqlite3`) | Not carried forward — new modules only import what they use. |
| 27 | Duplicated code (`get_pedidos_usuario`/`get_todos_pedidos`) | See #22. |
| 28 | Poor naming (`cursor2`/`cursor3`) | Eliminated along with the N+1 loops themselves. |
| 29 | Magic numbers (discount tiers) | `REVENUE_THRESHOLD_HIGH/MID/LOW`, `DISCOUNT_RATE_HIGH/MID/LOW` constants in `report_controller.py`. |

**Scope note on finding #4 (`DELETE /produtos/<id>` auth):** the task instructions explicitly limited new auth-gating to the two `/admin/*` endpoints and required the non-admin public API surface (routes, methods, request/response shapes) to stay unchanged. Adding an auth requirement to `DELETE /produtos/<id>` would have violated that constraint, so it was intentionally left as-is beyond the SQL-injection and soft-delete fixes. This is a residual gap the audit flags as CRITICAL and should be revisited once a real auth system exists.

**Scope note on finding #11/#12 (DI):** a full constructor-injected repository layer (passing a connection object into every model function) was judged too large a change for this pass without touching every function signature across the codebase. Instead, the bare module-level global was replaced with an encapsulated `DatabaseConnection` class instance, and the repository-per-entity split (models/*) was completed as specified. The seam for full DI (swapping `_db_instance` for a test double) now exists at one point (`database/connection.py`) instead of being scattered.

## 3. Dependencies

`requirements.txt` updated:
```
flask==3.1.1
flask-cors==5.0.1
werkzeug==3.1.8
python-dotenv==1.2.2
```
`werkzeug` was already a transitive Flask dependency; pinned explicitly since it's now imported directly (`generate_password_hash`/`check_password_hash`) and to know the exact version we use for `check_password_hash` compatibility. `python-dotenv` added for `.env` loading in `config/settings.py`.

Installed into a fresh virtualenv at `code-smells-project/.venv` via:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Install completed with no errors.

## 4. Boot output

Ran `python src/app.py` (port changed to 5050 for this environment — 5000 was
occupied by macOS AirPlay Receiver, unrelated to the refactor):

```
==================================================
SERVIDOR INICIADO
Rodando em http://localhost:5050
==================================================
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5050
```

App booted cleanly, no import/wiring errors. `python -c "app.create_app()"` was
also run beforehand to confirm all 19 URL rules registered (identical set to
the original `app.url_map`, plus Flask's implicit `/static/<path:filename>`):
`/`, `/produtos` (GET+POST), `/produtos/busca`, `/produtos/<int:id>`
(GET+PUT+DELETE), `/usuarios` (GET+POST), `/usuarios/<int:id>`, `/login`,
`/pedidos` (GET+POST), `/pedidos/usuario/<int:usuario_id>`,
`/pedidos/<int:pedido_id>/status`, `/relatorios/vendas`, `/health`,
`/admin/reset-db`, `/admin/query`.

## 5. Endpoint-by-endpoint check results

All requests below were run against the live background server with `curl`.

| Endpoint | Check | Result |
|---|---|---|
| `GET /` | Welcome payload | 200, identical shape to original |
| `GET /health` | No secrets in body | 200, `secret_key`/`debug`/`db_path` absent; counts correct |
| `GET /produtos` | List | 200, 10 seeded products, same shape |
| `GET /produtos/1` | Get by id | 200, same shape |
| `GET /produtos/9999` | Not found | 404, `{"erro":"Produto não encontrado","sucesso":false}` (unchanged) |
| `GET /produtos/busca?q=notebook` | Search by term | 200, 1 result |
| `GET /produtos/busca?categoria=moveis` | Search by category | 200, 1 result |
| `POST /produtos` (valid) | Create | 201, `{"dados":{"id":11},...}` |
| `POST /produtos` (name = `Hack'); DROP TABLE produtos;--`) | SQL injection attempt | 201 — stored as **literal string data**; subsequent `GET /produtos` confirmed the table was intact and the row exists verbatim, proving parameterized queries are in effect |
| `POST /produtos` (missing `preco`) | Required-field check | 400, `"Preço é obrigatório"` (unchanged message) |
| `POST /produtos` (negative `preco`) | Validation | 400, `"Preço não pode ser negativo"` (unchanged) |
| `PUT /produtos/11` (valid) | Update | 200, `"Produto atualizado"` |
| `PUT /produtos/11` (invalid category) | New shared validation | 400, `"Categoria inválida..."` — previously this was **accepted** (audit finding), now correctly rejected |
| `DELETE /produtos/12` | Soft delete | 200, `"Produto deletado"` |
| `GET /produtos/12` after delete | Confirms disappearance | 404, same as a hard delete would produce |
| `GET /usuarios` | List | 200, `senha` field now contains a `scrypt:...` hash, never plaintext |
| `GET /usuarios/1` | Get by id | 200, same shape, hash instead of plaintext |
| `POST /usuarios` (valid) | Create | 201 |
| `POST /usuarios` (password `"123"`) | New validation | 400, `"Senha deve ter ao menos 6 caracteres"` |
| `POST /usuarios` (email `"not-an-email"`) | New validation | 400, `"Email inválido"` |
| `POST /login` (seeded `admin@loja.com`/`admin123`) | Auth against hash | 200, `"Login OK"` — proves seed passwords were hashed at seed time and still authenticate with their original plaintext value |
| `POST /login` (wrong password) | Reject | 401, `"Email ou senha inválidos"` (unchanged) |
| `POST /login` (`' OR '1'='1` injection in email) | SQL injection attempt | 401 — parameterized query correctly treated it as a literal, no bypass |
| `POST /login` (newly created user) | End-to-end hash round-trip | 200, `"Login OK"` |
| `POST /pedidos` (2 items, valid) | Create order | 201; stock for product 1 dropped 10→8 confirming the batched decrement worked |
| `POST /pedidos` (`quantidade: -5`) | Stock-corruption bug fix | 400, `"quantidade deve ser um número inteiro positivo"`; stock confirmed **unchanged** (still 8) — previously this would have *increased* stock |
| `POST /pedidos` (insufficient stock) | Business rule | 400, `"Estoque insuficiente para Cadeira Gamer"` (unchanged) |
| `GET /pedidos` | List all (JOIN, no N+1) | 200, correct nested `itens` with `produto_nome` resolved |
| `GET /pedidos/usuario/2` | List by user (JOIN) | 200, same data filtered by user |
| `PUT /pedidos/1/status` → `aprovado` | Status transition | 200, `"Status atualizado"` |
| `PUT /pedidos/1/status` → `cancelado` | Stock restoration fix | 200; stock for product 1 confirmed back to **10** — previously this only printed a message and never actually restored stock |
| `GET /relatorios/vendas` | Discount-tier report | 200, correct discount/ticket-médio math using named constants |
| `POST /admin/reset-db` (no token) | Auth required | **401** `"Não autorizado"` — previously this was **wide open** to any anonymous caller |
| `POST /admin/query` (no token) | Auth required | **401** — previously a **fully open SQL console** |
| `POST /admin/query` (wrong token) | Auth required | 401 |
| `POST /admin/query` (correct `X-Admin-Token`) | Authorized admin access | 200, `{"dados":[{"total":12}],...}` |
| `POST /admin/reset-db` (correct token) | Authorized admin access | 200, `"Banco de dados resetado"` |
| `GET /does-not-exist` | Unknown route | 404 (Flask default, passed through by the `HTTPException` handler) |
| `DELETE /` | Wrong method | 405 (Flask default, passed through) |
| `POST /produtos` (malformed JSON body) | Robustness | 400, `"Dados inválidos"` (no 500/crash) |

No endpoint returned an unexpected 500. The background server was stopped
(`pkill -f "src/app.py"`) after all checks completed; `loja.db` was removed
from the working tree afterward so no test data persists in the repo.

## 6. Summary

- App boots cleanly from the new `src/` MVC layout with no changes to the
  observable behavior of any non-admin endpoint.
- Both previously-open admin endpoints now correctly require an
  `X-Admin-Token` header matching the `ADMIN_TOKEN` environment variable —
  the intended and expected admin-endpoint change per the task.
- SQL injection, plaintext passwords, hardcoded secret/debug leakage, the
  negative-quantity stock bug, the fake stock-restore-on-cancel, and the N+1
  query patterns were all verified fixed with live requests, not just by
  code inspection.
- Two items are explicitly out of full scope and called out above: auth on
  `DELETE /produtos/<id>` (excluded per task instructions) and full
  constructor-injected DI for the DB connection (partially addressed via a
  `DatabaseConnection` class instead of a bare global).
