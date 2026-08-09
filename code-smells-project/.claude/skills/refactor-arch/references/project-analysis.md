# Project Analysis Heuristics (Phase 1)

Goal: figure out, from the files on disk, what stack this project is, what it does, and how its code is currently organized — without asking the user and without assuming it's any specific project. Every signal below is something you can actually grep or `find` for; don't guess.

## 1. Detect the language

List the source files (`find . -maxdepth 3 -type f -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/venv/*'`) and look at extensions:

| Extension(s) | Language |
|---|---|
| `.py` | Python |
| `.js`, `.mjs`, `.cjs` | JavaScript |
| `.ts` | TypeScript |
| `.rb` | Ruby |
| `.go` | Go |
| `.java` | Java |

Whichever extension dominates the source tree (excluding dependency folders like `node_modules`, `venv`, `.venv`, `site-packages`) is the project's language. Report the count of files analyzed — this number must match what you actually counted, not a guess.

## 2. Detect the framework and dependencies

Read the dependency manifest for the detected language:

- Python: `requirements.txt`, `pyproject.toml`, or `Pipfile`. Look for `flask`, `django`, `fastapi`, `flask-sqlalchemy`, `flask-cors`, etc. Note exact pinned versions (e.g. `flask==3.1.1`) — you'll need these for the deprecated-API check in Phase 2.
- Node/JS/TS: `package.json` → `dependencies`/`devDependencies`. Look for `express`, `koa`, `fastify`, `sqlite3`, `pg`, `mongoose`, etc. Also read the `"main"` and `"scripts.start"` fields — they tell you the real entry point.

Cross-check against actual imports in the code (`import flask` / `require('express')`) — a stale manifest entry that's never imported shouldn't be reported as "the framework in use."

## 3. Detect the database

Signals, roughly in order of reliability:

- A `.db` / `.sqlite` file sitting in the project root.
- `sqlite3.connect(...)`, `CREATE TABLE` strings in Python code.
- An ORM: `db.Model` classes (Flask-SQLAlchemy), `mongoose.Schema(...)`, `sequelize.define(...)`.
- `SQLALCHEMY_DATABASE_URI`, `DATABASE_URL`, or a `.db.init_app(...)` call.
- Node: `new sqlite3.Database(...)`, `pg.Pool`, `mongoose.connect(...)`.

List the actual table/collection names you find (from `CREATE TABLE` statements or model class names) — this becomes the "DB tables" line in the Phase 1 summary.

## 4. Infer the domain

Don't guess the domain from the project's folder name — read the route paths and table/model names, they're the ground truth:

- Route paths like `/produtos`, `/pedidos`, `/usuarios` or `/products`, `/orders` → e-commerce.
- `/courses`, `/enrollments`, `/checkout` → LMS / online learning with a purchase flow.
- `/tasks`, `/categories`, `/users` with status/priority fields → task management.

Summarize the domain in one line, e.g. "E-commerce API (products, orders, users)" — mention the entities you actually saw, in the language the code uses for them if that's clearer.

## 5. Map the current architecture

This is the part that actually varies most between the 3 reference projects, so look carefully rather than assuming "everything is a monolith":

- **Flat monolith**: all logic lives in a handful of files at the project root (e.g. `app.py`, `models.py`, `controllers.py`, `database.py`) with no subfolders for models/routes/controllers. Call this out explicitly — it's the worst case for Phase 2/3.
- **Single God Class**: one class or file (regardless of folder structure) owns routing setup, DB access, and business logic together — common in quickly-hacked Node services (e.g. an `AppManager` class that does `initDb()` *and* `setupRoutes()` *and* the request handlers inline).
- **Partially layered**: folders already exist (`models/`, `routes/`, `services/`, `utils/`) but responsibilities still leak across them — e.g. routes doing raw validation and duplicating logic that exists in a service that's never called. Note this nuance explicitly; it changes what Phase 3 needs to do (reorganize + fix leaks, not build layers from scratch).

Count real files per folder to back up the classification (`find <dir> -name '*.py' | wc -l`, etc.) — never state a file count you haven't verified.

## Phase 1 output format

Print (and save to the working report) exactly this shape, with real detected values:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language>
Framework:     <framework + version if known>
Dependencies:  <notable deps>
Domain:        <one-line domain description>
Architecture:  <flat monolith | god class | partially layered> — <one-line justification>
Source files:  <N> files analyzed
DB tables:     <table/collection names>
================================
```
