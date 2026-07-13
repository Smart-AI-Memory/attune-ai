"""Tests for plugin/hooks/_state.py — session-continuity helpers.

Covers ``discover_specs``, ``git_state``, ``session_sentinel_path``,
and ``prune_stale_sentinels``. The hook scripts are loaded via
``importlib.util.spec_from_file_location`` to match the existing
plugin-hook test convention.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_state_module():
    """Load _state.py fresh — avoids cross-test sys.path leakage."""
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if "_state" in sys.modules:
        return sys.modules["_state"]
    spec = importlib.util.spec_from_file_location("_state", _HOOKS_DIR / "_state.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_state"] = module  # dataclasses-friendly registration
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def state_mod():
    return _load_state_module()


def _write_spec(
    spec_dir: Path,
    *,
    requirements_status: str | None = "approved",
    design_status: str | None = None,
    tasks_status: str | None = None,
) -> None:
    """Helper — populate a spec directory with phase files."""
    spec_dir.mkdir(parents=True, exist_ok=True)
    if requirements_status is not None:
        (spec_dir / "requirements.md").write_text(
            f"# Requirements\n\n**Status**: {requirements_status}\n",
            encoding="utf-8",
        )
    if design_status is not None:
        (spec_dir / "design.md").write_text(
            f"# Design\n\n**Status**: {design_status}\n",
            encoding="utf-8",
        )
    if tasks_status is not None:
        (spec_dir / "tasks.md").write_text(
            f"# Tasks\n\n**Status**: {tasks_status}\n",
            encoding="utf-8",
        )


# ── discover_specs ───────────────────────────────────────────


class TestDiscoverSpecs:
    def test_empty_root_returns_empty(self, tmp_path: Path, state_mod) -> None:
        assert state_mod.discover_specs([tmp_path]) == []

    def test_missing_specs_dir_tolerated(self, tmp_path: Path, state_mod) -> None:
        # No `specs/` dir exists; should still succeed.
        (tmp_path / "src").mkdir()
        assert state_mod.discover_specs([tmp_path]) == []

    def test_single_in_flight_spec(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "feat-x"
        _write_spec(spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        info = result[0]
        assert info.slug == "feat-x"
        assert info.phase == "requirements"
        assert info.status == "approved"
        assert info.layer == "workspace"

    def test_completed_tasks_excluded(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "done-feat"
        _write_spec(spec, tasks_status="complete")
        assert state_mod.discover_specs([tmp_path]) == []

    def test_tasks_phase_takes_priority_over_design(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "feat-y"
        _write_spec(
            spec,
            requirements_status="approved",
            design_status="approved",
            tasks_status="approved",
        )
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].phase == "tasks"
        assert result[0].status == "approved"

    def test_most_recent_first(self, tmp_path: Path, state_mod) -> None:
        older = tmp_path / "specs" / "older"
        newer = tmp_path / "specs" / "newer"
        _write_spec(older, requirements_status="approved")
        # Force older to have an mtime well in the past.
        old_t = time.time() - 3600
        os.utime(older / "requirements.md", (old_t, old_t))
        _write_spec(newer, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        slugs = [s.slug for s in result]
        assert slugs == ["newer", "older"]

    def test_malformed_status_line(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "feat-malformed"
        spec.mkdir(parents=True)
        # No Status: line at all
        (spec / "requirements.md").write_text("# Requirements\nno status here\n")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].status == ""

    def test_layer_specs_picked_up(self, tmp_path: Path, state_mod) -> None:
        layer_spec = tmp_path / "attune-rag" / "specs" / "rag-feat"
        _write_spec(layer_spec, requirements_status="approved")
        workspace_spec = tmp_path / "specs" / "ws-feat"
        _write_spec(workspace_spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        layers = {s.slug: s.layer for s in result}
        assert layers["ws-feat"] == "workspace"
        assert layers["rag-feat"] == "attune-rag"

    def test_skips_non_directory_entries(self, tmp_path: Path, state_mod) -> None:
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "README.md").write_text("not a spec dir")
        assert state_mod.discover_specs([tmp_path]) == []

    def test_docs_specs_at_root_is_workspace(self, tmp_path: Path, state_mod) -> None:
        # attune-rag/author/help keep specs under docs/specs/, not specs/.
        spec = tmp_path / "docs" / "specs" / "rag-feat"
        _write_spec(spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].slug == "rag-feat"
        assert result[0].layer == "workspace"

    def test_docs_specs_under_layer(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "attune-author" / "docs" / "specs" / "author-feat"
        _write_spec(spec, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].slug == "author-feat"
        assert result[0].layer == "attune-author"

    def test_both_conventions_coexist_without_dup(self, tmp_path: Path, state_mod) -> None:
        # A repo using specs/ and one using docs/specs/ side by side; no
        # double-counting, each attributed to the right layer.
        _write_spec(tmp_path / "specs" / "ws-feat", requirements_status="approved")
        _write_spec(
            tmp_path / "attune-rag" / "docs" / "specs" / "rag-feat",
            requirements_status="approved",
        )
        result = state_mod.discover_specs([tmp_path])
        layers = {s.slug: s.layer for s in result}
        assert layers == {"ws-feat": "workspace", "rag-feat": "attune-rag"}


# ── status reconciliation (self-truthing) ────────────────────


def _write_tasks_with_checklist(
    spec_dir: Path,
    *,
    header_status: str,
    checklist_lines: list[str],
    terminal_line: str | None = None,
) -> None:
    """Helper — write a tasks.md with a Completion checklist section.

    ``checklist_lines`` are appended verbatim under the
    ``## Completion checklist`` heading. Each should be a full
    ``- [x] body`` or ``- [ ] body`` line (caller controls the box
    state and whether the body is deferred).
    """
    spec_dir.mkdir(parents=True, exist_ok=True)
    body = f"# Tasks\n\n**Status**: {header_status}\n\n"
    if terminal_line is not None:
        body += f"{terminal_line}\n\n"
    body += "## Completion checklist\n\n"
    body += "\n".join(checklist_lines)
    body += "\n"
    (spec_dir / "tasks.md").write_text(body, encoding="utf-8")


class TestStatusReconciliation:
    """Regression guard for the self-truthing-spec-status spec."""

    def test_draft_header_with_closed_checklist_reconciles_to_complete(
        self, tmp_path: Path, state_mod
    ) -> None:
        """Architecture-realignment shape: draft header above a fully
        checked checklist (with deferred rows) → effective complete,
        conflict True, NOT in-flight."""
        spec_dir = tmp_path / "specs" / "ar-shape"
        _write_tasks_with_checklist(
            spec_dir,
            header_status="draft",
            checklist_lines=[
                "- [x] Phase 1 — Implementation",
                "- [x] Phase 2 — Tests",
                "- [ ] ~~Phase 3 — Stretch goal~~ deferred to v2",
                "- [ ] Audit cleanup — N/A",
            ],
        )
        result = state_mod.discover_specs([tmp_path])
        # Excluded from in-flight list per the reconciler.
        assert [s.slug for s in result] == []

        # Verify the reconciler reaches the expected verdict directly.
        verdict, source = state_mod._completion_signal((spec_dir / "tasks.md").read_text())
        assert verdict == "complete"
        assert source == "checklist"

    def test_approved_header_with_partial_checklist_stays_in_flight(
        self, tmp_path: Path, state_mod
    ) -> None:
        spec_dir = tmp_path / "specs" / "in-progress"
        _write_tasks_with_checklist(
            spec_dir,
            header_status="approved",
            checklist_lines=[
                "- [x] Phase 1 — Done",
                "- [ ] Phase 2 — Working",
                "- [ ] Phase 3 — Pending",
            ],
        )
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        spec = result[0]
        assert spec.status == "approved"
        assert spec.effective_status == "approved"
        assert spec.status_source == "header"
        assert spec.status_conflict is False

    def test_no_checklist_no_terminal_falls_back_to_header(self, tmp_path: Path, state_mod) -> None:
        """Header-only files behave exactly as they did before."""
        spec_dir = tmp_path / "specs" / "header-only"
        _write_spec(spec_dir, requirements_status="approved")
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        spec = result[0]
        assert spec.status == "approved"
        assert spec.effective_status == "approved"
        assert spec.status_source == "header"
        assert spec.status_conflict is False

    def test_malformed_checklist_falls_back_safely(self, tmp_path: Path, state_mod) -> None:
        """Heading present but body has no parseable ``- [ ]`` rows
        → no signal, fall back to header. Must NOT raise."""
        spec_dir = tmp_path / "specs" / "malformed"
        spec_dir.mkdir(parents=True)
        (spec_dir / "tasks.md").write_text(
            "# Tasks\n\n**Status**: in-progress\n\n"
            "## Completion checklist\n\n"
            "Some random unrelated prose with no checkbox rows.\n",
            encoding="utf-8",
        )
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        spec = result[0]
        assert spec.effective_status == "in-progress"
        assert spec.status_conflict is False

    def test_terminal_line_overrides_stale_approved_header(self, tmp_path: Path, state_mod) -> None:
        spec_dir = tmp_path / "specs" / "terminal-line"
        spec_dir.mkdir(parents=True)
        (spec_dir / "tasks.md").write_text(
            "# Tasks\n\n"
            "**Status**: approved\n\n"
            "## Phase 1 — Implementation\n\n"
            "Did a thing. The work landed in 2026-05-08.\n\n"
            "Spec status: closed\n",
            encoding="utf-8",
        )
        result = state_mod.discover_specs([tmp_path])
        # Excluded from in-flight per reconciliation.
        assert [s.slug for s in result] == []

        verdict, source = state_mod._completion_signal((spec_dir / "tasks.md").read_text())
        assert verdict == "closed"
        assert source == "terminal-line"

    def test_format_phase_renders_conflict_hint(self, state_mod) -> None:
        """When status_conflict is True, _format_phase appends the
        one-line hint so a stale header gets surfaced for fix."""
        # Load spec_orient module the same way state_mod is loaded.
        import importlib.util
        from pathlib import Path as _P

        plugin_hooks = _P(__file__).resolve().parents[3] / "plugin" / "hooks"
        spec = importlib.util.spec_from_file_location(
            "_test_spec_orient", plugin_hooks / "spec_orient.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        spec_info = state_mod.SpecInfo(
            slug="ar-shape",
            path=_P("/tmp/x"),
            layer="workspace",
            phase="tasks",
            status="draft",
            mtime=0.0,
            effective_status="complete",
            status_source="checklist",
            status_conflict=True,
        )
        rendered = mod._format_phase(spec_info)
        assert "complete" in rendered
        assert "tasks closed per checklist" in rendered
        assert '"draft"' in rendered
        assert "worth fixing" in rendered

    def test_format_phase_no_hint_when_no_conflict(self, state_mod) -> None:
        """When status_conflict is False, the hint stays absent."""
        import importlib.util
        from pathlib import Path as _P

        plugin_hooks = _P(__file__).resolve().parents[3] / "plugin" / "hooks"
        spec = importlib.util.spec_from_file_location(
            "_test_spec_orient2", plugin_hooks / "spec_orient.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        spec_info = state_mod.SpecInfo(
            slug="normal",
            path=_P("/tmp/x"),
            layer="workspace",
            phase="design",
            status="approved",
            mtime=0.0,
            effective_status="approved",
            status_source="header",
            status_conflict=False,
        )
        rendered = mod._format_phase(spec_info)
        assert rendered == "design approved"

    @staticmethod
    def _load_spec_orient(name: str):
        """Load spec_orient.py fresh (matches the conflict-hint tests)."""
        import importlib.util
        from pathlib import Path as _P

        plugin_hooks = _P(__file__).resolve().parents[3] / "plugin" / "hooks"
        spec = importlib.util.spec_from_file_location(name, plugin_hooks / "spec_orient.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_format_phase_renders_suspected_stale_hint(self, state_mod) -> None:
        """A suspected-stale spec appends the deliverables-present hint."""
        mod = self._load_spec_orient("_test_spec_orient_stale")
        spec_info = state_mod.SpecInfo(
            slug="shipped",
            path=Path("/tmp/x"),
            layer="workspace",
            phase="tasks",
            status="approved",
            mtime=0.0,
            effective_status="approved",
            status_source="header",
            status_conflict=False,
            staleness="suspected-stale",
        )
        rendered = mod._format_phase(spec_info)
        assert rendered.startswith("tasks approved")
        assert "deliverables present" in rendered
        assert '"approved"' in rendered
        assert "verify before building" in rendered

    def test_format_phase_no_stale_hint_for_ok_or_unknown(self, state_mod) -> None:
        """ok / unknown staleness render nothing beyond the base blurb."""
        mod = self._load_spec_orient("_test_spec_orient_ok")
        for verdict in ("ok", "unknown", "partial", "docs-only", "opted-out"):
            spec_info = state_mod.SpecInfo(
                slug="normal",
                path=Path("/tmp/x"),
                layer="workspace",
                phase="design",
                status="approved",
                mtime=0.0,
                effective_status="approved",
                status_source="header",
                status_conflict=False,
                staleness=verdict,
            )
            assert mod._format_phase(spec_info) == "design approved"

    def test_format_phase_conflict_wins_over_stale(self, state_mod) -> None:
        """status_conflict takes precedence when both signals are set."""
        mod = self._load_spec_orient("_test_spec_orient_precedence")
        spec_info = state_mod.SpecInfo(
            slug="both",
            path=Path("/tmp/x"),
            layer="workspace",
            phase="tasks",
            status="draft",
            mtime=0.0,
            effective_status="complete",
            status_source="terminal-line",
            status_conflict=True,
            staleness="suspected-stale",
        )
        rendered = mod._format_phase(spec_info)
        assert "worth fixing" in rendered
        assert "deliverables present" not in rendered

    def test_format_phase_suspected_stale_empty_status(self, state_mod) -> None:
        """A suspected-stale spec with no header status never raises."""
        mod = self._load_spec_orient("_test_spec_orient_empty")
        spec_info = state_mod.SpecInfo(
            slug="nostatus",
            path=Path("/tmp/x"),
            layer="workspace",
            phase="tasks",
            status="",
            mtime=0.0,
            effective_status="",
            status_source="header",
            status_conflict=False,
            staleness="suspected-stale",
        )
        rendered = mod._format_phase(spec_info)
        assert '"no status"' in rendered


# ── git_state ────────────────────────────────────────────────


class TestGitState:
    def test_non_git_dir_returns_empty(self, tmp_path: Path, state_mod) -> None:
        result = state_mod.git_state(tmp_path)
        assert result.branch == ""
        assert result.last_sha == ""
        assert result.last_subject == ""
        assert result.uncommitted == ()

    def test_clean_repo(self, tmp_path: Path, state_mod) -> None:
        _init_repo(tmp_path)
        _commit(tmp_path, "README.md", "hello\n", "feat: initial")
        result = state_mod.git_state(tmp_path)
        assert result.branch  # whatever the local default branch is
        assert len(result.last_sha) >= 7
        assert result.last_subject == "feat: initial"
        assert result.uncommitted == ()

    def test_dirty_repo_lists_uncommitted(self, tmp_path: Path, state_mod) -> None:
        _init_repo(tmp_path)
        _commit(tmp_path, "README.md", "hello\n", "feat: initial")
        (tmp_path / "new.txt").write_text("untracked\n")
        (tmp_path / "README.md").write_text("modified\n")
        result = state_mod.git_state(tmp_path)
        assert "new.txt" in result.uncommitted
        assert "README.md" in result.uncommitted


# ── session_sentinel_path ────────────────────────────────────


class TestSessionSentinelPath:
    def test_uses_override_dir(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        path = state_mod.session_sentinel_path("abc123")
        assert path == tmp_path / ".compact-warned-abc123"

    def test_falls_back_to_home_attune(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ATTUNE_AI_SENTINEL_DIR", raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        path = state_mod.session_sentinel_path("xyz")
        assert path == tmp_path / ".attune" / ".compact-warned-xyz"

    def test_sanitizes_session_id(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        path = state_mod.session_sentinel_path("../escape/attempt")
        assert path.parent == tmp_path
        assert ".." not in path.name

    def test_no_session_key_returns_none(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No identity -> None, never a shared 'unknown' bucket (the
        2026-07-13 headless-collapse regression guard)."""
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        assert state_mod.session_sentinel_path(None) is None
        assert state_mod.session_sentinel_path("") is None


