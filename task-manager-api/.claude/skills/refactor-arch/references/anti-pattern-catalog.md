# Anti-Pattern Catalog (Phase 2)

Cross-reference the codebase against every entry below. For each hit, record the exact file and line range — "bad code" is not a finding, `models.py:47-50` is. Severity follows the project's fixed scale:

- **CRITICAL** — breaks correct operation, exposes sensitive data (hardcoded credentials, SQL injection), or completely violates separation of concerns (a God Class holding DB + heavy logic + routing together).
- **HIGH** — strong MVC/SOLID violations that badly hurt maintainability/testability (heavy business logic stuck in Controllers, tight coupling with no dependency injection, mutable global state used app-wide).
- **MEDIUM** — standardization problems, duplication, or moderate performance bottlenecks (N+1 queries, misused middleware, missing route validation).
- **LOW** — readability improvements, bad variable naming, stray magic numbers.

This catalog is not exhaustive — if you find a real problem that doesn't map cleanly to an entry below, still report it and assign the severity that best matches the definitions above.

## CRITICAL

### 1. SQL Injection via string concatenation/interpolation
**Detection**: a SQL string built with `+`, f-strings, or template literals that splice in a request-derived value, e.g. `"SELECT * FROM x WHERE id = " + str(id)` or `` `SELECT * FROM x WHERE id = ${id}` `` fed straight into `execute()`/`query()`. Also flag string-built `INSERT`/`UPDATE` with user data spliced into the literal.
**Why it's critical**: any value from `request.args`, `request.get_json()`, `req.body`, or `req.params` reaching this string lets an attacker read/modify/delete arbitrary data.

### 2. Hardcoded credentials / secrets
**Detection**: `SECRET_KEY = "..."`, `password = "..."`, API keys, DB passwords, or SMTP credentials as literal strings in source (not read from env/config). Also flag secrets echoed back in an HTTP response (e.g. a `/health` endpoint that returns the secret key).
**Why it's critical**: anyone with source access (or, worse, anyone hitting an endpoint that echoes it) has full credentials.

### 3. God Class / God File
**Detection**: a single file or class that mixes database access, business logic, and route/wiring setup for multiple unrelated domains. Signals: file size well beyond its neighbors, a class with both an `initDb()`/schema-creation method and a `setupRoutes()`/handler method, or a `models.py` that has both raw SQL and response-shaping logic for 3+ entities.
**Why it's critical**: nothing in the file can be tested or changed in isolation; one change risks breaking unrelated features.

### 4. Unauthenticated destructive/admin endpoint
**Detection**: any route that deletes data, resets state, or executes arbitrary input (e.g. `/admin/reset-db`, `/admin/query` that runs raw SQL from the request body, a `DELETE /users/:id` with no auth check) with no authentication/authorization guard before the handler runs.
**Why it's critical**: it's a fully open door to destroy or exfiltrate data.

### 5. Weak or homegrown password "encryption"
**Detection**: unsalted `hashlib.md5(...)`/`hashlib.sha1(...)` for passwords, or a custom function that isn't a real cryptographic hash at all (e.g. a loop of base64 encoding branded as "crypto"), or passwords stored in plaintext.
**Why it's critical**: a DB leak turns instantly into a full credential leak; MD5/SHA1 are already broken for this use, and homegrown schemes are trivially reversible.

## HIGH

### 6. Fat Controller / business logic in the route layer
**Detection**: a route handler or controller function that itself computes discounts, validates cross-entity business rules, loops over collections to aggregate totals, etc., instead of delegating to a model/service and just shaping the HTTP response.
**Why it matters**: business rules can't be unit-tested without spinning up the whole HTTP layer, and the same rule tends to get re-implemented (and drift) in multiple handlers.

### 7. Tight coupling / no dependency injection
**Detection**: a module reaches directly for a global singleton connection, imports a concrete class and instantiates it inline deep inside business logic, or a class constructs its own dependencies (`this.db = new sqlite3.Database(...)` inside the class that also contains the business logic) rather than receiving them.
**Why it matters**: nothing can be swapped for a test double; every consumer is silently coupled to one specific implementation.

### 8. Mutable global state
**Detection**: a module-level mutable dict/object/counter (`let globalCache = {}`, a global `db_connection` reassigned by a getter) that many unrelated request handlers read and write.
**Why it matters**: request handling stops being safe/predictable under concurrency, and behavior becomes dependent on call order.

