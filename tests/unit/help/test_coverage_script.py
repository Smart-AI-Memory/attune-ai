"""Enforce that every registered workflow is either in .help/features.yaml
or explicitly allowlisted in scripts/check_help_coverage.py.

This catches the "shipped a workflow, forgot to add a help entry" drift
class. When this test fails, either:

    1. Add the new workflow to .help/features.yaml with a `files:` glob
       and regenerate templates via `attune-author generate <name>
       --all-kinds`, or
    2. Add the workflow to KNOWN_GAPS in scripts/check_help_coverage.py
       with a comment explaining why it's internal-only.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_help_coverage.py"


@pytest.fixture
def coverage_module():
    spec = importlib.util.spec_from_file_location("_check_help_coverage", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_check_help_coverage"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_check_help_coverage", None)


def test_no_new_workflow_drift(coverage_module):
    """No workflow may exist in code without a manifest entry or
    explicit KNOWN_GAPS allowlist entry."""
    repo_root = Path(__file__).resolve().parents[3]
    result = coverage_module.check(repo_root / ".help")
    assert result["uncovered"] == [], (
        "New workflows lack help coverage. Either add them to "
        ".help/features.yaml and regenerate templates, or add to "
        "KNOWN_GAPS in scripts/check_help_coverage.py.\n"
        f"uncovered: {result['uncovered']}"
    )


def test_aliases_resolve_to_real_manifest_entries(coverage_module):
    """Every ALIASES value must exist in the manifest — otherwise the
    alias points at a hallucinated feature."""
    repo_root = Path(__file__).resolve().parents[3]
    manifest = coverage_module._manifest_features(repo_root / ".help")
    for src, dest in coverage_module.ALIASES.items():
        assert dest in manifest, (
            f"ALIASES maps {src!r} -> {dest!r} but {dest!r} is not in " f".help/features.yaml"
        )


def test_known_gaps_still_refer_to_real_workflows(coverage_module):
    """Every name in KNOWN_GAPS must correspond to a real registered
    workflow — otherwise the allowlist has gone stale."""
    workflows = coverage_module._registered_workflows()
    stale = coverage_module.KNOWN_GAPS - workflows
    assert not stale, (
        f"KNOWN_GAPS contains names that are no longer registered "
        f"workflows — remove them: {sorted(stale)}"
    )