# ── resolve_session_key ──────────────────────────────────────


class TestResolveSessionKey:
    def test_session_id_wins(self, state_mod) -> None:
        payload = {"session_id": "abc", "transcript_path": "/x/y.jsonl"}
        assert state_mod.resolve_session_key(payload) == "abc"

    def test_transcript_stem_fallback(self, state_mod) -> None:
        """The transcript filename stem IS the session uuid."""
        payload = {"transcript_path": "/p/fdf0adc1-4322.jsonl"}
        assert state_mod.resolve_session_key(payload) == "fdf0adc1-4322"

    def test_no_identity_is_none(self, state_mod) -> None:
        assert state_mod.resolve_session_key({}) is None
        assert state_mod.resolve_session_key({"session_id": "", "transcript_path": ""}) is None


# ── prune_stale_sentinels ────────────────────────────────────


class TestPruneStaleSentinels:
    def test_no_dir_returns_zero(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "absent"))
        assert state_mod.prune_stale_sentinels() == 0

    def test_removes_old_sentinels_keeps_fresh(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path))
        old = tmp_path / ".compact-warned-old"
        fresh = tmp_path / ".compact-warned-fresh"
        unrelated = tmp_path / "other.txt"
        old.write_text("0.71")
        fresh.write_text("0.72")
        unrelated.write_text("hi")
        old_mtime = time.time() - 30 * 24 * 3600  # 30 days ago
        os.utime(old, (old_mtime, old_mtime))
        removed = state_mod.prune_stale_sentinels()
        assert removed == 1
        assert not old.exists()
        assert fresh.exists()
        assert unrelated.exists()  # untouched


