================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express ^4.18.2, sqlite3 ^5.1.6 (in-memory)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 7 | HIGH: 4 | MEDIUM: 6 | LOW: 4

## Findings

### [CRITICAL] God Class / God File
File: src/AppManager.js:4-139
Description: `AppManager` is a single class whose constructor opens the raw DB connection (5-8), whose `initDb()` creates the entire schema and seeds data for 5 unrelated tables (10-23), and whose `setupRoutes(app)` defines all 3 HTTP routes with checkout payment processing, nested-callback enrollment logic, and admin report aggregation inlined directly in the handlers (25-138). There is no models/, routes/, services/, or controllers/ separation anywhere in the project.
Impact: Nothing in this file can be unit-tested or changed in isolation — touching the checkout flow risks silently breaking the admin report or the DB bootstrap. New contributors must read the entire file to make any change safely.
Recommendation: Split into a data layer (models per entity: User, Course, Enrollment, Payment), a service/business layer (checkout service, reporting service), and thin route controllers that only translate HTTP <-> service calls, per the standard MVC playbook pattern.

### [CRITICAL] Broken Authentication — Password Never Verified on Checkout
File: src/AppManager.js:40-76
Description: When `POST /api/checkout` looks up an existing user by email (`SELECT id FROM users WHERE email = ?`, line 40), it only checks whether a row exists. If `user` is found, it goes straight to `processPaymentAndEnroll(user.id)` (line 74) without ever comparing the submitted `p` (password) against the stored `pass` hash. The `pass` column and `badCrypto` hash are only ever used when *creating* a brand-new user (line 68); an existing account's password is never checked again.
Impact: Anyone who knows (or guesses) a registered user's email can enroll that user in courses and trigger a payment on their behalf, with zero credential verification. This is a full account-takeover / impersonation path on the checkout flow.
Recommendation: On the existing-user branch, fetch the stored password hash and verify it against the submitted password using a real password-hashing library (e.g., bcrypt/argon2) before calling `processPaymentAndEnroll`; reject with 401 on mismatch.

