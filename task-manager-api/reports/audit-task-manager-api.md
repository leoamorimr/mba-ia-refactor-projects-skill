================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python / Flask 3.0.0 (Flask-SQLAlchemy 3.1.1, Flask-CORS 4.0.0, PyJWT 2.9.0)
Files:   24 analyzed | ~1373 lines of code

## Summary
CRITICAL: 2 | HIGH: 1 | MEDIUM: 4 | LOW: 1

## Findings

### [CRITICAL] Privilege Escalation via Unrestricted Role Assignment
File: controllers/user_controller.py:59-140
Description: `create_user` (lines 59-98) takes `role = data.get('role', 'user')` straight from the request body and only checks that it is one of `VALID_ROLES` (`user`, `admin`, `manager` — lines 84-87); it never checks what role the *caller* holds. `update_user` (lines 101-140) does the same for an existing account: if `'role' in data`, it validates the value against `VALID_ROLES` and assigns it (lines 126-129) with no check on the caller's own privilege. Both endpoints are reachable by any authenticated user through `POST /users` and `PUT /users/<id>` (routes/user_routes.py:25-32 and :35-42), which are guarded only by `@login_required` — a decorator that verifies the JWT is valid and the user is active (middlewares/auth.py:16-45), but never inspects `role`. Confirming the intended check was never wired in: `User.is_admin()` (models/user.py:34-35) is fully implemented but has zero call sites anywhere in the codebase (verified by grepping the whole tree for `is_admin`).
Impact: Any logged-in account, including a freshly created `role='user'` account, can call `PUT /users/<own_id>` with `{"role": "admin"}` to self-promote, or call `POST /users` with `{"role": "admin", ...}` to mint a brand-new admin account. Once admin, that account can delete any user, task, or category. This is a full authorization bypass hiding behind an authentication check that looks correct at a glance.
Recommendation: Add a real authorization layer on top of `login_required` (e.g. a `roles_required('admin')` decorator that reads `g.current_user` and calls the already-existing `User.is_admin()`), and require it on the `role` field of both `create_user`/`update_user`. Never let the field driving privilege come straight from the request body of an endpoint reachable by non-privileged callers — only an existing admin should be able to set another account's `role`, and a self-service signup route (if any) should always force `role='user'` server-side, ignoring any `role` in the payload.

### [CRITICAL] Sensitive PII Exposed via Unauthenticated Endpoints
File: routes/user_routes.py:9-22
Description: `GET /users` (get_users, lines 9-14) and `GET /users/<id>` (get_user, lines 17-22) have no `@login_required` decorator — contrast with the sibling `POST`/`PUT`/`DELETE` handlers in the same file, which all carry it (lines 25-51). Both return `user.to_public_dict()` (models/user.py:17-26), which includes the `email` field for every user in the system. `GET /users/<id>/tasks` (routes/user_routes.py:54-59) is equally unauthenticated and returns that user's full task list. The same gap exists in routes/report_routes.py:1-19: `GET /reports/summary` (lines 8-11) and `GET /reports/user/<id>` (lines 14-19) carry no auth guard at all — `user_report` (controllers/report_controller.py:107-140) returns `user['email']` (line 126) alongside per-user productivity statistics, and `summary_report` (controllers/report_controller.py:18-104) returns aggregated data plus a full `user_productivity` breakdown by name (lines 73-84).
Impact: Anyone who can reach the API — no token, no login — can enumerate every registered user's email address, role, and task history, plus derive per-user productivity metrics via the reports endpoints. This is a direct PII leak with no authentication barrier at all, not merely a missing-authorization edge case.
Recommendation: Add `@login_required` to `get_users`, `get_user`, `get_user_tasks` (routes/user_routes.py) and to both routes in routes/report_routes.py. If a public directory of users is genuinely required, return a reduced projection (name/role only, no email) from a dedicated public endpoint instead of reusing `to_public_dict()`, and keep the detailed/report views behind authentication.

### [HIGH] Missing Object-Level Authorization (IDOR) on Mutating Endpoints
File: controllers/user_controller.py:143-158
Description: `delete_user` (lines 143-158) lets any request that passes `@login_required` delete *any* user by id, cascading into `Task.query.filter_by(user_id=user_id).delete()` (line 148) — there is no check that the caller is deleting their own account or is an admin. The same shape repeats for tasks — `update_task`/`delete_task` (controllers/task_controller.py:104-157) never compare `task.user_id` against the caller's identity before mutating or removing a task that belongs to someone else — and for categories — `update_category`/`delete_category` (controllers/category_controller.py:70-117) apply no ownership or role check either. In every case the only gate is `login_required` (middlewares/auth.py:16-45), which authenticates but never authorizes; `g.current_user` is set on line 42 of that file but is never read anywhere else in the codebase.
Impact: Any authenticated user (regardless of role) can delete or modify another user's account, tasks they don't own, or shared categories. Beyond the role-escalation path already reported as CRITICAL, this means even a correctly-scoped `role='user'` account can grief/vandalize other users' data.
Recommendation: Introduce ownership checks (e.g. `task.user_id == g.current_user.id or g.current_user.is_admin()`) before mutating/deleting a resource in task_controller.py and category_controller.py, and restrict `delete_user`/`update_user` on user accounts other than the caller's own to admins only, using the same authorization helper recommended above.

