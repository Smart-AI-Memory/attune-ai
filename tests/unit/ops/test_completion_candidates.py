"""Unit tests for ``attune.ops.completion_candidates``.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T2).

Covers every public surface plus the private signal-check helpers:

- Per-signal correctness (status, edit-age, tasks, PRs, issues)
- Host-repo URL parsing (Q1 three shapes + None paths)
- Snapshot hash determinism
- Cache TTL behavior
- End-to-end ``detect_candidates`` with realistic fixture trees

Subprocess calls (git / gh) are mocked at the module's three
wrapper functions; no real network or git invocation happens.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from attune.ops import completion_candidates, dismiss_store
from attune.ops.completion_candidates import (
    CACHE_TTL_SECONDS,
    _check_last_edit_age,
    _check_no_open_issues,
    _check_referenced_prs_merged,
    _check_status_is_approved,
    _check_tasks_all_done,
    _extract_pr_refs,
    _format_pr_evidence,
    _preferred_status,
    _resolve_host_repo,
    _snapshot_hash,
    clear_cache,
    detect_candidates,
)
from attune.ops.config import Config
from attune.ops.routes.specs import SpecPhase, SpecRecord

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Module-level caches are persistent across tests by default."""
    clear_cache()


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    """Config rooted at tmp_path; spec root at <tmp>/project/docs/specs."""
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "docs" / "specs").mkdir(parents=True, exist_ok=True)
    return Config(
        project_root=project_root,
        attune_home=tmp_path / "attune-home",
    )


@pytest.fixture()
def specs_root(cfg: Config) -> Path:
    return cfg.project_root / "docs" / "specs"


