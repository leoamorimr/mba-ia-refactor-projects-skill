================================
PHASE 3 VALIDATION REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1, Flask-CORS 4.0.0), SQLite
Scope:   Restructure into MVC + fix all 22 findings from phase-2-audit.md

## 1. New directory tree

```
task-manager-api/
├── .env                        # local dev secrets (gitignored)
├── .env.example                # template for required/optional env vars
├── .gitignore                  # venv/, __pycache__/, *.db, .env, instance/
├── app.py                      # composition root: wiring only
├── database.py                 # db = SQLAlchemy() (unchanged)
├── config/
│   ├── __init__.py
│   └── settings.py             # SECRET_KEY / DEBUG / HOST / PORT / DB URI / JWT exp, all from env
├── models/                     # data only
│   ├── __init__.py
│   ├── task.py
│   ├── user.py
│   └── category.py
├── controllers/                # NEW — business logic / orchestration (was missing; logic lived in routes)
│   ├── __init__.py
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── category_controller.py
│   └── report_controller.py
├── routes/                     # HTTP routing + response shaping only
│   ├── __init__.py
│   ├── task_routes.py
│   ├── user_routes.py
│   ├── category_routes.py      # NEW — split out of report_routes.py (categories are their own domain)
│   └── report_routes.py
├── middlewares/                # NEW
│   ├── __init__.py
│   ├── auth.py                 # @login_required — verifies real signed JWTs
│   └── error_handler.py        # one centralized error handler for the whole app
├── utils/
│   ├── __init__.py
│   └── helpers.py              # single source of truth for constants/validation/formatting
├── seed.py
├── requirements.txt
└── README.md
```

`services/` (only ever contained the unused `NotificationService`) was deleted entirely — see finding #22 below.

Kept as-is per "adapting to a partially-organized project": `models/`, `routes/`, `utils/` folder names. Introduced `controllers/` and `middlewares/` as new layers (the project had no orchestration or middleware layer at all). Split `report_routes.py` into `report_routes.py` (reports only) + `category_routes.py` (categories are a distinct domain that had been living inside the reports file).

## 2. Findings fixed — mapping

### CRITICAL (5/5 fixed)

