"""Drift matrix (D3), read-only guard, and staleness math."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.handoff import verify

from .conftest import git


def _codes(warnings: list[dict]) -> set[str]:
    return {w["code"] for w in warnings}


@pytest.fixture()
def meta(repo: Path) -> dict:
    return verify.snapshot(repo, base_ref="main")


class TestDriftMatrix:
    def test_clean_tree_no_warnings(self, repo: Path, meta: dict) -> None:
        assert verify.drift(meta, repo) == []

    def test_head_moved(self, repo: Path, meta: dict) -> None:
        (repo / "more.txt").write_text("more\n", encoding="utf-8")
        git(repo, "add", "more.txt")
        git(repo, "commit", "-q", "-m", "more")
        codes = _codes(verify.drift(meta, repo))
        assert "head_moved" in codes
        assert "files_diverged" in codes

    def test_branch_missing(self, repo: Path, meta: dict) -> None:
        git(repo, "checkout", "-q", "main")
        git(repo, "branch", "-q", "-D", "feature/x")
        codes = _codes(verify.drift(meta, repo))
        assert "branch_missing" in codes

    def test_dirty_tree(self, repo: Path, meta: dict) -> None:
        (repo / "base.txt").write_text("edited\n", encoding="utf-8")
        codes = _codes(verify.drift(meta, repo))
        assert codes == {"dirty_tree"}

    def test_packet_stale_days(self, repo: Path, meta: dict) -> None:
        old = datetime.now(timezone.utc) - timedelta(days=verify.STALE_AFTER_DAYS + 3)
        meta = {**meta, "created_at": old.isoformat()}
        warnings = verify.drift(meta, repo)
        stale = [w for w in warnings if w["code"] == "packet_stale_days"]
        assert len(stale) == 1
        assert stale[0]["detail"] >= verify.STALE_AFTER_DAYS

    def test_warnings_never_mutate_repo(self, repo: Path, meta: dict) -> None:
        before = git(repo, "rev-parse", "HEAD")
        (repo / "base.txt").write_text("edited\n", encoding="utf-8")
        verify.drift(meta, repo)
        assert git(repo, "rev-parse", "HEAD") == before
        assert (repo / "base.txt").read_text(encoding="utf-8") == "edited\n"


class TestReadOnlyGuard:
    def test_mutating_subcommand_rejected(self, repo: Path) -> None:
        with pytest.raises(verify.GitReadError, match="not allowlisted"):
            verify._git(repo, "commit", "-m", "nope")

    def test_empty_args_rejected(self, repo: Path) -> None:
        with pytest.raises(verify.GitReadError):
            verify._git(repo)


class TestAgeMath:
    def test_invalid_created_at_returns_none(self) -> None:
        assert verify._packet_age_days("not-a-date") is None
        assert verify._packet_age_days("") is None

    def test_naive_timestamp_assumed_utc(self) -> None:
        naive = (datetime.now(timezone.utc) - timedelta(days=2)).replace(tzinfo=None)
        age = verify._packet_age_days(naive.isoformat())
        assert age is not None
        assert 1.9 < age < 2.1


class TestSlug:
    def test_slugify_branch(self) -> None:
        assert verify.slugify_branch("claude/handoff-t1-t2") == ("claude-handoff-t1-t2")
