================================
VALIDATION REPORT (Phase 3)
================================
Project: task-manager-api
Scope:   Apply the fixes from phase-2-audit.md in place, on top of the
         existing MVC layout. No re-restructuring performed.

## Directory tree (unchanged shape — already MVC before this pass)

```
task-manager-api/
├── app.py                       (composition root)
├── database.py
├── seed.py
├── requirements.txt
├── config/
│   ├── __init__.py
│   └── settings.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── task.py
│   └── category.py
├── controllers/
│   ├── __init__.py
│   ├── user_controller.py
│   ├── task_controller.py
│   ├── category_controller.py
│   └── report_controller.py
├── routes/
│   ├── __init__.py
│   ├── user_routes.py
│   ├── task_routes.py
│   ├── category_routes.py
│   └── report_routes.py
├── middlewares/
│   ├── __init__.py
│   ├── auth.py
│   └── error_handler.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

No files were added or moved; only file contents changed.

## Findings fixed

### [CRITICAL] Privilege Escalation via Unrestricted Role Assignment — FIXED
- `middlewares/auth.py`: added a `roles_required(*roles)` decorator built on
  `User.is_admin()`, usable as a route-level admin gate.
- `controllers/user_controller.py`:
  - `create_user(data, caller=None)` — if `caller` is not an admin, any
    `role` in the payload is ignored and the account is always created as
    `role='user'`. Only an admin caller may set an elevated role.
  - `update_user(user_id, data, caller=None)` — if `'role' in data` and the
    caller is not an admin, the request is rejected with 403 *before* any
    field is touched, regardless of whose account is being edited (self or
    other).
- `routes/user_routes.py`: `create_user`/`update_user`/`delete_user` now
  pass `caller=g.current_user` into the controller.

### [CRITICAL] Sensitive PII Exposed via Unauthenticated Endpoints — FIXED
Added `@login_required` to all five routes named in the audit:
- `routes/user_routes.py`: `GET /users`, `GET /users/<id>`,
  `GET /users/<id>/tasks`
- `routes/report_routes.py`: `GET /reports/summary`, `GET /reports/user/<id>`

All five now require a valid bearer token; verified 401 without one (see
endpoint checks below).

### [HIGH] Missing Object-Level Authorization (IDOR) — FIXED
- `controllers/user_controller.py`: `delete_user` — only the account owner
  or an admin may delete it (403 otherwise). Extended the same ownership
  gate to `update_user` as a whole (any field, not just `role`) since it is
  the same class of bug on the same resource.
- `controllers/task_controller.py`: `update_task`/`delete_task` — caller
  must be `task.user_id` or an admin, else 403.
- `controllers/category_controller.py`: `update_category`/`delete_category`
  — categories are shared/global resources with no owner field, so the
  "ownership or role check" the audit called for is a role check here:
  admin-only.
- `routes/task_routes.py` and `routes/category_routes.py` now pass
  `caller=g.current_user` into these controller calls.

### [MEDIUM] Missing Pagination — FIXED
- `controllers/task_controller.py::search_tasks` and
  `controllers/user_controller.py::get_user_tasks` now accept
  `page`/`per_page`, clamp them via the shared `clamp_pagination` helper,
  and apply `.limit()/.offset()` the same way `list_tasks` already did.
- `routes/task_routes.py` and `routes/user_routes.py` read `page`/`per_page`
  query params for these two routes and forward them.

### [MEDIUM] Deprecated SQLAlchemy Legacy Query API — FIXED
Replaced every `Model.query.get(id)` call site with `db.session.get(Model, id)`:
`middlewares/auth.py:38`; `controllers/report_controller.py:108`;
`controllers/category_controller.py` (`update_category`, `delete_category`);
`controllers/task_controller.py` (`get_task`, `create_task` x2,
`update_task` x2, `delete_task`); `controllers/user_controller.py`
(`get_user`, `update_user`, `delete_user`, `get_user_tasks`).
Verified with `grep -rn "\.query\.get(" --include="*.py" .` → no matches.

### [MEDIUM] Missing Input Validation — FIXED
- `controllers/task_controller.py::search_tasks` now validates `status`
  against `VALID_STATUSES` and returns 400 on an invalid value (previously
  silently produced an empty result set).
- `utils/helpers.py::is_valid_color` tightened to
  `re.fullmatch(r'#[0-9a-fA-F]{6}', color)` (was `len(color)==7 and
  color[0]=='#'`, which accepted e.g. `#zzzzzz`).

### [MEDIUM] Weak Password Policy / Guessable Seed Credentials — FIXED
- `utils/helpers.py`: `MIN_PASSWORD_LENGTH` raised from 4 to 8; new
  `is_valid_password(password)` also requires at least one letter and one
  digit. Used by both `create_user` and `update_user`.
- `seed.py`: demo accounts now use `demo-admin-2026` / `demo-user-2026` /
  `demo-manager-2026` instead of `1234` / `abcd` / `pass` — clearly
  non-production-looking, but long/complex enough to satisfy the app's own
  policy so the seeded accounts can still log in.

### [LOW] Duplicated Pagination Clamping — FIXED
- `utils/helpers.py`: added `DEFAULT_PAGE = 1`, `DEFAULT_PER_PAGE = 20`,
  `MAX_PER_PAGE = 100`, and `clamp_pagination(page, per_page)`.
