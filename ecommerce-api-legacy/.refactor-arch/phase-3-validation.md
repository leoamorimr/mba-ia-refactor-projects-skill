================================
PHASE 3 — REFACTOR VALIDATION REPORT
================================
Project: ecommerce-api-legacy
Stack:    Node.js + Express ^4.18.2, sqlite3 ^5.1.6 (in-memory), bcryptjs, zod, dotenv

## 1. New directory structure

The flat 3-file god-file setup (`src/app.js`, `src/AppManager.js`, `src/utils.js`) was
replaced with a layered MVC structure using Node/Express folder conventions.
`src/AppManager.js` and `src/utils.js` were deleted; every responsibility they held
was moved into the layers below.

```
ecommerce-api-legacy/
├── .env.example              # documents every env var; no secrets committed
├── .gitignore                 # node_modules/, .env
├── api.http                   # updated with pwd field + x-admin-key examples
├── package.json               # + bcryptjs, dotenv, zod
├── README.md                  # documents admin auth header
└── src/
    ├── app.js                 # composition root: wiring only
    ├── config/
    │   ├── index.js           # env-based settings (port, secrets, admin key, bcrypt rounds)
    │   └── database.js        # sole owner of the sqlite3 connection; promisified
    │                          # run/get/all + transaction() helper; schema + seed
    ├── models/                 # data access only, one file per entity
    │   ├── userModel.js
    │   ├── courseModel.js
    │   ├── enrollmentModel.js
    │   ├── paymentModel.js
    │   └── auditLogModel.js
    ├── controllers/            # orchestration / business rules
    │   ├── checkoutController.js
    │   ├── financialReportController.js
    │   └── userController.js
    ├── routes/                 # routing + response shaping only
    │   ├── index.js
    │   ├── checkoutRoutes.js
    │   ├── adminRoutes.js
    │   └── userRoutes.js
    ├── middlewares/
    │   ├── auth.js             # requireAdmin (shared-secret admin guard)
    │   ├── errorHandler.js     # single centralized error handler
    │   └── validators.js       # zod schemas for checkout / id param / report query
    ├── services/
    │   ├── paymentService.js   # card-approval rule + card masking
    │   ├── passwordService.js  # bcrypt hash/verify
    │   └── cacheService.js     # injectable cache (replaces global mutable cache)
    └── utils/
        ├── errors.js           # AppError + typed subclasses (404/401/400)
        └── logger.js           # structured JSON logger (replaces console.log)
```

## 2. Authentication mechanism (new — project had none)

There was no auth system at all in the legacy code. The simplest mechanism that
actually enforces authorization was implemented: a **shared-secret API key** checked
by the `requireAdmin` middleware (`src/middlewares/auth.js`) against `config.adminApiKey`
(env var `ADMIN_API_KEY`, dev-only default `dev-only-insecure-admin-key`, documented in
`.env.example` and `README.md`).

**How to authenticate as admin:** send header `x-admin-key: <ADMIN_API_KEY>` on any
request to:
- `GET /api/admin/financial-report`
- `DELETE /api/users/:id`

Missing or wrong key → `401 Unauthorized` with `{"error":"Unauthorized: valid x-admin-key header required"}`.

Checkout authentication (separate from the admin guard) is now a real password check:
existing users must submit the correct password (verified with bcrypt against the
stored hash); new users' passwords are hashed with bcrypt (no more silent `"123456"`
default).

## 3. Findings → fix mapping (21/21)

