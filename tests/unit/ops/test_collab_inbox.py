"""Collaboration inbox (roundtable-ruled, issue #1613).

Display-only invariants: promotion is never a GUI action; every
source degrades independently; the empty state says so honestly.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from attune.ops import collab_data
from attune.ops.collab_data import read_inbox, read_thread
from attune.ops.config import Config
from attune.ops.server import create_app


class FakeBoardRedis:
    """Just enough redis for the inbox: lists + meta hashes + TTLs."""

    def __init__(
        self,
        threads: dict[str, list[str]],
        meta: dict[str, dict[str, str]] | None = None,
        ttls: dict[str, int] | None = None,
    ) -> None:
        self._threads = threads
        self._meta = meta or {}
        self._ttls = ttls or {}

    def ping(self) -> bool:
        return True

    def scan_iter(self, match: str, count: int = 10):
        prefix = match.rstrip("*")
        for key in list(self._threads) + list(self._meta):
            if key.startswith(prefix):
                yield key

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._meta.get(key, {}))

    def llen(self, key: str) -> int:
        if key not in self._threads:
            raise TypeError("WRONGTYPE")
        return len(self._threads[key])

    def ttl(self, key: str) -> int:
        return self._ttls.get(key, -1)

    def lrange(self, key: str, start: int, stop: int) -> list[str]:
        value = self._threads.get(key)
        if value is None:
            return []
        return value[start:] if stop == -1 else value[start : stop + 1]


def _board(monkeypatch: pytest.MonkeyPatch, client: Any) -> None:
    monkeypatch.setattr(collab_data, "_connect", lambda url=None: client)


def _thread_key(thread: str) -> str:
    return collab_data.THREAD_PREFIX + thread


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.email=fixture@test",
            "-c",
            "user.name=Fixture",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-q", "-m", "base")
    # origin/main ref for the merged-branch check.
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    return root


def _packet(project: Path, slug: str, branch: str) -> None:
    handoffs = project / "docs" / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    (handoffs / f"{slug}.md").write_text(
        "---\n" f"branch: {json.dumps(branch)}\n" "---\n\n# Agent work handoff\n",
        encoding="utf-8",
    )


class TestInboxData:
    def test_all_sources_empty(self, project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _board(monkeypatch, FakeBoardRedis({}))
        inbox = read_inbox(project)
        assert inbox.board_reachable is True
        assert inbox.action_count == 0

    def test_pending_threads_sorted_by_ttl(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        threads = {
            _thread_key("q-a-001"): ["{}"],
            _thread_key("q-b-001"): ["{}", "{}"],
            _thread_key("q-c-001"): ["{}"],
            _thread_key("test-canary1"): ["{}"],
            _thread_key("routine-test-x-20260722"): ["{}"],
        }
        meta = {
            _thread_key("q-c-001") + ":meta": {"status": "promoted"},
        }
        ttls = {_thread_key("q-a-001"): 7200, _thread_key("q-b-001"): 3600}
        _board(monkeypatch, FakeBoardRedis(threads, meta, ttls))
        inbox = read_inbox(project)
        assert [r.thread for r in inbox.threads] == ["q-b-001", "q-a-001"]
        assert inbox.threads[0].ttl_hours == 1.0
        assert inbox.threads[0].messages == 2

    def test_board_down_degrades_files_still_read(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _board(monkeypatch, None)
        _packet(project, "gone-branch", "feature/gone")
        inbox = read_inbox(project)
        assert inbox.board_reachable is False
        assert [r.reason for r in inbox.stale_handoffs] == ["branch missing"]

    def test_merged_branch_packet_flagged(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _git(project, "checkout", "-q", "-b", "feature/done")
        _git(project, "checkout", "-q", "main")
        _board(monkeypatch, FakeBoardRedis({}))
        _packet(project, "feature-done", "feature/done")
        inbox = read_inbox(project)
        assert len(inbox.stale_handoffs) == 1
        assert "merged" in inbox.stale_handoffs[0].reason

    def test_live_branch_packet_not_flagged(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _git(project, "checkout", "-q", "-b", "feature/live")
        (project / "b.txt").write_text("b\n", encoding="utf-8")
        _git(project, "add", "b.txt")
        _git(project, "commit", "-q", "-m", "ahead")
        _git(project, "checkout", "-q", "main")
        _board(monkeypatch, FakeBoardRedis({}))
        _packet(project, "feature-live", "feature/live")
        inbox = read_inbox(project)
        assert inbox.stale_handoffs == []

    def test_untriaged_ledger_rows_counted(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _board(monkeypatch, FakeBoardRedis({}))
        ledger = project / "docs" / "specs" / "cross-review"
        ledger.mkdir(parents=True)
        (ledger / "receipts.md").write_text(
            "| 2026-07-28 | codex | branch | 2 sent / 0 omitted | 1 (findings) "
            "| not-triaged |\n"
            "| 2026-07-28 | agy | branch | 1 sent / 0 omitted | 0 (clean) "
            "| real |\n",
            encoding="utf-8",
        )
        inbox = read_inbox(project)
        assert inbox.untriaged_reviews == 1


class TestReadThread:
    def test_reads_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        raw = [json.dumps({"id": 1, "kind": "question", "author": "chair", "body": "Q"})]
        _board(monkeypatch, FakeBoardRedis({_thread_key("q-a-001"): raw}))
        messages = read_thread("q-a-001")
        assert messages is not None
        assert messages[0]["kind"] == "question"

    def test_rejects_namespace_escape(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _board(monkeypatch, FakeBoardRedis({}))
        assert read_thread("a:b") is None
        assert read_thread("a b") is None
        assert read_thread("") is None

    def test_board_down_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _board(monkeypatch, None)
        assert read_thread("q-a-001") is None


class TestRoutes:
    @pytest.fixture()
    def client(self, project: Path, tmp_path: Path) -> TestClient:
        cfg = Config(project_root=project, attune_home=tmp_path / "attune-home")
        c = TestClient(create_app(cfg))
        c.headers["Host"] = f"{cfg.host}:{cfg.port}"
        return c

    def test_empty_inbox_renders_quiet_state(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _board(monkeypatch, FakeBoardRedis({}))
        resp = client.get("/collab")
        assert resp.status_code == 200
        assert "Nothing needs your attention" in resp.text

    def test_pending_thread_renders_promote_command_not_button(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        threads = {_thread_key("q-a-001"): ["{}"]}
        _board(monkeypatch, FakeBoardRedis(threads, ttls={_thread_key("q-a-001"): 3600}))
        resp = client.get("/collab")
        assert resp.status_code == 200
        assert "/roundtable promote q-a-001" in resp.text
        # Display-only invariant: no form, no POST affordance.
        assert "<form" not in resp.text.lower()

    def test_thread_detail_renders_and_guards(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        raw = [json.dumps({"id": 1, "kind": "question", "author": "chair", "body": "Q?"})]
        _board(monkeypatch, FakeBoardRedis({_thread_key("q-a-001"): raw}))
        ok = client.get("/collab/thread", params={"id": "q-a-001"})
        assert ok.status_code == 200
        assert "Q?" in ok.text
        bad = client.get("/collab/thread", params={"id": "evil:key"})
        assert bad.status_code == 404

    def test_nav_contains_collab(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        _board(monkeypatch, FakeBoardRedis({}))
        resp = client.get("/collab")
        assert 'href="/collab"' in resp.text


class TestOutboxRow:
    """Docs-outbox monitoring row (docs-outbox R3/AC-4)."""

    def test_no_home_skips_row(self, project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _board(monkeypatch, FakeBoardRedis({}))
        assert read_inbox(project).docs_outbox is None

    def test_empty_outbox_no_row(
        self, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _board(monkeypatch, FakeBoardRedis({}))
        inbox = read_inbox(project, attune_home=tmp_path / "home")
        assert inbox.docs_outbox is None
        assert inbox.action_count == 0

    def test_pending_row_is_monitoring_only(
        self, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.docs_outbox.store import write_artifact

        _board(monkeypatch, FakeBoardRedis({}))
        home = tmp_path / "home"
        write_artifact("lesson", "fresh", "- **Body.**", attune_home=home)
        inbox = read_inbox(project, attune_home=home)
        assert inbox.docs_outbox is not None
        assert inbox.docs_outbox.count == 1
        assert inbox.docs_outbox.stale is False
        # Monitoring only: a fresh outbox never inflates the badge.
        assert inbox.action_count == 0

    def test_stale_outbox_counts_as_action(
        self, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from datetime import datetime, timedelta

        from attune.docs_outbox.store import write_artifact

        _board(monkeypatch, FakeBoardRedis({}))
        home = tmp_path / "home"
        write_artifact(
            "lesson", "old", "- **Body.**", attune_home=home, now=datetime.now() - timedelta(days=3)
        )
        inbox = read_inbox(project, attune_home=home)
        assert inbox.docs_outbox is not None
        assert inbox.docs_outbox.stale is True
        assert inbox.action_count == 1

    def test_route_renders_pending_row(
        self, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.docs_outbox.store import write_artifact

        _board(monkeypatch, FakeBoardRedis({}))
        cfg = Config(project_root=project, attune_home=tmp_path / "attune-home")
        write_artifact("lesson", "pending", "- **Body.**", attune_home=cfg.attune_home)
        client = TestClient(create_app(cfg))
        client.headers["Host"] = f"{cfg.host}:{cfg.port}"
        resp = client.get("/collab")
        assert resp.status_code == 200
        assert 'data-testid="collab-outbox"' in resp.text
        assert "1 doc(s) pending" in resp.text
