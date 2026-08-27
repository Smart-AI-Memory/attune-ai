"""Backend test configuration.

Sets JWT_SECRET_KEY for the test session if not already configured.
The backend auth service raises ValueError at module level when the key
is absent, which crashes pytest collection in CI where the key is not set.

Also puts backend/ on sys.path: the backend runs with that directory as
its root (main.py does ``from api import ...``), so router modules use
imports like ``from services.empathy_service import ...`` that only
resolve with backend/ importable.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-secret-not-for-production",  # pragma: allowlist secret
)

_BACKEND_DIR = str(Path(__file__).resolve().parents[2] / "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