- `controllers/task_controller.py`, `controllers/user_controller.py`,
  `controllers/category_controller.py` all now import these constants and
  the helper instead of each defining its own copy of the clamping logic.

## Dependencies

`requirements.txt` unchanged (`flask`, `flask-sqlalchemy`, `flask-cors`,
`python-dotenv`, `pyjwt`) — no new dependency was needed for any fix.
Created a local `.venv`, installed requirements into it (resolved to
SQLAlchemy 2.0.52, compatible with `db.session.get`), and created a local
`.env` from `.env.example` with a freshly generated `SECRET_KEY` (both
`.venv` and `.env` are already gitignored).

## Boot output

```
$ python3 -m py_compile app.py database.py seed.py <all controllers/models/routes/middlewares/utils/config>
OK   (no syntax errors)

$ python3 seed.py
Seed concluído com sucesso!
  3 usuários
  4 categorias
  10 tasks

$ python3 app.py
 * Serving Flask app 'app'
 * Debug mode: off
 WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000

$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/health
200
```

App boots cleanly and serves `/health` with no errors. Process was stopped
at the end of validation (`kill <pid>`; confirmed no task-manager-api
`app.py` process remains via `ps aux`).

## Endpoint-by-endpoint check results

Seed users: `joao@email.com` (id 1, role `admin`), `maria@email.com`
(id 2, role `user`), `pedro@email.com` (id 3, role `manager`).

### Auth-fix verification (the hard gate)

| Request | Expected | Actual |
|---|---|---|
| `GET /users` (no token) | 401 | **401** |
| `GET /users/1` (no token) | 401 | **401** |
| `GET /users/1/tasks` (no token) | 401 | **401** |
| `GET /reports/summary` (no token) | 401 | **401** |
| `GET /reports/user/1` (no token) | 401 | **401** |
| `GET /users` as admin token | 200 | **200** (returns list incl. email) |
| `GET /reports/summary` as admin token | 200 | **200** |
| `GET /reports/user/2` as user token | 200 | **200** |

### Privilege escalation (CRITICAL finding 1)

| Request | Expected | Actual |
|---|---|---|
| Maria (`user`) `PUT /users/2 {"role":"admin"}` | 403 | **403** `"Apenas administradores podem alterar o role"` |
| Maria `POST /users {..., "role":"admin"}` | 201, role forced to `user` | **201**, response `"role":"user"` |
| Admin `PUT /users/2 {"role":"admin"}` | 200, role changes | **200**, response `"role":"admin"` (reverted after test) |

### IDOR / ownership (HIGH finding 3)

| Request | Expected | Actual |
|---|---|---|
| Maria `DELETE /users/1` (joao, not her account) | 403 | **403** |
| Maria `PUT /users/3` (pedro's profile, non-role field) | 403 | **403** |
| Maria `PUT /tasks/3` (pedro's task) | 403 | **403** |
| Maria `DELETE /tasks/3` (pedro's task) | 403 | **403** |
| Maria `PUT /tasks/2` (her own task) | 200 | **200** |
| Maria `PUT /categories/1` (non-admin) | 403 | **403** |
| Maria `DELETE /categories/1` (non-admin) | 403 | **403** |
| Admin `PUT /categories/1` | 200 | **200** |

### Pagination (MEDIUM finding 4)

| Request | Expected | Actual |
|---|---|---|
| `GET /tasks/search?per_page=2` | ≤2 results | **2 results** |
| `GET /users/2/tasks?per_page=1` (as maria) | ≤1 result, 200 | **1 result, 200** |

### Input validation (MEDIUM finding 6)

| Request | Expected | Actual |
|---|---|---|
| `GET /tasks/search?status=bogus` | 400 | **400** `"Status inválido"` |
| `POST /categories {"color":"#zzzzzz"}` (admin) | 400 | **400** `"Cor inválida. Use o formato #RRGGBB"` |
| `POST /categories {"color":"#AB12ef"}` (admin) | 201 | **201** |

### Password policy (MEDIUM finding 7)

| Request | Expected | Actual |
|---|---|---|
| `POST /users` password=`"abcdefg"` (7 chars, no digit) | 400 | **400** |
| `POST /users` password=`"12345678"` (8 digits, no letter) | 400 | **400** |
| `POST /users` password=`"abcdefg1"` (8 chars, letter+digit) | 201 | **201** |

### Normal CRUD/list/search/report flows (contract preserved)

| Request | Expected | Actual |
|---|---|---|
| `GET /health` | 200 | **200** |
| `GET /tasks/stats` (unauth, out of scope) | 200 | **200** |
| `GET /categories` (unauth, out of scope) | 200 | **200** |
| `POST /login` (joao / maria) | 200 + JWT | **200**, tokens obtained and used throughout |
| Maria `POST /tasks` (create own task) | 201 | **201** |
| Maria `DELETE /tasks/<own new task>` | 200 | **200** |
| `POST /tasks` with no token | 401 | **401** |
| Admin `DELETE /categories/<throwaway>` | 200 | **200** |
| Admin `DELETE /users/<throwaway test accounts>` | 200 | **200** (cleanup) |

All checks passed. Test/throwaway users and categories created during
validation were deleted afterward; the seed data (`joao`/`maria`/`pedro`,
4 categories, 10 tasks) was left in its original state (maria's role was
promoted to admin and back to `user` as part of the escalation test, and
one task title was changed by the ownership test — both are inside the
seeded demo data, not new records).
