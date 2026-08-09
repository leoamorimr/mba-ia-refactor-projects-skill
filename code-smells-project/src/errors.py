"""Shared application exceptions, handled centrally by
`middlewares.error_handler` instead of a per-route try/except block.
"""


class ValidationError(Exception):
    """Raised when request input fails a business validation rule."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class UnauthorizedError(Exception):
    """Raised when a request lacks valid credentials/authorization."""
