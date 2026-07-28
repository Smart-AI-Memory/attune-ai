"""T3 memory linkage: D5 pointer stash/recall, degrade-silent with reason."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from attune.handoff import handoff_create, handoff_resume
from attune.memory import session_stash


class FakeBackend:
    """Searchable backend double: records writes, serves canned recalls."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self.remembered: list[dict[str, Any]] = []
        self.results = results or []

    def remember(self, content: str, **kwargs: Any) -> bool:
        self.remembered.append({"content": content, **kwargs})
        return True

    def stash(self, *args: Any, **kwargs: Any) -> bool:  # pragma: no cover
        return True

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.results[:limit]


@pytest.fixture()
def backend(monkeypatch: pytest.MonkeyPatch) -> FakeBackend:
    """Resolve the session stash to a recording fake backend."""
    fake = FakeBackend()
    monkeypatch.setattr(session_stash, "resolve_backend", lambda b=None: fake)
    monkeypatch.setattr(
        session_stash,
        "backend_status",
        lambda: {"ok": True, "backend": "FakeBackend", "reason": None},
    )
    return fake


class TestCreateLinkage:
    def test_create_stashes_handoff_pointer(self, repo: Path, backend: FakeBackend) -> None:
        result = handoff_create(repo, goal="Ship the thing", base_ref="main")
        assert result["ok"] is True
        assert result["memory"]["status"] == "captured"
        assert result["memory"]["id"]
        assert len(backend.remembered) == 1
        write = backend.remembered[0]
        assert "Ship the thing" in write["content"]
        assert "handoff" in write["topics"]
        assert "slug:feature-x" in write["topics"]

    def test_unreachable_backend_skips_with_reason_ok_stays_true(self, repo: Path) -> None:
        # The conftest `memory_offline` autouse fixture is the
        # unreachable-backend state; no override here.
        result = handoff_create(repo, goal="g", base_ref="main")
        assert result["ok"] is True
        assert result["memory"] == {"status": "skipped", "reason": "no_backend"}

    def test_backend_error_skips_without_raising(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: Any, **kwargs: Any) -> bool:
            raise RuntimeError("backend exploded")

        monkeypatch.setattr(session_stash, "stash_entry", boom)
        result = handoff_create(repo, goal="g", base_ref="main")
        assert result["ok"] is True
        assert result["memory"] == {"status": "skipped", "reason": "stash_error"}

    def test_rejected_packet_never_reaches_the_stash(
        self, repo: Path, backend: FakeBackend
    ) -> None:
        from attune.handoff import packet as packet_mod

        result = handoff_create(repo, goal="x" * (packet_mod.FIELD_CAP_BYTES + 1), base_ref="main")
        assert result["ok"] is False
        assert backend.remembered == []


class TestResumeLinkage:
    def test_resume_recalls_pointers_for_slug(
        self, repo: Path, backend: FakeBackend, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        handoff_create(repo, goal="g", base_ref="main")
        backend.results = [
            {
                "id": "abc123",
                "text": "Handoff packet feature-x: g",
                "topics": ["handoff", "slug:feature-x"],
                "score": 2.5,
                "session_id": "dropped-from-report",
            }
        ]
        result = handoff_resume(repo)
        assert result["ok"] is True
        memory = result["memory"]
        assert memory["status"] == "recalled"
        assert memory["count"] == 1
        assert memory["results"][0]["id"] == "abc123"
        assert memory["results"][0]["text"] == "Handoff packet feature-x: g"
        assert "session_id" not in memory["results"][0]

    def test_resume_empty_recall_is_honest_not_skipped(
        self, repo: Path, backend: FakeBackend
    ) -> None:
        handoff_create(repo, goal="g", base_ref="main")
        result = handoff_resume(repo)
        assert result["memory"] == {"status": "recalled", "count": 0, "results": []}

    def test_resume_unreachable_backend_skips_with_reason(self, repo: Path) -> None:
        handoff_create(repo, goal="g", base_ref="main")
        result = handoff_resume(repo)
        assert result["ok"] is True
        assert result["memory"] == {"status": "skipped", "reason": "no_backend"}

    def test_resume_recall_error_skips_without_raising(
        self, repo: Path, backend: FakeBackend, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        handoff_create(repo, goal="g", base_ref="main")

        def boom(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            raise RuntimeError("recall exploded")

        monkeypatch.setattr(session_stash, "recall_entries", boom)
        result = handoff_resume(repo)
        assert result["ok"] is True
        assert result["memory"] == {"status": "skipped", "reason": "recall_error"}
