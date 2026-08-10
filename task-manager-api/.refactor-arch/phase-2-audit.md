================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1, Flask-CORS 4.0.0)
Files:   16 analyzed (15 .py files + requirements.txt) | ~1164 lines of code

## Summary
CRITICAL: 5 | HIGH: 2 | MEDIUM: 6 | LOW: 9

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets — Flask SECRET_KEY
File: app.py:13
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` is a literal string committed to source control, not read from an environment variable or secrets manager.
Impact: The key signs/validates Flask sessions and any CSRF or signed-cookie mechanism built on it. Anyone with source access (or a leaked repo/backup) can forge session data or cookies.
Recommendation: Load `SECRET_KEY` from an environment variable (e.g. `os.environ['SECRET_KEY']`) with no hardcoded fallback in any environment that touches real data; fail startup if it's missing.

### [CRITICAL] Sensitive Data Exposure — Password Hash Returned in API Responses
File: models/user.py:16-25
Description: `User.to_dict()` includes `'password': self.password` (the stored password hash). This method is called and returned directly in `GET /users/<id>` (routes/user_routes.py:33), `POST /users` (routes/user_routes.py:85-86), `PUT /users/<id>` (routes/user_routes.py:129), and `POST /login` (routes/user_routes.py:209).
Impact: Every user-facing endpoint that touches a `User` leaks the password hash over the network. Combined with the weak MD5 hashing below, an attacker who observes traffic or logs can crack the hash offline (or use it directly against systems vulnerable to hash-pass-the-hash-style reuse).
Recommendation: Strip `password` from `to_dict()` entirely (or add a `to_public_dict()` used by all routes) so credential material never leaves the server process.

### [CRITICAL] Weak / Homegrown Password Hashing (MD5)
File: models/user.py:27-32
Description: `set_password`/`check_password` hash passwords with unsalted `hashlib.md5(...)`.
Impact: MD5 is cryptographically broken and has no per-user salt; a leaked `users` table can be reversed via rainbow tables/GPU brute force in seconds, exposing every user's real password (and any reused credentials on other systems).
Recommendation: Hash with `werkzeug.security.generate_password_hash` / `check_password_hash` (already a transitive Flask dependency) or `bcrypt`, both of which handle salting and cost factor automatically.

### [CRITICAL] Unauthenticated Destructive/Admin Endpoint — DELETE routes
File: routes/report_routes.py:211-223, routes/task_routes.py:225-238, routes/user_routes.py:134-151
Description: `DELETE /categories/<id>`, `DELETE /tasks/<id>`, and `DELETE /users/<id>` perform the delete with no authentication/authorization check at all. There is no auth decorator, `before_request` guard, or token check anywhere in the codebase — the `/login` endpoint issues a token (see the forgeable-token finding below) but nothing ever validates it against any route.
Impact: Any anonymous caller can permanently delete any task, user, or category. This is a fully open door to destroy data with a single unauthenticated HTTP request.
Recommendation: Introduce an auth middleware (e.g. a `@login_required` decorator backed by real signed JWTs) and apply it to every mutating route, gated by role checks (`is_admin()`) for destructive/admin actions.

### [CRITICAL] Hardcoded Credentials / Secrets — SMTP Password in NotificationService
File: services/notification_service.py:7-10
Description: `self.email_host`, `self.email_user`, and `self.email_password = 'senha123'` are literal SMTP credentials embedded in source.
Impact: Anyone with source access has full access to the associated Gmail account (and can send email as it), regardless of whether this service is currently wired up.
Recommendation: Load SMTP credentials from environment/secret storage, and rotate the exposed password immediately since it is already in version control history.

### [HIGH] Fat Controller / Business Logic in the Route Layer
File: routes/report_routes.py:12-101, routes/task_routes.py:11-63,273-299
Description: `summary_report` (report_routes.py) computes status/priority breakdowns, an overdue list, and per-user productivity stats — all with hand-rolled loops and counters — directly inside the route handler instead of delegating to a model/service. `get_tasks` and `task_stats` (task_routes.py) similarly reimplement `Task.to_dict()`, the overdue check that already exists as `Task.is_overdue()`, and status counting inline rather than calling the existing model methods.
Impact: These business rules can't be unit-tested without booting the full HTTP stack, and because they're re-implemented per handler (rather than called once from the model), the "is task overdue" and serialization rules have already started to drift between `Task.to_dict()`/`Task.is_overdue()` and their inline duplicates.
Recommendation: Move aggregation/reporting logic into a `ReportService`/`TaskService`, and have every route call `Task.to_dict()` / `Task.is_overdue()` / `Task.validate_status()` instead of re-deriving the same fields inline, so route handlers only shape the HTTP response.

### [HIGH] Forgeable / Predictable Auth Tokens
File: routes/user_routes.py:210
Description: `'token': 'fake-jwt-token-' + str(user.id)` builds the "auth token" by string concatenation of a public, guessable value (the user's numeric id) — it is not signed or verifiable.
Impact: Anyone can construct a valid-looking token for any user id (e.g. `fake-jwt-token-1` for an admin) without knowing their password. Even though no route currently checks this token, once one does, this scheme grants trivial account takeover.
Recommendation: Issue a real signed token (e.g. `PyJWT` with `SECRET_KEY`/an asymmetric key, including expiry and a signature) and verify it in an auth middleware applied to protected routes.

### [MEDIUM] Deprecated / Unsafe Flask Debug Mode in Entry Point
File: app.py:34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` is the app's `__main__` entry point, running the Werkzeug debugger with the interactive console enabled and binding to all network interfaces.
Impact: If this ever runs reachable from a network (not just localhost), an unhandled exception exposes the Werkzeug interactive debugger, which can be used to execute arbitrary Python code on the host.
Recommendation: Serve via a production WSGI server (gunicorn/uwsgi) with `debug=False`, and gate any debug flag behind an environment variable that defaults to off.

