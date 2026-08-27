"""Security regression tests for bearer-token verification on backend routes.

Guards the fix for the 17 endpoints that injected ``Depends(security)``
(a bare ``HTTPBearer``) but never verified the token — so any non-empty
bearer string, forged or expired, was accepted and the handler returned
2xx. Each route now depends on ``require_principal``, which decodes and
validates the JWT.

Coverage per previously-unverified route:
- forged bearer  -> 401 (was: accepted)
- valid bearer   -> passes auth (status not in {401, 403})
- missing header -> 403 (HTTPBearer auto_error; invariant)

Plus expired-token rejection and direct unit tests of the shared
verification helpers.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import jwt
import pytest

# The auth service evaluates JWT_SECRET_KEY at import time and raises if
# it is unset. Set it before importing anything under backend.services.
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-secret-not-for-production",  # pragma: allowlist secret
)

# `backend` is a PEP-420 namespace package (needs repo root on the path);
# the router modules import siblings as `api.*` (needs backend/ on the path).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_DIR = _REPO_ROOT / "backend"
for _p in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Avoid pulling EmpathyService / analyzer deps at import time.
sys.modules.setdefault("services", MagicMock())
sys.modules.setdefault("services.empathy_service", MagicMock())

from api import analysis, subscriptions, users  # noqa: E402
from api.dependencies import require_principal  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.services.auth_service import (  # noqa: E402
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    verify_access_token,
)


def _make_token(**overrides) -> str:
    """Mint a signed JWT valid under the test secret."""
    payload = {
        "sub": "user@example.com",
        "user_id": "user_123",
        "name": "Test User",
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
    }
    payload.update(overrides)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """A TestClient over just the three previously-unverified routers."""
    app = FastAPI()
    app.include_router(analysis.router)
    app.include_router(subscriptions.router)
    app.include_router(users.router)
    # Handlers run against MagicMock services on the valid-token path and may
    # 500; that is fine — we only assert they get PAST authentication.
    return TestClient(app, raise_server_exceptions=False)


# (method, path, request-kwargs) for every previously-unverified endpoint.
UNVERIFIED_ROUTES = [
    # analysis.py (6)
    ("POST", "/api/analysis/session", {"json": {"name": "s", "wizards": ["w"]}}),
    ("GET", "/api/analysis/session/abc", {}),
    ("POST", "/api/analysis/project", {"json": {"project_path": "/tmp/x"}}),
    ("POST", "/api/analysis/file", {"files": {"file": ("a.py", b"print()")}}),
    ("GET", "/api/analysis/history", {}),
    ("DELETE", "/api/analysis/session/abc", {}),
    # subscriptions.py (7)
    ("GET", "/api/subscriptions/", {}),
    (
        "POST",
        "/api/subscriptions/purchase",
        {"json": {"product": "book", "payment_method": "card"}},
    ),
    ("GET", "/api/subscriptions/team", {}),
    ("POST", "/api/subscriptions/team/members", {"json": {"email": "a@b.com"}}),
    ("DELETE", "/api/subscriptions/team/members/u1", {}),
    ("GET", "/api/subscriptions/licenses", {}),
    ("POST", "/api/subscriptions/licenses/lic1/deactivate", {}),
    # users.py (4)
    ("GET", "/api/users/profile", {}),
    ("PUT", "/api/users/profile", {"json": {}}),
    ("GET", "/api/users/usage", {}),
    ("DELETE", "/api/users/account", {}),
]


def test_seventeen_routes_enumerated():
    """Pin the count so a route added without auth is noticed."""
    assert len(UNVERIFIED_ROUTES) == 17


@pytest.mark.parametrize("method,path,kwargs", UNVERIFIED_ROUTES)
def test_forged_bearer_rejected(client, method, path, kwargs):
    """A forged (unsigned-garbage) bearer must be rejected with 401."""
    headers = {"Authorization": "Bearer not-a-real-jwt"}
    resp = client.request(method, path, headers=headers, **kwargs)
    assert (
        resp.status_code == 401
    ), f"{method} {path} accepted a forged bearer (got {resp.status_code})"


@pytest.mark.parametrize("method,path,kwargs", UNVERIFIED_ROUTES)
def test_missing_header_rejected(client, method, path, kwargs):
    """No Authorization header -> rejected (HTTPBearer auto_error, 401/403)."""
    resp = client.request(method, path, **kwargs)
    assert resp.status_code in (
        401,
        403,
    ), f"{method} {path} allowed a missing bearer (got {resp.status_code})"


@pytest.mark.parametrize("method,path,kwargs", UNVERIFIED_ROUTES)
def test_valid_bearer_passes_auth(client, method, path, kwargs):
    """A valid token gets past auth (status is not an auth rejection)."""
    headers = {"Authorization": f"Bearer {_make_token()}"}
    resp = client.request(method, path, headers=headers, **kwargs)
    assert resp.status_code not in (
        401,
        403,
    ), f"{method} {path} rejected a valid bearer (got {resp.status_code})"


def test_expired_bearer_rejected(client):
    """An expired-but-well-signed token is rejected with 401."""
    expired = _make_token(exp=datetime.utcnow() - timedelta(minutes=1))
    resp = client.get("/api/users/profile", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


# --- Direct unit tests of the shared verification helpers -----------------


def test_verify_access_token_accepts_valid():
    payload = verify_access_token(_make_token())
    assert payload["sub"] == "user@example.com"
    assert payload["user_id"] == "user_123"


def test_verify_access_token_rejects_forged():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        verify_access_token("garbage.not.jwt")
    assert exc.value.status_code == 401


def test_verify_access_token_rejects_wrong_secret():
    from fastapi import HTTPException

    forged = jwt.encode({"sub": "x"}, "a-different-secret", algorithm=JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        verify_access_token(forged)
    assert exc.value.status_code == 401


def test_require_principal_returns_payload_for_valid_token():
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_make_token())
    principal = require_principal(creds)
    assert principal["user_id"] == "user_123"


def test_require_principal_raises_for_forged_token():
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="nope")
    with pytest.raises(HTTPException) as exc:
        require_principal(creds)
    assert exc.value.status_code == 401
