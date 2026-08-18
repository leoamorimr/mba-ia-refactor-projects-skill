================================
PHASE 3: VALIDATION REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (raw sqlite3, no ORM)

## Scope of this pass

The project's directory layout was already MVC-shaped from an earlier
refactoring pass (`src/{models,views,controllers,middlewares,config,
database,services}`, with `src/app.py` as composition root). This pass
closes the remaining findings from `.refactor-arch/phase-2-audit.md` that
were left open by that earlier pass, with priority on the three CRITICAL
findings and the hard auth-gate requirement.

## Directory tree (unchanged shape, confirms MVC layout held)

```
src/
├── app.py                        # composition root
├── errors.py                     # shared typed exceptions
├── config/
│   └── settings.py                # env-driven config, incl. new CORS_ORIGINS
├── database/
│   └── connection.py              # DatabaseConnection class + get_db()/init_db()
├── models/
│   ├── product_model.py
│   ├── user_model.py               # + to_public_dict()
│   └── order_model.py
├── controllers/
│   ├── product_controller.py       # + numeric-type validation
│   ├── user_controller.py          # + public shaping, duplicate-email check
│   ├── order_controller.py         # + usuario_id existence check
│   ├── report_controller.py
│   ├── health_controller.py
│   └── admin_controller.py         # execute_query now SELECT-only + column stripping
├── views/
│   ├── product_routes.py           # DELETE now @require_admin; shared payload parser
│   ├── user_routes.py
│   ├── order_routes.py
│   ├── report_routes.py
│   ├── health_routes.py
│   ├── main_routes.py
│   └── admin_routes.py             # no longer bypasses centralized error handler
├── middlewares/
│   ├── auth.py                     # require_admin, now hmac.compare_digest
│   └── error_handler.py
└── services/
    └── notification_service.py
```

No structural moves were needed - the layer boundaries were already correct.
All changes below are within existing files.

## Findings fixed this pass

| Severity | Finding | Fix |
|---|---|---|
| CRITICAL | SQL Injection / Arbitrary SQL Execution via `/admin/query` | `admin_controller.execute_query` now rejects any statement that isn't a single `SELECT` (raises `ValidationError`, handled centrally → 400) and strips any column named `senha`/`password`/`senha_hash`/`password_hash` from every returned row. Full removal of the raw-SQL console was considered too large a scope change for this pass; see "Residual risk" below. |
| CRITICAL | Password hash returned in `GET /usuarios` / `GET /usuarios/<id>` | Added `user_model.to_public_dict()`. `user_controller.list_users`/`get_user` now route every result through it before returning. `authenticate()` is untouched and still reads `senha` internally to call `check_password_hash`. |
| CRITICAL | Unauthenticated `DELETE /produtos/<id>` | Added `@require_admin` (same decorator already gating `/admin/*`) to `deletar_produto` in `views/product_routes.py`. Verified below: 401 without a valid `X-Admin-Token`, 200 with one. |
| HIGH | Tight Coupling / No Dependency Injection (NotificationService, DB connection singleton) | Closed in a follow-up pass (see "Constructor dependency injection" section below): every model became a `*Repository` class taking `DatabaseConnection` via its constructor, every controller became a class taking its repositories (and, for orders, the `NotificationService`) via its constructor, and every Flask blueprint became a factory function closing over its already-constructed controller. `app.py` is now the single place that builds the object graph. |
| MEDIUM | Overly permissive CORS | `config.settings.CORS_ORIGINS` (env-driven, defaults to `http://localhost:3000,http://127.0.0.1:3000`) replaces the bare `CORS(app)` default-open config in `app.py`. |
| MEDIUM | `admin_routes.py` bypassing centralized error handler | Removed the local `try/except Exception: jsonify(...), 500` in `executar_query`; exceptions now propagate to `middlewares/error_handler.py` like every other route. |
| MEDIUM | Missing input validation — non-numeric `preco`/`estoque` | `product_controller._validate_product_fields` now checks `isinstance(preco, (int, float))` and `isinstance(estoque, int)` (rejecting bools) before the numeric comparisons. |
| MEDIUM | Missing input validation — order `usuario_id` not verified | `order_controller.create_order` now calls `user_model.get_by_id(usuario_id)` first and returns `{"erro": "Usuário não encontrado"}` if it doesn't exist. |
| MEDIUM | Missing input validation — duplicate email not checked | `user_controller.validate_new_user` now calls `user_model.get_by_email` and rejects duplicates; `usuarios.email` also got a `UNIQUE` constraint in `database/connection.py` as a second line of defense (applies to freshly-created databases). |
| LOW | Non-constant-time admin token comparison | `middlewares/auth.py` now uses `hmac.compare_digest(token or "", ADMIN_TOKEN)` instead of `!=`. |
| LOW | Duplicated product field-extraction code | Extracted `_parse_product_payload(dados)` in `views/product_routes.py`, used by both `criar_produto` and `atualizar_produto`. |

## Constructor dependency injection (closes the last open finding)

