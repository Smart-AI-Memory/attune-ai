"""Status-line baseline gate (T2) — unit tests + the CI corpus sweep.

The sweep test is the D7-pattern enforcer: it fails CI whenever a spec
directory under ``docs/specs/`` is illegible to the lifecycle
detector. Landed red against the 2026-07-20 corpus (24 dirs), fixed
green by the same PR's backfill.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.gates.lifecycle import status_line_gate
from attune.ops.specs_data import _PHASE_FILES

REPO_ROOT = Path(__file__).resolve().parents[3]
SPECS_ROOT = REPO_ROOT / "docs" / "specs"


def _write(spec_dir: Path, fname: str, status_line: str, extra: str = "") -> None:
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / fname).write_text(f"# Title\n\n{status_line}\n{extra}\n", encoding="utf-8")


class TestStatusLineGate:
    def test_in_vocabulary_status_passes(self, tmp_path):
        _write(tmp_path / "s", "requirements.md", "**Status:** approved (2026-07-20) — ok")
        receipt = status_line_gate(tmp_path / "s")
        assert receipt.state == "PASS"
        assert receipt.findings == []

    def test_garbled_leading_token_revises(self, tmp_path):
        _write(tmp_path / "s", "requirements.md", "**Status:** RATIFIED by chair")
        receipt = status_line_gate(tmp_path / "s")
        assert receipt.state == "REVISE"
        assert any("ratified" in f for f in receipt.findings)

    def test_missing_requirements_status_revises(self, tmp_path):
        _write(tmp_path / "s", "requirements.md", "no status here at all")
        receipt = status_line_gate(tmp_path / "s")
        assert receipt.state == "REVISE"

    def test_whole_bold_convention_parses(self, tmp_path):
        # The table-authored convention: **Status: value** (whole bold).
        _write(tmp_path / "s", "requirements.md", "**Status: approved (2026-07-20)** — chair")
        receipt = status_line_gate(tmp_path / "s")
        assert receipt.state == "PASS"

    def test_parked_without_resume_trigger_revises(self, tmp_path):
        _write(tmp_path / "s", "tasks.md", "**Status:** parked (2026-07-19) — chair ruling")
        receipt = status_line_gate(tmp_path / "s")
        assert receipt.state == "REVISE"
        assert any("Resume-Trigger" in f for f in receipt.findings)

    def test_parked_with_resume_trigger_passes(self, tmp_path):
        _write(
            tmp_path / "s",
            "tasks.md",
            "**Status:** parked (2026-07-19) — Resume-Trigger: 2026-07-28",
        )
        receipt = status_line_gate(tmp_path / "s")
        assert receipt.state == "PASS"

    def test_dir_with_no_parseable_file_revises(self, tmp_path):
        _write(tmp_path / "s", "decisions.md", "just a log, no status")
        receipt = status_line_gate(tmp_path / "s")
        assert receipt.state == "REVISE"


def _spec_dirs() -> list[Path]:
    """Mirror `_list_specs_in_root`'s selection: >=1 canonical phase file."""
    if not SPECS_ROOT.is_dir():
        return []
    return sorted(
        d
        for d in SPECS_ROOT.iterdir()
        if d.is_dir() and any((d / f).is_file() for f in _PHASE_FILES)
    )


@pytest.mark.parametrize("spec_dir", _spec_dirs(), ids=lambda d: d.name)
def test_corpus_sweep_every_spec_dir_is_legible(spec_dir):
    """CI enforcer: every spec dir passes the status-line gate."""
    receipt = status_line_gate(spec_dir)
    assert receipt.state == "PASS", "\n".join(receipt.findings)


# Dirs that legitimately carry .md content without a canonical phase
# file. Seeded EMPTY 2026-08-09 (the corpus had no counter-example) and
# shrink-only: never add an entry to silence a new unbucketed dir — add
# a decisions.md (or other phase file) so the dir becomes visible to
# the lifecycle detector and the sweep above.
_UNBUCKETED_ALLOWLIST: frozenset[str] = frozenset()


def _unbucketed_spec_dirs() -> list[Path]:
    """Non-archive dirs under docs/specs/ with .md content but no phase file.

    These are invisible to ``_list_specs_in_root`` and therefore to the
    corpus sweep above — the product-direction-review trap: nine files
    and eight weeks of executed work, entirely unbucketed until the
    2026-08-08 triage hand-added a decisions.md.
    """
    if not SPECS_ROOT.is_dir():
        return []
    return sorted(
        d
        for d in SPECS_ROOT.iterdir()
        if d.is_dir()
        and d.name != "archive"
        and d.name not in _UNBUCKETED_ALLOWLIST
        and not any((d / f).is_file() for f in _PHASE_FILES)
        and any(d.rglob("*.md"))
    )


def test_no_unbucketed_spec_dirs():
    """CI enforcer: every spec dir with .md content carries a phase file."""
    offenders = _unbucketed_spec_dirs()
    assert not offenders, (
        "docs/specs/ dirs with .md content but none of "
        f"{', '.join(_PHASE_FILES)} are invisible to the lifecycle "
        "detector and the status-line sweep. Add a decisions.md (or "
        "another phase file) to: " + ", ".join(d.name for d in offenders)
    )


def test_unbucketed_allowlist_is_not_stale():
    """Shrink-only ratchet: drop allowlist entries once they gain a
    phase file or disappear."""
    stale = sorted(
        name
        for name in _UNBUCKETED_ALLOWLIST
        if not (SPECS_ROOT / name).is_dir()
        or any((SPECS_ROOT / name / f).is_file() for f in _PHASE_FILES)
    )
    assert not stale, "Remove stale _UNBUCKETED_ALLOWLIST entries: " + ", ".join(stale)
