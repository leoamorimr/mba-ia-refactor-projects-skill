"""Shared constants and small pure helpers.

This is the single source of truth for validation rules and formatting
used across models/controllers -- nothing here should be re-implemented
inline anywhere else in the codebase.
"""
import re
from datetime import datetime, timezone

VALID_STATUSES = ['pending', 'in_progress', 'done', 'cancelled']
VALID_ROLES = ['user', 'admin', 'manager']

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PASSWORD_LENGTH = 4
PRIORITY_MIN = 1
PRIORITY_MAX = 5

DEFAULT_STATUS = 'pending'
DEFAULT_PRIORITY = 3
DEFAULT_COLOR = '#000000'

_EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')


def utc_now():
    """Current UTC time, as a naive datetime.

    SQLite (via SQLAlchemy's DateTime column) always round-trips naive
    datetimes -- any tzinfo attached before a write is stripped on read.
    `due_date` is also always naive (parsed from a plain "YYYY-MM-DD"
    string). Returning a naive-but-UTC value here keeps every datetime in
    the app directly comparable, while still avoiding the deprecated
    `datetime.utcnow()` call.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_date(date_obj):
    if date_obj:
        return str(date_obj)
    return None


def calculate_percentage(part, total):
    if total == 0:
        return 0
    return round((part / total) * 100, 2)


def validate_email(email):
    return bool(email) and bool(_EMAIL_PATTERN.match(email))


def parse_date(date_string):
    for date_format in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError:
            continue
    return None


def is_valid_color(color):
    return bool(color) and len(color) == 7 and color[0] == '#'


def process_task_data(data):
    """Validate and normalize the task fields present in `data`.

    Only keys present in `data` are validated and returned in the result
    dict -- callers are responsible for applying their own defaults for
    keys that are absent (e.g. on create) and for required-field checks
    (e.g. title must be present on create but is optional on update).

    Returns (fields, None) on success, or (None, error_message) on the
    first validation failure.
    """
    result = {}

    if 'title' in data:
        title = data['title']
        if not title:
            return None, 'Título não pode ser vazio'
        title = title.strip()
        if len(title) < MIN_TITLE_LENGTH or len(title) > MAX_TITLE_LENGTH:
            return None, f'Título deve ter entre {MIN_TITLE_LENGTH} e {MAX_TITLE_LENGTH} caracteres'
        result['title'] = title

    if 'description' in data:
        result['description'] = data['description']

    if 'status' in data:
        if data['status'] not in VALID_STATUSES:
            return None, 'Status inválido'
        result['status'] = data['status']

    if 'priority' in data:
        priority = data['priority']
        if isinstance(priority, bool) or not isinstance(priority, int):
            return None, 'Prioridade inválida'
        if priority < PRIORITY_MIN or priority > PRIORITY_MAX:
            return None, f'Prioridade deve ser entre {PRIORITY_MIN} e {PRIORITY_MAX}'
        result['priority'] = priority

    if 'due_date' in data:
        if data['due_date']:
            parsed = parse_date(data['due_date'])
            if not parsed:
                return None, 'Formato de data inválido. Use YYYY-MM-DD'
            result['due_date'] = parsed
        else:
            result['due_date'] = None

    if 'tags' in data:
        tags = data['tags']
        if isinstance(tags, list):
            result['tags'] = ','.join(tags)
        else:
            result['tags'] = tags

    return result, None
