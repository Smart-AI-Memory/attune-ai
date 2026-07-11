"""Tests for the spec-status-integrity Deliverables parser in _state.py.

Covers ``deliverables_for_spec`` — the machine-readable
``## Deliverables`` contract a spec declares so the staleness
classifier can check whether its work has shipped. Mock-free /
filesystem-only per testing-conventions.md (no ``live`` marker, no
API key).

The hook module is loaded via ``spec_from_file_location`` to match the
existing plugin-hook test convention (see
``test_session_continuity_state.py``).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import json as _json
import sys
import types as _types
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


def _load_spec_audit_module():
    """Load spec_audit.py fresh (its sibling _state import resolves via
    the sys.path bootstrap in the hook header)."""
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    spec = importlib.util.spec_from_file_location("spec_audit", _HOOKS_DIR / "spec_audit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["spec_audit"] = module  # dataclasses-friendly registration
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def state_mod():
    return _load_state_module()


@pytest.fixture
def audit_mod():
    return _load_spec_audit_module()


def _block(*items: str, heading: str = "## Deliverables") -> str:
    """Wrap deliverable list items in a minimal spec document."""
    body = "\n".join(items)
    return f"# Some Spec\n\n**Status**: approved\n\n{heading}\n\n{body}\n"


# ── path-only items ──────────────────────────────────────────


class TestPathOnly:
    def test_single_path(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(_block("- attune-rag/src/attune_rag/foo.py"))
        assert result.entries == (
            state_mod.DeliverableEntry(pattern="attune-rag/src/attune_rag/foo.py"),
        )
        assert result.is_na is False
        assert result.opt_out is False

    def test_multiple_paths(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(
            _block(
                "- attune-ai/plugin/hooks/spec_audit.py",
                "- attune-rag/src/attune_rag/foo.py",
            )
        )
        assert [e.pattern for e in result.entries] == [
            "attune-ai/plugin/hooks/spec_audit.py",
            "attune-rag/src/attune_rag/foo.py",
        ]
        assert all(e.symbol == "" for e in result.entries)

    def test_glob_pattern_preserved(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(_block("- attune-gui/tests/**/test_bar.py"))
        assert result.entries[0].pattern == "attune-gui/tests/**/test_bar.py"


# ── symbol suffix ────────────────────────────────────────────


class TestSymbolSuffix:
    def test_em_dash_symbol(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(
            _block("- attune-ai/plugin/hooks/spec_audit.py — symbol: audit_specs")
        )
        entry = result.entries[0]
        assert entry.pattern == "attune-ai/plugin/hooks/spec_audit.py"
        assert entry.symbol == "audit_specs"

    def test_double_hyphen_symbol(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(
            _block("- attune-ai/plugin/hooks/spec_audit.py -- symbol: audit_specs")
        )
        entry = result.entries[0]
        assert entry.pattern == "attune-ai/plugin/hooks/spec_audit.py"
        assert entry.symbol == "audit_specs"


# ── backtick tolerance ───────────────────────────────────────


class TestBacktickVariants:
    def test_backtick_wrapped_path(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(_block("- `attune-ai/plugin/hooks/spec_audit.py`"))
        assert result.entries[0].pattern == "attune-ai/plugin/hooks/spec_audit.py"
        assert result.entries[0].symbol == ""

    def test_backtick_wrapped_with_symbol(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(
            _block("- `attune-ai/plugin/hooks/spec_audit.py` — symbol: audit_specs")
        )
        entry = result.entries[0]
        assert entry.pattern == "attune-ai/plugin/hooks/spec_audit.py"
        assert entry.symbol == "audit_specs"


# ── N/A sentinel ─────────────────────────────────────────────


class TestNaSentinel:
    def test_lone_na_sets_is_na(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(_block("- N/A"))
        assert result.is_na is True
        assert result.entries == ()

    def test_na_without_slash(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(_block("- NA"))
        assert result.is_na is True

    def test_italic_none_sets_is_na(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(_block("- _None_"))
        assert result.is_na is True
        assert result.entries == ()

    def test_na_does_not_become_an_entry(self, state_mod) -> None:
        # N/A must be caught by the sentinel branch, not parsed as a path.
        result = state_mod.deliverables_for_spec(_block("- N/A"))
        assert all(e.pattern != "N/A" for e in result.entries)


# ── opt-out ──────────────────────────────────────────────────


class TestOptOut:
    def test_drift_check_ignore_sets_opt_out(self, state_mod) -> None:
        text = _block("- attune-rag/src/foo.py") + "\ndrift-check: ignore\n"
        result = state_mod.deliverables_for_spec(text)
        assert result.opt_out is True
        # Entries still parse — opt_out is an independent signal.
        assert len(result.entries) == 1

    def test_opt_out_anywhere_without_block(self, state_mod) -> None:
        text = "# Draft\n\n**Status**: draft\n\ndrift-check: ignore\n"
        result = state_mod.deliverables_for_spec(text)
        assert result.opt_out is True
        assert result.entries == ()

    def test_no_opt_out_by_default(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(_block("- attune-rag/src/foo.py"))
        assert result.opt_out is False


# ── absent / malformed blocks ────────────────────────────────


class TestAbsentOrMalformed:
    def test_no_deliverables_section(self, state_mod) -> None:
        text = "# Spec\n\n**Status**: approved\n\n## Overview\n\nSome prose.\n"
        result = state_mod.deliverables_for_spec(text)
        assert result.entries == ()
        assert result.is_na is False
        assert result.opt_out is False

    def test_empty_block_zero_entries(self, state_mod) -> None:
        text = "# Spec\n\n## Deliverables\n\n## Next Section\n\n- not a deliverable\n"
        result = state_mod.deliverables_for_spec(text)
        assert result.entries == ()

    def test_malformed_items_skipped(self, state_mod) -> None:
        # A bare list bullet with no content, and prose lines, are ignored.
        text = _block("-", "just prose, not a bullet", "- attune-rag/src/ok.py")
        result = state_mod.deliverables_for_spec(text)
        assert [e.pattern for e in result.entries] == ["attune-rag/src/ok.py"]

    def test_section_bounded_by_next_h2(self, state_mod) -> None:
        # Items after the next ## heading must NOT be collected.
        text = (
            "# Spec\n\n## Deliverables\n\n"
            "- attune-rag/src/in_section.py\n\n"
            "## Testing strategy\n\n"
            "- attune-rag/src/out_of_section.py\n"
        )
        result = state_mod.deliverables_for_spec(text)
        assert [e.pattern for e in result.entries] == ["attune-rag/src/in_section.py"]

    def test_case_insensitive_heading(self, state_mod) -> None:
        result = state_mod.deliverables_for_spec(
            _block("- attune-rag/src/foo.py", heading="## deliverables")
        )
        assert len(result.entries) == 1


# ── resolution + classifier (task 2) ─────────────────────────


@pytest.fixture
def workspace(tmp_path: Path):
    """A workspace root whose layer dir is reached through a symlink.

    Mirrors the on-disk layout: ``~/attune/attune-rag`` is a symlink to
    the real ``~/attune-rag`` checkout. Returns the workspace root used
    as the resolution base. Skips when symlinks aren't available.
    """
    layer = tmp_path / "attune-rag"
    (layer / "src" / "attune_rag").mkdir(parents=True)
    (layer / "src" / "attune_rag" / "foo.py").write_text(
        "def foo():\n    return 1\n", encoding="utf-8"
    )
    (layer / "tests" / "unit").mkdir(parents=True)
    (layer / "tests" / "unit" / "test_bar.py").write_text(
        "def test_bar():\n    assert True\n", encoding="utf-8"
    )
    root = tmp_path / "attune"
    root.mkdir()
    try:
        (root / "attune-rag").symlink_to(layer, target_is_directory=True)
    except (OSError, NotImplementedError):  # pragma: no cover - platform guard
        pytest.skip("symlinks not supported in this environment")
    return root


class TestResolveEntry:
    def test_existing_path_resolves(self, state_mod, workspace) -> None:
        entry = state_mod.DeliverableEntry(pattern="attune-rag/src/attune_rag/foo.py")
        assert state_mod._resolve_entry(entry, [workspace]) is True

    def test_missing_path_does_not_resolve(self, state_mod, workspace) -> None:
        entry = state_mod.DeliverableEntry(pattern="attune-rag/src/nope.py")
        assert state_mod._resolve_entry(entry, [workspace]) is False

    def test_glob_resolves_across_symlink(self, state_mod, workspace) -> None:
        # ** must recurse inside the real dir reached through the symlink.
        entry = state_mod.DeliverableEntry(pattern="attune-rag/tests/**/test_bar.py")
        assert state_mod._resolve_entry(entry, [workspace]) is True

    def test_symbol_present_resolves(self, state_mod, workspace) -> None:
        entry = state_mod.DeliverableEntry(
            pattern="attune-rag/src/attune_rag/foo.py", symbol="def foo"
        )
        assert state_mod._resolve_entry(entry, [workspace]) is True

    def test_symbol_absent_does_not_resolve(self, state_mod, workspace) -> None:
        # File exists, but the named symbol is not in it.
        entry = state_mod.DeliverableEntry(
            pattern="attune-rag/src/attune_rag/foo.py", symbol="def missing_symbol"
        )
        assert state_mod._resolve_entry(entry, [workspace]) is False

    def test_directory_deliverable_resolves_on_existence(self, state_mod, workspace) -> None:
        entry = state_mod.DeliverableEntry(pattern="attune-rag/src/attune_rag")
        assert state_mod._resolve_entry(entry, [workspace]) is True


class TestClassifyStaleness:
    def _spec(self, *items: str, status: str = "approved") -> str:
        body = "\n".join(items)
        return f"# Spec\n\n**Status**: {status}\n\n## Deliverables\n\n{body}\n"

    def test_all_resolve_non_terminal_is_suspected_stale(self, state_mod, workspace) -> None:
        text = self._spec(
            "- attune-rag/src/attune_rag/foo.py",
            "- attune-rag/tests/**/test_bar.py",
            status="approved",
        )
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "suspected-stale"

    def test_all_resolve_terminal_status_is_ok(self, state_mod, workspace) -> None:
        text = self._spec("- attune-rag/src/attune_rag/foo.py", status="complete (2026-06-17)")
        assert state_mod.classify_staleness(text, "complete (2026-06-17)", [workspace]) == "ok"

    def test_body_terminal_signal_clears_stale(self, state_mod, workspace) -> None:
        # Header says approved, but a terminal line deeper in the doc wins.
        text = (
            "# Spec\n\n**Status**: approved\n\n"
            "## Deliverables\n\n- attune-rag/src/attune_rag/foo.py\n\n"
            "Status: shipped #99\n"
        )
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "ok"

    def test_partial_when_one_of_two_resolves(self, state_mod, workspace) -> None:
        text = self._spec(
            "- attune-rag/src/attune_rag/foo.py",  # exists
            "- attune-rag/src/attune_rag/missing.py",  # absent
            status="approved",
        )
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "partial"

    def test_bad_symbol_makes_it_partial(self, state_mod, workspace) -> None:
        text = self._spec(
            "- attune-rag/src/attune_rag/foo.py",  # resolves
            "- attune-rag/src/attune_rag/foo.py — symbol: def nope",  # symbol absent
            status="approved",
        )
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "partial"

    def test_opt_out_is_opted_out(self, state_mod, workspace) -> None:
        text = (
            self._spec("- attune-rag/src/attune_rag/foo.py", status="approved")
            + "\ndrift-check: ignore\n"
        )
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "opted-out"

    def test_na_is_docs_only(self, state_mod, workspace) -> None:
        text = self._spec("- N/A", status="approved")
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "docs-only"

    def test_no_block_is_unknown(self, state_mod, workspace) -> None:
        text = "# Spec\n\n**Status**: approved\n\n## Overview\n\nProse.\n"
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "unknown"

    def test_entries_none_present_is_unknown(self, state_mod, workspace) -> None:
        # Declared deliverables, none shipped yet — pre-implementation.
        text = self._spec("- attune-rag/src/attune_rag/not_yet.py", status="approved")
        assert state_mod.classify_staleness(text, "approved", [workspace]) == "unknown"


# ── discover_specs wiring (task 3) ───────────────────────────


def _spec_file(spec_dir: Path, *, status: str, deliverable: str) -> None:
    """Write a one-file spec with a Deliverables block."""
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "tasks.md").write_text(
        f"# Tasks\n\n**Status**: {status}\n\n## Deliverables\n\n- {deliverable}\n",
        encoding="utf-8",
    )


@pytest.fixture
def spec_tree(tmp_path: Path):
    """A workspace root with three specs and one shipped source file.

    - ``shipped-spec``  — approved, deliverable present  → suspected-stale
    - ``pending-spec``  — approved, deliverable absent   → unknown
    - ``done-spec``     — complete, deliverable present  → ok (terminal)
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "shipped.py").write_text("x = 1\n", encoding="utf-8")
    specs = tmp_path / "specs"
    _spec_file(specs / "shipped-spec", status="approved", deliverable="src/shipped.py")
    _spec_file(specs / "pending-spec", status="approved", deliverable="src/not_yet.py")
    _spec_file(specs / "done-spec", status="complete (2026-06-17)", deliverable="src/shipped.py")
    return tmp_path