### 9. Forgeable / predictable auth tokens
**Detection**: a "token" built by string concatenation (e.g. `'fake-jwt-token-' + user.id`), or any auth scheme where the token can be derived from public information instead of being cryptographically signed/verified.
**Why it matters**: anyone can forge a valid-looking token for any user id — this is not actually authentication.

## MEDIUM

### 10. N+1 queries
**Detection**: a query run once, followed by a loop that runs another query per row (e.g. fetch all orders, then `SELECT ... WHERE order_id = ?` inside the loop for each one; or `User.query.get(t.user_id)` called inside a loop over tasks).
**Why it matters**: response time grows linearly with row count instead of being close to constant; it's invisible with seed data and painful in production.

### 11. Missing input validation at the route boundary
**Detection**: a handler reads `request.get_json()`/`req.body` and passes fields straight into a query or model without checking type, range, or required-ness (beyond a bare "is it present" check the assignment already expects — look for the *absence* of any check on numeric ranges, enums, formats).
**Why it matters**: malformed or malicious input reaches the data layer unchecked.

### 12. No structured logging / no centralized error handling
**Detection**: `print(...)`/`console.log(...)` used as the only diagnostic output, and every handler wrapping itself in its own `try/except`/`try/catch` that duplicates the same "log and return 500" logic instead of one shared error handler.
**Why it matters**: errors aren't queryable/aggregable in production, and the duplicated try/catch is copy-paste debt.

### 13. Missing pagination on list endpoints
**Detection**: a `GET` collection endpoint (`/tasks`, `/users`, `/produtos`) that always does `Model.query.all()` / `SELECT *` with no `limit`/`offset`/`page` support.
**Why it matters**: response size and query cost grow unbounded with data volume.

### 14. Deletes that break referential integrity
**Detection**: a `DELETE` handler that removes a row without also removing or reassigning rows that reference it by foreign key (orphaned children left behind — sometimes admitted in a comment).
**Why it matters**: the DB accumulates orphaned rows that later reads may crash on or silently misreport.

### 15. Deprecated API usage
**Detection** — check the manifest's pinned versions and grep for these concrete patterns (this list is a starting point, not exhaustive — always check the actual installed/pinned version against the framework's changelog too):

| Pattern found | Deprecated since | Modern replacement |
|---|---|---|
| `datetime.utcnow()` / `datetime.utcfromtimestamp()` (Python) | Python 3.12 | `datetime.now(timezone.utc)` |
| Flask `app.run(debug=True)` left on for what looks like a production entry point | — (security anti-pattern, not a version deprecation) | Run via a production WSGI server (gunicorn/uwsgi) with `debug=False`, gate debug on an env var |
| Node `new Buffer(...)` | Node 6 / deprecated fully in later Node | `Buffer.from(...)` |
| Bare Node callback-style API where a Promise-based version exists in the same library (e.g. `fs.readFile` callback style in a codebase that otherwise uses `async/await`) | library-specific | `fs.promises.*` / `util.promisify` |
| SQLAlchemy `Model.query.get(id)` in newer SQLAlchemy releases | SQLAlchemy 2.0 (legacy Query API) | `db.session.get(Model, id)` |
| Express body parsing via a separate `body-parser` package | Express 4.16+ | built-in `express.json()` |

Report this as its own finding (severity MEDIUM, or LOW if the API still works fine and just has a newer idiom) whenever a pattern above — or an equivalent one you find via version-aware research — actually appears in the code.

## LOW

### 16. Duplicated code
**Detection**: two functions/handlers with near-identical bodies (same loop shape, same field list) that differ only in a filter or a name — a copy-paste that should be one parametrized function.

### 17. Magic numbers
**Detection**: unexplained literal numbers driving business rules (discount thresholds, pagination sizes, retry counts) with no named constant.

### 18. Poor naming
**Detection**: single-letter or meaningless variable names (`u`, `e`, `p`, `cc`) for anything beyond a tiny local loop index, especially in code carrying business meaning (a card number, a user object).

### 19. Dead code / unused imports and unused abstractions
**Detection**: imports never referenced in the file, or a helper function that's fully implemented but never called anywhere (grep its name across the whole project to confirm zero call sites before reporting).

### 20. Overly broad exception handling
**Detection**: a bare `except:` (Python) or an empty/ignored `catch` that swallows every error class, hiding real bugs behind a generic "something went wrong" response.
