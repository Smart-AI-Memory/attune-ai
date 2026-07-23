"""Exceptions-first attention header (roundtable-ruled, issue #1612).

Facts must be exact: hydration age from the hydrator's own stamp,
drift from corpus-file mtimes vs that stamp, pending count from
board thread meta. Header renders only when an exception exists.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops import memory_data
from attune.ops.config import Config
from attune.ops.memory_data import STALE_AFTER_HOURS, read_attention
from attune.ops.server import create_app

from .test_memory_page import FakeRedis


def _stamp(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _project(tmp_path: Path, lessons_mtime_hours_ago: float) -> Path:
    root = tmp_path / "proj"
    (root / ".claude").mkdir(parents=True)
    lessons = root / ".claude" / "lessons.md"
    lessons.write_text("# lessons\n", encoding="utf-8")
    ago = datetime.now(timezone.utc) - timedelta(hours=lessons_mtime_hours_ago)
    os.utime(lessons, (ago.timestamp(), ago.timestamp()))
    return root


class TestReadAttention:
    def test_unreachable_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(memory_data, "connect", lambda url=None: None)
        assert read_attention(_project(tmp_path, 5)) is None

    def test_fresh_hydration_no_exceptions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = {"attune:memory:hydrated_at": _stamp(1.0)}
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        attention = read_attention(_project(tmp_path, 5))
        assert attention is not None
        assert attention.stale is False
        assert attention.changed_since == []
        assert attention.pending_threads == 0
        assert attention.has_exceptions is False

    def test_old_hydration_is_stale(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = {"attune:memory:hydrated_at": _stamp(STALE_AFTER_HOURS + 2)}
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        attention = read_attention(_project(tmp_path, STALE_AFTER_HOURS + 5))
        assert attention is not None
        assert attention.stale is True
        assert attention.age_hours is not None
        assert attention.has_exceptions is True

    def test_missing_stamp_is_stale(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis({}))
        attention = read_attention(_project(tmp_path, 5))
        assert attention is not None
        assert attention.stale is True
        assert attention.age_hours is None

    def test_corpus_changed_after_hydration_lists_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = {"attune:memory:hydrated_at": _stamp(6.0)}
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        attention = read_attention(_project(tmp_path, 1.0))
        assert attention is not None
        assert attention.changed_since == [".claude/lessons.md"]
        assert attention.has_exceptions is True

    def test_pending_threads_counted_promoted_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = {
            "attune:memory:hydrated_at": _stamp(1.0),
            "attune:roundtable:thread:q-a-001:meta": {"seq": "4"},
            "attune:roundtable:thread:q-b-001:meta": {
                "seq": "9",
                "status": "promoted",
            },
        }
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        attention = read_attention(_project(tmp_path, 5))
        assert attention is not None
        assert attention.pending_threads == 1


class TestHeaderRendering:
    @pytest.fixture()
    def client(self, tmp_path: Path) -> TestClient:
        project = _project(tmp_path, 1.0)
        cfg = Config(project_root=project, attune_home=tmp_path / "attune-home")
        c = TestClient(create_app(cfg))
        c.headers["Host"] = f"{cfg.host}:{cfg.port}"
        return c

    def test_header_absent_when_no_exceptions(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = {"attune:memory:hydrated_at": _stamp(0.5)}
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        resp = client.get("/memory")
        assert resp.status_code == 200
        assert "memory-attention" not in resp.text

    def test_header_renders_stale_and_pending(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = {
            "attune:memory:hydrated_at": _stamp(STALE_AFTER_HOURS + 3),
            "attune:roundtable:thread:q-x-001:meta": {"seq": "2"},
        }
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        resp = client.get("/memory")
        assert resp.status_code == 200
        assert "memory-attention" in resp.text
        assert "Hydration stale" in resp.text
        assert "Deliberation threads pending promotion" in resp.text
        assert "/roundtable promote" in resp.text

    def test_header_never_500s_on_bad_stamp(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = {"attune:memory:hydrated_at": "not-a-timestamp"}
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        resp = client.get("/memory")
        assert resp.status_code == 200
        assert "Hydration stale" in resp.text
