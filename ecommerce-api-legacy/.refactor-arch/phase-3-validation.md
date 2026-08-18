================================
PHASE 3 — REFACTOR VALIDATION REPORT (follow-up round)
================================
Project: ecommerce-api-legacy
Stack:    Node.js + Express ^4.18.2, sqlite3 ^5.1.6 (in-memory), bcryptjs, zod, dotenv

This is a **targeted fix-up round**, not a restructuring pass. The project was
already in clean MVC shape from the prior refactor (`config/`, `controllers/`,
`middlewares/`, `models/`, `routes/`, `services/`, `utils/` under `src/`). No
folders were reorganized and no files were moved. The only job this round was
to apply the fix matching each of the 5 findings from `.refactor-arch/phase-2-audit.md`
(0 CRITICAL / 1 HIGH / 1 MEDIUM / 3 LOW).

## 1. Directory structure (unchanged in shape)

```
ecommerce-api-legacy/
├── .env.example
├── api.http
├── package.json
├── README.md
└── src/
    ├── app.js                     # composition root (unchanged)
    ├── config/
    │   ├── index.js               # MODIFIED — fail-fast on missing ADMIN_API_KEY,
    │   │                          #            unused fields removed
    │   └── database.js            # MODIFIED — getDb no longer exported publicly
    ├── models/
    │   ├── userModel.js           # MODIFIED — uses utils/query.findByIdsIn
    │   ├── courseModel.js         # unchanged
    │   ├── enrollmentModel.js     # MODIFIED — uses utils/query.findByIdsIn
    │   ├── paymentModel.js        # MODIFIED — uses utils/query.findByIdsIn,
    │   │                          #            PAYMENT_STATUS.DENIED removed
    │   └── auditLogModel.js       # unchanged
    ├── controllers/
    │   ├── checkoutController.js  # unchanged
    │   ├── financialReportController.js  # unchanged
    │   └── userController.js      # unchanged
    ├── routes/
    │   ├── index.js               # unchanged
    │   ├── checkoutRoutes.js      # unchanged
    │   ├── adminRoutes.js         # unchanged
    │   └── userRoutes.js          # MODIFIED — DELETE now returns JSON
    ├── middlewares/
    │   ├── auth.js                # unchanged
    │   ├── errorHandler.js        # unchanged
    │   └── validators.js          # MODIFIED — named pagination constants
    ├── services/                  # unchanged (paymentService, passwordService, cacheService)
    └── utils/
        ├── errors.js              # MODIFIED — BadRequestError removed
        ├── logger.js              # unchanged
        └── query.js               # NEW — shared findByIdsIn(table, column, ids, cols) helper
```

Only one new file was added (`src/utils/query.js`, a small shared helper — not a
new layer or a reorganization). No existing file was moved or renamed. `git status`
confirms: 9 modified files under `src/`, plus `.env.example`, `README.md`, `api.http`
updated for finding #1, and one untracked new file (`src/utils/query.js`).

## 2. Findings fixed (5/5)

| # | Severity | Finding | Fix applied |
|---|----------|---------|-------------|
| 1 | HIGH | `adminApiKey` fell back to the literal `'dev-only-insecure-admin-key'` when `ADMIN_API_KEY` unset; same value hardcoded in `README.md` and `api.http` | `src/config/index.js` now throws a clear `Error` at require-time if `process.env.ADMIN_API_KEY` is unset (checked immediately after `dotenv.config()`, so a local `.env` still satisfies it). `README.md` and `api.http` now show `<set-a-strong-admin-key>` instead of a real working value. `.env.example` documents `ADMIN_API_KEY` as REQUIRED with the same placeholder. |
| 2 | MEDIUM | `DELETE /api/users/:id` responded with `res.status(200).send(result.message)` (raw text) | `src/routes/userRoutes.js:13` changed to `res.status(200).json({ message: result.message })`. Verified live: response is now `{"message":"..."}` with `content-type: application/json`. |
| 3 | LOW | Dead code: `dbUser`/`dbPass`/`paymentGatewayKey`/`smtpUser` (config), `BadRequestError` (utils/errors.js), `PAYMENT_STATUS.DENIED` (paymentModel.js), `getDb` export (config/database.js) | Grepped the whole `src/` tree first to confirm zero references outside their own definitions before removing each. `dbUser`/`dbPass`/`paymentGatewayKey`/`smtpUser` fields deleted from `config/index.js` (and their env vars removed from `.env.example`). `BadRequestError` class + export deleted from `utils/errors.js`. `PAYMENT_STATUS.DENIED` deleted from `paymentModel.js` (only `PAID` remains, matching the only status the app ever writes). `getDb` is no longer in `database.js`'s `module.exports` — it remains as an internal, unexported helper since `run`/`get`/`all` still call it. |
| 4 | LOW | Near-identical "build placeholders + `SELECT ... WHERE col IN (...)`" logic duplicated in `enrollmentModel.js`, `paymentModel.js`, `userModel.js` | Extracted `findByIdsIn(table, column, ids, selectColumns)` into new `src/utils/query.js`. All three models' batch-lookup functions (`findByCourseIds`, `findByEnrollmentIds`, `findByIds`) now call it instead of re-implementing the placeholder-building logic. |
| 5 | LOW | Magic numbers `1`, `50`, `100` embedded in the pagination zod schema | `src/middlewares/validators.js` now defines `DEFAULT_REPORT_PAGE = 1`, `DEFAULT_REPORT_LIMIT = 50`, `MAX_REPORT_LIMIT = 100` near the top of the file, and `reportQuerySchema` references them instead of the inline literals. |

No CRITICAL findings this round, so no auth-gating work was needed or done.

## 3. Dependencies

