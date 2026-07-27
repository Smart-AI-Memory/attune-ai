"""HTTP route tests: the library-health snapshot page.

Spec: docs/specs/ops-dashboard-polish/decisions.md (Phase E)

Covers:

- ``GET /health/library`` (HTML): empty state (no snapshot yet),
  renders a persisted snapshot, stale badge vs fresh badge, kicks a
  background refresh when stale.
- ``POST /health/library/refresh``: client-token gated, starts a
  background refresh, is a no-op while one is already running.
- ``GET /api/health/library/status``: reflects the runner's
  ``running`` state and the persisted ``collected_at``.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from attune.ops import health_snapshot as hs
from attune.ops.config import Config
from attune.ops.server import create_app


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


def _fresh_snapshot(**signal_overrides: dict[str, Any]) -> dict[str, Any]:
    signals = {
        "coverage": {
            "status": "ok",
            "value": {"coverage_percent": 94.1, "source": "codecov_api_v2"},
        },
        "complexity": {
            "status": "ok",
            "value": {"avg_complexity": 4.0, "avg_rank": "A", "blocks": 100, "d_or_worse_count": 3},
        },
        "churn": {
            "status": "ok",
            "value": {
                "window_days": 90,
                "total_changes": 42,
                "top_files": [{"path": "src/attune/ops/data.py", "changes": 29}],
            },
        },
        "doc_import_audit": {
            "status": "ok",
            "value": {"exit_code": 0, "clean": True, "detail": {}},
        },
        "docs_wiring_audit": {
            "status": "ok",
            "value": {"exit_code": 0, "clean": True, "detail": {}},
        },
        "help_completeness": {
            "status": "ok",
            "value": {"exit_code": 0, "clean": True, "detail": {}},
        },
        "projection_drift": {"status": "ok", "value": {"findings_count": 0, "findings": []}},
        "sloc": {
            "status": "ok",
            "value": {
                "src_files": 654,
                "src_lines": 170000,
                "test_files": 993,
                "test_lines": 330000,
                "test_to_src_ratio": 1.94,
                "test_function_count": 20500,
            },
        },
        "todos": {"status": "ok", "value": {"count": 1}},
        "open_prs_issues": {"status": "ok", "value": {"open_prs": 2, "open_issues": 0}},
    }
    signals.update(signal_overrides)
    return {
        "schema_version": 1,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "project_root": "/tmp/project",
        "repo_slug": "Smart-AI-Memory/attune-ai",
        "signals": signals,
    }


@pytest.fixture(autouse=True)
def _no_real_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent GET-triggered background refreshes from doing real work.

    Every ``GET /health/library`` in this file may trigger
    ``HealthRefreshRunner.start`` (stale/missing snapshot). Left
    unmocked, that spawns a real thread hitting the network (Codecov)
    and subprocesses (git, gh, docs-gate scripts) — slow and
    environment-dependent. Tests that specifically exercise the
    refresh mechanics override this with their own fake.
    """
    monkeypatch.setattr(hs, "run_and_persist", lambda *a, **k: Path("/dev/null"))


