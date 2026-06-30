"""Drift-guard: orchestration tools must not invoke retired model snapshots.

Anthropic retires dated model snapshots (e.g. ``claude-3-5-sonnet-20241022``)
on published dates; once retired they 404 at invocation time. The
``models_to_try`` fallback lists in the orchestration test-generation tools
once carried two retired 3.5 Sonnet snapshots as Capable-tier fallbacks
(latent 404 behind the primary ``claude-sonnet-5`` alias). This test fails
if any retired dated snapshot reappears as an invocation target in those
files.

Stable aliases (e.g. ``claude-sonnet-5``) never retire and are the correct
form for in-code invocation targets.
"""

from pathlib import Path

import pytest

# Repo root: tests/unit/orchestration/<file>.py -> parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]

# Dated snapshots Anthropic has retired (or has a near-term retirement date).
# Source: Anthropic model deprecation table. These must never appear as
# invocation targets in source code; use the stable alias instead.
RETIRED_DATED_SNAPSHOTS = frozenset(
    {
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-haiku-20241022",
        "claude-3-haiku-20240307",
        "claude-3-7-sonnet-20250219",
        "claude-3-opus-20240229",
    }
)

# Files that build ``models_to_try`` invocation lists. These intentionally
# contain NO pricing-table keys or docstring examples, so a plain substring
# check has no legitimate false positives here.
INVOCATION_TARGET_FILES = (
    "src/attune/orchestration/tools/test_generation.py",
    "src/attune/orchestration/tools/testing.py",
)


@pytest.mark.parametrize("rel_path", INVOCATION_TARGET_FILES)
def test_no_retired_snapshot_in_invocation_targets(rel_path: str) -> None:
    """Each orchestration tool file is free of retired dated snapshots."""
    text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    found = sorted(snap for snap in RETIRED_DATED_SNAPSHOTS if snap in text)
    assert not found, (
        f"{rel_path} references retired model snapshot(s) {found}; "
        f"use a stable alias (e.g. 'claude-sonnet-5') instead"
    )
