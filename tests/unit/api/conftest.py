"""API unit test configuration.

Sets JWT_SECRET_KEY for the test session if not already configured. The
backend API routers now depend on ``api.dependencies.require_principal``,
which transitively imports ``backend.services.auth_service`` — that module
raises ValueError at import time when the key is absent (as in keyless CI).
Mirrors ``tests/unit/backend/conftest.py``.
"""

import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-secret-not-for-production",  # pragma: allowlist secret
)