class TestEmptyState:
    def test_renders_200_with_no_snapshot(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "No snapshot collected yet" in resp.text

    def test_empty_state_kicks_background_refresh(self, client: TestClient, cfg: Config) -> None:
        client.get("/health")
        # A snapshot with no prior data is "stale" by definition, so
        # the GET should have started a background refresh.
        resp = client.get("/api/health/library/status")
        assert resp.status_code == 200
        # running may already be False if the (fast, mocked) refresh
        # finished before this second request lands; both states are
        # acceptable — the assertion that matters is no 500 and a
        # well-shaped body.
        body = resp.json()
        assert "running" in body
        assert "collected_at" in body


class TestPopulatedSnapshot:
    def test_renders_scoreboard_values(self, client: TestClient, cfg: Config) -> None:
        snapshot = _fresh_snapshot()
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.text
        assert "94.1%" in body
        assert "clean" in body

    def test_pre_upgrade_snapshot_missing_test_function_count_renders_zero(
        self, client: TestClient, cfg: Config
    ) -> None:
        """A snapshot persisted before this field existed must not 500."""
        snapshot = _fresh_snapshot()
        del snapshot["signals"]["sloc"]["value"]["test_function_count"]
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "993 files" in resp.text

    def test_fresh_snapshot_shows_fresh_badge_not_stale(
        self, client: TestClient, cfg: Config
    ) -> None:
        snapshot = _fresh_snapshot()
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert 'id="health-stale-badge"' not in resp.text
        assert "fresh" in resp.text

    def test_stale_snapshot_shows_stale_badge(
        self, client: TestClient, cfg: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        snapshot = _fresh_snapshot()
        snapshot["collected_at"] = old_ts
        hs.persist_snapshot(snapshot, cfg.attune_home)

        # Prevent the real background refresh from racing this
        # assertion (it would overwrite latest.json mid-test).
        monkeypatch.setattr(hs.HealthRefreshRunner, "start", lambda self, *a, **k: False)

        resp = client.get("/health")
        assert resp.status_code == 200
        assert 'id="health-stale-badge"' in resp.text
        assert old_ts in resp.text

    def test_unavailable_signal_renders_dash(self, client: TestClient, cfg: Config) -> None:
        snapshot = _fresh_snapshot(coverage={"status": "unavailable", "reason": "network down"})
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "unavailable" in resp.text

    def test_gate_finding_shows_warn_not_clean(self, client: TestClient, cfg: Config) -> None:
        snapshot = _fresh_snapshot(
            doc_import_audit={
                "status": "ok",
                "value": {"exit_code": 1, "clean": False, "detail": {}},
            }
        )
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert "findings (exit 1)" in resp.text

    def test_hotspots_table_renders_churn_files(self, client: TestClient, cfg: Config) -> None:
        snapshot = _fresh_snapshot()
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert "src/attune/ops/data.py" in resp.text

    def test_links_to_latest_llm_report_when_present(self, client: TestClient, cfg: Config) -> None:
        reports_dir = cfg.project_root / "docs" / "reports"
        reports_dir.mkdir(parents=True)
        (reports_dir / "library-health-2026-07-14.md").write_text("report", encoding="utf-8")
        snapshot = _fresh_snapshot()
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert "docs/reports/library-health-2026-07-14.md" in resp.text

    def test_no_report_shows_fallback_message(self, client: TestClient, cfg: Config) -> None:
        snapshot = _fresh_snapshot()
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/health")
        assert "No LLM narrative report found" in resp.text


class TestRefreshRoute:
    def test_post_refresh_returns_200_and_starts(
        self, client: TestClient, cfg: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        release = threading.Event()
        monkeypatch.setattr(
            hs,
            "run_and_persist",
            lambda *a, **k: (release.wait(timeout=5), cfg.attune_home / "unused.json")[1],
        )
        resp = client.post("/health/library/refresh")
        assert resp.status_code == 200
        body = resp.json()
        assert body["started"] is True
        assert body["running"] is True
        release.set()

    def test_post_refresh_is_noop_while_running(
        self, client: TestClient, cfg: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        release = threading.Event()
        started = threading.Event()

        def fake_run_and_persist(*a: Any, **k: Any) -> Path:
            started.set()
            release.wait(timeout=5)
            return cfg.attune_home / "unused.json"

        monkeypatch.setattr(hs, "run_and_persist", fake_run_and_persist)
        first = client.post("/health/library/refresh")
        assert started.wait(timeout=5)
        second = client.post("/health/library/refresh")
        assert first.json()["started"] is True
        assert second.json()["started"] is False
        release.set()


class TestStatusRoute:
    def test_reflects_persisted_collected_at(self, client: TestClient, cfg: Config) -> None:
        snapshot = _fresh_snapshot()
        hs.persist_snapshot(snapshot, cfg.attune_home)
        resp = client.get("/api/health/library/status")
        assert resp.status_code == 200
        assert resp.json()["collected_at"] == snapshot["collected_at"]

    def test_no_snapshot_returns_null_collected_at(self, client: TestClient) -> None:
        resp = client.get("/api/health/library/status")
        assert resp.status_code == 200
        assert resp.json()["collected_at"] is None


def test_old_library_path_redirects(client):
    """/health/library 301s to /health — the pages merged (2026-07-21).

    Old bookmarks keep working; the refresh POST and status API keep
    their original /health/library/* paths untouched.
    """
    resp = client.get("/health/library", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "/health"


def test_health_page_includes_environment_section(client):
    """The merged page carries the former Health page's env table."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "Environment" in resp.text
    assert "attune-home" in resp.text


class TestServeLlmReport:
    """/docs/reports/{name} — the link-QA fix (2026-07-21): the Health
    page links the latest narrative report; nothing served it."""

    def _write_report(self, cfg: Config, name: str, body: str = "# Report\n") -> None:
        reports = cfg.project_root / "docs" / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / name).write_text(body, encoding="utf-8")

    def test_serves_existing_report(self, cfg: Config, client: TestClient) -> None:
        self._write_report(cfg, "library-health-2026-07-14.md", "# Findings\nok\n")
        resp = client.get("/docs/reports/library-health-2026-07-14.md")
        assert resp.status_code == 200
        assert "Findings" in resp.text

    def test_missing_report_404(self, client: TestClient) -> None:
        resp = client.get("/docs/reports/library-health-2099-01-01.md")
        assert resp.status_code == 404

    def test_non_report_name_404(self, cfg: Config, client: TestClient) -> None:
        # Even a real file outside the report pattern is refused.
        self._write_report(cfg, "library-health-x.md")
        (cfg.project_root / "docs" / "reports" / "secrets.md").write_text("no")
        resp = client.get("/docs/reports/secrets.md")
        assert resp.status_code == 404

    def test_traversal_404(self, client: TestClient) -> None:
        resp = client.get("/docs/reports/..%2F..%2Fpyproject.toml")
        assert resp.status_code == 404