# ── workspace_roots ──────────────────────────────────────────


class TestWorkspaceRoots:
    def test_override_takes_precedence(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Use os.pathsep so this test is portable: ":" on POSIX, ";" on
        # Windows. Hardcoding ":" caused Windows to split on the drive
        # letter ("C:") and shred the path.
        monkeypatch.setenv(
            "ATTUNE_AI_WORKSPACE_ROOTS",
            os.pathsep.join([str(tmp_path / "a"), str(tmp_path / "b")]),
        )
        roots = state_mod.workspace_roots(cwd=tmp_path)
        assert roots == [tmp_path / "a", tmp_path / "b"]

    def test_default_uses_cwd(
        self, tmp_path: Path, state_mod, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ATTUNE_AI_WORKSPACE_ROOTS", raising=False)
        # Make ~/attune absent so we get a clean single-entry result.
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "fake-home"))
        roots = state_mod.workspace_roots(cwd=tmp_path)
        assert roots[0] == tmp_path.resolve()


# ── fixtures ─────────────────────────────────────────────────


def _init_repo(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "commit.gpgsign", "false"],
        check=True,
    )


def _commit(path: Path, filename: str, content: str, message: str) -> None:
    (path / filename).write_text(content)
    subprocess.run(["git", "-C", str(path), "add", filename], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", message],
        check=True,
        capture_output=True,
    )