### [MEDIUM] Missing Pagination on List Endpoints
File: controllers/task_controller.py:160-186
Description: `search_tasks` builds a filtered query and calls `tasks_query.all()` unconditionally (line 185), with no `limit`/`offset`/`page` support, unlike `list_tasks` (same file, lines 29-49) which does implement clamped pagination. `get_user_tasks` (controllers/user_controller.py:161-180) has the identical gap: `Task.query.filter_by(user_id=user_id).all()` (line 166) returns every matching row unbounded.
Impact: `GET /tasks/search` and `GET /users/<id>/tasks` response size and query cost grow unbounded with the number of matching rows — invisible with seed data, but a real risk once a user or search filter matches thousands of tasks.
Recommendation: Reuse the same `page`/`per_page` clamping pattern (and helper, once de-duplicated per the LOW finding below) already used in `list_tasks`, `list_users`, and `list_categories` for these two endpoints as well.

### [MEDIUM] Deprecated SQLAlchemy Legacy Query API
File: controllers/task_controller.py:53-145
Description: `Task.query.get(...)` / `User.query.get(...)` / `Category.query.get(...)` — the legacy SQLAlchemy 1.x `Query.get()` API, deprecated under SQLAlchemy 2.0 (the version line Flask-SQLAlchemy 3.1.1 requires) — is used pervasively instead of `db.session.get(Model, id)`: controllers/task_controller.py:53,75,79,105,118,124,145; controllers/user_controller.py:49,102,144,162; controllers/category_controller.py:71,101; controllers/report_controller.py:108; middlewares/auth.py:38.
Impact: The app still works today, but every one of these 16 call sites emits a `LegacyAPIWarning` and is a removal candidate in a future SQLAlchemy major version; the pattern is copy-pasted into every controller and the auth middleware, so an eventual removal means a wide, mechanical-but-easy-to-miss find-and-replace across the whole codebase.
Recommendation: Replace `Model.query.get(id)` with `db.session.get(Model, id)` everywhere listed above; consider a small `get_or_404`-style helper in utils/helpers.py so the lookup-plus-404 pattern (`if not x: return None, '... não encontrada', 404`) that's repeated in nearly every controller function stops being copy-pasted too.

### [MEDIUM] Missing Input Validation at the Route Boundary
File: controllers/task_controller.py:160-186
Description: `search_tasks` filters by `Task.status == status` (line 169) without checking `status` against `VALID_STATUSES` first, unlike `process_task_data` (utils/helpers.py:93-96) which does enforce that enum on create/update — an invalid status value silently yields an empty result set instead of a 400. Separately, `is_valid_color` (utils/helpers.py:64-65) only checks `len(color) == 7 and color[0] == '#'`; it accepts any string of that shape (e.g. `#zzzzzz`) as a "valid" color, so `create_category`/`update_category` (controllers/category_controller.py:53-55, :86-89) will happily store a non-hex value.
Impact: Malformed filter/field values reach the data layer (or get stored) without a clear validation error, making bad input silently swallowed (empty search results) or silently persisted (garbage color values) instead of rejected with a 400.
Recommendation: Validate `status` in `search_tasks` against `VALID_STATUSES` the same way `process_task_data` already does, returning 400 on a bad value; tighten `is_valid_color` to actually verify the six characters after `#` are hex digits (e.g. `re.fullmatch(r'#[0-9a-fA-F]{6}', color)`).

### [MEDIUM] Weak Password Policy and Guessable Seed Credentials
File: utils/helpers.py:15
Description: `MIN_PASSWORD_LENGTH = 4` is the only password strength rule enforced by `create_user`/`update_user` (controllers/user_controller.py:78-79, :121-123) — a 4-character password like `1234` passes. seed.py:17-36 populates the database with exactly that: the admin account `joao@email.com` gets password `'1234'` (seed.py:20), `maria@email.com` gets `'abcd'` (seed.py:27), and `pedro@email.com` gets `'pass'` (seed.py:34).
Impact: If this seed script is ever pointed at a shared or production-like database (or its output is mistaken for real onboarding data), it creates a fully-privileged admin account with a trivially guessable 4-character password, and the length policy itself would let a real user pick an equally weak password.
Recommendation: Raise `MIN_PASSWORD_LENGTH` to a realistic minimum (8+, ideally with a complexity check), and change seed.py to generate random per-run passwords (or clearly non-production-looking ones) for demo accounts, printing them once at seed time rather than hardcoding guessable literals in source.

### [LOW] Duplicated Code and Magic Number in Pagination Clamping
File: controllers/task_controller.py:25-31
Description: The identical two lines `page = max(page, 1)` / `per_page = max(min(per_page, 100), 1)` (task_controller.py:30-31) are copy-pasted verbatim in controllers/user_controller.py:21-22 and controllers/category_controller.py:18-19, each preceded by its own private `DEFAULT_PAGE = 1` / `DEFAULT_PER_PAGE = 20` constants (task_controller.py:25-26, user_controller.py:16-17, category_controller.py:13-14) instead of sharing one definition from utils/helpers.py. The `100` page-size cap is also a bare literal repeated three times with no named constant.
Impact: Three independent copies of the same pagination policy mean a future change (e.g. raising the cap, or adding a `total_count` field) has to be made — and can drift — in three places.
Recommendation: Move `DEFAULT_PAGE`, `DEFAULT_PER_PAGE`, and a new `MAX_PER_PAGE = 100` constant into utils/helpers.py, and factor the two clamping lines into a single `clamp_pagination(page, per_page)` helper reused by all three controllers.

================================
Total: 8 findings
================================
