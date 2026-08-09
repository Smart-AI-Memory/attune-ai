"""Drift guard: plugin/help/generated/concepts matches the generator.

Skills added under plugin/skills/ auto-derive ``tool-<name>`` concept
templates via scripts/generate_concept_templates.py. Adding a skill
without re-running the generator leaves the generated corpus stale;
before this guard nothing in CI ran the ``--check`` (13 skills shipped
without their concept files, 2026-08-09).

Scoped to the concept generator ONLY: the lessons-derived generators
(errors/faqs/warnings/notes/comparisons) drift with every lessons.md
append and refresh deliberately at release-prep cadence, so gating the
full ``generate_all.py --check`` here would be perpetually red. The
other skill-reading generators (reference/task/quickstart) carry
pre-existing drift and can join this gate once regenerated.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "generate_concept_templates.py"


@pytest.mark.unit
def test_generated_concepts_in_sync() -> None:
    """``generate_concept_templates.py --check`` reports zero stale files."""
    if not SCRIPT.exists():
        pytest.skip("scripts/generate_concept_templates.py not found")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        "Generated concept templates are out of sync with their sources "
        "(plugin/skills/*/SKILL.md + curated _CONCEPTS). Run:\n"
        "  python scripts/generate_concept_templates.py\n"
        "and commit the changes under plugin/help/generated/concepts/.\n\n"
        f"--check output:\n{result.stdout[-2000:]}\n{result.stderr[-800:]}"
    )