| # | Severity | Finding | Fix applied |
|---|----------|---------|-------------|
| 1 | CRITICAL | God Class / God File | Split `AppManager.js` into `models/` (5 files, data only), `controllers/` (3 files, orchestration), `routes/` (4 files, routing), `config/database.js` (connection/schema/seed), `services/` (payment/password/cache), `middlewares/` (auth/error/validation). |
| 2 | CRITICAL | Broken auth — password never verified on checkout | `checkoutController.resolveUserId` now calls `passwordService.verifyPassword` against the stored hash for existing users and throws `UnauthorizedError` (401) on mismatch; verified live in test 3 below. |
| 3 | CRITICAL | Sensitive data logged in plaintext (card + gateway secret) | Removed the `console.log` line entirely; `checkoutController` now logs via the structured `logger` with `paymentService.maskCard()` — only `**** **** **** 4444` is ever logged, never the gateway key. Verified in boot log (section 5). |
| 4 | CRITICAL | Unauthenticated admin endpoint | `GET /api/admin/financial-report` now requires `requireAdmin` middleware; unauthenticated calls get 401 (verified in test 5). |
| 5 | CRITICAL | Unauthenticated destructive delete endpoint | `DELETE /api/users/:id` now requires `requireAdmin`; unauthenticated calls get 401 (verified in test 7). |
| 6 | CRITICAL | Hardcoded credentials/secrets | `src/utils.js`'s literal `config` object removed; `src/config/index.js` reads every secret from `process.env`, with clearly-labeled `dev-only-*` fallbacks for local dev only. The exposed `pk_live_1234567890abcdef` key is gone from source; flagging again here that it must be rotated with the real payment gateway since it was previously committed. |
| 7 | CRITICAL | Weak/homegrown password hashing (`badCrypto`) | Replaced with `bcryptjs` (`passwordService.hashPassword`/`verifyPassword`), salted, configurable rounds via `BCRYPT_SALT_ROUNDS`. The `"123456"` silent default is gone — password is now a required, validated field for both new and existing users. |
| 8 | HIGH | Tight coupling / no DI | DB connection instantiation lives solely in `config/database.js` (composition root concern); `checkoutController` is a factory (`createCheckoutController({ cacheService })`) that receives its cache dependency via injection instead of importing a shared mutable module. |
| 9 | HIGH | Fat controller — checkout logic in route handler | All checkout orchestration moved to `controllers/checkoutController.js`; `routes/checkoutRoutes.js` only validates, calls the controller, and shapes the response. |
| 10 | HIGH | Fat controller — financial report aggregation in route handler | Aggregation moved to `controllers/financialReportController.js`; the route only calls it and returns JSON. |
| 11 | HIGH | Mutable global state (`globalCache`/`totalRevenue`) | Replaced with `services/cacheService.js`, a class instantiated once in the composition root (`app.js`) and injected into the checkout controller — no module-level mutable export. |
| 12 | MEDIUM | No centralized error handling / no structured logging | Added `middlewares/errorHandler.js` registered last in `app.js`; introduced typed `AppError` subclasses (`utils/errors.js`) that map to status codes; replaced all `console.log` diagnostics with `utils/logger.js` (structured JSON lines). |
| 13 | MEDIUM | Missing input validation — checkout payload | `middlewares/validators.js` (`validateCheckout`, zod schema) checks types/formats for `usr`, `eml` (valid email), `pwd`, `c_id` (positive int), `card` (13–19 digits) before any DB call. |
| 14 | MEDIUM | Missing pagination on financial report | `validateReportQuery` accepts optional `page`/`limit` query params (default `page=1`, `limit=50`, max `100`); `courseModel.listPage` applies `LIMIT`/`OFFSET` to the outer course list. |
| 15 | MEDIUM | N+1 queries in financial report | `financialReportController.getReport` now runs 4 queries total regardless of data volume (1 for courses, 1 batched `IN (...)` for enrollments, 2 parallel batched `IN (...)` for payments/users) instead of `1 + N + 2N`. |
| 16 | MEDIUM | Missing input validation — delete id param | `validateUserIdParam` (zod) requires `id` to be a positive integer before the controller runs; non-numeric ids now get 400 instead of silently reaching the query. |
| 17 | MEDIUM | Deletes that break referential integrity | `userController.deleteUser` wraps `paymentModel.deleteByEnrollmentUserId`, `enrollmentModel.deleteByUserId`, and `userModel.deleteById` in one `database.transaction()`; dependents are removed atomically with the user. Verified live in the post-delete report sanity check (section 5) — no orphaned/"Unknown" rows. |
| 18 | LOW | Dead code (`totalRevenue`) | Removed entirely; not carried into any new module. |
| 19 | LOW | Poor naming (`u`, `e`, `p`, `cid`, `cc`) | Wire format (`usr`/`eml`/`pwd`/`c_id`/`card`) preserved for API compatibility, but `validateCheckout` maps them to descriptive names (`username`, `email`, `password`, `courseId`, `cardNumber`) used everywhere downstream. |
| 20 | LOW | Magic number — card approval rule | Extracted to `paymentService.APPROVED_TEST_CARD_PREFIX` with a comment documenting it's a test-card stand-in for a real gateway integration. |
| 21 | LOW | Magic numbers — `badCrypto` constants | Moot: `badCrypto` itself was deleted and replaced by bcrypt (finding #7); no unexplained loop-bound/substring literals remain. |

## 4. Dependencies added

Added to `package.json` and installed via `npm install` (194 packages, 0 install errors):
- `bcryptjs` — pure-JS bcrypt-compatible hashing (avoids native build issues, same API/algorithm as `bcrypt`)
- `dotenv` — loads `.env` for local development
- `zod` — schema validation at route boundaries

`sqlite3` and `express` versions unchanged.

## 5. Boot verification

```
$ npm start
> desafio-arquitetura-ia-boilerplate@1.0.0 start
> node src/app.js

{"level":"info","message":"Database seeded with initial data","timestamp":"2026-08-09T17:51:34.240Z"}
{"level":"info","message":"Frankenstein LMS rodando na porta 3000...","timestamp":"2026-08-09T17:51:34.243Z"}
```

App booted cleanly on port 3000 (no `.env` present — all config used the labeled
dev-only defaults). No errors, no stack traces.

## 6. Endpoint-by-endpoint validation (live curl requests)

### 6.1 Checkout — new user (should succeed)
```bash
curl -s -i -X POST http://localhost:3000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
```
Result: `HTTP/1.1 200 OK`
```json
{"msg":"Sucesso","enrollment_id":2}
```
Matches original happy-path shape (`{msg, enrollment_id}`).

### 6.2 Checkout — existing user + correct password (should succeed)
```bash
curl -s -i -X POST http://localhost:3000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Leonan","eml":"leonan@fullcycle.com.br","pwd":"123","c_id":2,"card":"4111222233334444"}'
```
Result: `HTTP/1.1 200 OK`
```json
{"msg":"Sucesso","enrollment_id":3}
```
The seeded user `leonan@fullcycle.com.br` has password `123` (hashed with bcrypt at
seed time so the check is real, not bypassed).

### 6.3 Checkout — existing user + wrong password (should now reject, unlike before)
```bash
curl -s -i -X POST http://localhost:3000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{"usr":"Leonan","eml":"leonan@fullcycle.com.br","pwd":"wrongpass","c_id":2,"card":"4111222233334444"}'
```
Result: `HTTP/1.1 401 Unauthorized`
```json
{"error":"Credenciais inválidas"}
```
Confirms the broken-authentication finding is fixed — this previously succeeded
silently with zero credential verification.

### 6.4 Admin financial report — no credentials (should now 401, unlike before)
```bash
curl -s -i http://localhost:3000/api/admin/financial-report
```
Result: `HTTP/1.1 401 Unauthorized`
```json
{"error":"Unauthorized: valid x-admin-key header required"}
```

### 6.5 Admin financial report — with correct admin credentials (should succeed)
```bash
curl -s -i http://localhost:3000/api/admin/financial-report \
  -H "x-admin-key: dev-only-insecure-admin-key"
```
Result: `HTTP/1.1 200 OK`
```json
[
  {"course":"Clean Architecture","revenue":997,"students":[{"student":"Leonan","paid":997}]},
  {"course":"Docker","revenue":994,"students":[{"student":"Guilherme","paid":497},{"student":"Leonan","paid":497}]}
]
```
Matches original happy-path shape (`[{course, revenue, students:[{student, paid}]}]`),
correctly reflecting the two checkouts from 6.1/6.2.

### 6.6 Delete user — no credentials (should now 401, unlike before)
```bash
curl -s -i -X DELETE http://localhost:3000/api/users/1
```
Result: `HTTP/1.1 401 Unauthorized`
```json
{"error":"Unauthorized: valid x-admin-key header required"}
```

### 6.7 Delete user — with admin credentials (should succeed)
```bash
curl -s -i -X DELETE http://localhost:3000/api/users/1 \
  -H "x-admin-key: dev-only-insecure-admin-key"
```
Result: `HTTP/1.1 200 OK`
```
Usuário deletado com sucesso, incluindo matrículas e pagamentos associados.
```
Same response type (plain text, 200) as the original happy path; wording updated
because the original text literally admitted to leaving orphaned rows, which this
refactor fixes (see 6.8).

### 6.8 Sanity check — referential integrity after delete
```bash
curl -s -i http://localhost:3000/api/admin/financial-report -H "x-admin-key: dev-only-insecure-admin-key"
```
Result: `HTTP/1.1 200 OK`
```json
[
  {"course":"Clean Architecture","revenue":0,"students":[]},
  {"course":"Docker","revenue":497,"students":[{"student":"Guilherme","paid":497}]}
]
```
Leonan's enrollment/payment for "Clean Architecture" is gone along with the user —
no orphaned rows, no "Unknown" student entries, no crash. This confirms the
cascade-delete transaction worked.

### 6.9 Additional sanity checks (not required, run for extra confidence)
- Deleting the same user id again → `404 {"error":"Usuário não encontrado"}`.
- Checkout with a card not starting with `4` → `400 {"error":"Pagamento recusado"}`.
- Checkout with a non-existent course id → `404 {"error":"Curso não encontrado"}`.

## 7. Log output during the test run (no secrets/PII leaked)

```json
{"level":"info","message":"Database seeded with initial data",...}
{"level":"info","message":"Frankenstein LMS rodando na porta 3000...",...}
{"level":"info","message":"Processing checkout payment",...,"maskedCard":"**** **** **** 4444"}
{"level":"info","message":"Cache set",...,"key":"last_checkout_2"}
{"level":"info","message":"Processing checkout payment",...,"maskedCard":"**** **** **** 4444"}
{"level":"info","message":"Cache set",...,"key":"last_checkout_1"}
{"level":"warn","message":"Credenciais inválidas",...,"statusCode":401,"path":"/api/checkout"}
{"level":"warn","message":"Unauthorized: valid x-admin-key header required",...,"statusCode":401,"path":"/api/admin/financial-report"}
{"level":"warn","message":"Unauthorized: valid x-admin-key header required",...,"statusCode":401,"path":"/api/users/1"}
{"level":"warn","message":"Usuário não encontrado",...,"statusCode":404,"path":"/api/users/1"}
{"level":"info","message":"Processing checkout payment",...,"maskedCard":"**** **** **** 4444"}
{"level":"warn","message":"Pagamento recusado",...,"statusCode":400,"path":"/api/checkout"}
{"level":"warn","message":"Curso não encontrado",...,"statusCode":404,"path":"/api/checkout"}
```
No raw card number and no `paymentGatewayKey` value appear anywhere in the log —
only the masked last-4 digits, confirming finding #3 is fixed.

## 8. Process cleanup

The background server was stopped after validation (`pkill -f "node src/app.js"`);
confirmed no `node src/app.js` process remained running.

## 9. Known deviations from the original contract (intentional, per task scope)

- `POST /api/checkout`: an existing user with no/wrong password, or a new user with
  no password, now gets `400`/`401` instead of silently succeeding with a default
  `"123456"` password — this is the fix for findings #2 and #7, not a regression.
- `GET /api/admin/financial-report` and `DELETE /api/users/:id`: unauthenticated
  requests now get `401` instead of succeeding — this is the fix for findings #4/#5,
  not a regression.
- `DELETE /api/users/:id` success message text changed (see 6.7) because the original
  text described the very data-integrity bug this refactor fixes; status code and
  response type (plain text, 200) are unchanged.
- Error response bodies across all routes are now `{"error": "..."}` JSON instead of
  the original ad-hoc plain-text messages (e.g. `"Curso não encontrado"`, `"Erro DB"`).
  Only non-happy-path responses changed shape; the task's preservation requirement was
  scoped to happy-path shapes, and centralizing error shape was itself one of the
  MEDIUM findings (#12) to fix.

## 10. Summary

All 21 findings from the phase-2 audit were addressed with the matching (or
closest-intent) playbook transformation. The app boots cleanly, all three original
routes respond with their original happy-path shapes, and every previously-broken or
wide-open security path (checkout auth bypass, unauthenticated admin report,
unauthenticated destructive delete) now correctly rejects unauthenticated/invalid
requests while continuing to serve legitimate ones.
