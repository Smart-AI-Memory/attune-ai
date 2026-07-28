"""Tests for the ops dashboard's per-process client-token gate.

Covers docs/specs/ops-mutating-endpoint-auth/: the session-token
endpoint + meta tag (Phase 2), and the X-Attune-Client gate on every
mutating route (Phase 3) — missing/wrong header → 403, correct header
passes the gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops.config import Config
from attune.ops.security import current_session_token
from attune.ops.server import create_app

# Every mutating route under the dashboard (the inventory from Phase 1).
# A request to each WITHOUT the client token must be rejected.
MUTATING_ROUTES = [
    ("PUT", "/api/specs/demo/decisions/status"),
    ("POST", "/api/specs/demo/completion-candidates/dismiss"),
    ("POST", "/workflows/security-audit/run"),
    ("POST", "/api/telemetry/interaction"),
    ("POST", "/curator/dismiss"),
    ("POST", "/curator/answer"),
]


@pytest.fixture(autouse=True)
def _bypass_client_token(monkeypatch):
    """Override the conftest bypass — this file MUST test the real gate,
    so re-establish a concrete session token.
    """
    monkeypatch.setattr("attune.ops.security._SESSION_TOKEN", "fixed-test-client-token")


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    project = tmp_path / "project"
    project.mkdir()
    return Config(project_root=project, attune_home=tmp_path / "attune-home")


@pytest.fixture()
def client(cfg: Config) -> TestClient:
    app = create_app(cfg)
    c = TestClient(app)
    c.headers["Host"] = f"{cfg.host}:{cfg.port}"
    return c


@pytest.fixture()
def client_allow_run(tmp_path: Path) -> TestClient:
    """Client with allow_run=True (the CLI default) so the token gate is
    the only 403 source — the read-only gate that also guards
    specs/run mutations doesn't mask it."""
    project = tmp_path / "project"
    project.mkdir()
    cfg = Config(
        project_root=project,
        attune_home=tmp_path / "attune-home",
        allow_run=True,
    )
    c = TestClient(create_app(cfg))
    c.headers["Host"] = f"{cfg.host}:{cfg.port}"
    return c


# --- Phase 2: token endpoint + meta tag ----------------------------------


def test_session_token_endpoint_returns_token(client: TestClient) -> None:
    resp = client.get("/api/session/token")
    assert resp.status_code == 200
    token = resp.json()["token"]
    assert token and isinstance(token, str)
    assert token == current_session_token()


def test_rendered_page_carries_client_token_meta(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'name="attune-client-token"' in resp.text
    # The minted token is embedded so the page JS can read it.
    assert current_session_token() in resp.text


# --- Phase 3: the gate ----------------------------------------------------


@pytest.mark.parametrize(("method", "path"), MUTATING_ROUTES)
def test_mutating_route_without_token_is_403(client: TestClient, method: str, path: str) -> None:
    resp = client.request(method, path, json={})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "invalid_client"


@pytest.mark.parametrize(("method", "path"), MUTATING_ROUTES)
def test_mutating_route_with_wrong_token_is_403(client: TestClient, method: str, path: str) -> None:
    resp = client.request(method, path, json={}, headers={"X-Attune-Client": "nope"})
    assert resp.status_code == 403


@pytest.mark.parametrize(("method", "path"), MUTATING_ROUTES)
def test_mutating_route_with_correct_token_passes_gate(
    client_allow_run: TestClient, method: str, path: str
) -> None:
    # With the right token (and allow_run on) the gate lets the request
    # through — the route may then 400/422/etc. on the empty body, but it
    # must NOT be the 403 the token gate produces.
    resp = client_allow_run.request(
        method, path, json={}, headers={"X-Attune-Client": current_session_token()}
    )
    assert resp.status_code != 403
