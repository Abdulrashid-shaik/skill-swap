class BusinessRuleError(Exception):
    """Raised when an operation violates a business rule (e.g. requesting an
    exchange with an incompatible user). Views catch this and surface the
    message to the user; the HTTP layer never bypasses these checks."""