1. **Hardcoded SECRET_KEY** (`app.py:13`) → `config/settings.py` reads `SECRET_KEY` from the environment via `python-dotenv`; the app now **refuses to start** if it's unset (`RuntimeError`). `app.py` imports it from config, never touches `os.environ` directly.
2. **Password hash leaking via `User.to_dict()`** (`models/user.py:16-25`) → renamed to `User.to_public_dict()`, which no longer includes `password` at all. Every route that serializes a user (`GET/POST/PUT /users`, `GET /users/<id>`, `POST /login`) now goes through this method. Verified live: `GET /users/1` and `POST /login` responses contain no `password` key.
3. **MD5 password hashing** (`models/user.py:27-32`) → replaced with `werkzeug.security.generate_password_hash` / `check_password_hash` in `set_password`/`check_password`.
4. **Unauthenticated DELETE routes** → new `middlewares/auth.py` (`@login_required`) verifies a real signed JWT (PyJWT, HS256, `SECRET_KEY`) via `Authorization: Bearer <token>`, and checks the user still exists/is active. Applied to all mutating routes: `POST/PUT/DELETE /tasks`, `POST/PUT/DELETE /users`, `POST/PUT/DELETE /categories`. Verified live: these all return `401` with no/invalid token, and succeed with a token from `/login`.
5. **Hardcoded SMTP password** (`services/notification_service.py:7-10`) → the whole file was **deleted** (see finding #22 — it was dead code, never imported anywhere), which removes the hardcoded secret from the codebase entirely rather than just relocating it.

### HIGH (2/2 fixed)

6. **Fat controller / business logic in routes** (`report_routes.py`, `task_routes.py`) → all aggregation, stats, overdue checks and serialization moved into `controllers/*.py`. Routes now only parse the request, call a controller function, and `jsonify()` the result + status code. Duplicated overdue logic also now calls `Task.is_overdue()` everywhere instead of re-deriving it.
7. **Forgeable fake JWT** (`'fake-jwt-token-' + str(user.id)`) → `controllers/user_controller.py:_issue_token()` issues a real PyJWT token (`user_id`, `role`, `iat`, `exp`, signed with `SECRET_KEY`), verified by `middlewares/auth.py`. Verified live: token is a proper 3-part JWT; a hand-crafted/garbage token is rejected with `401 Token inválido`.

### MEDIUM (6/6 fixed)

8. **Unsafe debug/`0.0.0.0` default** → `config/settings.py`: `DEBUG` defaults to `false`, `HOST` defaults to `127.0.0.1`, both overridable via `FLASK_DEBUG`/`FLASK_HOST` env vars for real deployment.
9. **Missing input validation** (`update_category` TypeError on empty body; unchecked `priority` type) → every write handler now checks `if not data: return 400` before use; `utils/helpers.process_task_data()` rejects non-`int` priority with a clean `400` instead of crashing; `category` `color` is validated with `is_valid_color()`. Verified live: empty-body `PUT /categories/<id>` → `400`; `priority: "high"` → `400 Prioridade inválida` (previously would have raised an unhandled `TypeError`).
10. **`delete_category` breaking referential integrity** → `category_controller.delete_category()` now runs `Task.query.filter_by(category_id=...).update({'category_id': None})` before deleting the category. Verified live: assigned a task to a category, deleted the category, re-fetched the task — `category_id` is `null`, no dangling FK.
11. **Missing pagination** on `GET /tasks`, `GET /users`, `GET /categories` → all three accept `page`/`per_page` query params (`.limit().offset()`), default `per_page=20` (capped at 100). Response shape is unchanged (still a bare JSON array) since seed data volume is well under the default page size.
12. **N+1 queries** → `GET /tasks` uses `joinedload(Task.user, Task.category)` (was 1+2N queries, now O(1) additional queries); `GET /users` and `GET /categories` task-count columns use a single grouped aggregate query (`GROUP BY user_id`/`category_id`) instead of one `.count()` per row; `/reports/summary`'s per-user productivity loop and overdue list use grouped aggregate queries / a single filtered query instead of loading all tasks and looping in Python.
13. **No structured logging / no centralized error handling** → all `print(...)` calls removed from the request-serving code path; controllers use `logging.getLogger(__name__)` (`logger.info` on create/update/delete). `middlewares/error_handler.py` registers one `@app.errorhandler(HTTPException)` + `@app.errorhandler(Exception)` pair — unexpected exceptions are logged once and return a uniform `{"error": "Erro interno do servidor"}, 500`; controllers only catch what they need to (a `db.session.commit()` failure, to roll back) and re-raise.

### LOW (9/9 — 8 fixed as specified, 1 resolved via deletion; see notes)

14. **`datetime.utcnow()` deprecated** → replaced project-wide with `utils.helpers.utc_now()`. Note: this returns a **naive** UTC datetime (`datetime.now(timezone.utc).replace(tzinfo=None)`) rather than a tz-aware one. This is a deliberate adaptation, not an oversight: SQLite/SQLAlchemy's `DateTime` column always round-trips naive datetimes (it strips tzinfo on write and never restores it on read), and `due_date` is always naive too (parsed from a plain `"YYYY-MM-DD"` string). Returning a tz-aware value here would make every `task.due_date < utc_now()` comparison in `is_overdue()`/reports raise `TypeError: can't compare offset-naive and offset-aware datetimes` the moment a value round-trips through the DB. `utc_now()` avoids the deprecated call while keeping every datetime in the app naive-but-actually-UTC and therefore directly comparable — this is the "make sure any stored/naive values already in the DB are treated consistently" instruction from the audit's own recommendation.
15. **Dead dependencies** (`marshmallow`, `requests`, `python-dotenv` unused) → `marshmallow` and `requests` removed from `requirements.txt`. `python-dotenv` kept and now genuinely wired up (`config/settings.py` calls `load_dotenv()`). Added `PyJWT==2.9.0` for real token signing/verification.
16. **Duplicated overdue-check logic** (6 copies) → deleted from `task_routes.py`, `user_routes.py`, `report_routes.py`; every call site now calls `Task.is_overdue()`.
17. **Single-letter loop variables** (`u`, `t`, `c`, `p`) → renamed to `user`, `task`, `category` throughout the new `controllers/` and `routes/` code.
18. **Unused imports** (`os, sys, time, json`, `hashlib`) → removed. `app.py`/`routes/*.py` only import what they use.
19. **Bare `except:`** → replaced with specific handling: validation-shaped failures (bad date, bad priority, bad numeric query param) return a controlled `400` via explicit checks/`try/except ValueError`; genuinely unexpected DB errors are caught only to roll back (`except Exception: db.session.rollback(); raise`) and then propagate to the centralized error handler, which logs them via `logging`.
20. **Magic numbers** (`3`, `200`, `1`, `5`) → `utils/helpers.py` constants (`MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, `PRIORITY_MIN`, `PRIORITY_MAX`, `DEFAULT_PRIORITY`, `DEFAULT_STATUS`, `DEFAULT_COLOR`) are now actually imported and used by `process_task_data()`, `Task.validate_priority()`/`validate_status()`, and the controllers — no literal `1`/`5`/`3`/`200` left in validation logic.
21. **Dead `NotificationService`** → **deleted** (`services/notification_service.py` and the now-empty `services/` folder). Decision/rationale: it was never imported anywhere in the codebase, its SMTP integration was never exercised, and wiring it up would mean designing a notification feature (retry/queueing/from-address policy) that's out of scope for this structural+security refactor. Deleting it also fully resolves the CRITICAL hardcoded-SMTP-password finding at the root instead of just relocating that secret to an unused env var. If task/overdue notifications become an actual product requirement later, re-introduce it as `controllers/notification_controller.py` backed by env-configured SMTP settings in `config/settings.py`.
22. **Dead `utils/helpers.py` abstractions** → `generate_id()`, `sanitize_string()`, and `log_action()` were deleted (never used anywhere, and `log_action`'s `print`-based logging would have duplicated the new `logging` setup). Every remaining function/constant (`utc_now`, `format_date`, `calculate_percentage`, `validate_email`, `parse_date`, `is_valid_color`, `process_task_data`, and all the `VALID_*`/`*_LENGTH`/`PRIORITY_*`/`DEFAULT_*` constants) is now genuinely imported and called from models and/or controllers — this file is the single source of truth for validation/formatting, not a second unused layer.

## 3. Boot log (excerpt)

```
$ source venv/bin/activate && python3 app.py
 * Serving Flask app 'app'
 * Debug mode: off
2026-08-10 09:20:29,309 INFO werkzeug: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
2026-08-10 09:20:29,309 INFO werkzeug: Press CTRL+C to quit
```

Sample request log lines showing structured logging + centralized 401/404/405 handling:

```
2026-08-10 09:21:27,121 INFO controllers.task_controller: Task updated: id=11
2026-08-10 09:21:27,121 INFO werkzeug: 127.0.0.1 - - [10/Aug/2026 09:21:27] "PUT /tasks/11 HTTP/1.1" 200 -
2026-08-10 09:21:27,137 INFO werkzeug: 127.0.0.1 - - [10/Aug/2026 09:21:27] "DELETE /tasks/1 HTTP/1.1" 401 -
2026-08-10 09:21:43,420 INFO controllers.category_controller: Category created: id=5 name=Temp Category
2026-08-10 09:22:11,159 INFO werkzeug: 127.0.0.1 - - [10/Aug/2026 09:22:11] "PATCH /tasks HTTP/1.1" 405 -
```

Dependency install (clean, no conflicts):
```
Flask==3.0.0, Flask-Cors==4.0.0, Flask-SQLAlchemy==3.1.1, PyJWT==2.9.0,
python-dotenv==1.0.0, SQLAlchemy==2.0.51, Werkzeug==3.1.8
```

Seed output:
```
$ python3 seed.py
Seed concluído com sucesso!
  3 usuários
  4 categorias
  10 tasks
```

## 4. Endpoint-by-endpoint validation

All requests run against the live app (`http://127.0.0.1:5000`) seeded via `seed.py`. "Before" = original behavior per the audit; "After" = observed behavior post-refactor.

| Method | Path | Before | After (observed) | Result |
|---|---|---|---|---|
| GET | `/` | 200, `{message, version}` | 200, identical | PASS |
| GET | `/health` | 200, `{status, timestamp}` | 200, identical | PASS |
| GET | `/tasks` | 200, array of task dicts + `overdue`/`user_name`/`category_name`, N+1 queries | 200, identical shape, single query + `joinedload` (no N+1), respects `page`/`per_page` | PASS |
| GET | `/tasks?page=1&per_page=2` | not supported | 200, 2 items returned | PASS (new capability) |
| GET | `/tasks/<id>` | 200 with task + `overdue`; 404 if missing | identical (200/404) | PASS |
| GET | `/tasks/9999` | 404 `Task não encontrada` | 404 identical | PASS |
| GET | `/tasks/search?q=...` | 200, filtered list | 200, identical, plus clean 400 on non-numeric `priority`/`user_id` (previously would crash) | PASS |
| GET | `/tasks/stats` | 200, computed via full-table Python loop | 200, identical shape, computed via aggregate `COUNT`/filtered query | PASS |
| POST | `/tasks` (no token) | 201 (no auth existed) | **401** `Token de autenticação ausente` | PASS (intended auth-gate change) |
| POST | `/tasks` (valid token) | 201 | 201, identical body shape | PASS |
| POST | `/tasks` (missing title) | 400 | 400 identical | PASS |
| POST | `/tasks` (`priority: "high"`) | unhandled 500 (`TypeError`) | **400** `Prioridade inválida` | PASS (bug fixed) |
| POST | `/tasks` (bad `due_date`) | 400 | 400 identical message | PASS |
| POST | `/tasks` (empty body) | 400 | 400 identical | PASS |
| PUT | `/tasks/<id>` (no token) | 200 (no auth existed) | **401** | PASS (intended change) |
| PUT | `/tasks/<id>` (valid token) | 200 | 200 identical | PASS |
| DELETE | `/tasks/<id>` (no token) | 200 (no auth existed — the CRITICAL finding) | **401** `Token de autenticação ausente` | PASS (fixed) |
| DELETE | `/tasks/<id>` (valid token) | 200 `{message}` | 200 identical | PASS |
| DELETE | `/tasks/<id>` (garbage token) | n/a | **401** `Token inválido` | PASS |
| GET | `/users` | 200, array incl. `password` hash | 200, array, **no `password` field**, `task_count` via aggregate query (was N+1-ish `len(u.tasks)`) | PASS (security fix) |
| GET | `/users/<id>` | 200 incl. `password` + embedded tasks | 200, **no `password`**, tasks embedded identically otherwise | PASS (security fix) |
| GET | `/users/<id>/tasks` | 200, subset of task fields + `overdue` | 200, identical field set, `overdue` via `Task.is_overdue()` | PASS |
| POST | `/users` (no token) | 201 (no auth existed) | **401** | PASS (intended change) |
| POST | `/users` (valid token) | 201 incl. `password` hash | 201, **no `password`** | PASS (security fix) |
| POST | `/users` (dup email) | 409 | 409 identical | PASS |
| POST | `/users` (bad email) | 400 | 400 identical | PASS |
| PUT | `/users/<id>` (valid token) | 200 incl. `password` | 200, **no `password`** | PASS |
| DELETE | `/users/<id>` (no token) | 200 (no auth existed — CRITICAL finding) | **401** | PASS (fixed) |
| DELETE | `/users/<id>` (valid token) | 200, cascades task deletion | 200 identical, cascade via bulk delete | PASS |
| GET | `/users/9999` | 404 | 404 identical | PASS |
| POST | `/login` (valid creds) | 200, `token: 'fake-jwt-token-<id>'` (forgeable) | 200, **real signed JWT** (3-part, HS256, `exp`/`iat`), `user` has no `password` | PASS (auth fix) |
| POST | `/login` (wrong password) | 401 | 401 identical | PASS |
| POST | `/login` (empty body) | 400 | 400 identical | PASS |
| GET | `/categories` | 200, array + `task_count` via N+1 (`.count()` per row) | 200, identical shape, single aggregate query | PASS |
| POST | `/categories` (no token) | 201 (no auth existed) | **401** | PASS (intended change) |
| POST | `/categories` (valid token) | 201 | 201, plus new `color` format validation | PASS |
| PUT | `/categories/<id>` (empty body) | unhandled 500 (`TypeError` on `'name' in data`) | **400** `Dados inválidos` | PASS (bug fixed) |
| PUT | `/categories/<id>` (bad color) | 200, stored unvalidated | **400** `Cor inválida. Use o formato #RRGGBB` | PASS (bug fixed) |
| DELETE | `/categories/<id>` (no token) | 200 (no auth existed — CRITICAL finding) | **401** | PASS (fixed) |
| DELETE | `/categories/<id>` (valid token, has tasks) | 200, but left tasks with dangling `category_id` | 200, dependent tasks' `category_id` nulled first — verified by re-fetching a task after its category was deleted | PASS (referential-integrity fix) |
| DELETE | `/categories/9999` | 404 | 404 identical | PASS |
| GET | `/reports/summary` | 200, computed via ~10 sequential full-table loads + Python loops (N+1) | 200, identical shape, computed via grouped aggregate queries | PASS |
| GET | `/reports/user/<id>` | 200 | 200 identical | PASS |
| GET | `/nonexistent` | 404 HTML (default Flask) | 404 **JSON** via centralized handler | PASS (improved, same status code) |
| PATCH | `/tasks` (unsupported method) | 405 HTML | 405 **JSON** via centralized handler | PASS (improved) |
| POST | `/tasks` (malformed JSON body) | 400 (Werkzeug `BadRequest`, HTML) | 400 **JSON** `Dados inválidos` (via `get_json(silent=True)`) | PASS (improved) |

No endpoint regressed. The only behavior changes are the ones explicitly scoped as intentional: `password` no longer appears in any response, and `POST/PUT/DELETE` on `/tasks`, `/users`, `/categories` now require a valid `Authorization: Bearer <token>` obtained from `POST /login`.

## 5. Process notes

- Dependencies installed into a fresh `venv/` via `pip install -r requirements.txt` — clean install, no version conflicts.
- App booted with `python3 app.py`, exercised via `curl` against every route above (including negative/edge cases), then stopped (`kill`) at the end of validation. Confirmed the port was free afterward (a request to `127.0.0.1:5000/health` post-shutdown was answered by macOS's unrelated AirPlay/ControlCenter listener on the same port, returning `403` — not the Flask app).
- `seed.py`'s own `print()` calls were intentionally left as-is: it's a standalone one-off CLI/dev script, not part of the request-serving path the audit's logging finding was about.
