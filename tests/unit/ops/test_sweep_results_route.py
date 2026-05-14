"""HTTP route tests: GET /workflows/discovery-sweep/results/{hash}.

Spec: docs/specs/discovery-sweep-ops-integration/design.md
      (Phase 2B — read API)

Covers:

- 400 on malformed scope_hash (not 16 lowercase hex chars).
- 404 when no result exists for the given hash.
- 200 + JSON body on success.
- Sidecar JSON round-trips through the route unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops import sweep_results
from attune.ops.config import Config
from attune.ops.server import create_app


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    return Config(
        project_root=tmp_path / "project",
        attune_home=tmp_path / "attune-home",
    )


@pytest.fixture()
def client(cfg: Config) -> TestClient:
    """TestClient with a Host header the trusted-host middleware accepts."""
    app = create_app(cfg)
    c = TestClient(app)
    # TrustedHostMiddleware allows the default 127.0.0.1:8765 by default.
    c.headers["Host"] = f"{cfg.host}:{cfg.port}"
    return c


class TestMalformedHash:
    def test_too_short(self, client: TestClient) -> None:
        resp = client.get("/workflows/discovery-sweep/results/short")
        assert resp.status_code == 400
        assert "16 lowercase hex" in resp.json()["detail"]

    def test_too_long(self, client: TestClient) -> None:
        resp = client.get("/workflows/discovery-sweep/results/" + "a" * 17)
        assert resp.status_code == 400

    def test_uppercase_rejected(self, client: TestClient) -> None:
        resp = client.get("/workflows/discovery-sweep/results/AAAAAAAAAAAAAAAA")
        assert resp.status_code == 400

    def test_non_hex_rejected(self, client: TestClient) -> None:
        resp = client.get("/workflows/discovery-sweep/results/zzzzzzzzzzzzzzzz")
        assert resp.status_code == 400


class TestMissingResult:
    def test_returns_404(self, client: TestClient) -> None:
        # Valid shape, no file on disk.
        resp = client.get("/workflows/discovery-sweep/results/0123456789abcdef")
        assert resp.status_code == 404


class TestSuccess:
    def test_round_trip(self, client: TestClient, cfg: Config) -> None:
        payload = {
            "queue": [{"source": "x", "title": "t"}],
            "questions": [],
            "rejected": [],
            "metadata": {"sources": ["x"]},
        }
        sweep_results.persist_result("src/", payload, cfg)
        digest = sweep_results.scope_hash("src/")
        resp = client.get(f"/workflows/discovery-sweep/results/{digest}")
        assert resp.status_code == 200
        assert resp.json() == payload

    def test_corrupt_sidecar_returns_404(self, client: TestClient, cfg: Config) -> None:
        # read_result returns None on corrupt JSON (logged warning);
        # the route surfaces that as 404 — "no usable data" is
        # operationally equivalent to "no data" for the dashboard.
        out_dir = sweep_results.results_dir(cfg)
        (out_dir / "deadbeefdeadbeef.json").write_text("{not valid", encoding="utf-8")
        resp = client.get("/workflows/discovery-sweep/results/deadbeefdeadbeef")
        assert resp.status_code == 404
