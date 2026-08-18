"""Centralized application configuration.

Every secret and environment-dependent value is read from the environment
here, and nowhere else. Nothing in models/controllers/views should reference
`os.environ` directly - they import from this module instead.
"""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

# SECRET_KEY has no hardcoded fallback baked into the repo. If it isn't
# provided via the environment, a random key is generated at process start
# so the app can still boot locally, but sessions won't survive a restart
# and this must never happen in a real deployment.
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# Debug mode defaults to OFF and must be explicitly enabled via env var.
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# Not a secret - safe to default locally.
DB_PATH = os.environ.get("DB_PATH", "loja.db")

# Token required by the `require_admin` middleware to access /admin/* routes.
# If unset, admin routes are unreachable (fail closed) rather than falling
# back to any hardcoded value.
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

# Comma-separated list of origins allowed to make cross-origin requests.
# Defaults to localhost dev origins only - never "*" - since the wide-open
# default previously let any website issue cross-origin requests against
# every route, including the mutating /produtos, /pedidos and /usuarios
# endpoints.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