No changes to `package.json` (none of the 5 fixes required a new dependency).
Ran `npm install` anyway to materialize `node_modules` for the boot test — 194
packages installed, 0 errors, `package-lock.json` unchanged.

## 4. Boot verification

### 4.1 Fail-fast check WITHOUT `ADMIN_API_KEY` set (the key regression test for finding #1)

```
$ env -i PATH="$PATH" HOME="$HOME" node src/app.js
/.../src/config/index.js:13
    throw new Error(
    ^

Error: Missing required environment variable ADMIN_API_KEY. Set it in your environment or in a local .env file before starting the app (see .env.example).
    at Object.<anonymous> (/.../src/config/index.js:13:11)
    ...
Node.js v22.22.1

$ echo $?
1
```

Confirmed: the app no longer silently starts with the insecure default — it now
fails fast at boot with a clear, actionable error message, and exits non-zero
before any server is opened.

### 4.2 Normal boot WITH `ADMIN_API_KEY` set

```
$ ADMIN_API_KEY="test-strong-admin-key-123" PORT=3000 node src/app.js
{"level":"info","message":"Database seeded with initial data","timestamp":"2026-08-18T09:20:22.999Z"}
{"level":"info","message":"Frankenstein LMS rodando na porta 3000...","timestamp":"2026-08-18T09:20:23.003Z"}
```

Boots cleanly, no errors, no stack traces — confirms local/dev usability is
preserved as long as `ADMIN_API_KEY` is set (via env var here; a `.env` file
works identically since `dotenv.config()` runs before the check).

## 5. Endpoint-by-endpoint validation (live curl requests, app running with `ADMIN_API_KEY=test-strong-admin-key-123`)

### 5.1 Checkout — new user (success)
Request: `POST /api/checkout` `{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}`
Result: `200` — `{"msg":"Sucesso","enrollment_id":2}`

### 5.2 Checkout — existing user, correct password (success)
Request: `POST /api/checkout` `{"usr":"Leonan","eml":"leonan@fullcycle.com.br","pwd":"123","c_id":2,"card":"4111222233334444"}`
Result: `200` — `{"msg":"Sucesso","enrollment_id":3}`

### 5.3 Checkout — existing user, wrong password (still rejected)
Result: `401` — `{"error":"Credenciais inválidas"}`

### 5.4 Checkout — payment declined
Request: card not starting with `4` (`5111222233334444`)
Result: `400` — `{"error":"Pagamento recusado"}`

### 5.5 `GET /api/users/:id`
Result: `404` — `Cannot GET /api/users/1`. **This route does not exist and never did** —
the original API surface is only `POST /api/checkout`, `GET /api/admin/financial-report`,
and `DELETE /api/users/:id` (confirmed against `api.http` and `src/routes/index.js`,
which mounts exactly `checkoutRoutes`, `adminRoutes`, `userRoutes` — the latter defines
only the `DELETE` handler). The 404 is expected behavior, not a regression; no such
endpoint was added since the task requires preserving, not expanding, the public API
surface.

### 5.6 `GET /api/admin/financial-report` — no credentials
Result: `401` — `{"error":"Unauthorized: valid x-admin-key header required"}`

### 5.6b same endpoint — wrong key
Result: `401` — `{"error":"Unauthorized: valid x-admin-key header required"}`

### 5.7 `GET /api/admin/financial-report` — correct `x-admin-key`
Result: `200` —
```json
[{"course":"Clean Architecture","revenue":997,"students":[{"student":"Leonan","paid":997}]},{"course":"Docker","revenue":994,"students":[{"student":"Guilherme","paid":497},{"student":"Leonan","paid":497}]}]
```
Correctly reflects the two checkouts from 5.1/5.2. Also verified pagination still
works with the new named constants: `?page=1&limit=1` → `200` with one course;
`?limit=101` → `400` — `{"error":"Number must be less than or equal to 100"}` (cap
still enforced at 100 after the magic-number extraction).

### 5.8 `DELETE /api/users/:id` — no credentials
Result: `401` — `{"error":"Unauthorized: valid x-admin-key header required"}`

### 5.9 `DELETE /api/users/:id` — with admin credentials (JSON shape confirmed — finding #2)
Result: `200`, `content-type: application/json; charset=utf-8` —
```json
{"message":"Usuário deletado com sucesso, incluindo matrículas e pagamentos associados."}
```
This confirms finding #2 is fixed: the response is now a JSON object (previously
raw text/`send()`).

### 5.10 Referential-integrity sanity check after delete
`GET /api/admin/financial-report` (with admin key) afterward shows Leonan's
enrollment/payment removed cleanly — no orphaned rows:
```json
[{"course":"Clean Architecture","revenue":0,"students":[]},{"course":"Docker","revenue":497,"students":[{"student":"Guilherme","paid":497}]}]
```

### 5.11 Extra sanity check
Deleting the same (already-deleted) user id again → `404` — `{"error":"Usuário não encontrado"}`.

## 6. Process cleanup

The background server (PID confirmed via `ps`) was stopped after all checks
completed; verified no `node src/app.js` process remained running.

## 7. Summary

All 5 findings from this round's phase-2 audit were fixed exactly as specified,
with no architectural reorganization (none was needed or requested). The app
boots cleanly when `ADMIN_API_KEY` is set (env var or `.env`, since `dotenv` loads
before the fail-fast check runs) and now refuses to boot at all when it is
missing — closing the insecure-default HIGH finding without breaking local/dev
usability. Every original endpoint (`POST /api/checkout`, `GET /api/admin/financial-report`,
`DELETE /api/users/:id`) was exercised live and responds correctly, including the
intentional shape change on the delete endpoint (text → JSON) and the unchanged
401 rejection behavior for missing/wrong admin credentials.
