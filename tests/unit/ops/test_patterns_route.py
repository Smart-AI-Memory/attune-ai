"""Tests for the dashboard /patterns route (pattern-review-queue R6).

Exercised against a real ``FileStashBackend`` (injected via
``app.state.pattern_backend``) so the stage → render → promote/reject
lifecycle round-trips through the actual backend, not a mock. The
``tests/unit/ops/conftest.py`` autouse fixture nulls the session token,
so the no-header POSTs here satisfy ``require_client_token``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.memory.file_stash import FileStashBackend
from attune.memory.types import StagedPattern
from attune.ops.config import Config
from attune.ops.server import create_app
from attune.pattern_review import (
    ACTIVE_PREFIX,
    STAGED_PREFIX,
    PatternReviewQueue,
    PersistentPatternLibrary,
)


@pytest.fixture
def backend(tmp_path: Path) -> FileStashBackend:
    return FileStashBackend(base_dir=str(tmp_path / "stash"))


@pytest.fixture
def client(tmp_path: Path, backend: FileStashBackend) -> TestClient:
    cfg = Config(
        project_root=tmp_path,
        attune_home=tmp_path / "ah",
        allow_run=False,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(cfg)
    # Route reads app.state.pattern_backend; the queue/library share it so
    # the dashboard and the test see one store.
    app.state.pattern_backend = backend
    return TestClient(app)


def _staged(
    pattern_id: str = "p1",
    *,
    agent_id: str = "a1",
    pattern_type: str = "behavioral",
    name: str = "Retry on 503",
    confidence: float = 0.8,
    code: str | None = "x = 1",
) -> StagedPattern:
    return StagedPattern(
        pattern_id=pattern_id,
        agent_id=agent_id,
        pattern_type=pattern_type,
        name=name,
        description="desc",
        code=code,
        confidence=confidence,
    )


def _stage(backend: FileStashBackend, *patterns: StagedPattern) -> None:
    queue = PatternReviewQueue(backend=backend)
    for p in patterns:
        queue.stage(p)


class TestGetPatternsPage:
    def test_renders_staged_patterns(self, client, backend):
        _stage(
            backend,
            _staged("p1", name="Retry on 503", pattern_type="behavioral"),
            _staged("p2", name="Cache the parse", pattern_type="performance"),
        )
        resp = client.get("/patterns")
        assert resp.status_code == 200
        body = resp.text
        assert "Retry on 503" in body
        assert "Cache the parse" in body
        assert "behavioral" in body
        assert "2 staged" in body

    def test_empty_queue_shows_empty_state(self, client):
        resp = client.get("/patterns")
        assert resp.status_code == 200
        assert "The review queue is empty" in resp.text


class TestPromote:
    def test_promote_moves_to_library_and_clears_queue(self, client, backend):
        _stage(backend, _staged("p1"))

        resp = client.post("/patterns/promote", json={"pattern_id": "p1"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Dropped from the staging queue...
        assert backend.retrieve(STAGED_PREFIX + "p1") in (None, {}, "")
        # ...and durable in the active library prefix.
        lib = PersistentPatternLibrary(backend=backend)
        assert lib.get_pattern("p1") is not None
        assert backend.retrieve(ACTIVE_PREFIX + "p1") is not None

    def test_promote_unknown_id_returns_404(self, client):
        resp = client.post("/patterns/promote", json={"pattern_id": "nope"})
        assert resp.status_code == 404
        assert resp.json()["ok"] is False

    def test_promote_requires_pattern_id(self, client):
        resp = client.post("/patterns/promote", json={})
        assert resp.status_code == 400
        assert resp.json()["ok"] is False

    def test_promote_duplicate_in_library_returns_409_and_keeps_staged(self, client, backend):
        # Pre-seed the active library with p1, then stage another p1.
        lib = PersistentPatternLibrary(backend=backend)
        lib.contribute_pattern("a1", PatternReviewQueue._to_pattern(_staged("p1")))
        _stage(backend, _staged("p1", name="dup"))

        resp = client.post("/patterns/promote", json={"pattern_id": "p1"})
        assert resp.status_code == 409
        assert resp.json()["ok"] is False
        # Still staged — reviewer can rename or reject.
        assert PatternReviewQueue(backend=backend).get("p1") is not None


class TestReject:
    def test_reject_drops_from_queue(self, client, backend):
        _stage(backend, _staged("p1"))

        resp = client.post("/patterns/reject", json={"pattern_id": "p1", "reason": "noise"})
        assert resp.status_code == 200
        assert resp.json()["removed"] is True
        assert PatternReviewQueue(backend=backend).get("p1") is None

    def test_reject_unknown_id_returns_404(self, client):
        resp = client.post("/patterns/reject", json={"pattern_id": "nope"})
        assert resp.status_code == 404
        assert resp.json()["ok"] is False

    def test_reject_requires_pattern_id(self, client):
        resp = client.post("/patterns/reject", json={})
        assert resp.status_code == 400
        assert resp.json()["ok"] is False


class TestTokenGate:
    def test_promote_rejected_without_token_when_gate_active(self, client, backend, monkeypatch):
        # Re-arm the token (conftest nulls it) to prove the gate is wired.
        monkeypatch.setattr("attune.ops.security._SESSION_TOKEN", "real-token")
        _stage(backend, _staged("p1"))
        resp = client.post("/patterns/promote", json={"pattern_id": "p1"})
        assert resp.status_code == 403

    def test_reject_rejected_without_token_when_gate_active(self, client, backend, monkeypatch):
        monkeypatch.setattr("attune.ops.security._SESSION_TOKEN", "real-token")
        _stage(backend, _staged("p1"))
        resp = client.post("/patterns/reject", json={"pattern_id": "p1"})
        assert resp.status_code == 403
