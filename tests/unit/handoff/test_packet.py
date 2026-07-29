"""Packet assembly: git-derived truth, caps, overwrite, security."""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.handoff import handoff_create, handoff_resume
from attune.handoff import packet as packet_mod

from .conftest import git


class TestAssembly:
    def test_frontmatter_fields_are_git_derived(self, repo: Path) -> None:
        result = handoff_create(repo, goal="Ship the thing", base_ref="main")
        assert result["ok"] is True
        verified = result["packet"]["verified"]
        assert verified["branch"] == "feature/x"
        assert verified["head_sha"] == git(repo, "rev-parse", "HEAD")
        assert verified["merge_base"] == git(repo, "merge-base", "HEAD", "main")
        assert verified["changed_files"] == ["feat.txt"]
        assert result["slug"] == "feature-x"
        assert Path(result["path"]).name == "feature-x.md"

    def test_caller_cannot_fabricate_verification_result(self, repo: Path) -> None:
        result = handoff_create(
            repo,
            goal="g",
            verification=[{"claim": "tests pass", "probe": "pytest -q"}],
            base_ref="main",
        )
        assert result["ok"] is True
        rows = result["packet"]["asserted"]["verification"]
        assert rows[0]["result"] == "not run"

    def test_empty_sections_omitted_from_file(self, repo: Path) -> None:
        result = handoff_create(repo, goal="Only a goal", base_ref="main")
        text = Path(result["path"]).read_text(encoding="utf-8")
        assert "## Goal" in text
        assert "## Next action" not in text
        assert "## Verification" not in text

    def test_missing_base_ref_degrades_truthfully(self, repo: Path) -> None:
        result = handoff_create(repo, goal="g", base_ref="does-not-exist")
        assert result["ok"] is True
        verified = result["packet"]["verified"]
        assert verified["merge_base"] is None
        assert verified["changed_files"] == []
        assert "merge_base_error" in verified


class TestCaps:
    def test_field_over_cap_rejected_with_limit(self, repo: Path) -> None:
        result = handoff_create(repo, goal="x" * (packet_mod.FIELD_CAP_BYTES + 1), base_ref="main")
        assert result == {
            "ok": False,
            "reason": "field_over_cap",
            "field": "goal",
            "limit": packet_mod.FIELD_CAP_BYTES,
        }

    def test_packet_over_cap_rejected(self, repo: Path) -> None:
        near_cap = "x" * (packet_mod.FIELD_CAP_BYTES - 1)
        result = handoff_create(
            repo,
            goal=near_cap,
            acceptance_criteria=near_cap,
            scope_assumptions=near_cap,
            current_state=near_cap,
            next_action=near_cap,
            base_ref="main",
        )
        assert result["ok"] is False
        assert result["reason"] == "packet_over_cap"
        assert result["limit"] == packet_mod.PACKET_CAP_BYTES


class TestOverwrite:
    def test_one_packet_per_branch_with_superseded_at(self, repo: Path) -> None:
        first = handoff_create(repo, goal="v1", base_ref="main")
        second = handoff_create(repo, goal="v2", base_ref="main")
        handoffs = list((repo / "docs" / "handoffs").glob("*.md"))
        assert len(handoffs) == 1
        meta, sections = packet_mod.parse(Path(second["path"]).read_text(encoding="utf-8"))
        assert meta["superseded_at"] == first["packet"]["verified"]["created_at"]
        assert sections["goal"] == "v2"


class TestSecurity:
    def test_resume_rejects_traversal_slug(self, repo: Path) -> None:
        for bad in ("../evil", "a/b", "..", ".hidden", ""):
            result = handoff_resume(repo, slug=bad)
            assert result["ok"] is False
            assert result["reason"] == "invalid_slug"

    def test_write_denied_is_truthful_failure(self, repo: Path, monkeypatch) -> None:
        def deny(self: Path, *args, **kwargs) -> None:
            raise PermissionError("Operation not permitted")

        monkeypatch.setattr(Path, "write_text", deny)
        result = handoff_create(repo, goal="g", base_ref="main")
        assert result["ok"] is False
        assert result["reason"] == "write_denied"


class TestRoundTrip:
    def test_resume_reports_verified_warnings_asserted_memory(self, repo: Path) -> None:
        handoff_create(repo, goal="Ship it", next_action="Run T2", base_ref="main")
        report = handoff_resume(repo)
        assert report["ok"] is True
        assert list(report)[:1] == ["ok"]
        for key in ("verified", "warnings", "asserted", "memory"):
            assert key in report
        assert report["asserted"]["goal"] == "Ship it"
        assert report["memory"]["status"] == "skipped"
        assert report["warnings"] == []

    def test_resume_without_packet_reports_not_found(self, repo: Path) -> None:
        result = handoff_resume(repo)
        assert result["ok"] is False
        assert result["reason"] == "packet_not_found"


class TestMemoryIsolationGuard:
    """No handoff test may write a reachable live backend (2026-07-28).

    The D5 linkage is degrade-silent, so before the ``memory_offline``
    autouse fixture landed (#1694) these tests stashed real pointers
    into the developer's live AMS. This guard trips if that isolation
    ever drifts — fixture removed, ``memory_link`` bypassing the
    ``session_stash`` seam, or ``stash_entry`` no longer routing through
    the patched ``resolve_backend``.
    """

    def test_create_cannot_reach_live_backend(self, repo: Path) -> None:
        result = handoff_create(repo, goal="isolation-guard sentinel", base_ref="main")
        assert result["ok"] is True
        memory = result["memory"]
        if memory.get("status") == "captured":
            from attune.memory import session_stash

            # Best-effort: remove the pointer this very test just leaked
            # before failing loudly.
            session_stash.forget_entries([memory["id"]], source="test-isolation-guard")
            pytest.fail(
                "handoff_create wrote to a real memory backend from a unit "
                "test; the memory_offline autouse fixture in "
                "tests/unit/handoff/conftest.py no longer isolates the "
                "session_stash seam"
            )
        # reason pins the skip to the fixture's patched backend_status —
        # an error-path skip (stash_error) would mask broken isolation.
        assert memory == {"status": "skipped", "reason": "no_backend"}
