"""Application configuration.

All secrets and environment-dependent values are read from environment
variables here, and nowhere else in the codebase. Models, controllers and
routes must import from this module instead of touching `os.environ`
directly.
"""
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        'SECRET_KEY environment variable must be set. '
        'Copy .env.example to .env and set a real value before starting the app.'
    )

# Debug mode and the network interface the dev server binds to must be
# explicitly opted into via env vars -- both default to the safe option.
DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
PORT = int(os.environ.get('FLASK_PORT', '5000'))

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')

JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))
