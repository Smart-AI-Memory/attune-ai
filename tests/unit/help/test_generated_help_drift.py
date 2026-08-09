"""Drift guard: skill-derived generated help matches its generators.

Skills added under plugin/skills/ auto-derive templates in
plugin/help/generated/ via the deterministic (no-LLM) Jinja
generators below. Adding or editing a skill without re-running them
leaves the generated corpus stale; before this guard nothing in CI
ran the ``--check`` (13 skills shipped without concept files,
2026-08-09, and reference/task/quickstart carried ~90 stale entries).

Scoped to the skill-derived generators ONLY: the lessons-derived
generators (errors/faqs/warnings/notes/comparisons) drift with every
lessons.md append and refresh deliberately at release-prep cadence,
so gating the full ``generate_all.py --check`` here would be
perpetually red.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

GENERATORS = [
    "generate_concept_templates.py",
    "generate_reference_templates.py",
    "generate_task_templates.py",
    "generate_quickstart_templates.py",
    "generate_troubleshooting_templates.py",
]


@pytest.mark.unit
@pytest.mark.parametrize("script_name", GENERATORS)
def test_generated_templates_in_sync(script_name: str) -> None:
    """Each generator's ``--check`` reports zero stale files."""
    script = REPO_ROOT / "scripts" / script_name
    if not script.exists():
        pytest.skip(f"scripts/{script_name} not found")
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"Generated templates are out of sync with their sources "
        f"(plugin/skills/*/SKILL.md and curated entries). Run:\n"
        f"  python scripts/{script_name}\n"
        f"and commit the changes under plugin/help/generated/.\n\n"
        f"--check output:\n{result.stdout[-2000:]}\n{result.stderr[-800:]}"
    )
