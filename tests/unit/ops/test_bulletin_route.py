"""Tests for the /api/bulletin/active route."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.bulletin import BulletinEntry, FileBulletinBackend
from attune.ops.config import Config
from attune.ops.server import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """FastAPI test client with attune_home pointed at tmp_path."""
    cfg = Config(
        project_root=tmp_path,
        attune_home=tmp_path / "ah",
        allow_run=False,
        trusted_hosts=("testserver", "test"),
    )
    return TestClient(create_app(cfg))


def _seed(
    attune_home: Path,
    *,
    actor_id: str = "actor-1",
    workflow: str = "code-review",
    run_id: str = "run-1",
    status: str = "running",
    heartbeat: str | None = None,
    scope: str | None = None,
) -> None:
    """Write a bulletin entry to ``<attune_home>/bulletin/`` directly."""
    backend = FileBulletinBackend(attune_home / "bulletin")
    backend.append(
        BulletinEntry(
            actor_id=actor_id,
            actor_kind="cli",
            workflow=workflow,
            run_id=run_id,
            current_status=status,  # type: ignore[arg-type]
            scope=scope,
            last_heartbeat=heartbeat or datetime.now(timezone.utc).isoformat(),
        )
    )


class TestEmptyState:
    def test_no_bulletin_dir_returns_empty_list(self, client: TestClient) -> None:
        """The route works even before any actor has written."""
        resp = client.get("/api/bulletin/active")
        assert resp.status_code == 200
        assert resp.json() == {"entries": []}


class TestPopulated:
    def test_single_entry_returned(self, client: TestClient, tmp_path: Path) -> None:
        _seed(tmp_path / "ah", run_id="run-1")
        resp = client.get("/api/bulletin/active")
        data = resp.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["run_id"] == "run-1"
        assert data["entries"][0]["current_status"] == "running"

    def test_multiple_actors_visible(self, client: TestClient, tmp_path: Path) -> None:
        _seed(tmp_path / "ah", actor_id="actor-A", run_id="A-1")
        _seed(tmp_path / "ah", actor_id="actor-B", run_id="B-1")
        resp = client.get("/api/bulletin/active")
        actors = {e["actor_id"] for e in resp.json()["entries"]}
        assert actors == {"actor-A", "actor-B"}

    def test_scope_propagated(self, client: TestClient, tmp_path: Path) -> None:
        _seed(tmp_path / "ah", scope="src/attune/ops/", run_id="r1")
        entry = resp_first(client.get("/api/bulletin/active"))
        assert entry["scope"] == "src/attune/ops/"


class TestStaleAndTerminal:
    def test_stale_entry_filtered(self, client: TestClient, tmp_path: Path) -> None:
        """Entries with heartbeat > 90s old are dropped (backend filters)."""
        old = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        _seed(tmp_path / "ah", heartbeat=old, run_id="r-stale")
        resp = client.get("/api/bulletin/active")
        assert resp.json()["entries"] == []

    @pytest.mark.parametrize("status", ["completed", "failed", "cancelled"])
    def test_terminal_entry_filtered(self, client: TestClient, tmp_path: Path, status: str) -> None:
        """Terminal entries don't appear in the active list."""
        # Write a running record then a terminal one for the same run.
        _seed(tmp_path / "ah", run_id="r-done")
        _seed(
            tmp_path / "ah",
            run_id="r-done",
            status=status,
            heartbeat=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
        )
        resp = client.get("/api/bulletin/active")
        assert resp.json()["entries"] == []


class TestPayloadShape:
    def test_response_has_entries_key(self, client: TestClient, tmp_path: Path) -> None:
        _seed(tmp_path / "ah", run_id="r1")
        body = client.get("/api/bulletin/active").json()
        assert "entries" in body
        assert isinstance(body["entries"], list)

    def test_entry_fields_match_dataclass(self, client: TestClient, tmp_path: Path) -> None:
        _seed(tmp_path / "ah", run_id="r1")
        entry = resp_first(client.get("/api/bulletin/active"))
        expected_keys = {
            "actor_id",
            "actor_kind",
            "workflow",
            "run_id",
            "started_at",
            "last_heartbeat",
            "current_status",
            "scope",
            "hostname",
        }
        assert set(entry.keys()) == expected_keys


class TestBackendFailure:
    """The route must swallow backend errors — bulletin is advisory."""

    def test_backend_exception_returns_empty_list(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A backend that raises must not produce a 500 — return [] instead."""

        def _boom(self, *_a, **_kw):
            raise RuntimeError("catastrophic backend error")

        # Patch the bulletin's read_active to raise — covers the
        # except Exception guard in the route handler.
        monkeypatch.setattr("attune.bulletin.FileBulletinBackend.read_active", _boom)

        resp = client.get("/api/bulletin/active")
        assert resp.status_code == 200
        assert resp.json() == {"entries": []}


def resp_first(resp) -> dict:
    """Return the first entry from a response payload."""
    body = resp.json()
    assert body["entries"], "expected at least one entry"
    return body["entries"][0]