### [CRITICAL] Sensitive Data Logged in Plaintext
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` prints the full raw card value submitted by the client and the live payment-gateway secret key to stdout on every checkout request.
Impact: Card data and the payment gateway's live secret key end up in process logs, which are commonly shipped to log aggregators, crash dumps, or CI output — turning a routine checkout into a PCI-scope data leak and a credential leak simultaneously.
Recommendation: Never log raw card numbers or secrets; log a masked/last-4 representation (or nothing) and remove the secret key from any log line entirely. Route diagnostic output through a structured logger with a redaction policy.

### [CRITICAL] Unauthenticated Admin Endpoint
File: src/AppManager.js:80-129
Description: `GET /api/admin/financial-report` returns full revenue and per-student payment data for every course with no authentication or authorization check before the handler runs.
Impact: Any unauthenticated caller can pull the entire business's financial report, including which students paid what for which course — a full confidential-data exfiltration path.
Recommendation: Add an authentication/authorization middleware (admin-role check) in front of this route before any other change; the route must reject unauthenticated requests with 401/403.

### [CRITICAL] Unauthenticated Destructive Endpoint
File: src/AppManager.js:131-137
Description: `DELETE /api/users/:id` deletes a user row directly from the `users` table with no authentication/authorization guard at all — any caller who knows or guesses an id can delete any account.
Impact: A fully open door to destroy arbitrary user data with a single unauthenticated HTTP call.
Recommendation: Require authentication and authorization (the requester must be the account owner or an admin) before executing the delete; return 401/403 otherwise.

### [CRITICAL] Hardcoded Credentials / Secrets
File: src/utils.js:1-7
Description: The `config` object hardcodes a DB admin username/password (`dbUser`/`dbPass`), a live payment-gateway API key (`paymentGatewayKey: "pk_live_1234567890abcdef"`), and an SMTP user, all as literal strings committed to source.
Impact: Anyone with source/repo access has production-grade credentials, including a live payment key that could be used to move real money or impersonate the service with the payment processor.
Recommendation: Move every secret to environment variables (or a secrets manager), read them via `process.env`, and rotate the exposed `pk_live_...` key immediately since it has already been committed to source.

### [CRITICAL] Weak/Homegrown Password "Encryption"
File: src/utils.js:17-23
Description: `badCrypto(pwd)` is not a real cryptographic hash — it repeatedly base64-encodes the raw password and concatenates truncated slices of the result 10,000 times, then truncates to 10 characters. Since base64 is a reversible encoding, not a one-way function, the "hash" leaks the original password. It is used at src/AppManager.js:68 to store new users' passwords, and falls back to the hardcoded default `"123456"` when no password is submitted.
Impact: A DB leak turns instantly into a full plaintext-password leak because the transform is trivially reversible (it's not even a real digest); the hardcoded `"123456"` fallback also means any checkout with no password creates a guessable account.
Recommendation: Replace `badCrypto` with a real, salted password hash (bcrypt/argon2/scrypt) and require an explicit password instead of silently defaulting to `"123456"`.

### [HIGH] Tight Coupling / No Dependency Injection
File: src/AppManager.js:5-8
Description: The `AppManager` constructor directly instantiates its own concrete DB dependency (`this.db = new sqlite3.Database(':memory:')`) inside the exact same class that also holds all the business logic and route wiring.
Impact: The DB connection can never be swapped for a test double or a different implementation; every consumer of `AppManager` is silently and permanently coupled to this one in-memory SQLite instance, making unit testing of business logic impossible without a real DB.
Recommendation: Inject the DB connection (or a repository built on top of it) into `AppManager`/services via the constructor, so tests can pass a mock/fake.

### [HIGH] Fat Controller — Checkout Business Logic in the Route Handler
File: src/AppManager.js:28-78
Description: The `POST /api/checkout` handler itself decides payment approval (`cc.startsWith("4") ? "PAID" : "DENIED"` at line 46), creates users, hashes passwords, inserts enrollments, inserts payments, and writes audit logs — all inline in the Express callback instead of delegating to a service layer.
Impact: None of this business logic (payment decisioning, enrollment rules) can be unit-tested without spinning up the full HTTP layer and an in-memory DB; the same rules will tend to be re-implemented and drift if reused elsewhere.
Recommendation: Extract a `CheckoutService`/`PaymentService` that owns the payment-approval rule and enrollment/payment persistence; the route handler should only parse the request, call the service, and shape the HTTP response.

### [HIGH] Fat Controller — Financial Report Aggregation in the Route Handler
File: src/AppManager.js:80-129
Description: The `GET /api/admin/financial-report` handler builds the report shape, accumulates `courseData.revenue += payment.amount`, and tracks per-course completion counters (`coursesPending`, `enrPending`) directly inside the route callback.
Impact: The revenue-aggregation rule is untestable in isolation and tightly bound to the specific nested-callback control flow, making it fragile to change.
Recommendation: Move the aggregation into a reporting service/repository method that returns the shaped report; the route should only call it and return the JSON.

### [HIGH] Mutable Global State
File: src/utils.js:9-15
Description: `globalCache` (a module-level mutable object, line 9) and `totalRevenue` (a module-level mutable counter, line 10) are declared at module scope and exported. `logAndCache` (12-15) mutates `globalCache` as a side effect, and it is called from a completely different module (`src/AppManager.js:59`) on every successful checkout.
Impact: Request handling is no longer safe or predictable under concurrency — any handler anywhere in the app can read/write this shared state, so behavior becomes dependent on call order and is invisible to reason about from any single call site.
Recommendation: Replace the module-level cache with an explicit, injected cache/store (or remove it if genuinely unused) rather than a shared mutable module export.

### [MEDIUM] No Centralized Error Handling / No Structured Logging
File: src/AppManager.js:28-137
Description: Every DB callback re-implements its own ad-hoc "if (err) return res.status(500).send(...)" logic (e.g. lines 38, 41, 48, 51, 55, 84) instead of funneling into one shared Express error handler, and the only diagnostic output anywhere in the app is `console.log` (line 45, and `src/utils.js:13`).
Impact: Errors aren't queryable/aggregable in production, and the duplicated error-shaping logic is copy-paste debt that will drift as handlers evolve independently.
Recommendation: Add a centralized Express error-handling middleware and pass errors to it (`next(err)`) instead of duplicating `res.status(500)` in every callback; replace `console.log` with a structured logger.

### [MEDIUM] Missing Input Validation at Route Boundary — Checkout Payload
File: src/AppManager.js:29-35
Description: `POST /api/checkout` reads `usr`, `eml`, `pwd`, `c_id`, `card` straight from `req.body` and only checks bare presence (`if (!u || !e || !cid || !cc)`). There is no validation that `cid` is a valid integer/id, that `card` matches a plausible card-number format/length, or that `eml` is a well-formed email.
Impact: Malformed or malicious input (non-numeric course id, garbage card string, malformed email) reaches the data layer and business logic unchecked, producing confusing 404/500s or silently wrong behavior instead of a clear 400.
Recommendation: Add schema validation (e.g., a validation middleware/library) at the route boundary that checks types, formats, and required-ness before any DB call runs.

### [MEDIUM] Missing Pagination on List Endpoint
File: src/AppManager.js:80-129
Description: `GET /api/admin/financial-report` always loads every course, every enrollment per course, and every user/payment per enrollment with no `limit`/`offset`/`page` support of any kind.
Impact: Response size and query cost grow unbounded with the number of courses/enrollments; this is invisible with the current seed data (2 courses, 1 enrollment) and will degrade badly in production.
Recommendation: Add pagination (limit/offset or cursor-based) to the report query, or at minimum paginate the outer `courses` loop.

### [MEDIUM] N+1 Queries in Financial Report
File: src/AppManager.js:83-126
Description: The handler runs one query for all courses (83), then inside `courses.forEach` runs a separate `enrollments` query per course (92), and inside that `enrollments.forEach` runs a separate `users` query (104) and a separate `payments` query (106) per enrollment — a triple-nested N+1 pattern.
Impact: Response time grows linearly (actually closer to O(courses × enrollments)) with data volume instead of a small constant number of queries; this will not show up with seed data but will be severe under real load.
Recommendation: Replace the nested per-row queries with a small number of JOINed queries (courses ⋈ enrollments ⋈ users ⋈ payments) and assemble the report in memory from the joined result set.

### [MEDIUM] Missing Input Validation at Route Boundary — Delete Id Param
File: src/AppManager.js:131-133
Description: `DELETE /api/users/:id` takes `req.params.id` and passes it straight into the query with no check that it's a valid numeric id, and no check that a matching user actually exists before reporting success.
Impact: Non-numeric or nonsensical ids are silently accepted and produce a misleading "deleted" response regardless of whether anything was actually deleted.
Recommendation: Validate `id` is a positive integer at the route boundary, and check the delete actually affected a row (`this.changes`) before returning a success response.

### [MEDIUM] Deletes That Break Referential Integrity
File: src/AppManager.js:131-137
Description: `DELETE /api/users/:id` removes the `users` row only; it never removes or reassigns the user's `enrollments` or `payments` rows. The response literally admits this: `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."`
Impact: The DB accumulates orphaned `enrollments`/`payments` rows referencing a deleted user, which the financial report (and any future read) may crash on or silently misreport (e.g. "Unknown" students already appearing in the report logic at line 113).
Recommendation: Cascade the delete (remove/anonymize dependent `enrollments` and `payments` in the same transaction) or soft-delete the user instead of hard-deleting while dependents remain.