### [MEDIUM] Missing Input Validation at the Route Boundary
File: routes/report_routes.py:190-209, routes/task_routes.py:113-114,181-184
Description: `update_category` (report_routes.py) calls `data = request.get_json()` and immediately does `if 'name' in data:` with no `if not data: return 400` guard (unlike every other handler in the file) — an empty/absent JSON body raises an unhandled `TypeError` instead of a clean 400. It also writes `cat.color` straight from user input with no format check (contrast with the unused `is_valid_color()` helper in utils/helpers.py). Separately, `create_task`/`update_task` (task_routes.py) compare `priority < 1 or priority > 5` without checking that `priority` is numeric first, so a non-numeric `priority` (e.g. a string) raises an unhandled `TypeError` rather than returning a validation error.
Impact: Malformed requests crash the handler with a generic Flask 500/HTML error page instead of a controlled JSON error response, and unchecked fields (like `color`) reach the database unvalidated.
Recommendation: Validate `request.get_json()` for `None`/wrong-type before touching it in every handler, and validate field types (e.g. `isinstance(priority, int)`) before range checks — ideally via a shared schema (marshmallow is already a pinned dependency but is never used).

### [MEDIUM] Deletes That Break Referential Integrity
File: routes/report_routes.py:211-223
Description: `delete_category` deletes a `Category` row without reassigning or clearing the `category_id` on the `Task` rows that reference it (contrast with `delete_user`, routes/user_routes.py:140-142, which does delete the dependent tasks first).
Impact: Tasks are left with a `category_id` pointing at a category that no longer exists — a dangling foreign key. Any code path that assumes `category_id` is always resolvable silently gets `None` back (as in task_routes.py:50-57) and reports are quietly wrong.
Recommendation: Before deleting a category, either null out `Task.category_id` for its tasks or block the delete while tasks still reference it (409 Conflict), matching the pattern already used for user deletion.

### [MEDIUM] Missing Pagination on List Endpoints
File: routes/task_routes.py:14, routes/user_routes.py:12, routes/report_routes.py:159
Description: `GET /tasks`, `GET /users`, and `GET /categories` all call `Model.query.all()` with no `limit`/`offset`/`page` parameter support.
Impact: Response size and query cost grow unbounded as the tables grow; this is invisible with seed data (10 tasks, 3 users) and becomes a real latency/memory problem in production.
Recommendation: Add `page`/`per_page` query params and use SQLAlchemy's `.paginate()` (or `limit()`/`offset()`) on all three collection endpoints.

### [MEDIUM] N+1 Queries
File: routes/task_routes.py:41-57
Description: `get_tasks` fetches all tasks once, then for every task runs `User.query.get(t.user_id)` and `Category.query.get(t.category_id)` inside the loop (lines 41-49 and 50-57). The same shape recurs in `summary_report` (report_routes.py:53-68, one `Task.query.filter_by(user_id=u.id).all()` per user) and `get_categories` (report_routes.py:161-164, one `Task.query.filter_by(category_id=c.id).count()` per category).
Impact: Response time grows linearly with the number of tasks/users/categories instead of issuing a small, constant number of queries — fine with seed data, painful once the tables hold real volume.
Recommendation: Replace the per-row lookups with eager loading (`Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()`) or a single aggregate query (e.g. `GROUP BY` for the per-user/per-category counts).