class TestDiscoverSpecsStaleness:
    def test_default_excludes_terminal_and_populates_staleness(self, state_mod, spec_tree) -> None:
        result = state_mod.discover_specs([spec_tree])
        by_slug = {s.slug: s for s in result}
        # Terminal spec excluded by default.
        assert set(by_slug) == {"shipped-spec", "pending-spec"}
        assert by_slug["shipped-spec"].staleness == "suspected-stale"
        assert by_slug["pending-spec"].staleness == "unknown"

    def test_deliverables_field_populated(self, state_mod, spec_tree) -> None:
        result = state_mod.discover_specs([spec_tree])
        shipped = next(s for s in result if s.slug == "shipped-spec")
        assert [e.pattern for e in shipped.deliverables] == ["src/shipped.py"]

    def test_include_terminal_returns_all_with_ok(self, state_mod, spec_tree) -> None:
        result = state_mod.discover_specs([spec_tree], include_terminal=True)
        by_slug = {s.slug: s for s in result}
        assert set(by_slug) == {"shipped-spec", "pending-spec", "done-spec"}
        assert by_slug["done-spec"].staleness == "ok"

    def test_spec_without_block_is_unknown(self, state_mod, tmp_path) -> None:
        spec = tmp_path / "specs" / "no-block"
        spec.mkdir(parents=True)
        (spec / "tasks.md").write_text(
            "# Tasks\n\n**Status**: approved\n\n## Overview\n\nProse.\n",
            encoding="utf-8",
        )
        result = state_mod.discover_specs([tmp_path])
        assert len(result) == 1
        assert result[0].staleness == "unknown"
        assert result[0].deliverables == ()