### [LOW] Dead Code / Unused Import
File: src/AppManager.js:2
Description: `totalRevenue` is destructured from `require('./utils')` but is never referenced anywhere else in the file — confirmed via a full-project grep with zero other call/read sites besides its declaration and export in `src/utils.js`.
Impact: Dead import adds confusion about what state the class actually depends on and suggests an abandoned/incomplete feature (a revenue counter that's never updated or read).
Recommendation: Remove the unused import, or, if a running revenue total is actually wanted, wire it up properly instead of leaving a half-finished global.

### [LOW] Poor Naming
File: src/AppManager.js:29-33
Description: The checkout handler destructures request fields into single/near-meaningless letter names: `u` (username), `e` (email), `p` (password), `cid` (course id), `cc` (credit card) — `cc` in particular holds a raw card number, i.e. business-critical/sensitive data hidden behind a two-letter name.
Impact: Reduces readability and increases the chance of mixing up fields (e.g. confusing `p` for something else) in a code path that already handles payments and PII.
Recommendation: Rename to descriptive identifiers (`username`, `email`, `password`, `courseId`, `cardNumber`).

### [LOW] Magic Numbers — Card Approval Rule
File: src/AppManager.js:46
Description: `let status = cc.startsWith("4") ? "PAID" : "DENIED";` hardcodes the business rule "cards starting with 4 are approved" as a bare string literal with no named constant or explanation.
Impact: The approval rule's meaning (Visa-prefix heuristic used as a stand-in for real payment processing) is not documented anywhere and is easy to miss or misread as a real integration.
Recommendation: Extract into a named constant/function (e.g. `isApprovedTestCard(cardNumber)`) or, more importantly, replace the fake check with a real payment-gateway integration.

### [LOW] Magic Numbers — badCrypto Constants
File: src/utils.js:17-23
Description: The loop bound `10000` (line 19) and the slice lengths `substring(0, 2)` (line 20) and `substring(0, 10)` (line 22) are unexplained literals with no named constants, on top of `badCrypto` already being flagged as cryptographically unsound.
Impact: Even setting aside the crypto weakness, the numbers give no hint of intent, making the function harder to review or safely modify.
Recommendation: Replace with named constants once the function itself is replaced by a real hashing library (see the CRITICAL weak-crypto finding).

================================
Total: 21 findings
================================
