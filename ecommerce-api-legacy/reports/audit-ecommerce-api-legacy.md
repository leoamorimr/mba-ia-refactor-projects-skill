================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.18
Files:   23 analyzed | ~747 lines of code

## Summary
CRITICAL: 0 | HIGH: 1 | MEDIUM: 1 | LOW: 3

## Findings

### [HIGH] Forgeable / Predictable Auth Token (Insecure Default Admin Credential)
File: src/config/index.js:18 (consumed at src/middlewares/auth.js:10-15)
Description: The only authentication mechanism protecting `GET /api/admin/financial-report` and `DELETE /api/users/:id` is a single shared-secret header (`x-admin-key`) compared against `config.adminApiKey`. That value falls back to the literal string `'dev-only-insecure-admin-key'` (`config/index.js:18`) whenever the `ADMIN_API_KEY` environment variable is not set. The exact fallback string is also printed verbatim in `README.md:18-21` and hardcoded into `api.http:2` as the example header value, so it is committed to source control in three places.
Impact: If a deployment ever forgets to set `ADMIN_API_KEY` (a very common ops mistake, especially for a small/legacy-style service like this one), the working admin credential is public knowledge to anyone with repository access — a `curl` copied straight from the README grants full access to the financial report and to the destructive user-delete endpoint. This is functionally equivalent to a predictable/forgeable auth token: the secret can be obtained from public source instead of being provisioned per-deployment.
Recommendation: Fail fast instead of silently falling back for this specific value — throw at boot if `process.env.ADMIN_API_KEY` is unset (unlike the other, genuinely inert placeholders in the same config object, this one is wired into a live authorization check). If a default is still wanted for local dev, generate it randomly per-process rather than using a fixed string, and never print a real/working key value in README/`api.http` — show a placeholder instead.

### [MEDIUM] Inconsistent API Response Format (Standardization Problem)
File: src/routes/userRoutes.js:13
Description: `DELETE /api/users/:id` responds with `res.status(200).send(result.message)` — a raw text/HTML body — while every other endpoint in the API responds with `res.status(200).json(...)` (`src/routes/checkoutRoutes.js:14`, `src/routes/adminRoutes.js:13`) and all error responses go through the centralized handler as JSON (`src/middlewares/errorHandler.js:11,15`).
Impact: API consumers cannot rely on a single content type/response shape across endpoints; a client that always does `response.json()` will throw on this one success path, and the inconsistency is exactly the kind of standardization gap that compounds as more endpoints are added.
Recommendation: Change the handler to `res.status(200).json({ message: result.message })` so every 2xx response in the API is JSON, matching the shape already used by the other two routes.

### [LOW] Dead Code / Unused Abstractions
File: src/config/index.js:11-14
Description: Several pieces of code are fully wired up but never consumed anywhere:
- `dbUser`, `dbPass`, `paymentGatewayKey`, `smtpUser` (`src/config/index.js:11-14`) are defined and read from `process.env` but never referenced by any other file in `src/` (confirmed by project-wide grep) — the app only ever uses SQLite in-memory storage, so `dbUser`/`dbPass` describe a data store that doesn't exist, and no payment-gateway or SMTP integration exists to consume the other two.
- `BadRequestError` (`src/utils/errors.js:19-23`) is defined and exported but never thrown anywhere in the codebase (only `ValidationError`, `UnauthorizedError`, `NotFoundError`, and `PaymentDeniedError` are actually used).
- `PAYMENT_STATUS.DENIED` (`src/models/paymentModel.js:4`) is defined but no code path ever creates a payment with that status — `checkoutController.js` throws `PaymentDeniedError` before any payment row is written when a card is declined, so `DENIED` is unreachable.
- `getDb` (`src/config/database.js:16-21`, exported at `src/config/database.js:92`) is exported from the database module but never called by any consumer outside the module itself — all real access goes through `run`/`get`/`all`/`transaction`.
Impact: Low direct risk, but these unused values/exports are misleading during onboarding or future audits (e.g. `dbUser`/`dbPass` read as if a credentialed external DB exists) and add surface area that has to be mentally filtered out when reasoning about the code.
Recommendation: Remove the four unused config fields (or wire them to a real integration if one is actually planned), remove `BadRequestError` and `PAYMENT_STATUS.DENIED` until a code path needs them, and drop the `getDb` export from `database.js`'s public module interface.

### [LOW] Duplicated Code Across Batch ID-Lookup Queries
File: src/models/enrollmentModel.js:14-21
Description: The same three-step shape — bail out on an empty array, build a `?,?,?` placeholder string by mapping over the id array, then run a `SELECT ... WHERE <col> IN (...)` — is repeated nearly verbatim in three different model files: `enrollmentModel.findByCourseIds` (`src/models/enrollmentModel.js:14-21`), `paymentModel.findByEnrollmentIds` (`src/models/paymentModel.js:16-23`), and `userModel.findByIds` (`src/models/userModel.js:13-17`).
Impact: Not a correctness problem (all three are safely parameterized), but any future fix to this pattern (e.g. chunking very large id arrays to stay under SQLite's parameter limit) has to be applied in three places by hand, and it's easy to update two and miss the third.
Recommendation: Extract a small shared helper in `config/database.js` (or a new `utils/query.js`), e.g. `findByIdsIn(table, column, ids, selectColumns)`, and have all three models call it instead of re-implementing the placeholder-building logic.

### [LOW] Magic Numbers in Pagination Defaults
File: src/middlewares/validators.js:52-53
Description: `reportQuerySchema` hardcodes the pagination defaults and cap inline: `z.coerce.number().int().positive().optional().default(1)` for `page` and `z.coerce.number().int().positive().max(100).optional().default(50)` for `limit` — the values `1`, `50`, and `100` are unnamed literals embedded directly in the schema.
Impact: Minor readability/maintainability cost — a future change to the default page size or the max limit requires finding and understanding this specific line rather than updating one named constant, and the values carry no self-documentation about why 50/100 were chosen.
Recommendation: Extract `DEFAULT_REPORT_PAGE = 1`, `DEFAULT_REPORT_LIMIT = 50`, and `MAX_REPORT_LIMIT = 100` as named constants near the top of `validators.js` and reference them in the schema.

================================
Total: 5 findings
================================
