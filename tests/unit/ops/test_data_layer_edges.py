"""Edge coverage for the collab-inbox and memory-page data layers.

Existing suites mock ``_connect``/``connect`` and drive happy paths;
these tests cover the raw seams those mocks skip: real client
construction (via ``sys.modules`` fakes, never a live Redis), the
read-only git allowlist, packet-frontmatter parsing, and every
degrade branch in the memory readers. All keyless and network-free.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from attune.ops import collab_data, memory_data
from attune.ops.collab_data import read_inbox, read_thread
from attune.ops.memory_data import (
    MEMORY_KEY_PREFIX,
    _build_row,
    _edge_preview,
    _first_line,
    node_count,
    read_attention,
    read_node,
    read_overview,
)

from .test_memory_page import FakeRedis


class _FakePingableClient:
    def __init__(self, fail_ping: bool = False) -> None:
        self.fail_ping = fail_ping

    def ping(self) -> bool:
        if self.fail_ping:
            raise ConnectionError("refused")
        return True


def _fake_redis_module(client: _FakePingableClient) -> SimpleNamespace:
    class _FakeRedisCls:
        @staticmethod
        def from_url(url: str, **kwargs: object) -> _FakePingableClient:
            return client

    return SimpleNamespace(Redis=_FakeRedisCls)


class TestCollabConnect:
    def test_success_returns_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakePingableClient()
        monkeypatch.setitem(sys.modules, "redis", _fake_redis_module(client))
        assert collab_data._connect("redis://example.invalid:6379/0") is client

    def test_ping_failure_degrades_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakePingableClient(fail_ping=True)
        monkeypatch.setitem(sys.modules, "redis", _fake_redis_module(client))
        assert collab_data._connect() is None

    def test_missing_package_degrades_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "redis", None)
        assert collab_data._connect() is None


class _ThreadScanClient:
    """Minimal board client driving _pending_threads directly."""

    def __init__(
        self,
        threads: dict[str, list[str]],
        meta: dict[str, dict[str, str]] | None = None,
        ttls: dict[str, int] | None = None,
        extra_keys: list[str] | None = None,
    ) -> None:
        self._threads = threads
        self._meta = meta or {}
        self._ttls = ttls or {}
        self._extra = extra_keys or []

    def scan_iter(self, match: str, count: int = 10):
        yield from list(self._threads) + list(self._meta) + self._extra

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._meta.get(key, {}))

    def llen(self, key: str) -> int:
        if key not in self._threads:
            raise TypeError("WRONGTYPE")
        return len(self._threads[key])

    def ttl(self, key: str) -> int:
        return self._ttls.get(key, -1)


def _thread_key(thread: str) -> str:
    return collab_data.THREAD_PREFIX + thread


class TestPendingThreadFilters:
    def test_diagnostic_promoted_and_wrongtype_keys_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _ThreadScanClient(
            threads={
                _thread_key("q-real-001"): ["m1", "m2"],
                _thread_key("test-canary"): ["m1"],
                _thread_key("routine-test-canary"): ["m1"],
                _thread_key("q-promoted-001"): ["m1"],
            },
            meta={
                _thread_key("q-promoted-001") + ":meta": {"status": "promoted"},
            },
            ttls={_thread_key("q-real-001"): 7200},
            # A non-list key inside the namespace: llen raises, row skipped.
            extra_keys=[_thread_key("q-wrongtype-001")],
        )
        monkeypatch.setattr(collab_data, "_connect", lambda url=None: client)

        inbox = read_inbox(tmp_path)

        assert inbox.board_reachable is True
        assert [(r.thread, r.messages, r.ttl_hours) for r in inbox.threads] == [
            ("q-real-001", 2, 2.0)
        ]
        # One actionable thread only — canaries and promoted excluded.
        assert inbox.action_count == 1

    def test_scan_failure_marks_board_unreachable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _Exploding:
            def scan_iter(self, match: str, count: int = 10):
                raise ConnectionError("dropped mid-scan")

        monkeypatch.setattr(collab_data, "_connect", lambda url=None: _Exploding())
        inbox = read_inbox(tmp_path)
        assert inbox.board_reachable is False
        assert inbox.threads == []


class TestGitAllowlist:
    def test_disallowed_verb_returns_none(self, tmp_path: Path) -> None:
        assert collab_data._git(tmp_path, "push", "origin", "main") is None
        assert collab_data._git(tmp_path) is None

    def test_oserror_and_timeout_return_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _oserror(*args: object, **kwargs: object) -> None:
            raise OSError("git missing")

        monkeypatch.setattr(collab_data.subprocess, "run", _oserror)
        assert collab_data._git(tmp_path, "rev-parse", "HEAD") is None

        def _timeout(*args: object, **kwargs: object) -> None:
            raise subprocess.TimeoutExpired(cmd="git", timeout=10)

        monkeypatch.setattr(collab_data.subprocess, "run", _timeout)
        assert collab_data._git(tmp_path, "rev-parse", "HEAD") is None

    def test_nonzero_exit_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            collab_data.subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=128, stdout="fatal\n"),
        )
        assert collab_data._git(tmp_path, "rev-parse", "HEAD") is None

    def test_success_strips_stdout(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            collab_data.subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=0, stdout="abc123\n"),
        )
        assert collab_data._git(tmp_path, "rev-parse", "HEAD") == "abc123"


class TestPacketBranch:
    def test_unreadable_path_returns_empty(self, tmp_path: Path) -> None:
        # A directory raises OSError on read_text on every platform.
        assert collab_data._packet_branch(tmp_path) == ""

    def test_frontmatter_terminator_stops_scan(self, tmp_path: Path) -> None:
        packet = tmp_path / "p.md"
        packet.write_text('---\nslug: x\n---\nbranch: "late"\n', encoding="utf-8")
        assert collab_data._packet_branch(packet) == ""

    def test_bad_json_value_returns_empty(self, tmp_path: Path) -> None:
        packet = tmp_path / "p.md"
        packet.write_text("---\nbranch: not-json\n---\n", encoding="utf-8")
        assert collab_data._packet_branch(packet) == ""

    def test_valid_branch_parsed(self, tmp_path: Path) -> None:
        packet = tmp_path / "p.md"
        packet.write_text('---\nbranch: "feat/x"\n---\n', encoding="utf-8")
        assert collab_data._packet_branch(packet) == "feat/x"


class TestStaleHandoffs:
    def _project_with_packet(self, tmp_path: Path, branch: str = "feat/x") -> Path:
        handoffs = tmp_path / "docs" / "handoffs"
        handoffs.mkdir(parents=True)
        (handoffs / "feat-x.md").write_text(f'---\nbranch: "{branch}"\n---\n', encoding="utf-8")
        return tmp_path

    def test_missing_branch_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = self._project_with_packet(tmp_path)
        monkeypatch.setattr(collab_data, "_git", lambda repo, *args: None)
        rows = collab_data._stale_handoffs(root)
        assert [(r.slug, r.reason) for r in rows] == [("feat-x", "branch missing")]

    def test_merged_branch_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = self._project_with_packet(tmp_path)
        # rev-parse resolves (branch exists), merge-base succeeds (merged).
        monkeypatch.setattr(collab_data, "_git", lambda repo, *args: "ok")
        rows = collab_data._stale_handoffs(root)
        assert [(r.slug, r.reason) for r in rows] == [
            ("feat-x", "branch merged — packet should be deleted")
        ]

    def test_live_branch_not_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = self._project_with_packet(tmp_path)

        def _git(repo: Path, *args: str) -> str | None:
            return "ok" if args[0] == "rev-parse" else None

        monkeypatch.setattr(collab_data, "_git", _git)
        assert collab_data._stale_handoffs(root) == []

    def test_packet_without_branch_skipped(self, tmp_path: Path) -> None:
        handoffs = tmp_path / "docs" / "handoffs"
        handoffs.mkdir(parents=True)
        (handoffs / "no-branch.md").write_text("# just notes\n", encoding="utf-8")
        assert collab_data._stale_handoffs(tmp_path) == []


class TestReadThreadEdges:
    def test_whitespace_thread_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            collab_data, "_connect", lambda url=None: pytest.fail("must not connect")
        )
        assert read_thread("has space") is None
        assert read_thread("") is None

    def test_lrange_failure_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _Client:
            def lrange(self, key: str, start: int, stop: int) -> list[str]:
                raise ConnectionError("dropped")

        monkeypatch.setattr(collab_data, "_connect", lambda url=None: _Client())
        assert read_thread("q-a-001") is None

    def test_bad_items_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _Client:
            def lrange(self, key: str, start: int, stop: int) -> list[Any]:
                return ["{not json", '"a-string"', '{"author": "codex"}', None]

        monkeypatch.setattr(collab_data, "_connect", lambda url=None: _Client())
        assert read_thread("q-a-001") == [{"author": "codex"}]


class TestMemoryConnect:
    def test_missing_package_degrades(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "redis", None)
        assert memory_data.connect() is None

    def test_ping_failure_degrades(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakePingableClient(fail_ping=True)
        monkeypatch.setitem(sys.modules, "redis", _fake_redis_module(client))
        assert memory_data.connect() is None

    def test_success_returns_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakePingableClient()
        monkeypatch.setitem(sys.modules, "redis", _fake_redis_module(client))
        assert memory_data.connect("redis://example.invalid:6379/9") is client


class _ExplodingScanClient:
    def ping(self) -> bool:
        return True

    def scan_iter(self, match: str, count: int = 10):
        raise ConnectionError("dropped mid-read")

    def get(self, key: str) -> str:
        raise ConnectionError("dropped")

    def type(self, key: str) -> str:
        raise ConnectionError("dropped")


class TestMemoryDegradePaths:
    def test_read_overview_mid_read_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(memory_data, "connect", lambda url=None: _ExplodingScanClient())
        assert read_overview() is None

    def test_read_node_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(memory_data, "connect", lambda url=None: None)
        assert read_node(MEMORY_KEY_PREFIX + "node:x") is None

    def test_read_node_mid_read_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(memory_data, "connect", lambda url=None: _ExplodingScanClient())
        assert read_node(MEMORY_KEY_PREFIX + "node:x") is None

    def test_node_count_unreachable_and_mid_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(memory_data, "connect", lambda url=None: None)
        assert node_count() is None
        monkeypatch.setattr(memory_data, "connect", lambda url=None: _ExplodingScanClient())
        assert node_count() is None

    def test_read_attention_get_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(memory_data, "connect", lambda url=None: _ExplodingScanClient())
        assert read_attention(tmp_path) is None

    def test_pending_threads_scan_failure_counts_zero(self) -> None:
        assert memory_data._pending_threads(_ExplodingScanClient()) == 0


class TestMemoryValueShapes:
    def test_set_and_unknown_shaped_keys_render(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store: dict[str, object] = {
            MEMORY_KEY_PREFIX + "markers:seen": {"a", "b", "c"},
            MEMORY_KEY_PREFIX + "weird:num": 42,  # shape "none" -> unknown
        }
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        overview = read_overview()
        assert overview is not None
        by_kind = {row.kind: row for row in overview.rows}
        assert by_kind["set"].description == "a, b, c"
        assert by_kind["set"].size == "3 members"
        assert by_kind["unknown"].description == ""
        assert overview.kind_counts == {"set": 1, "unknown": 1}

    def test_read_node_list_and_set_dispatch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store: dict[str, object] = {
            MEMORY_KEY_PREFIX + "edges:x": ['{"target": "y"}', '{"target": "z"}'],
            MEMORY_KEY_PREFIX + "markers:seen": {"b", "a"},
        }
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        edges = read_node(MEMORY_KEY_PREFIX + "edges:x")
        assert edges == {"edge 1": '{"target": "y"}', "edge 2": '{"target": "z"}'}
        members = read_node(MEMORY_KEY_PREFIX + "markers:seen")
        assert members == {"members": "a\nb"}

    def test_read_node_unsupported_type_renders_note(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _ZsetClient:
            def type(self, key: str) -> str:
                return "zset"

        monkeypatch.setattr(memory_data, "connect", lambda url=None: _ZsetClient())
        fields = read_node(MEMORY_KEY_PREFIX + "scores:x")
        assert fields == {"type": "zset", "note": "unsupported value type for display"}

    def test_pending_threads_skips_non_meta_keys(self) -> None:
        class _MixedClient:
            def scan_iter(self, match: str, count: int = 10):
                yield "attune:roundtable:thread:q-real-001"  # no :meta suffix
                yield "attune:roundtable:thread:q-real-001:meta"

            def hgetall(self, key: str) -> dict[str, str]:
                return {"status": "open"}

        assert memory_data._pending_threads(_MixedClient()) == 1


class TestMemoryRowHelpers:
    def test_first_line_all_blank(self) -> None:
        assert _first_line("\n   \n\t\n") == ""

    def test_human_size_kilobyte_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        big_text = "x" * 2048
        store: dict[str, object] = {MEMORY_KEY_PREFIX + "lesson:big": {"text": big_text}}
        monkeypatch.setattr(memory_data, "connect", lambda url=None: FakeRedis(store))
        overview = read_overview()
        assert overview is not None
        assert overview.rows[0].size == "2.0 KB"

    def test_edge_preview_skips_bad_json(self) -> None:
        preview = _edge_preview(["{broken", '{"target": "t1", "type": "REL"}'])
        assert preview == "→ t1 (REL)"

    def test_edge_preview_without_type(self) -> None:
        assert _edge_preview(['{"target": "t1"}']) == "→ t1"

    def test_build_row_exception_result_cleared(self) -> None:
        row = _build_row(
            MEMORY_KEY_PREFIX + "node:x",
            "hash",
            RuntimeError("WRONGTYPE"),
            hash_kinds={},
        )
        assert row.description == ""
        assert row.size == ""
        assert row.kind == "node"