### [MEDIUM] No Structured Logging / No Centralized Error Handling
File: routes/task_routes.py:146-154
Description: `create_task` (and nearly every other write handler across task_routes.py, user_routes.py, and report_routes.py) wraps its own `try/except`, uses `print(...)` as its only diagnostic output (e.g. `print(f"Task criada: {task.id} - {task.title}")` at line 149, `print(f"Erro ao criar task: {str(e)}")` at line 153), and returns a duplicated "log and return 500" JSON body.
Impact: Errors aren't queryable/aggregable in production (stdout `print` output is not structured or leveled), and the copy-pasted try/except-log-500 block is duplicated across roughly a dozen handlers, so any change to the error format has to be repeated everywhere.
Recommendation: Replace `print` with Python's `logging` module (or a structured logger), and register a single Flask error handler (`@app.errorhandler(Exception)`) so handlers can let exceptions propagate instead of each one duplicating its own catch-log-500 logic.

### [LOW] Deprecated API Usage — datetime.utcnow()
File: models/task.py:15-16
Description: `datetime.utcnow` is used as the default for `created_at`/`updated_at` (models/task.py:15-16) and in the overdue comparison (models/task.py:52). The same deprecated call recurs throughout the codebase: models/user.py:14, models/category.py:11, routes/task_routes.py:31,72,136,203,215,285, routes/user_routes.py:172, routes/report_routes.py:35,42,45,71,133, services/notification_service.py:35, utils/helpers.py:38, and seed.py:66-74.
Impact: `datetime.utcnow()` is deprecated as of Python 3.12 (it returns a naive datetime with no tzinfo, which is error-prone for comparisons across timezones) — it still works today, but will require a broad, mechanical fix later.
Recommendation: Replace with `datetime.now(timezone.utc)` project-wide, and make sure any stored/naive values already in the DB are treated consistently.