class TestInformativeStatusRecognition:
    """Regression guard: terminal status must be recognized in the
    *informative* form people actually write — ``complete (date) —
    reason`` — and across markdown bold variants, not just the bare
    word. Before this fix a correctly-marked spec stayed in-flight
    forever because ``"complete (date) — ..." not in _TERMINAL_VERDICTS``.
    """

    def test_leading_verdict_tokenizes_first_word(self, state_mod) -> None:
        lv = state_mod._leading_verdict
        assert lv("complete (2026-06-09) — shipped #694") == "complete"
        assert lv("  living (ongoing program)") == "living"
        assert lv("draft") == "draft"
        assert lv("") == ""
        assert lv("**complete**") == "complete"

    def test_informative_complete_header_excluded(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "done-informative"
        _write_spec(
            spec,
            requirements_status="complete (2026-06-09) — shipped #694",
        )
        assert state_mod.discover_specs([tmp_path]) == []

    def test_colon_inside_bold_variant_parsed(self, tmp_path: Path, state_mod) -> None:
        # ``**Status:** complete`` — colon inside the bold — was the
        # exact format the old regex missed (collaboration-gates).
        spec = tmp_path / "specs" / "colon-inside-bold"
        spec.mkdir(parents=True)
        (spec / "requirements.md").write_text(
            "# Requirements\n\n**Status:** complete (2026-06-09) — shipped\n",
            encoding="utf-8",
        )
        assert state_mod.discover_specs([tmp_path]) == []

    def test_ongoing_living_excluded_not_in_flight(self, tmp_path: Path, state_mod) -> None:
        spec = tmp_path / "specs" / "living-program"
        _write_spec(spec, requirements_status="living (ongoing program)")
        assert state_mod.discover_specs([tmp_path]) == []

    @pytest.mark.parametrize("word", ["shipped", "done", "completed"])
    def test_done_synonyms_excluded(self, tmp_path: Path, state_mod, word: str) -> None:
        spec = tmp_path / "specs" / f"done-{word}"
        _write_spec(spec, requirements_status=f"{word} 2026-06-09")
        assert state_mod.discover_specs([tmp_path]) == []

    @pytest.mark.parametrize("word", ["draft", "approved", "in-progress"])
    def test_non_terminal_still_in_flight(self, tmp_path: Path, state_mod, word: str) -> None:
        spec = tmp_path / "specs" / f"open-{word}"
        _write_spec(spec, requirements_status=f"{word} (2026-06-09)")
        result = state_mod.discover_specs([tmp_path])
        assert [s.slug for s in result] == [f"open-{word}"]
