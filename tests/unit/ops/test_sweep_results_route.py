"""HTTP route tests: discovery-sweep dashboard surface.

Spec: docs/specs/discovery-sweep-ops-integration/design.md
      (Phase 2B — read API; Phase 3 — chips API + HTML detail page)

Covers:

- ``GET /api/workflows/discovery-sweep/results/{scope_hash}`` (JSON):
  malformed hash → 400, missing file → 404, valid → 200 + payload.
- ``GET /api/workflows/discovery-sweep/chips`` (JSON): empty store
  returns has_result=False with zero counts; populated store returns
  per-bucket counts and the matching scope_hash.
- ``GET /workflows/discovery-sweep/results/{scope_hash}`` (HTML):
  malformed hash → 400, missing → 404, present → 200 + bucket
  filter handling.
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
    project = tmp_path / "project"
    project.mkdir()
    return Config(
        project_root=project,
        attune_home=tmp_path / "attune-home",
    )


@pytest.fixture()
def client(cfg: Config) -> TestClient:
    """TestClient with a Host header the trusted-host middleware accepts."""
    app = create_app(cfg)
    c = TestClient(app)
    c.headers["Host"] = f"{cfg.host}:{cfg.port}"
    return c


_JSON = "/api/workflows/discovery-sweep/results/"
_HTML = "/workflows/discovery-sweep/results/"


class TestJsonRouteMalformedHash:
    def test_too_short(self, client: TestClient) -> None:
        resp = client.get(_JSON + "short")
        assert resp.status_code == 400
        assert "16 lowercase hex" in resp.json()["detail"]

    def test_too_long(self, client: TestClient) -> None:
        resp = client.get(_JSON + "a" * 17)
        assert resp.status_code == 400

    def test_uppercase_rejected(self, client: TestClient) -> None:
        resp = client.get(_JSON + "AAAAAAAAAAAAAAAA")
        assert resp.status_code == 400

    def test_non_hex_rejected(self, client: TestClient) -> None:
        resp = client.get(_JSON + "zzzzzzzzzzzzzzzz")
        assert resp.status_code == 400


class TestJsonRouteMissingResult:
    def test_returns_404(self, client: TestClient) -> None:
        resp = client.get(_JSON + "0123456789abcdef")
        assert resp.status_code == 404


class TestJsonRouteSuccess:
    def test_round_trip(self, client: TestClient, cfg: Config) -> None:
        payload = {
            "queue": [{"source": "x", "title": "t"}],
            "questions": [],
            "rejected": [],
            "metadata": {"sources": ["x"]},
        }
        sweep_results.persist_result("src/", payload, cfg)
        digest = sweep_results.scope_hash("src/")
        resp = client.get(_JSON + digest)
        assert resp.status_code == 200
        assert resp.json() == payload

    def test_corrupt_sidecar_returns_404(self, client: TestClient, cfg: Config) -> None:
        out_dir = sweep_results.results_dir(cfg)
        (out_dir / "deadbeefdeadbeef.json").write_text("{not valid", encoding="utf-8")
        resp = client.get(_JSON + "deadbeefdeadbeef")
        assert resp.status_code == 404


class TestChipsApi:
    def test_no_result_returns_zero_counts(self, client: TestClient, cfg: Config) -> None:
        resp = client.get("/api/workflows/discovery-sweep/chips?scope=src/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_result"] is False
        assert body["queue"] == 0
        assert body["questions"] == 0
        assert body["rejected"] == 0
        assert body["scope_hash"] == sweep_results.scope_hash("src/")

    def test_with_result_returns_counts(self, client: TestClient, cfg: Config) -> None:
        payload = {
            "queue": [{"a": 1}, {"a": 2}, {"a": 3}],
            "questions": [{"finding": {}, "reason": "r", "next_step": "ns"}],
            "rejected": [
                {"finding": {}, "rule": "r1"},
                {"finding": {}, "rule": "r2"},
            ],
            "metadata": {},
        }
        sweep_results.persist_result("src/foo", payload, cfg)
        resp = client.get("/api/workflows/discovery-sweep/chips?scope=src/foo")
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_result"] is True
        assert body["queue"] == 3
        assert body["questions"] == 1
        assert body["rejected"] == 2

    def test_empty_scope_falls_back_to_project_root(self, client: TestClient, cfg: Config) -> None:
        resp = client.get("/api/workflows/discovery-sweep/chips")
        assert resp.status_code == 200
        body = resp.json()
        assert body["scope_hash"] == sweep_results.scope_hash(str(cfg.project_root))
        assert body["has_result"] is False


class TestHtmlDetailPage:
    def test_malformed_hash_400(self, client: TestClient) -> None:
        resp = client.get(_HTML + "short")
        assert resp.status_code == 400

    def test_missing_returns_404(self, client: TestClient) -> None:
        resp = client.get(_HTML + "0123456789abcdef")
        assert resp.status_code == 404

    def test_renders_findings(self, client: TestClient, cfg: Config) -> None:
        payload = {
            "queue": [
                {
                    "source": "bug-predict",
                    "severity": "high",
                    "title": "Possible NPE on user input",
                    "description": "x",
                    "file": "src/foo.py",
                    "line": 42,
                    "evidence": "if x == None:",
                    "confidence": 0.8,
                    "tags": ["null-check"],
                }
            ],
            "questions": [
                {
                    "finding": {
                        "source": "security-audit",
                        "severity": "medium",
                        "title": "Possible PII log",
                        "description": "",
                        "file": None,
                        "line": None,
                        "evidence": None,
                        "confidence": 0.6,
                        "tags": [],
                    },
                    "reason": "LOCATION_MISSING",
                    "next_step": "Add file/line metadata",
                }
            ],
            "rejected": [
                {
                    "finding": {
                        "source": "pattern-scan",
                        "severity": "low",
                        "title": "Bare except",
                        "description": "",
                        "file": "tests/foo.py",
                        "line": 1,
                        "evidence": None,
                        "confidence": 0.5,
                        "tags": [],
                    },
                    "rule": "SEVERITY_BELOW_THRESHOLD",
                }
            ],
            "metadata": {"spent_usd": 0.12, "budget_usd": 1.0, "duration_ms": 4200},
        }
        sweep_results.persist_result("src/", payload, cfg)
        digest = sweep_results.scope_hash("src/")
        resp = client.get(_HTML + digest)
        assert resp.status_code == 200
        body = resp.text
        assert "Possible NPE on user input" in body
        assert "Possible PII log" in body
        assert "Bare except" in body
        # Bucket nav links present.
        assert "?bucket=queue" in body
        assert "?bucket=questions" in body
        assert "?bucket=rejected" in body

    def test_bucket_filter_hides_other_sections(self, client: TestClient, cfg: Config) -> None:
        payload = {
            "queue": [
                {
                    "source": "bug-predict",
                    "severity": "high",
                    "title": "Queue Q",
                    "description": "",
                    "file": None,
                    "line": None,
                    "evidence": None,
                    "confidence": 0.9,
                    "tags": [],
                }
            ],
            "questions": [
                {
                    "finding": {
                        "source": "x",
                        "severity": "medium",
                        "title": "Question Q",
                        "description": "",
                        "file": None,
                        "line": None,
                        "evidence": None,
                        "confidence": 0.5,
                        "tags": [],
                    },
                    "reason": "r",
                    "next_step": "ns",
                }
            ],
            "rejected": [],
            "metadata": {},
        }
        sweep_results.persist_result("src/", payload, cfg)
        digest = sweep_results.scope_hash("src/")
        resp = client.get(_HTML + digest + "?bucket=queue")
        assert resp.status_code == 200
        body = resp.text
        assert "Queue Q" in body
        assert "Question Q" not in body

    def test_unknown_bucket_filter_renders_all(self, client: TestClient, cfg: Config) -> None:
        payload = {
            "queue": [
                {
                    "source": "bug-predict",
                    "severity": "high",
                    "title": "Queue Q",
                    "description": "",
                    "file": None,
                    "line": None,
                    "evidence": None,
                    "confidence": 0.9,
                    "tags": [],
                }
            ],
            "questions": [],
            "rejected": [],
            "metadata": {},
        }
        sweep_results.persist_result("src/", payload, cfg)
        digest = sweep_results.scope_hash("src/")
        resp = client.get(_HTML + digest + "?bucket=garbage")
        assert resp.status_code == 200
        assert "Queue Q" in resp.text