# ── spec_audit CLI (task 5) ──────────────────────────────────


def _audit_spec_file(spec_dir: Path, *, status: str, deliverables: list[str]) -> None:
    """Write a one-file spec with one or more Deliverables items."""
    spec_dir.mkdir(parents=True, exist_ok=True)
    items = "\n".join(f"- {d}" for d in deliverables)
    (spec_dir / "tasks.md").write_text(
        f"# Tasks\n\n**Status**: {status}\n\n## Deliverables\n\n{items}\n",
        encoding="utf-8",
    )


@pytest.fixture
def audit_tree(tmp_path: Path):
    """A workspace with one of each staleness verdict for the matrix.

    - ``shipped-spec`` approved, present            → suspected-stale
    - ``partial-spec`` approved, 1 present / 1 not  → partial
    - ``pending-spec`` approved, absent             → unknown (0 of 1)
    - ``done-spec``    complete, present            → ok
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "shipped.py").write_text("x = 1\n", encoding="utf-8")
    specs = tmp_path / "specs"
    _audit_spec_file(specs / "shipped-spec", status="approved", deliverables=["src/shipped.py"])
    _audit_spec_file(
        specs / "partial-spec",
        status="approved",
        deliverables=["src/shipped.py", "src/missing.py"],
    )
    _audit_spec_file(specs / "pending-spec", status="approved", deliverables=["src/not_yet.py"])
    _audit_spec_file(
        specs / "done-spec", status="complete (2026-06-17)", deliverables=["src/shipped.py"]
    )
    return tmp_path


class TestAuditSpecs:
    def test_rows_classify_each_spec(self, audit_mod, audit_tree) -> None:
        by_slug = {r.slug: r for r in audit_mod.audit_specs([audit_tree])}
        assert by_slug["shipped-spec"].staleness == "suspected-stale"
        assert by_slug["shipped-spec"].resolved == 1
        assert by_slug["shipped-spec"].total == 1
        assert by_slug["partial-spec"].staleness == "partial"
        assert by_slug["partial-spec"].resolved == 1
        assert by_slug["partial-spec"].total == 2
        assert by_slug["pending-spec"].staleness == "unknown"
        assert by_slug["done-spec"].staleness == "ok"  # terminal, included

    def test_empty_workspace_returns_no_rows(self, audit_mod, tmp_path) -> None:
        assert audit_mod.audit_specs([tmp_path]) == []


class TestFormatReport:
    def test_matrix_headers_and_stale_footer(self, audit_mod, audit_tree) -> None:
        report = audit_mod.format_report(audit_mod.audit_specs([audit_tree]))
        for header in ("Spec", "Layer", "Status", "Staleness", "Unresolved"):
            assert header in report
        assert "⚠ suspected-stale" in report
        assert "shipped-spec" in report
        assert "1 of 2" in report  # partial detail (unresolved of total)
        assert "verify & update" in report

    def test_empty_report(self, audit_mod) -> None:
        report = audit_mod.format_report([])
        assert "(no specs found)" in report


class TestMainExitCodes:
    def test_default_exit_zero_with_stale(self, audit_mod, audit_tree, monkeypatch, capsys) -> None:
        monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", str(audit_tree))
        assert audit_mod.main([]) == 0
        out = capsys.readouterr().out
        assert "SPEC STATUS AUDIT" in out

    def test_strict_exit_one_with_stale(self, audit_mod, audit_tree, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", str(audit_tree))
        assert audit_mod.main(["--strict"]) == 1

    def test_strict_exit_zero_without_stale(self, audit_mod, tmp_path, monkeypatch) -> None:
        # Only a pending (unknown) spec — nothing suspected-stale.
        _audit_spec_file(
            tmp_path / "specs" / "pending",
            status="approved",
            deliverables=["src/not_yet.py"],
        )
        monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", str(tmp_path))
        assert audit_mod.main(["--strict"]) == 0

    def test_main_is_crash_proof(self, audit_mod, monkeypatch) -> None:
        def _boom(*_a, **_k):
            raise RuntimeError("disk on fire")

        monkeypatch.setattr(audit_mod, "audit_specs", _boom)
        # Warn-by-default: a thrown audit still exits 0.
        assert audit_mod.main([]) == 0


# ── extract_pr_refs (spec-status-integrity-hooks, task 2) ─────


class TestExtractPrRefs:
    """Four citation styles + negatives, per workspace design §1."""

    def test_pr_hash_style(self, state_mod) -> None:
        refs = state_mod.extract_pr_refs("Shipped via PR #212 yesterday.")
        assert refs == [state_mod.PrRef(number=212, repo=None, explicit=True)]

    def test_bare_hash_is_ambiguous(self, state_mod) -> None:
        refs = state_mod.extract_pr_refs("landed in attune #1191 last week")
        assert refs == [state_mod.PrRef(number=1191, repo=None, explicit=False)]

    def test_inline_in_status_single(self, state_mod) -> None:
        refs = state_mod.extract_pr_refs("**Status**: complete — shipped in #567")
        assert refs == [state_mod.PrRef(number=567, repo=None, explicit=False)]

    def test_inline_in_status_pr_list(self, state_mod) -> None:
        refs = state_mod.extract_pr_refs("**Status**: complete — shipped (PRs #303, #304)")
        assert refs == [
            state_mod.PrRef(number=303, repo=None, explicit=True),
            state_mod.PrRef(number=304, repo=None, explicit=True),
        ]

    def test_markdown_pull_url_resolves_repo(self, state_mod) -> None:
        text = "Done in [#95](https://github.com/Smart-AI-Memory/attune-author/pull/95)."
        refs = state_mod.extract_pr_refs(text)
        # Exactly one ref: the link text ``#95`` must NOT also produce a
        # bare current-repo ref.
        assert refs == [
            state_mod.PrRef(number=95, repo="Smart-AI-Memory/attune-author", explicit=True)
        ]

    def test_bare_pull_url(self, state_mod) -> None:
        text = "See https://github.com/Smart-AI-Memory/attune-rag/pull/188 for details."
        refs = state_mod.extract_pr_refs(text)
        assert refs == [
            state_mod.PrRef(number=188, repo="Smart-AI-Memory/attune-rag", explicit=True)
        ]

    # ── negatives ────────────────────────────────────────────

    def test_issue_url_yields_nothing(self, state_mod) -> None:
        text = "Tracked in [#12](https://github.com/Smart-AI-Memory/attune/issues/12)."
        assert state_mod.extract_pr_refs(text) == []

    def test_non_pull_github_url_yields_nothing(self, state_mod) -> None:
        text = "[the repo](https://github.com/Smart-AI-Memory/attune-rag/tree/main/src)"
        assert state_mod.extract_pr_refs(text) == []

    def test_hash_followed_by_word_chars_rejected(self, state_mod) -> None:
        assert state_mod.extract_pr_refs("commit #12abc is unrelated") == []

    def test_word_char_prefix_rejected(self, state_mod) -> None:
        assert state_mod.extract_pr_refs("channel foo#42 and anchor ##7") == []

    def test_code_fence_content_ignored(self, state_mod) -> None:
        text = "before\n```\nPR #999 and #888\n```\nafter"
        assert state_mod.extract_pr_refs(text) == []

    def test_inline_code_ignored(self, state_mod) -> None:
        assert state_mod.extract_pr_refs("cite specs as `PR #NNN` or `#123`") == []

    def test_empty_text(self, state_mod) -> None:
        assert state_mod.extract_pr_refs("") == []

    # ── dedupe + ordering ────────────────────────────────────

    def test_duplicates_dedupe_to_first_occurrence(self, state_mod) -> None:
        refs = state_mod.extract_pr_refs("PR #212 shipped this; see #212 again")
        assert refs == [state_mod.PrRef(number=212, repo=None, explicit=True)]

    def test_bare_then_explicit_upgrades_flag(self, state_mod) -> None:
        refs = state_mod.extract_pr_refs("see #212, later merged as PR #212")
        assert refs == [state_mod.PrRef(number=212, repo=None, explicit=True)]

    def test_same_number_different_repo_is_distinct(self, state_mod) -> None:
        text = "local #95 and [#95](https://github.com/Smart-AI-Memory/attune-author/pull/95)"
        refs = state_mod.extract_pr_refs(text)
        assert state_mod.PrRef(number=95, repo=None, explicit=False) in refs
        assert (
            state_mod.PrRef(number=95, repo="Smart-AI-Memory/attune-author", explicit=True) in refs
        )
        assert len(refs) == 2

    def test_document_order_across_styles(self, state_mod) -> None:
        text = (
            "First [#7](https://github.com/Smart-AI-Memory/attune-gui/pull/7), "
            "then PR #3, then bare #9."
        )
        refs = state_mod.extract_pr_refs(text)
        assert [r.number for r in refs] == [7, 3, 9]


# ── vocabulary lint + parked/glyph semantics (task 3) ─────────


class TestLintStatusToken:
    """Token table per workspace design §1 — recognized forms lint
    clean; unknown leading tokens are named unparseable, never guessed."""

    @pytest.mark.parametrize(
        "status",
        [
            # canonical 8
            "draft",
            "in-review",
            "approved",
            "in-progress",
            "implemented",
            "complete",
            "superseded",
            "parked",
            # historical terminal/ongoing aliases
            "closed",
            "completed",
            "retired",
            "shipped",
            "done",
            "living",
            "ongoing",
            # parked family
            "paused",
            "blocked",
            "deferred",
            # accepted in-flight forms
            "not started",
            "open",
            "pending",
            # glyphs
            "✓",
            "✅",
            "✓ (2026-07-10)",
            # informative decoration around a recognized token
            "approved (2026-07-10 — Patrick)",
            "**in-review** (attune #32)",
            "complete (2026-06-09) — shipped #694",
        ],
    )
    def test_recognized_tokens_lint_clean(self, state_mod, status) -> None:
        assert state_mod.lint_status_token(status) is None

    @pytest.mark.parametrize("status", ["wibble", "TODO: revisit", "phase-two", ""])
    def test_unknown_tokens_are_unparseable(self, state_mod, status) -> None:
        message = state_mod.lint_status_token(status)
        assert message is not None
        assert "unparseable" in message
        # The lint names the canonical 8, never guesses.
        for token in ("draft", "in-review", "approved", "implemented", "parked"):
            assert token in message


class TestParkedAndGlyphSemantics:
    def _spec(self, status: str) -> str:
        return f"# Spec\n\n**Status**: {status}\n\n## Deliverables\n\n- attune-rag/src/attune_rag/foo.py\n"

    @pytest.mark.parametrize("status", ["parked", "paused (til Q3)", "blocked on #12", "deferred"])
    def test_parked_family_not_in_flight(self, state_mod, status) -> None:
        assert state_mod._is_in_flight("tasks", status) is False

    @pytest.mark.parametrize("status", ["implemented (2026-07-10)", "✓", "✅ shipped"])
    def test_new_terminal_forms_not_in_flight(self, state_mod, status) -> None:
        assert state_mod._is_in_flight("tasks", status) is False

    def test_draft_still_in_flight(self, state_mod) -> None:
        assert state_mod._is_in_flight("tasks", "draft") is True

    @pytest.mark.parametrize("status", ["parked (2026-07-10)", "implemented", "✓"])
    def test_all_resolved_but_parked_or_terminal_is_ok(self, state_mod, workspace, status) -> None:
        # Parked family + new terminal forms are skipped by drift checks.
        text = self._spec(status)
        assert state_mod.classify_staleness(text, status, [workspace]) == "ok"

    def test_body_implemented_line_is_terminal_signal(self, state_mod) -> None:
        verdict, source = state_mod._completion_signal(
            "# Spec\n\nprose\n\nStatus: implemented in #99\n"
        )
        assert verdict == "implemented"
        assert source == "terminal-line"

    def test_glyph_leading_verdict(self, state_mod) -> None:
        assert state_mod._leading_verdict("✓ (2026-07-10)") == "✓"
        assert state_mod._leading_verdict("✅") == "✅"


# ── --pr-links mode + drift cache + --json (task 4) ───────────
#
# Golden fixture: a miniature of the specs/SPEC-AUDIT-2026-06-17
# findings — in-flight specs whose implementing PRs merged (drifted),
# one with no PR trail (not drifted), one citing an unmerged PR
# (merged-only filter), one citing an issue number (404s on the pulls
# endpoint), and a terminal spec that must never be queried. gh is
# patched at the subprocess boundary (testing-conventions.md — no live
# calls in the default suite).


def _pr_spec(spec_dir: Path, *, status: str, body: str) -> None:
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "tasks.md").write_text(
        f"# Tasks\n\n**Status**: {status}\n\n{body}\n", encoding="utf-8"
    )


@pytest.fixture
def golden_tree(tmp_path: Path):
    specs = tmp_path / "specs"
    # DONE-in-reality, header still approved → drifted (local merged PR).
    _pr_spec(
        specs / "gui-batch-status-sse",
        status="approved (2026-06-14)",
        body="SSE endpoint shipped in #67 with 10 tests.",
    )
    # DONE via a cross-repo PR → drifted (explicit pull-URL).
    _pr_spec(
        specs / "rag-gate-accuracy-baseline",
        status="approved (2026-06-04)",
        body="Tasks 1-8 merged via [#51](https://github.com/Smart-AI-Memory/attune-author/pull/51).",
    )
    # Genuinely open — no PR citations → not drifted.
    _pr_spec(
        specs / "long-cache-ttl-citations",
        status="approved (2026-06-14)",
        body="No implementation yet; best no-key build candidate.",
    )
    # Cites a PR that is still OPEN → merged-only filter keeps it clean.
    _pr_spec(
        specs / "help-memory-tool",
        status="approved (2026-06-14)",
        body="Option A landing via #99 (in review).",
    )
    # Cites a number that is an ISSUE, not a PR → resolver says no.
    _pr_spec(
        specs / "hash-regenerate-button",
        status="draft",
        body="Tracked alongside issue #400.",
    )
    # Terminal — must never be queried even though it cites a PR.
    _pr_spec(
        specs / "template-path-rename",
        status="complete (2026-06-17)",
        body="Shipped in PR #212.",
    )
    return tmp_path


class _FakeGh:
    """Canned gh responses keyed by PR number; records every call."""

    #: number -> ("merged" | "open" | "issue")
    STATES = {"67": "merged", "51": "merged", "99": "open", "400": "issue", "212": "merged"}

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.cwds: list[object] = []

    def __call__(self, args, cwd=None):
        self.calls.append(list(args))
        self.cwds.append(cwd)
        number = next(
            (tok.rstrip("/").rsplit("/", 1)[-1] for tok in args if tok[-1:].isdigit()), ""
        )
        state = self.STATES.get(number)
        if state == "issue":
            return _types.SimpleNamespace(returncode=1, stdout="", stderr="Not Found (404)")
        if args[0] == "api":
            payload = {"merged": state == "merged", "number": int(number or 0)}
        else:
            payload = {"state": "MERGED" if state == "merged" else "OPEN"}
        return _types.SimpleNamespace(returncode=0, stdout=_json.dumps(payload), stderr="")


@pytest.fixture
def fake_gh(audit_mod, monkeypatch):
    fake = _FakeGh()
    monkeypatch.setattr(audit_mod, "_run_gh", fake)
    return fake


class TestPrLinksGolden:
    def _audit(self, audit_mod, golden_tree):
        return audit_mod.audit_specs([golden_tree], pr_links=True, resolver=audit_mod._PrResolver())

    def test_reproduces_2026_06_17_verdicts(self, audit_mod, golden_tree, fake_gh) -> None:
        by_slug = {r.slug: r for r in self._audit(audit_mod, golden_tree)}
        assert by_slug["gui-batch-status-sse"].drifted is True
        assert by_slug["gui-batch-status-sse"].merged_prs == ("#67",)
        assert by_slug["rag-gate-accuracy-baseline"].drifted is True
        assert by_slug["rag-gate-accuracy-baseline"].merged_prs == ("attune-author #51",)
        assert by_slug["long-cache-ttl-citations"].drifted is False
        assert by_slug["help-memory-tool"].drifted is False  # unmerged PR
        assert by_slug["hash-regenerate-button"].drifted is False  # issue ref
        assert by_slug["template-path-rename"].drifted is False  # terminal

    def test_terminal_specs_never_queried(self, audit_mod, golden_tree, fake_gh) -> None:
        self._audit(audit_mod, golden_tree)
        assert not any("212" in tok for call in fake_gh.calls for tok in call)

    def test_cross_repo_uses_api_endpoint(self, audit_mod, golden_tree, fake_gh) -> None:
        self._audit(audit_mod, golden_tree)
        api_calls = [c for c in fake_gh.calls if c[0] == "api"]
        assert api_calls == [["api", "repos/Smart-AI-Memory/attune-author/pulls/51"]]

    def test_local_refs_resolve_via_spec_dir_cwd(self, audit_mod, golden_tree, fake_gh) -> None:
        self._audit(audit_mod, golden_tree)
        view_cwds = [
            cwd
            for call, cwd in zip(fake_gh.calls, fake_gh.cwds, strict=True)
            if call[0] == "pr" and "67" in call
        ]
        assert view_cwds and all("gui-batch-status-sse" in str(c) for c in view_cwds)


class TestPrResolverBounds:
    def test_cache_dedupes_repeat_lookups(self, audit_mod, fake_gh, state_mod, tmp_path) -> None:
        resolver = audit_mod._PrResolver()
        ref = state_mod.PrRef(number=67, repo=None, explicit=True)
        assert resolver.merged(ref, tmp_path, "workspace") is True
        assert resolver.merged(ref, tmp_path, "workspace") is True
        assert resolver.calls == 1

    def test_call_cap_bounds_gh_spend(
        self, audit_mod, fake_gh, state_mod, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(audit_mod, "_MAX_GH_CALLS", 3)
        resolver = audit_mod._PrResolver()
        for n in range(1, 10):
            resolver.merged(state_mod.PrRef(number=n, repo=None, explicit=True), tmp_path, "x")
        assert resolver.calls == 3
        assert len(fake_gh.calls) == 3

    def test_missing_gh_goes_dead_not_fatal(
        self, audit_mod, state_mod, tmp_path, monkeypatch
    ) -> None:
        def _absent(args, cwd=None):
            raise FileNotFoundError("gh")

        monkeypatch.setattr(audit_mod, "_run_gh", _absent)
        resolver = audit_mod._PrResolver()
        ref = state_mod.PrRef(number=1, repo=None, explicit=True)
        assert resolver.merged(ref, tmp_path, "x") is False
        assert resolver.dead is True
        # Subsequent lookups short-circuit without touching gh again.
        assert (
            resolver.merged(state_mod.PrRef(number=2, repo=None, explicit=True), tmp_path, "x")
            is False
        )
        assert resolver.calls == 1

    def test_malformed_gh_output_is_not_merged(
        self, audit_mod, state_mod, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            audit_mod,
            "_run_gh",
            lambda args, cwd=None: _types.SimpleNamespace(
                returncode=0, stdout="not json", stderr=""
            ),
        )
        resolver = audit_mod._PrResolver()
        assert (
            resolver.merged(state_mod.PrRef(number=5, repo=None, explicit=True), tmp_path, "x")
            is False
        )


class TestDriftCache:
    def test_cache_schema_and_content(self, audit_mod, golden_tree, fake_gh) -> None:
        results = audit_mod.audit_specs(
            [golden_tree], pr_links=True, resolver=audit_mod._PrResolver()
        )
        written = audit_mod.write_drift_cache(results, [golden_tree])
        assert written == [golden_tree / ".attune" / "spec-drift.json"]
        data = _json.loads(written[0].read_text(encoding="utf-8"))
        assert isinstance(data["generated_at"], float)
        entry = data["specs"]["workspace/gui-batch-status-sse"]
        assert entry == {"verdict": "drifted", "prs": ["#67"], "signal": "pr-links"}
        # Clean in-flight specs are recorded too (checked-and-clean).
        assert data["specs"]["workspace/long-cache-ttl-citations"]["verdict"] == "ok"
        # Terminal specs carry no drift signal.
        assert "workspace/template-path-rename" not in data["specs"]


class TestPrLinksMain:
    def test_offline_makes_no_gh_calls(self, audit_mod, golden_tree, monkeypatch, capsys) -> None:
        def _boom(args, cwd=None):
            raise AssertionError("gh must not be invoked with --offline")

        monkeypatch.setattr(audit_mod, "_run_gh", _boom)
        monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", str(golden_tree))
        assert audit_mod.main(["--pr-links", "--offline"]) == 0
        assert not (golden_tree / ".attune" / "spec-drift.json").exists()

    def test_default_exit_zero_with_drift(
        self, audit_mod, golden_tree, fake_gh, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", str(golden_tree))
        assert audit_mod.main(["--pr-links"]) == 0
        out = capsys.readouterr().out
        assert "⚠ drifted" in out
        assert "flip the status or mark them parked" in out
        # main --pr-links writes the cache as a side effect.
        assert (golden_tree / ".attune" / "spec-drift.json").exists()

    def test_strict_exit_one_on_drift(self, audit_mod, golden_tree, fake_gh, monkeypatch) -> None:
        monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", str(golden_tree))
        assert audit_mod.main(["--pr-links", "--strict"]) == 1

    def test_json_output_parses(self, audit_mod, golden_tree, fake_gh, monkeypatch, capsys) -> None:
        monkeypatch.setenv("ATTUNE_AI_WORKSPACE_ROOTS", str(golden_tree))
        assert audit_mod.main(["--pr-links", "--json"]) == 0
        payload = _json.loads(capsys.readouterr().out)
        assert payload["counts"]["drifted"] == 2
        assert sorted(payload["drifted"]) == [
            "workspace/gui-batch-status-sse",
            "workspace/rag-gate-accuracy-baseline",
        ]
        assert payload["specs"]["workspace/help-memory-tool"]["drifted"] is False
