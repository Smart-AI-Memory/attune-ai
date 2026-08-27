"""Security tests: every protected API route must VERIFY its bearer token.

Regression guard for the 16.0.0 post-release finding (also flagged
2026-08-02): users/subscriptions/analysis endpoints injected
``Depends(HTTPBearer())`` but never called ``verify_token``, so any
syntactically valid bearer header authenticated against destructive
routes (account deletion, purchases, license deactivation, team-member
removal).

Coverage:
1. A forged token (signed with the wrong key) is rejected with 401
   on every route in the three previously-unprotected routers.
2. A garbage non-JWT token is rejected with 401.
3. A missing Authorization header is rejected (403 from HTTPBearer).
4. A genuinely valid token still authenticates (200).
5. Drift guard: the parametrized route table covers EVERY route in
   those routers, so a new endpoint cannot ship untested.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timedelta

import pytest

pytest.importorskip("bcrypt")
pytest.importorskip("email_validator")  # routers declare EmailStr fields
import jwt  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import analysis, subscriptions, users  # noqa: E402
from backend.services.auth_service import JWT_ALGORITHM, JWT_SECRET_KEY  # noqa: E402


def _make_token(secret: str) -> str:
    """Create a JWT with the given signing secret."""
    payload = {
        "sub": "user@example.com",
        "user_id": 1,
        "name": "Test User",
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


FORGED_TOKEN = _make_token("attacker-controlled-wrong-secret-key!!")  # pragma: allowlist secret
GARBAGE_TOKEN = "not-a-jwt-at-all"


@pytest.fixture(scope="module")
def client() -> TestClient:
    """App with the three previously-unprotected routers mounted."""
    app = FastAPI()
    app.include_router(users.router)
    app.include_router(subscriptions.router)
    app.include_router(analysis.router)
    # The auth dependency must reject BEFORE any service work happens;
    # a None service makes the test fail loudly if a handler ever runs.
    app.dependency_overrides[analysis.get_empathy_service] = lambda: None
    return TestClient(app)


# (method, path, request kwargs) — one row per protected route.
PROTECTED_ROUTES = [
    # users
    ("GET", "/api/users/profile", {}),
    ("PUT", "/api/users/profile", {"json": {"name": "X"}}),
    ("GET", "/api/users/usage", {}),
    ("DELETE", "/api/users/account", {}),
    # subscriptions
    ("GET", "/api/subscriptions/", {}),
    (
        "POST",
        "/api/subscriptions/purchase",
        {"json": {"product": "book", "payment_method": "card"}},
    ),
    ("GET", "/api/subscriptions/team", {}),
    (
        "POST",
        "/api/subscriptions/team/members",
        {"json": {"email": "new@example.com"}},
    ),
    ("DELETE", "/api/subscriptions/team/members/user_1", {}),
    ("GET", "/api/subscriptions/licenses", {}),
    ("POST", "/api/subscriptions/licenses/lic_1/deactivate", {}),
    # analysis
    (
        "POST",
        "/api/analysis/session",
        {"json": {"name": "s", "wizards": ["security_wizard"]}},
    ),
    ("GET", "/api/analysis/session/sess_1", {}),
    ("POST", "/api/analysis/project", {"json": {"project_path": "/tmp/p"}}),
    ("POST", "/api/analysis/file", {"files": {"file": ("a.py", b"print(1)")}}),
    ("GET", "/api/analysis/history", {}),
    ("DELETE", "/api/analysis/session/sess_1", {}),
]

ROUTE_IDS = [f"{m} {p}" for m, p, _ in PROTECTED_ROUTES]


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_ROUTES, ids=ROUTE_IDS)
def test_forged_bearer_rejected(client, method, path, kwargs):
    """A syntactically valid JWT signed with the wrong key must get 401."""
    response = client.request(
        method,
        path,
        headers={"Authorization": f"Bearer {FORGED_TOKEN}"},
        **kwargs,
    )
    assert response.status_code == 401, (
        f"{method} {path} accepted a forged bearer token "
        f"(got {response.status_code}): token verification is missing"
    )


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_ROUTES, ids=ROUTE_IDS)
def test_garbage_bearer_rejected(client, method, path, kwargs):
    """A non-JWT bearer value must get 401."""
    response = client.request(
        method,
        path,
        headers={"Authorization": f"Bearer {GARBAGE_TOKEN}"},
        **kwargs,
    )
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_ROUTES, ids=ROUTE_IDS)
def test_missing_auth_header_rejected(client, method, path, kwargs):
    """No Authorization header must be rejected outright.

    HTTPBearer returns 401 on FastAPI >= 0.135 and 403 on older versions.
    """
    response = client.request(method, path, **kwargs)
    assert response.status_code in (401, 403)


def test_valid_token_still_authenticates(client):
    """A token signed with the real key passes verification (no lockout)."""
    token = _make_token(JWT_SECRET_KEY)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/users/profile", headers=headers).status_code == 200
    assert client.get("/api/subscriptions/", headers=headers).status_code == 200
    assert client.get("/api/analysis/history", headers=headers).status_code == 200


def test_route_table_covers_all_router_routes(client):
    """Drift guard: every route in these routers appears in PROTECTED_ROUTES."""
    expected = {
        (method, route.path)
        for router in (users.router, subscriptions.router, analysis.router)
        for route in router.routes
        for method in route.methods
    }
    listed = set()
    for method, path, _ in PROTECTED_ROUTES:
        # Map concrete test paths back to route templates.
        template = (
            path.replace("user_1", "{user_id}")
            .replace("lic_1", "{license_id}")
            .replace("sess_1", "{session_id}")
        )
        listed.add((method, template))
    assert (
        listed == expected
    ), f"untested routes: {expected - listed}; stale rows: {listed - expected}"