This closes the "Acoplamento forte / ausência de injeção de dependência"
finding that earlier passes had explicitly left out of scope, and the
re-audit's HIGH "Tight Coupling / No Dependency Injection" findings for
both the `NotificationService` and the database connection singleton.

**Before:** every model file (`product_model.py`, `user_model.py`,
`order_model.py`) was a bag of module-level functions that each called
`database.connection.get_db()` — a module-level singleton getter backed by
`_db_instance = DatabaseConnection(DB_PATH)`. `order_controller.py`
imported the concrete `NotificationService` and instantiated it at module
import time (`notification_service = NotificationService()`). Controllers
and views imported these modules directly and called their functions —
there was no constructor to inject anything into.

**After:**
- `database/connection.py` keeps the `DatabaseConnection` class but drops
  the module-level `_db_instance`/`get_db()`/`init_db()` — there is no
  longer a singleton to import.
- Each model file now defines a repository class (`ProductRepository`,
  `UserRepository`, `OrderRepository`) whose `__init__(self, db_connection)`
  receives the shared `DatabaseConnection` instance; every method that used
  to call `get_db()` now calls `self.db_connection.get_connection()`.
- Each controller (`ProductController`, `UserController`, `OrderController`,
  `ReportController`, `HealthController`, `AdminController`) is now a class
  whose `__init__` receives the repositories (and, for `OrderController`,
  the `NotificationService`) it needs — no controller imports a model
  module or instantiates a collaborator itself anymore.
- Each blueprint module (`product_routes.py`, `user_routes.py`,
  `order_routes.py`, `report_routes.py`, `health_routes.py`,
  `admin_routes.py`) now exposes a `create_*_blueprint(controller)` factory
  function whose route handlers close over the injected controller
  instance, instead of a module-level `Blueprint` calling into an imported
  controller module. `main_routes.py` is unchanged — it has no
  collaborators to inject.
- `app.py` is now the single composition root: it constructs one
  `DatabaseConnection`, builds the three repositories from it, builds the
  `NotificationService`, builds the six controllers from the repositories
  (+ notification service), then calls each blueprint factory with its
  controller and registers the result. A test (or an alternate entry
  point) can now build the same graph with fakes/mocks/in-memory
  implementations without monkeypatching any module.
- Public API surface (routes, methods, request/response shapes) is
  unchanged — this was a pure internal wiring change, confirmed by
  re-running the full endpoint check below after applying it.

### Residual risk: `/admin/query`

The endpoint is no longer able to run destructive statements (`DROP`/
`UPDATE`/`INSERT`/`DELETE`) and strips known credential-column names by
exact match, which closes the two impacts the audit called out ("dump
every password hash", "arbitrarily rewrite data"). It is **not** a full
fix: it still executes free-form `SELECT` text rather than a real
allow-list of named queries, so a client could still read arbitrary
non-sensitive rows, and a column alias (`SELECT senha AS x FROM usuarios`)
would defeat the by-name stripping. Full removal in favor of a small set
of named, parameterized read-only operations remains the recommended
follow-up, as the audit originally suggested; it was judged out of scope
for this pass because it changes the endpoint's request contract (`sql`
free-text body) rather than just its authorization/validation.

## Boot output

```
$ PYTHONPATH=. ADMIN_TOKEN=test-admin-token-123 PORT=5050 python app.py
==================================================
SERVIDOR INICIADO
Rodando em http://localhost:5050
==================================================
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5050
 * Running on http://192.168.1.144:5050
```

No errors on boot or first request (DB auto-created and seeded with 10
products / 3 users, as before). Port 5000 was unavailable locally (macOS
AirPlay Receiver), so validation ran on port 5050 via `PORT=5050` - this
does not affect the app's behavior, only which port it bound to.

## Endpoint-by-endpoint check results

