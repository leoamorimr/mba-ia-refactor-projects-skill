# Target Architecture Guidelines (Phase 3)

The target is MVC: **Models**, **Views/Routes**, and **Controllers**, each with a single, non-overlapping responsibility. These rules apply regardless of language — adapt the folder naming to the ecosystem's convention, but keep the separation itself non-negotiable.

## Layer responsibilities

### Models — data only
- Own the schema/table definition and all direct data access (raw SQL, ORM queries, parameterized statements).
- Expose plain functions or methods like `get_by_id`, `create`, `update`, `delete`, `list` — no HTTP concepts (no `request`, `response`, status codes) inside a model.
- Simple per-instance helpers are fine on a model (e.g. `is_overdue()`, `to_dict()`), but cross-entity business rules (discounts, order totals, report aggregation) belong in a controller or service, not in the model.
- One model file per domain entity (`product_model.py`, `user_model.py`), never one file for every entity in the app.

### Views / Routes — routing only
- Define URL paths, HTTP methods, and wire each route to exactly one controller function.
- Do request/response shaping only: parse the incoming body/query params, call the controller, translate its return value into an HTTP response with the right status code.
- No business logic, no direct DB access, no validation beyond "is this endpoint even the right shape" (e.g. required-field presence can live here or in the controller — pick one place and be consistent, don't duplicate it in both).
- Group routes by domain (`product_routes`, `order_routes`) rather than one giant route file for the whole app, once the app has more than a couple of entities.

### Controllers — orchestration
- Receive already-parsed input from the route layer, apply business rules (validation, calculations, cross-entity coordination), call one or more models, and return a plain result (dict/object) for the route to serialize.
- This is where the "God File" logic that used to live in the monolith belongs — split by domain (`product_controller.py`, `order_controller.py`).
- Controllers may call other controllers or a service layer, but never define routes and never contain raw SQL.

### Supporting layers

- **Config** (`config/settings.py` or `config/index.js`): all secrets and environment-dependent values (`SECRET_KEY`, DB path/URI, API keys, ports) read from environment variables here, nowhere else. Nothing in models/controllers/routes should reference `os.environ`/`process.env` directly — they import from config.
- **Middlewares** (`middlewares/error_handler.*`): one centralized error handler registered once at the app level, instead of every route/controller repeating its own try/catch-and-log. Auth middleware belongs here too, and applying it is **not optional**: every mutable route (POST/PUT/PATCH/DELETE) that the audit marked CRITICAL for missing authentication must be gated by it, independent of path prefix — an unauthenticated destructive route outside `/admin/*` is just as CRITICAL as one inside it.
- **Entry point / composition root** (`app.py` / `src/app.js`): the only file that imports config, initializes the DB connection, registers all routes/blueprints/routers, and starts the server. It should contain wiring, not logic.

## Suggested layout

Python/Flask:
```
src/
├── config/
│   └── settings.py
├── models/
│   ├── product_model.py
│   └── user_model.py
├── controllers/
│   ├── product_controller.py
│   └── order_controller.py
├── views/               (Flask calls these "routes"; either folder name is fine, be consistent)
│   └── routes.py        (or split per domain once it grows)
├── middlewares/
│   └── error_handler.py
└── app.py               (composition root)
```

Node/Express — same shape, JS conventions:
```
src/
├── config/
│   └── index.js
├── models/
│   ├── userModel.js
│   └── courseModel.js
├── controllers/
│   ├── userController.js
│   └── checkoutController.js
├── routes/
│   └── index.js          (or split per domain)
├── middlewares/
│   └── errorHandler.js
└── app.js                 (composition root)
```

## Adapting to a partially-organized project

If the project already has `models/`, `routes/`, `services/` (like a project that's midway to good structure), don't blow away what's already correctly placed. Instead:

1. Keep the existing folder names if they already match a layer above (routes stays routes, models stays models).
2. Introduce a `controllers/` (or reuse an existing `services/` folder as the controller layer, whichever name the project already leans toward) and **move** business logic currently sitting in route handlers into it.
3. Deduplicate: if the same business rule (e.g. an "is this overdue" calculation) is repeated in the model and in three different route files, keep exactly one implementation — in the model if it's a per-instance property, in the controller/service if it spans multiple entities — and have every other call site use it.
4. Add the `config/` module and `middlewares/error_handler` even if nothing else changes structurally, since hardcoded secrets and scattered error handling are almost always present even in "organized" projects.

## Non-negotiables, regardless of starting point

- Zero hardcoded secrets after refactoring — everything sensitive comes from environment variables (with a safe local default only for non-secret settings like a debug flag).
- Zero raw string-concatenated SQL — parameterized queries or the ORM's query builder only.
- One error-handling strategy for the whole app, not one per route.
- The original public API surface (paths, methods, request/response shapes) must keep working — this is a structural refactor, not a rewrite of the contract. This does not protect a missing auth check: adding a required auth guard to a route the audit flagged CRITICAL for missing authentication is an in-scope fix, not a contract change, even if the route responded to unauthenticated requests before.
