================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js)
Framework:     Express ^4.18.2 (package.json dependency, confirmed via `require('express')` in src/app.js)
Dependencies:  express ^4.18.2, sqlite3 ^5.1.6 (in-memory DB via `new sqlite3.Database(':memory:')`)
Domain:        LMS with a purchase flow — courses, enrollments, payments, users (routes: POST /api/checkout, GET /api/admin/financial-report, DELETE /api/users/:id; console banner logs "Frankenstein LMS"). Note: the repo/folder is named "ecommerce-api-legacy" but the actual entities and README ("LMS API (com fluxo de checkout)") point to an LMS domain, not generic e-commerce.
Architecture:  god class — src/AppManager.js is a single class whose constructor opens the DB connection, whose initDb() creates the schema and seeds data, and whose setupRoutes(app) defines all 3 routes with business logic (payment processing, nested-callback enrollment flow, admin report aggregation) inlined directly in the handlers; src/app.js merely instantiates it, and src/utils.js holds shared config/helpers — no models/, routes/, services/, or controllers/ folders exist at all.
Source files:  3 files analyzed (src/app.js, src/AppManager.js, src/utils.js)
DB tables:     users, courses, enrollments, payments, audit_logs (5 tables, SQLite in-memory)
================================