@pytest.fixture()
def fake_gh(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch the three subprocess wrappers with in-memory fakes.

    Returns a state dict the test mutates::

        state["prs"][(repo, pr_number)] = {"state": "closed", ...} | None
        state["issues"][(slug, repo)] = [{"number": ..., ...}, ...] | None
        state["remotes"][str(cwd)] = "git@github.com:owner/name.git" | None

    Missing entries return safe defaults (issues: [], others: None).
    """
    state: dict[str, dict] = {"prs": {}, "issues": {}, "remotes": {}}

    def fake_pr(repo: str, pr_number: int) -> dict[str, Any] | None:
        return state["prs"].get((repo, pr_number))

    def fake_issues(slug: str, repo: str) -> list[dict[str, Any]] | None:
        if (slug, repo) in state["issues"]:
            return state["issues"][(slug, repo)]
        return []

    def fake_remote(cwd: Path) -> str | None:
        return state["remotes"].get(str(cwd))

    monkeypatch.setattr(completion_candidates, "_run_gh_pr_view", fake_pr)
    monkeypatch.setattr(completion_candidates, "_run_gh_issue_search", fake_issues)
    monkeypatch.setattr(completion_candidates, "_run_git_remote_origin", fake_remote)
    return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec(
    root: Path,
    slug: str,
    *,
    decisions_status: str | None = "approved",
    tasks_md: str | None = None,
    extra_md: dict[str, str] | None = None,
    age_hours: float = 100.0,
) -> Path:
    """Build a fixture spec dir with controllable signal state."""
    spec_dir = root / slug
    spec_dir.mkdir(parents=True, exist_ok=True)
    if decisions_status is not None:
        (spec_dir / "decisions.md").write_text(
            f"# {slug}\n\n**Status**: {decisions_status}\n",
            encoding="utf-8",
        )
    if tasks_md is not None:
        (spec_dir / "tasks.md").write_text(tasks_md, encoding="utf-8")
    if extra_md:
        for filename, content in extra_md.items():
            (spec_dir / filename).write_text(content, encoding="utf-8")
    # Force mtime to control age.
    cutoff = time.time() - age_hours * 3600
    for md in spec_dir.glob("*.md"):
        os.utime(md, (cutoff, cutoff))
    return spec_dir


def _build_spec_record(
    slug: str,
    path: str,
    statuses: dict[str, str | None],
    last_modified_age_hours: float = 100.0,
) -> SpecRecord:
    """Build a SpecRecord directly (bypassing filesystem)."""
    phases = [
        SpecPhase(
            name=name,
            file=f"{name}.md",
            exists=name in statuses,
            status=statuses.get(name),
        )
        for name in ("decisions", "requirements", "design", "tasks")
    ]
    last = datetime.now(timezone.utc) - timedelta(hours=last_modified_age_hours)
    return SpecRecord(
        slug=slug,
        root="/fake",
        path=path,
        phases=phases,
        last_modified=last.isoformat(),
    )


# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------


class TestPreferredStatus:
    def test_decisions_wins(self) -> None:
        spec = _build_spec_record("s", "/p", {"decisions": "approved", "tasks": "draft"})
        assert _preferred_status(spec) == "approved"

    def test_falls_back_to_tasks(self) -> None:
        spec = _build_spec_record("s", "/p", {"tasks": "approved"})
        assert _preferred_status(spec) == "approved"

    def test_falls_back_through_order(self) -> None:
        spec = _build_spec_record("s", "/p", {"requirements": "approved"})
        assert _preferred_status(spec) == "approved"

    def test_returns_none_when_no_status_set(self) -> None:
        spec = _build_spec_record("s", "/p", {"decisions": None, "tasks": None})
        assert _preferred_status(spec) is None

    def test_strips_and_lowercases(self) -> None:
        spec = _build_spec_record("s", "/p", {"decisions": "  APPROVED  "})
        assert _preferred_status(spec) == "approved"


class TestCheckStatusIsApproved:
    """The status filter — only `approved` qualifies."""

    @pytest.mark.parametrize(
        "status,expected",
        [
            ("approved", True),
            ("draft", False),
            ("in-review", False),
            ("complete", False),
            ("partial", False),
            ("paused", False),
            ("retired", False),
            (None, False),
        ],
    )
    def test_filter(self, status: str | None, expected: bool) -> None:
        spec = _build_spec_record("s", "/p", {"decisions": status})
        assert _check_status_is_approved(spec) is expected


# ---------------------------------------------------------------------------
# Edit-age check
# ---------------------------------------------------------------------------


class TestCheckLastEditAge:
    def test_23h_fails(self) -> None:
        now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
        spec = _build_spec_record(
            "s",
            "/p",
            {"decisions": "approved"},
            last_modified_age_hours=0,  # we'll override
        )
        # Build a spec with last_modified = 23h before now.
        last = (now - timedelta(hours=23)).isoformat()
        spec = SpecRecord(slug="s", root="/r", path="/p", phases=spec.phases, last_modified=last)
        ok, ev = _check_last_edit_age(spec, now=now)
        assert ok is False
        assert ev is None

    def test_25h_passes(self) -> None:
        now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
        last = (now - timedelta(hours=25)).isoformat()
        spec = SpecRecord(
            slug="s",
            root="/r",
            path="/p",
            phases=[],
            last_modified=last,
        )
        ok, ev = _check_last_edit_age(spec, now=now)
        assert ok is True
        assert ev is not None
        assert "last edit" in ev

    def test_missing_last_modified_fails(self) -> None:
        spec = SpecRecord(slug="s", root="/r", path="/p", phases=[], last_modified=None)
        ok, ev = _check_last_edit_age(spec)
        assert (ok, ev) == (False, None)

    def test_unparseable_last_modified_fails(self) -> None:
        spec = SpecRecord(
            slug="s",
            root="/r",
            path="/p",
            phases=[],
            last_modified="not-a-date",
        )
        ok, ev = _check_last_edit_age(spec)
        assert (ok, ev) == (False, None)

    def test_naive_datetime_rejected(self) -> None:
        spec = SpecRecord(
            slug="s",
            root="/r",
            path="/p",
            phases=[],
            last_modified="2026-05-01T12:00:00",
        )
        ok, ev = _check_last_edit_age(spec)
        assert (ok, ev) == (False, None)

    def test_evidence_phrasing_singular_vs_plural(self) -> None:
        now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
        # 26 hours -> 1 day (max(1, int(26/24)) = 1)
        last = (now - timedelta(hours=26)).isoformat()
        spec = SpecRecord(slug="s", root="/r", path="/p", phases=[], last_modified=last)
        ok, ev = _check_last_edit_age(spec, now=now)
        assert ok is True and ev == "✓ last edit 1 day ago"

        # 5 days -> "5 days ago"
        last = (now - timedelta(days=5)).isoformat()
        spec = SpecRecord(slug="s", root="/r", path="/p", phases=[], last_modified=last)
        ok, ev = _check_last_edit_age(spec, now=now)
        assert ok is True and ev == "✓ last edit 5 days ago"


# ---------------------------------------------------------------------------
# Tasks check
# ---------------------------------------------------------------------------


class TestCheckTasksAllDone:
    def test_missing_tasks_md_passes(self, tmp_path: Path) -> None:
        ok, ev = _check_tasks_all_done(tmp_path)
        assert ok is True
        assert ev == "✓ no tasks.md (decisions-only spec)"

    def test_empty_tasks_md_fails(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text("# Tasks\n\nJust a header.\n", encoding="utf-8")
        ok, ev = _check_tasks_all_done(tmp_path)
        assert (ok, ev) == (False, None)

    def test_all_checked_rows_pass(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text(
            "# Tasks\n\n- [x] First\n- [x] Second\n- [x] Third\n",
            encoding="utf-8",
        )
        ok, ev = _check_tasks_all_done(tmp_path)
        assert ok is True
        assert ev == "✓ 3 task rows complete"

    def test_one_unchecked_row_fails(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text(
            "- [x] First\n- [ ] Second\n- [x] Third\n", encoding="utf-8"
        )
        ok, ev = _check_tasks_all_done(tmp_path)
        assert (ok, ev) == (False, None)

    def test_capital_X_recognized(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text("- [X] First\n- [x] Second\n", encoding="utf-8")
        ok, _ = _check_tasks_all_done(tmp_path)
        assert ok is True

    def test_table_done_markers_count(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text(
            "| Task | Status |\n"
            "|------|--------|\n"
            "| T1 | **done** |\n"
            "| T2 | **complete** |\n",
            encoding="utf-8",
        )
        ok, ev = _check_tasks_all_done(tmp_path)
        assert ok is True
        assert ev == "✓ 2 task rows complete"

    def test_mixed_checkbox_and_table_pass(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text(
            "- [x] First\n\n| T | S |\n|---|---|\n| T2 | **done** |\n",
            encoding="utf-8",
        )
        ok, ev = _check_tasks_all_done(tmp_path)
        assert ok is True
        assert ev == "✓ 2 task rows complete"

    def test_unchecked_row_in_mixed_format_fails(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text(
            "- [ ] First\n\n| T | S |\n|---|---|\n| T2 | **done** |\n",
            encoding="utf-8",
        )
        ok, _ = _check_tasks_all_done(tmp_path)
        assert ok is False

    def test_singular_evidence_phrasing(self, tmp_path: Path) -> None:
        (tmp_path / "tasks.md").write_text("- [x] Only\n", encoding="utf-8")
        ok, ev = _check_tasks_all_done(tmp_path)
        assert ok is True
        assert ev == "✓ 1 task row complete"


# ---------------------------------------------------------------------------
# PR ref extraction
# ---------------------------------------------------------------------------


class TestExtractPrRefs:
    def test_finds_hash_refs(self, tmp_path: Path) -> None:
        (tmp_path / "decisions.md").write_text("Shipped in #324 and #325.\n", encoding="utf-8")
        assert _extract_pr_refs(tmp_path) == [324, 325]

    def test_finds_pr_word_refs(self, tmp_path: Path) -> None:
        (tmp_path / "decisions.md").write_text("See PR 100 and pr 200.\n", encoding="utf-8")
        assert _extract_pr_refs(tmp_path) == [100, 200]

    def test_deduplicates_across_files(self, tmp_path: Path) -> None:
        (tmp_path / "decisions.md").write_text("#324\n", encoding="utf-8")
        (tmp_path / "tasks.md").write_text("#324 #325\n", encoding="utf-8")
        assert _extract_pr_refs(tmp_path) == [324, 325]

    def test_ignores_discursive_files(self, tmp_path: Path) -> None:
        # Per Q5: only decisions.md and tasks.md are scanned.
        (tmp_path / "_sequencing.md").write_text("#999\n", encoding="utf-8")
        (tmp_path / "audit.md").write_text("#888\n", encoding="utf-8")
        (tmp_path / "decisions.md").write_text("#324\n", encoding="utf-8")
        assert _extract_pr_refs(tmp_path) == [324]

    def test_empty_when_no_refs(self, tmp_path: Path) -> None:
        (tmp_path / "decisions.md").write_text("No PR mentioned.\n", encoding="utf-8")
        assert _extract_pr_refs(tmp_path) == []

    def test_missing_files_are_skipped(self, tmp_path: Path) -> None:
        # Neither decisions.md nor tasks.md present.
        assert _extract_pr_refs(tmp_path) == []

    def test_returns_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "decisions.md").write_text("#3 #1 #2\n", encoding="utf-8")
        assert _extract_pr_refs(tmp_path) == [1, 2, 3]


# ---------------------------------------------------------------------------
# PR merged check
# ---------------------------------------------------------------------------


class TestCheckReferencedPrsMerged:
    def test_empty_pr_list_passes(self, fake_gh: dict) -> None:
        ok, ev = _check_referenced_prs_merged([], "owner/repo")
        assert ok is True
        assert ev is None

    def test_all_merged_passes(self, fake_gh: dict) -> None:
        fake_gh["prs"][("owner/repo", 1)] = {
            "state": "closed",
            "merged_at": "2026-05-14T12:00:00Z",
        }
        fake_gh["prs"][("owner/repo", 2)] = {
            "state": "closed",
            "merged_at": "2026-05-14T12:00:00Z",
        }
        ok, ev = _check_referenced_prs_merged([1, 2], "owner/repo")
        assert ok is True
        assert ev is not None
        assert "#1" in ev and "#2" in ev

    def test_one_open_fails(self, fake_gh: dict) -> None:
        fake_gh["prs"][("owner/repo", 1)] = {
            "state": "closed",
            "merged_at": "2026-05-14T12:00:00Z",
        }
        fake_gh["prs"][("owner/repo", 2)] = {
            "state": "open",
            "merged_at": None,
        }
        ok, ev = _check_referenced_prs_merged([1, 2], "owner/repo")
        assert (ok, ev) == (False, None)

    def test_closed_not_merged_fails(self, fake_gh: dict) -> None:
        fake_gh["prs"][("owner/repo", 1)] = {
            "state": "closed",
            "merged_at": None,
        }
        ok, ev = _check_referenced_prs_merged([1], "owner/repo")
        assert (ok, ev) == (False, None)

    def test_gh_failure_fails(self, fake_gh: dict) -> None:
        # Missing entry -> fake returns None -> treat as gh failure.
        ok, ev = _check_referenced_prs_merged([99], "owner/repo")
        assert (ok, ev) == (False, None)

    def test_truncates_long_pr_lists_in_evidence(self) -> None:
        # Direct unit test on the formatter.
        ev = _format_pr_evidence(list(range(1, 11)))
        assert "#1" in ev and "#5" in ev
        assert "#6" not in ev
        assert "…+5 more" in ev


# ---------------------------------------------------------------------------
# Open-issues check
# ---------------------------------------------------------------------------


class TestCheckNoOpenIssues:
    def test_empty_result_passes(self, fake_gh: dict) -> None:
        ok, ev = _check_no_open_issues("my-spec", "owner/repo")
        assert ok is True
        assert ev == "✓ no open issues reference this spec"

    def test_nonempty_result_fails(self, fake_gh: dict) -> None:
        fake_gh["issues"][("my-spec", "owner/repo")] = [
            {"number": 42, "title": "fix my-spec"},
        ]
        ok, ev = _check_no_open_issues("my-spec", "owner/repo")
        assert (ok, ev) == (False, None)

    def test_gh_failure_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            completion_candidates,
            "_run_gh_issue_search",
            lambda slug, repo: None,
        )
        ok, ev = _check_no_open_issues("my-spec", "owner/repo")
        assert (ok, ev) == (False, None)


# ---------------------------------------------------------------------------
# Host-repo discovery (Q1)
# ---------------------------------------------------------------------------


class TestResolveHostRepo:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("git@github.com:Smart-AI-Memory/attune-ai.git", "Smart-AI-Memory/attune-ai"),
            ("https://github.com/Smart-AI-Memory/attune-ai.git", "Smart-AI-Memory/attune-ai"),
            ("https://github.com/Smart-AI-Memory/attune-ai", "Smart-AI-Memory/attune-ai"),
            ("http://github.com/owner/name", "owner/name"),
        ],
    )
    def test_parses_known_url_shapes(
        self,
        tmp_path: Path,
        fake_gh: dict,
        url: str,
        expected: str,
    ) -> None:
        root = tmp_path / "docs" / "specs"
        root.mkdir(parents=True)
        fake_gh["remotes"][str(tmp_path / "docs")] = url
        assert _resolve_host_repo(root) == expected

    def test_returns_none_when_no_remote(self, tmp_path: Path, fake_gh: dict) -> None:
        root = tmp_path / "docs" / "specs"
        root.mkdir(parents=True)
        # No remote configured for this cwd.
        assert _resolve_host_repo(root) is None

    def test_returns_none_for_unrecognized_url(self, tmp_path: Path, fake_gh: dict) -> None:
        root = tmp_path / "docs" / "specs"
        root.mkdir(parents=True)
        fake_gh["remotes"][str(tmp_path / "docs")] = "ssh://gitlab.com/x/y"
        assert _resolve_host_repo(root) is None

    def test_memoized_per_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = {"n": 0}

        def fake_remote(cwd: Path) -> str | None:
            call_count["n"] += 1
            return "git@github.com:owner/name.git"

        monkeypatch.setattr(completion_candidates, "_run_git_remote_origin", fake_remote)
        root = tmp_path / "docs" / "specs"
        root.mkdir(parents=True)
        _resolve_host_repo(root)
        _resolve_host_repo(root)
        _resolve_host_repo(root)
        assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# Snapshot hash
# ---------------------------------------------------------------------------


class TestSnapshotHash:
    def test_deterministic_same_inputs(self, tmp_path: Path) -> None:
        h1 = _snapshot_hash(tmp_path, [1, 2, 3], "2026-05-15T12:00:00+00:00")
        h2 = _snapshot_hash(tmp_path, [1, 2, 3], "2026-05-15T12:00:00+00:00")
        assert h1 == h2

    def test_pr_order_does_not_matter(self, tmp_path: Path) -> None:
        h1 = _snapshot_hash(tmp_path, [3, 1, 2], "x")
        h2 = _snapshot_hash(tmp_path, [1, 2, 3], "x")
        assert h1 == h2

    def test_tasks_mtime_change_changes_hash(self, tmp_path: Path) -> None:
        tasks = tmp_path / "tasks.md"
        tasks.write_text("- [x] one\n", encoding="utf-8")
        os.utime(tasks, (1000.0, 1000.0))
        h1 = _snapshot_hash(tmp_path, [], "x")
        os.utime(tasks, (2000.0, 2000.0))
        h2 = _snapshot_hash(tmp_path, [], "x")
        assert h1 != h2

    def test_last_modified_change_changes_hash(self, tmp_path: Path) -> None:
        h1 = _snapshot_hash(tmp_path, [], "2026-05-15T12:00:00+00:00")
        h2 = _snapshot_hash(tmp_path, [], "2026-05-16T12:00:00+00:00")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestCache:
    def test_two_calls_within_ttl_return_same_list(self, cfg: Config, fake_gh: dict) -> None:
        now = 1_000_000.0
        c1 = detect_candidates(cfg, now=now)
        c2 = detect_candidates(cfg, now=now + CACHE_TTL_SECONDS - 1)
        assert c1 is c2  # exact list identity

    def test_call_past_ttl_recomputes(self, cfg: Config, fake_gh: dict) -> None:
        now = 1_000_000.0
        c1 = detect_candidates(cfg, now=now)
        c2 = detect_candidates(cfg, now=now + CACHE_TTL_SECONDS + 1)
        # Recomputed - different list object, even if equal content.
        assert c1 is not c2

    def test_clear_cache_forces_recompute(self, cfg: Config, fake_gh: dict) -> None:
        now = 1_000_000.0
        c1 = detect_candidates(cfg, now=now)
        clear_cache()
        c2 = detect_candidates(cfg, now=now)
        assert c1 is not c2


# ---------------------------------------------------------------------------
# End-to-end: detect_candidates
# ---------------------------------------------------------------------------


class TestDetectCandidatesEndToEnd:
    def test_empty_spec_root_returns_empty(self, cfg: Config, fake_gh: dict) -> None:
        assert detect_candidates(cfg) == []

    def test_approved_spec_no_prs_no_issues_qualifies(
        self, cfg: Config, specs_root: Path, fake_gh: dict
    ) -> None:
        _make_spec(
            specs_root,
            "ready-spec",
            decisions_status="approved",
            tasks_md="- [x] T1\n- [x] T2\n",
            age_hours=48,
        )
        # No remote -> no repo, no PR refs -> still qualifies.
        result = detect_candidates(cfg)
        assert len(result) == 1
        c = result[0]
        assert c.slug == "ready-spec"
        assert c.current_status == "approved"
        assert any("task rows complete" in e for e in c.evidence)

    def test_draft_spec_filtered_out(self, cfg: Config, specs_root: Path, fake_gh: dict) -> None:
        _make_spec(specs_root, "drafty", decisions_status="draft")
        assert detect_candidates(cfg) == []

    def test_recently_edited_spec_filtered_out(
        self, cfg: Config, specs_root: Path, fake_gh: dict
    ) -> None:
        _make_spec(
            specs_root,
            "fresh",
            decisions_status="approved",
            age_hours=1,
        )
        assert detect_candidates(cfg) == []

    def test_pr_refs_require_host_repo(self, cfg: Config, specs_root: Path, fake_gh: dict) -> None:
        # PR ref present but no remote configured -> rejected.
        _make_spec(
            specs_root,
            "spec-with-prs",
            decisions_status="approved",
            extra_md={"decisions.md": "**Status**: approved\nSee #324\n"},
            age_hours=48,
        )
        assert detect_candidates(cfg) == []

    def test_pr_refs_all_merged_qualifies(
        self, cfg: Config, specs_root: Path, fake_gh: dict
    ) -> None:
        repo = "owner/name"
        fake_gh["remotes"][str(cfg.project_root / "docs")] = f"git@github.com:{repo}.git"
        fake_gh["prs"][(repo, 324)] = {
            "state": "closed",
            "merged_at": "2026-05-14T12:00:00Z",
        }
        _make_spec(
            specs_root,
            "merged-spec",
            decisions_status="approved",
            extra_md={
                "decisions.md": "**Status**: approved\nShipped in #324\n",
            },
            age_hours=48,
        )
        result = detect_candidates(cfg)
        assert len(result) == 1
        assert any("#324" in e for e in result[0].evidence)

    def test_open_issue_blocks_candidate(
        self, cfg: Config, specs_root: Path, fake_gh: dict
    ) -> None:
        repo = "owner/name"
        fake_gh["remotes"][str(cfg.project_root / "docs")] = f"https://github.com/{repo}"
        fake_gh["issues"][("blocked-spec", repo)] = [{"number": 100, "title": "blocked-spec broke"}]
        _make_spec(
            specs_root,
            "blocked-spec",
            decisions_status="approved",
            age_hours=48,
        )
        assert detect_candidates(cfg) == []

    def test_dismissed_candidate_suppressed_within_ttl(
        self, cfg: Config, specs_root: Path, fake_gh: dict
    ) -> None:
        _make_spec(
            specs_root,
            "dismissed-spec",
            decisions_status="approved",
            tasks_md="- [x] T1\n",
            age_hours=48,
        )
        # First call: candidate qualifies. Capture its snapshot hash.
        result = detect_candidates(cfg)
        assert len(result) == 1
        snap = result[0].snapshot_hash

        # Dismiss it.
        dismiss_store.save("dismissed-spec", snap, cfg)
        clear_cache()
        # Now suppressed.
        assert detect_candidates(cfg) == []

    def test_dismissed_resurfaces_when_signal_changes(
        self, cfg: Config, specs_root: Path, fake_gh: dict
    ) -> None:
        _make_spec(
            specs_root,
            "resurface-spec",
            decisions_status="approved",
            tasks_md="- [x] T1\n",
            age_hours=48,
        )
        result = detect_candidates(cfg)
        assert len(result) == 1
        # Dismiss with the WRONG snapshot hash -> never matches current ->
        # always re-surfaces.
        dismiss_store.save("resurface-spec", "stale-hash", cfg)
        clear_cache()
        result = detect_candidates(cfg)
        assert len(result) == 1
        assert result[0].slug == "resurface-spec"

    def test_multiple_specs_mixed_status(
        self, cfg: Config, specs_root: Path, fake_gh: dict
    ) -> None:
        _make_spec(specs_root, "a", decisions_status="approved", tasks_md="- [x] T\n", age_hours=48)
        _make_spec(specs_root, "b", decisions_status="draft", age_hours=48)
        _make_spec(specs_root, "c", decisions_status="approved", tasks_md="- [ ] T\n", age_hours=48)
        result = detect_candidates(cfg)
        slugs = {c.slug for c in result}
        assert slugs == {"a"}


# ---------------------------------------------------------------------------
# Subprocess wrappers — direct tests with mocked subprocess.run
# ---------------------------------------------------------------------------


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> Any:
    """Build a minimal CompletedProcess stand-in."""

    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestRunGitRemoteOrigin:
    def test_success_returns_url(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: _completed(0, "git@github.com:o/n.git\n"),
        )
        assert completion_candidates._run_git_remote_origin(tmp_path) == "git@github.com:o/n.git"

    def test_nonzero_returncode_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(1, "", "err"))
        assert completion_candidates._run_git_remote_origin(tmp_path) is None

    def test_empty_stdout_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, "   \n"))
        assert completion_candidates._run_git_remote_origin(tmp_path) is None

    def test_oserror_returns_none(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def raises(*a: Any, **kw: Any) -> None:
            raise OSError("no git")

        monkeypatch.setattr("subprocess.run", raises)
        assert completion_candidates._run_git_remote_origin(tmp_path) is None

    def test_timeout_returns_none(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:

        def raises(*a: Any, **kw: Any) -> None:
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        monkeypatch.setattr("subprocess.run", raises)
        assert completion_candidates._run_git_remote_origin(tmp_path) is None


class TestRunGhPrView:
    def test_success_returns_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = json.dumps({"state": "closed", "merged_at": "x"})
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, payload))
        result = completion_candidates._run_gh_pr_view("o/n", 1)
        assert result == {"state": "closed", "merged_at": "x"}

    def test_nonzero_returncode_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(1, "", "404"))
        assert completion_candidates._run_gh_pr_view("o/n", 99) is None

    def test_invalid_json_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, "not json"))
        assert completion_candidates._run_gh_pr_view("o/n", 1) is None

    def test_non_dict_json_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, "[]"))
        assert completion_candidates._run_gh_pr_view("o/n", 1) is None

    def test_timeout_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:

        def raises(*a: Any, **kw: Any) -> None:
            raise subprocess.TimeoutExpired(cmd="gh", timeout=10)

        monkeypatch.setattr("subprocess.run", raises)
        assert completion_candidates._run_gh_pr_view("o/n", 1) is None


class TestRunGhIssueSearch:
    def test_success_returns_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = json.dumps([{"number": 1, "title": "x"}])
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, payload))
        result = completion_candidates._run_gh_issue_search("slug", "o/n")
        assert result == [{"number": 1, "title": "x"}]

    def test_empty_list_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, "[]"))
        assert completion_candidates._run_gh_issue_search("slug", "o/n") == []

    def test_nonzero_returncode_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(1))
        assert completion_candidates._run_gh_issue_search("slug", "o/n") is None

    def test_invalid_json_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, "broken"))
        assert completion_candidates._run_gh_issue_search("slug", "o/n") is None

    def test_non_list_json_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: _completed(0, "{}"))
        assert completion_candidates._run_gh_issue_search("slug", "o/n") is None