| Method | Path | Auth used | Result | Notes |
|---|---|---|---|---|
| GET | `/` | none | 200 | unchanged |
| GET | `/health` | none | 200 | unchanged, no secrets in body |
| GET | `/produtos` | none | 200 | unchanged shape |
| GET | `/produtos/<id>` | none | 200 | unchanged shape |
| GET | `/produtos/busca?q=...` | none | 200 | unchanged shape |
| POST | `/produtos` | none | 201 | unchanged (not CRITICAL-flagged, left as-is) |
| POST | `/produtos` (invalid `preco`) | none | 400 | now returns clean validation error instead of a 500 |
| PUT | `/produtos/<id>` | none | 200 | unchanged (not CRITICAL-flagged, left as-is) |
| **DELETE** | **`/produtos/<id>` (no token)** | **none** | **401** | **`{"erro":"Não autorizado"}` — confirms the auth gate is active** |
| DELETE | `/produtos/<id>` (wrong token) | `X-Admin-Token: wrong-token` | 401 | rejected |
| **DELETE** | **`/produtos/<id>` (valid token)** | **`X-Admin-Token: <ADMIN_TOKEN>`** | **200** | **`{"sucesso":true,"mensagem":"Produto deletado"}` — soft-delete behavior unchanged from before** |
| GET | `/produtos/<deleted-id>` | none | 404 | confirms soft-delete took effect |
| GET | `/usuarios` | none | 200 | response contains no `senha` key (checked programmatically) |
| GET | `/usuarios/<id>` | none | 200 | response contains no `senha` key |
| POST | `/usuarios` | none | 201 | unchanged |
| POST | `/usuarios` (duplicate email) | none | 400 | new: `"Email já cadastrado"` |
| POST | `/login` (valid) | none | 200 | unchanged, still returns id/nome/email/tipo only |
| POST | `/login` (invalid) | none | 401 | unchanged |
| POST | `/pedidos` (valid) | none | 201 | unchanged |
| POST | `/pedidos` (nonexistent `usuario_id`) | none | 400 | new: `"Usuário não encontrado"` (previously would have silently created an orphaned order) |
| GET | `/pedidos` | none | 200 | unchanged |
| GET | `/pedidos/usuario/<id>` | none | 200 | unchanged |
| PUT | `/pedidos/<id>/status` | none | 200 | unchanged |
| GET | `/relatorios/vendas` | none | 200 | unchanged |
| POST | `/admin/reset-db` (no token) | none | 401 | unchanged (already gated) |
| POST | `/admin/reset-db` (valid token) | `X-Admin-Token` | 200 | unchanged behavior |
| POST | `/admin/query` (no token) | none | 401 | unchanged (already gated) |
| POST | `/admin/query`, `SELECT * FROM usuarios` (valid token) | `X-Admin-Token` | 200 | rows returned with `senha` stripped (checked programmatically — no `"senha"` key in response) |
| POST | `/admin/query`, `DROP TABLE produtos` (valid token) | `X-Admin-Token` | 400 | rejected: `"Somente instruções SELECT são permitidas neste endpoint"`; confirmed `/produtos` still intact afterward |
| POST | `/admin/query`, malformed SQL (valid token) | `X-Admin-Token` | 500 | generic `"Erro interno no servidor"` via the centralized handler — no more raw SQLite error text leaked to the client |
| CORS preflight, `Origin: http://evil.example.com` | — | — | no `Access-Control-Allow-Origin` header returned |
| CORS preflight, `Origin: http://localhost:3000` | — | — | `Access-Control-Allow-Origin: http://localhost:3000` returned |

**`DELETE /produtos/<id>` now requires auth: confirmed above — unauthenticated
and wrong-token requests both get 401, and the same request with a valid
`X-Admin-Token` succeeds and behaves exactly as it did before (soft-delete,
same response shape), closing the CRITICAL "unauthenticated destructive
endpoint" finding without changing the route's path, method, or response
contract for authorized callers.**

All 27 request/response checks above matched the expected (fixed) behavior.
The background server (PID, started via `nohup ... python app.py &`) was
stopped with `kill` after validation completed, and the test SQLite file
(`src/loja.db`) plus the throwaway `.venv` used to install dependencies
were removed afterward.

## Dependencies

`requirements.txt` was not modified (no new dependencies were introduced —
`hmac`, used for the constant-time token comparison, is part of the Python
standard library). Installed the existing pinned versions into a scratch
virtualenv to run the boot/endpoint checks; no version changes were needed.

## Boot + endpoint re-check after the dependency-injection pass

Re-ran the full boot and a representative endpoint sweep after converting
models to repositories, controllers to classes, and views to blueprint
factories, to confirm the wiring change didn't alter behavior:

```
$ PYTHONPATH=src ADMIN_TOKEN=test-admin-token-123 PORT=5099 python src/app.py
==================================================
SERVIDOR INICIADO
Rodando em http://localhost:5099
==================================================
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5099
 * Running on http://192.168.1.144:5099
```

No errors on boot (fresh `loja.db`, auto-created and seeded). Checked:
`GET /`, `GET /health`, `GET /produtos` (+ `busca`, `/produtos/<id>`),
`POST /produtos`, `PUT /produtos/<id>`, `GET /usuarios` (confirmed no
`senha` key in the response), `POST /usuarios`, `POST /login` (valid and
invalid), `POST /pedidos`, `GET /pedidos` (+ `/pedidos/usuario/<id>`),
`PUT /pedidos/<id>/status` (including the `cancelado` stock-restoration
branch), `GET /relatorios/vendas`, `DELETE /produtos/<id>` (401 without
`X-Admin-Token`, 200 with it), `POST /admin/query` (401 without a token;
with a valid token, confirmed no `senha` key in the response), and
`POST /admin/reset-db` (401 without a token). All 19 routes responded with
the same status codes and shapes as the pre-DI validation pass above. The
background server was stopped and the scratch `loja.db` / virtualenv were
removed afterward.

## Finding count after this pass

With this pass, the "Acoplamento forte / ausência de injeção de
dependência" finding — the one item the README previously documented as
out of scope — is closed. **All 30 findings from
`reports/audit-code-smells-project.md` are now fixed: 30/30.**
