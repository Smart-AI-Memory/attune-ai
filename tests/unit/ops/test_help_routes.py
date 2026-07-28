"""End-to-end tests for the help-page routes (HTML + JSON API).

Builds a synthetic .help/templates corpus, spins up the full
FastAPI app via TestClient, and exercises every help-related
route — both the dashboard HTML pages and the JSON API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops.config import Config
from attune.ops.help_data import EXPECTED_KINDS
from attune.ops.server import create_app


def _write_template(
    root: Path,
    feature: str,
    kind: str,
    *,
    title: str | None = None,
    body: str = "",
) -> None:
    feat_dir = root / feature
    feat_dir.mkdir(parents=True, exist_ok=True)
    path = feat_dir / f"{kind}.md"
    title = title or f"{feature} {kind}"
    ts = datetime.now(timezone.utc).isoformat()
    path.write_text(
        f"---\n"
        f"type: {kind}\n"
        f"generated_at: {ts}\n"
        f"source_hash: x\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"{body or 'Standard intro paragraph for this template.'}\n",
        encoding="utf-8",
    )


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    root = tmp_path / ".help" / "templates"
    # security-audit — all 11 kinds, will be featured
    for k in EXPECTED_KINDS:
        _write_template(root, "security-audit", k)
    # incomplete-feature — 2 kinds
    _write_template(root, "incomplete-feature", "concept")
    _write_template(root, "incomplete-feature", "task")
    # smart-test — picked up by featured fallback / curated
    for k in EXPECTED_KINDS:
        _write_template(root, "smart-test", k)
    cfg = Config(
        project_root=tmp_path,
        attune_home=tmp_path / "ah",
        allow_run=False,
        trusted_hosts=("testserver", "test"),
    )
    return TestClient(create_app(cfg))


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------


class TestHelpIndexApi:
    def test_returns_corpus_summary(self, client: TestClient) -> None:
        resp = client.get("/api/help/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_features"] == 3
        assert data["total_templates"] == 11 + 2 + 11
        assert data["incomplete_count"] == 1
        feature_names = {f["name"] for f in data["features"]}
        assert "security-audit" in feature_names
        assert "incomplete-feature" in feature_names


class TestHelpSearchApi:
    def test_empty_query_returns_empty_hits(self, client: TestClient) -> None:
        resp = client.get("/api/help/search?q=")
        assert resp.status_code == 200
        assert resp.json()["hits"] == []

    def test_query_returns_results_or_empty_gracefully(self, client: TestClient) -> None:
        # Tiny fixture, attune-rag might still return zero — test the shape
        resp = client.get("/api/help/search?q=security&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "limit" in data
        assert "hits" in data
        assert data["query"] == "security"
        assert data["limit"] == 5

    def test_limit_clamped(self, client: TestClient) -> None:
        resp = client.get("/api/help/search?q=x&limit=9999")
        assert resp.status_code == 200
        assert resp.json()["limit"] == 50


class TestHelpFeatureApi:
    def test_existing_feature(self, client: TestClient) -> None:
        resp = client.get("/api/help/feature/security-audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "security-audit"
        assert len(data["kinds"]) == 11

    def test_missing_feature_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/help/feature/nonexistent")
        assert resp.status_code == 404

    def test_invalid_slug_returns_400(self, client: TestClient) -> None:
        resp = client.get("/api/help/feature/Bad-Slug")
        assert resp.status_code == 400


class TestHelpTemplateApi:
    def test_existing_template(self, client: TestClient) -> None:
        resp = client.get("/api/help/template/security-audit/task")
        assert resp.status_code == 200
        data = resp.json()
        assert data["feature"] == "security-audit"
        assert data["kind"] == "task"
        assert "body" in data

    def test_missing_template_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/help/template/security-audit/nonexistent-kind")
        # Slug "nonexistent-kind" is shape-valid but file missing → 404
        assert resp.status_code == 404

    def test_invalid_feature_slug(self, client: TestClient) -> None:
        resp = client.get("/api/help/template/Bad/task")
        assert resp.status_code == 400

    def test_invalid_kind_slug(self, client: TestClient) -> None:
        resp = client.get("/api/help/template/security-audit/Bad-Kind")
        assert resp.status_code == 400


class TestHelpGapsApi:
    def test_returns_gap_report(self, client: TestClient) -> None:
        resp = client.get("/api/help/gaps")
        assert resp.status_code == 200
        data = resp.json()
        assert "incomplete" in data
        assert "stale" in data
        incomplete_names = {f["name"] for f in data["incomplete"]}
        assert "incomplete-feature" in incomplete_names


class TestHelpFeaturedApi:
    def test_returns_featured_list(self, client: TestClient) -> None:
        resp = client.get("/api/help/featured")
        assert resp.status_code == 200
        data = resp.json()
        assert "featured" in data
        names = [f["name"] for f in data["featured"]]
        # Curated picks include security-audit and smart-test
        assert "security-audit" in names


class TestHelpRecentApi:
    def test_returns_recent_list(self, client: TestClient) -> None:
        resp = client.get("/api/help/recent?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert "recent" in data
        assert len(data["recent"]) <= 3

    def test_limit_clamped(self, client: TestClient) -> None:
        resp = client.get("/api/help/recent?limit=9999")
        assert resp.status_code == 200
        assert len(resp.json()["recent"]) <= 20


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------


class TestHelpHomePage:
    def test_renders_home(self, client: TestClient) -> None:
        resp = client.get("/help")
        assert resp.status_code == 200
        body = resp.text
        assert "How can attune help?" in body
        assert "Admin tools" in body
        # Featured topic present
        assert "security-audit" in body


class TestHelpSearchPage:
    def test_empty_query_renders(self, client: TestClient) -> None:
        resp = client.get("/help/search?q=")
        assert resp.status_code == 200
        assert "Enter a query" in resp.text

    def test_with_query(self, client: TestClient) -> None:
        resp = client.get("/help/search?q=security")
        assert resp.status_code == 200
        assert "security" in resp.text


class TestHelpAdminPage:
    def test_renders_admin(self, client: TestClient) -> None:
        resp = client.get("/help/admin")
        assert resp.status_code == 200
        body = resp.text
        assert "Admin tools" in body
        # incomplete-feature shows up in the incomplete table
        assert "incomplete-feature" in body
        # Report-only surface (T4 retired the regen actions): no
        # regen buttons, and the release-prep guidance is present.
        assert "Regenerate all stale" not in body
        assert "data-regen-action" not in body
        assert "/coach maintain" in body


class TestHelpFeaturePage:
    def test_renders_feature(self, client: TestClient) -> None:
        resp = client.get("/help/security-audit")
        assert resp.status_code == 200
        body = resp.text
        assert "security-audit" in body
        assert "task" in body

    def test_missing_feature_404(self, client: TestClient) -> None:
        resp = client.get("/help/nonexistent")
        assert resp.status_code == 404

    def test_invalid_slug_400(self, client: TestClient) -> None:
        resp = client.get("/help/Bad-Slug")
        assert resp.status_code == 400


class TestHelpTemplatePage:
    def test_renders_template(self, client: TestClient) -> None:
        resp = client.get("/help/security-audit/task")
        assert resp.status_code == 200
        body = resp.text
        # H1 rendered from markdown
        assert "security-audit task" in body
        # Sidebar shows sibling kinds
        assert "concept" in body
        assert "reference" in body

    def test_missing_template_404(self, client: TestClient) -> None:
        resp = client.get("/help/security-audit/nonexistent-kind")
        assert resp.status_code == 404

    def test_invalid_feature_400(self, client: TestClient) -> None:
        resp = client.get("/help/Bad-Slug/task")
        assert resp.status_code == 400

    def test_invalid_kind_400(self, client: TestClient) -> None:
        resp = client.get("/help/security-audit/Bad-Kind")
        assert resp.status_code == 400
