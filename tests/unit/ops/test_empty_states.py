"""D2 empty/error-state sweep (ops-dashboard-polish).

The unified pass the D2 row asked for: every dashboard page must
render meaningfully — HTTP 200 plus either real content or an
explicit empty-state message — when its data source is empty,
missing, or unreachable. A blank project root IS the empty condition
for most sources (no docs/specs/, no telemetry jsonl, no runs); the
rest are simulated at the data-layer boundary.

Each test asserts a HUMAN-MEANINGFUL marker string, not just a 200 —
a page that 200s into a bare table with no explanation fails D2's
"renders meaningfully" bar.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops.config import Config
from attune.ops.server import create_app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App over a blank project root and blank attune-home."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    project = tmp_path / "project"
    project.mkdir()
    cfg = Config(project_root=project, attune_home=tmp_path / "attune-home")
    app = create_app(cfg)
    c = TestClient(app)
    c.headers["Host"] = f"{cfg.host}:{cfg.port}"
    return c


class TestEmptySources:
    def test_home_renders_with_no_telemetry(self, client: TestClient) -> None:
        """Empty jsonl → zero KPIs with honest footnotes, not a crash."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "no activity yet today" in resp.text

    def test_home_recent_runs_empty_state(self, client: TestClient) -> None:
        resp = client.get("/")
        assert "No runs yet this session" in resp.text

    def test_workflows_page_with_no_workflows(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulates attune-ai not importable in the server venv."""
        from attune.ops import data

        monkeypatch.setattr(data, "list_workflows", lambda: [])
        resp = client.get("/workflows")
        assert resp.status_code == 200
        assert "No workflows are visible" in resp.text

    def test_specs_page_with_no_specs_dir(self, client: TestClient) -> None:
        """Blank project root has no docs/specs/ at all."""
        resp = client.get("/specs")
        assert resp.status_code == 200
        assert "No specs" in resp.text

    def test_telemetry_page_with_empty_jsonl(self, client: TestClient) -> None:
        resp = client.get("/telemetry")
        assert resp.status_code == 200
        assert "No telemetry" in resp.text

    def test_runs_history_api_with_no_runs(self, client: TestClient) -> None:
        """Run history is an API surface (feeds the workflows page);
        with no persisted runs it must return a clean empty list."""
        resp = client.get("/api/runs/code-review")
        assert resp.status_code == 200
        assert resp.json() == {"workflow": "code-review", "runs": []}

    def test_health_page_without_api_key(self, client: TestClient) -> None:
        """ANTHROPIC_API_KEY unset must render guidance, not crash."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "ANTHROPIC_API_KEY" in resp.text

    # NOTE (D2 sweep findings, 2026-07-21):
    # - /memory's unreachable-Redis empty state is asserted in
    #   test_memory_page.py (rides the C1 held draft, not main yet).
    # - There is NO /sessions page on main — the C2 row's "done"
    #   claim is stale; recorded in the spec's decisions.md.

    def test_health_library_with_no_snapshot(self, client: TestClient) -> None:
        resp = client.get("/health/library")
        assert resp.status_code == 200
        assert "No snapshot" in resp.text

    def test_unknown_page_renders_styled_404(self, client: TestClient) -> None:
        resp = client.get("/definitely-not-a-page")
        assert resp.status_code == 404
        assert "attune ops" in resp.text
