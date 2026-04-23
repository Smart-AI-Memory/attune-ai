"""Backend test configuration.

Sets JWT_SECRET_KEY for the test session if not already configured.
The backend auth service raises ValueError at module level when the key
is absent, which crashes pytest collection in CI where the key is not set.
"""

import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-secret-not-for-production",  # pragma: allowlist secret
)
