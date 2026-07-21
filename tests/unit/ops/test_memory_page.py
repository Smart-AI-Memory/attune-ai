"""Memory page (ops-dashboard-polish C1/C3): data layer + routes.

Spec: docs/specs/ops-dashboard-polish/ — C1 premise re-validated
2026-07-21 against the post-#1239 Redis-derived index.

Covers the degradation contract (unreachable Redis renders an
explanatory empty state, never a 500), family bucketing + pagination,
the detail view's namespace guard, and the Home KPI's hide-on-None
behavior. Redis is faked at the client boundary — no server needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops import memory_data
from attune.ops.config import Config
from attune.ops.memory_data import (
    MEMORY_KEY_PREFIX,
    read_node,
    read_overview,
)
from attune.ops.server import create_app


class FakeWrongType(Exception):
    """Stands in for redis.exceptions.ResponseError WRONGTYPE."""


class FakePipeline:
    """Values in the store may be dicts (hashes) or strs (strings) —
    HMGET on a string yields an in-list exception when
    ``raise_on_error=False``, mirroring redis-py."""

    def __init__(self, store: dict[str, object]) -> None:
        self._store = store
        self._calls: list[tuple[str, tuple[str, ...]]] = []

    def hmget(self, key: str, *fields: str) -> None:
        self._calls.append((key, fields))

    def execute(self, raise_on_error: bool = True) -> list[object]:
        results: list[object] = []
        for key, fields in self._calls:
            value = self._store.get(key, {})
            if isinstance(value, dict):
                results.append([value.get(f) for f in fields])
            elif raise_on_error:
                raise FakeWrongType("WRONGTYPE")
            else:
                results.append(FakeWrongType("WRONGTYPE"))
        return results


class FakeRedis:
    """Just enough of redis-py for the memory data layer."""

    def __init__(self, store: dict[str, object]) -> None:
        self._store = store

    def ping(self) -> bool:
        return True

    def scan_iter(self, match: str, count: int = 10):
        prefix = match.rstrip("*")
        yield from (k for k in self._store if k.startswith(prefix))

    def pipeline(self, transaction: bool = True) -> FakePipeline:
        return FakePipeline(self._store)

    def type(self, key: str) -> str:
        value = self._store.get(key)
        if value is None:
            return "none"
        return "hash" if isinstance(value, dict) else "string"

    def hgetall(self, key: str) -> dict[str, str]:
        value = self._store.get(key, {})
        if not isinstance(value, dict):
            raise FakeWrongType("WRONGTYPE")
        return dict(value)

    def get(self, key: str) -> str | None:
        value = self._store.get(key)
        return value if isinstance(value, str) else None


def _store() -> dict[str, object]:
    return {
        f"{MEMORY_KEY_PREFIX}curated:north_star": {
            "type": "project",
            "description": "the ratified direction",
            "updated_at": "2026-07-21",
            "text": "one wheel",
        },
        f"{MEMORY_KEY_PREFIX}lesson:42": {"text": "bulk sed sweeps need audits"},
        f"{MEMORY_KEY_PREFIX}file:global:feedback_x": {
            "type": "feedback",
            "description": "pointer",
        },
        # A plain-string marker key in the namespace — the live index
        # has these (attune:memory:context); they must not degrade the
        # page (2026-07-21 dogfood catch).
        f"{MEMORY_KEY_PREFIX}context": "hydrated 2026-07-21",
        "unrelated:key": {"text": "never listed"},
    }


@pytest.fixture()
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    client = FakeRedis(_store())
    monkeypatch.setattr(memory_data, "connect", lambda url=None: client)
    return client


@pytest.fixture()
def unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_data, "connect", lambda url=None: None)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    project = tmp_path / "project"
    project.mkdir()
    cfg = Config(project_root=project, attune_home=tmp_path / "attune-home")
    app = create_app(cfg)
    c = TestClient(app)
    c.headers["Host"] = f"{cfg.host}:{cfg.port}"
    return c


class TestDataLayer:
    def test_unreachable_returns_none(self, unreachable: None) -> None:
        assert read_overview() is None
        assert read_node(f"{MEMORY_KEY_PREFIX}lesson:42") is None
        assert memory_data.node_count() is None

    def test_family_counts_and_rows(self, fake: FakeRedis) -> None:
        overview = read_overview()
        assert overview is not None
        assert overview.total == 4  # unrelated:key never counted
        assert overview.family_counts == {
            "curated": 1,
            "lesson": 1,
            "file": 1,
            "context": 1,
        }
        assert {r.family for r in overview.rows} == {"curated", "lesson", "file", "context"}
        curated = next(r for r in overview.rows if r.family == "curated")
        assert curated.name == "north_star"
        assert curated.node_type == "project"
        assert curated.description == "the ratified direction"

    def test_family_filter(self, fake: FakeRedis) -> None:
        overview = read_overview(family="lesson")
        assert overview is not None
        assert [r.family for r in overview.rows] == ["lesson"]
        # Counts still cover every family even when filtered.
        assert overview.family_counts["curated"] == 1

    def test_pagination_windows_and_clamps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store = {
            f"{MEMORY_KEY_PREFIX}lesson:{i:04d}": {"text": str(i)}
            for i in range(memory_data.PAGE_SIZE + 3)
        }
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        first = read_overview(page=1)
        second = read_overview(page=2)
        clamped = read_overview(page=99)
        assert first is not None and second is not None and clamped is not None
        assert len(first.rows) == memory_data.PAGE_SIZE
        assert len(second.rows) == 3
        assert first.pages == 2
        # Out-of-range pages clamp to the last page, not an empty table.
        assert clamped.page == 2
        assert len(clamped.rows) == 3

    def test_read_node_namespace_guard(self, fake: FakeRedis) -> None:
        # The guard fires BEFORE any Redis read — a key outside the
        # memory namespace is refused even though the store has it.
        assert read_node("unrelated:key") is None

    def test_read_node_returns_fields(self, fake: FakeRedis) -> None:
        fields = read_node(f"{MEMORY_KEY_PREFIX}curated:north_star")
        assert fields is not None
        assert fields["text"] == "one wheel"

    def test_read_node_missing_key(self, fake: FakeRedis) -> None:
        assert read_node(f"{MEMORY_KEY_PREFIX}curated:nope") is None

    def test_node_count(self, fake: FakeRedis) -> None:
        assert memory_data.node_count() == 4

    def test_string_key_does_not_degrade_overview(self, fake: FakeRedis) -> None:
        """The live-index regression (2026-07-21): a plain-string key in
        the namespace must yield an empty-fields row, not kill the page."""
        overview = read_overview()
        assert overview is not None
        context_row = next(r for r in overview.rows if r.family == "context")
        assert context_row.node_type == ""
        assert context_row.description == ""

    def test_read_node_string_key(self, fake: FakeRedis) -> None:
        fields = read_node(f"{MEMORY_KEY_PREFIX}context")
        assert fields == {"value": "hydrated 2026-07-21"}


class TestRoutes:
    def test_page_degrades_when_unreachable(self, client: TestClient, unreachable: None) -> None:
        resp = client.get("/memory")
        assert resp.status_code == 200
        assert "Memory index unreachable" in resp.text

    def test_page_renders_families_and_rows(self, client: TestClient, fake: FakeRedis) -> None:
        resp = client.get("/memory")
        assert resp.status_code == 200
        assert "north_star" in resp.text
        assert "Lessons" in resp.text
        assert "the ratified direction" in resp.text

    def test_nav_contains_memory(self, client: TestClient, unreachable: None) -> None:
        resp = client.get("/memory")
        assert 'href="/memory"' in resp.text

    def test_node_detail_renders(self, client: TestClient, fake: FakeRedis) -> None:
        key = f"{MEMORY_KEY_PREFIX}curated:north_star"
        resp = client.get("/memory/node", params={"key": key})
        assert resp.status_code == 200
        assert "one wheel" in resp.text

    def test_node_detail_404_outside_namespace(self, client: TestClient, fake: FakeRedis) -> None:
        resp = client.get("/memory/node", params={"key": "unrelated:key"})
        assert resp.status_code == 404
        assert "not a readable memory node" in resp.text

    def test_home_kpi_hidden_when_unreachable(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(memory_data, "node_count", lambda client=None: None)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Memory nodes" not in resp.text

    def test_home_kpi_shown_with_count(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(memory_data, "node_count", lambda client=None: 1053)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Memory nodes" in resp.text
        assert "1,053" in resp.text
