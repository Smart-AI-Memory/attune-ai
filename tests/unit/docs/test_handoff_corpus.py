"""Corpus lint: tracked handoffs are structurally valid session-start input.

Roundtable ``q-context-mgmt-next-001`` (2026-08-18), safe-tonight item
2: OQ1's RETIRE ruling made ``docs/handoffs/<branch-slug>.md`` the
FIRST surface the session-start nudge offers — hand-written prose
promoted to load-bearing input deserves the same corpus-is-the-fixture
guard that spec statuses got in #2086. Structural checks only; the
stricter intake semantics (fail-closed schema vs graceful degrade) are
an open chair question and deliberately NOT encoded here.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HANDOFFS_DIR = REPO_ROOT / "docs" / "handoffs"

#: Non-handoff files allowed in the directory.
SKIP_NAMES = frozenset({"readme.md", "template.md"})

#: Sections every handoff must carry (from templates/agent-handoff.md).
REQUIRED_SECTIONS = ("## Goal", "## Current state", "## Next action")

#: Branch-slug filenames: branch name with '/' replaced by '-'.
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.md$")


def _corpus() -> list[Path]:
    return [p for p in sorted(HANDOFFS_DIR.glob("*.md")) if p.name.lower() not in SKIP_NAMES]


def test_handoffs_dir_exists() -> None:
    assert HANDOFFS_DIR.is_dir()


def test_filenames_are_branch_slugs() -> None:
    bad = [p.name for p in _corpus() if not SLUG_RE.match(p.name)]
    assert not bad, f"handoff filenames must be branch slugs (`/`→`-`): {bad}"


def test_every_handoff_has_h1_and_required_sections() -> None:
    offenders: list[str] = []
    for path in _corpus():
        text = path.read_text(encoding="utf-8")
        if not text.startswith("# "):
            offenders.append(f"{path.name}: missing leading h1")
        for section in REQUIRED_SECTIONS:
            if section not in text:
                offenders.append(f"{path.name}: missing '{section}'")
    assert not offenders, (
        "handoff corpus lint failures (template: templates/agent-handoff.md): " f"{offenders}"
    )


def test_no_empty_handoffs() -> None:
    empty = [p.name for p in _corpus() if p.stat().st_size < 80]
    assert not empty, f"placeholder/empty handoffs should be deleted: {empty}"