### [LOW] Dead Dependencies in requirements.txt
File: requirements.txt:4-6
Description: `marshmallow==3.20.1`, `requests==2.31.0`, and `python-dotenv==1.0.0` are pinned but never imported anywhere in the codebase (confirmed via project-wide grep — `marshmallow` only appears inside a string in a seed data description, `requests`/`dotenv` don't appear at all).
Impact: Extra install/build surface and version-bump churn for packages that provide zero value; `python-dotenv`'s absence also means `SECRET_KEY`/SMTP credentials genuinely have no env-loading mechanism in place despite the dependency being present, which is misleading.
Recommendation: Remove the three unused pins, or — better — actually wire up `python-dotenv` for config loading and `marshmallow` for the request-validation schemas this project needs (see the missing-input-validation finding).

### [LOW] Duplicated Code — Overdue-Check Logic Reimplemented Repeatedly
File: routes/report_routes.py:34-37
Description: The same nested check — `if t.due_date: if t.due_date < datetime.utcnow(): if t.status != 'done' and t.status != 'cancelled': ...` — is copy-pasted with only the "then" branch changing, across report_routes.py:34-37 and 132-135, task_routes.py:30-39, 71-80, and 284-287, and user_routes.py:171-180 — six near-identical copies of logic that already exists once as `Task.is_overdue()` (models/task.py:50-60).
Impact: Any change to what counts as "overdue" (e.g. adding a grace period) requires editing six call sites correctly; missing one silently produces inconsistent `overdue` flags between endpoints.
Recommendation: Delete all six inline copies and call `task.is_overdue()` everywhere an overdue flag is needed.

### [LOW] Poor Naming — Single-Letter Variables for Domain Objects
File: routes/report_routes.py:53-68
Description: Loop variables carrying full domain objects are named with single letters throughout the routes: `u` for a `User` (report_routes.py:55, user_routes.py:14), `t` for a `Task` (report_routes.py:33,56,59,119, task_routes.py:16, user_routes.py:37,161), `c`/`cat` for a `Category` (report_routes.py:161), and `p` for a priority value (models/task.py:45).
Impact: Reads like `u.name`, `t.status`, `c.id` require the reader to mentally re-map the letter to its type every time, especially once multiple single-letter names are in scope in the same function (e.g. `t` and `u` together in report_routes.py:53-68).
Recommendation: Rename to `user`, `task`, `category` (or their plural-safe singular form) in every loop that iterates a collection of domain entities.

### [LOW] Dead Code / Unused Imports
File: routes/task_routes.py:7
Description: `import json, os, sys, time` (task_routes.py:7) — none of `json`, `os`, `sys`, or `time` are referenced anywhere in the file. Similarly, `routes/user_routes.py:6` imports `hashlib` and `json` but never uses either (only `re` from that line is used), and `routes/report_routes.py:8` imports `json` but never uses it.
Impact: Dead imports add noise and make it harder to tell, at a glance, what a module's real dependencies are.
Recommendation: Remove the unused names from each import statement (`os, sys, time` and `json` from task_routes.py:7; `hashlib, json` from user_routes.py:6; `json` from report_routes.py:8).

### [LOW] Overly Broad Exception Handling
File: routes/task_routes.py:62-63
Description: A bare `except:` swallows every exception with no logging at all in `get_tasks` (task_routes.py:62-63), `create_task`'s date parsing (task_routes.py:137), and `delete_task` (task_routes.py:236). The same bare-`except` pattern recurs in report_routes.py:186-188,207-209,221-223 and user_routes.py:130-132,149-151, and in `utils/helpers.py:46-49` (`parse_date`).
Impact: Every real bug (a programming error, a bad DB constraint, an out-of-memory condition) gets silently reduced to the same generic "Erro interno"/500 response with zero trace of what actually happened, making production issues nearly impossible to diagnose.
Recommendation: Catch specific exception types you expect (e.g. `SQLAlchemyError`, `ValueError`), log the exception (see the structured-logging finding), and let anything unexpected propagate to a centralized error handler instead of a bare `except:`.

### [LOW] Magic Numbers
File: routes/task_routes.py:96-100
Description: Title-length bounds (`3`, `200`) and the priority range (`1`, `5`) are hardcoded inline at task_routes.py:96-100 and 113-114 (and again at 167-170, 181-184 in `update_task`), even though `utils/helpers.py:110-116` already defines `MIN_TITLE_LENGTH`, `MAX_TITLE_LENGTH`, and a priority-adjacent set of constants that are never imported or used anywhere.
Impact: The business rule ("titles must be 3-200 chars", "priority is 1-5") is duplicated as raw literals in at least two places per rule; changing the rule means hunting down every literal instead of editing one constant, and the constants that were clearly meant for this purpose sit dead in `utils/helpers.py`.
Recommendation: Import and use the existing `MIN_TITLE_LENGTH`/`MAX_TITLE_LENGTH` constants (and add equivalent ones for priority bounds) instead of repeating literals.

### [LOW] Dead Code / Unused Abstraction — NotificationService
File: services/notification_service.py:1-48
Description: `NotificationService` (with `send_email`, `notify_task_assigned`, `notify_task_overdue`, `get_notifications`) is a fully implemented class that is never imported or instantiated anywhere in the codebase (confirmed via project-wide grep for `NotificationService`/`notification_service` — the only hit is its own definition).
Impact: A whole layer of "working" code (and its hardcoded SMTP credential, flagged separately as CRITICAL) sits unused, misleading anyone who assumes task assignment/overdue notifications are actually sent.
Recommendation: Either wire it into `create_task`/the overdue check (after fixing its hardcoded credentials and adding dependency injection for the SMTP client), or delete the file if notifications are out of scope.

### [LOW] Dead Code / Unused Abstractions — utils/helpers.py
File: utils/helpers.py:9-116
Description: Of the nine helpers/constant-blocks defined in this file, only `format_date` and `calculate_percentage` (lines 9-17) are even imported anywhere (routes/report_routes.py:7) — and that import is itself unused (see the Fat Controller finding; report_routes.py recomputes both inline instead of calling them). `validate_email` (19-23), `sanitize_string` (25-29), `generate_id` (31-34), `log_action` (36-41), `is_valid_color` (52-55), `process_task_data` (57-108), and the constants block (`VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`, 110-116) have zero references anywhere outside this file.
Impact: This is effectively a second, unused validation/serialization layer that duplicates logic already reimplemented (worse, inline and inconsistently) in the route handlers — dead weight that also hides the fact that no single source of truth for validation actually exists.
Recommendation: Either delete the unused functions/constants, or — preferably — make them the single source of truth by having every route call `process_task_data`/`validate_email`/the shared constants instead of re-deriving the same checks inline.

================================
Total: 22 findings
================================
