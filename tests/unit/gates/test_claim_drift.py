"""G1 — count-and-claim drift guard (docs/specs/claim-drift-gates/).

Every hand-maintained count/version claim in a user-facing surface is
asserted against the LIVE value derived from the owning registry. The
manifest below is data: adding a new claim site is a one-line diff.
An unmatched regex is itself a failure — a claim site that disappears
silently is drift too.

Ruled context: D4 (2026-07-12) — workflow totals use the DISTINCT
CLASS count ("20 workflows"), not the slug count. D7 (2026-07-20) —
this gate runs in CI only, not pre-commit (needs importable attune).

Keyless, no network, < seconds (G goals). Run me serially:
    pytest tests/unit/gates/test_claim_drift.py -p no:xdist
"""

from __future__ import annotations

import glob
import re
from functools import lru_cache
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def live_values() -> dict[str, str]:
    """Derive every gated value from its owning registry."""
    from attune.mcp.server import AttuneMCPServer
    from attune.workflows import discover_workflows

    registry = discover_workflows()
    version = re.search(
        r'^version\s*=\s*"([^"]+)"',
        (REPO / "pyproject.toml").read_text(encoding="utf-8"),
        re.M,
    ).group(1)
    return {
        "skills": str(len(glob.glob(str(REPO / "plugin" / "skills" / "*" / "SKILL.md")))),
        "tools": str(len(AttuneMCPServer().tools)),
        # D4: totals quote distinct workflow classes, not slugs.
        "workflows": str(len(set(registry.values()))),
        "workflow_slugs": str(len(registry)),
        "version": version,
    }


# --- The claim-site manifest -------------------------------------------
# (file, human label, regex with ONE capture group, live-value key).
# Every regex must match at least once in its file; every captured
# value must equal the live value.
# `(?:<[^>]*>)?` tolerates the `<!-- cap:... -->` ownership markers
# that scripts/project_capabilities.py wraps around governed claims.
# The assertion is unchanged — same wording, same number, same count;
# this gate stays independent (no projector imports, own derivation).
MANIFEST: tuple[tuple[str, str, str, str], ...] = (
    (
        "README.md",
        "hero workflow count",
        r"(\d+) workflows and (?:<!-- cap:[a-z_]+ -->)?\d+ MCP tools",
        "workflows",
    ),
    ("README.md", "hero tool count", r"\d+ workflows and (?:<[^>]*>)?(\d+) MCP tools", "tools"),
    ("README.md", "skills table row", r"\| (?:<[^>]*>)?(\d+) auto-triggering skills", "skills"),
    ("README.md", "tools table row", r"\| (?:<[^>]*>)?(\d+) MCP tools", "tools"),
    (
        ".claude-plugin/marketplace.json",
        "marketplace skill claims",
        r"(\d+) auto-triggering skills",
        "skills",
    ),
    ("plugin/README.md", "plugin version", r"\*\*Version:\*\* (\d+\.\d+\.\d+)", "version"),
    ("plugin/README.md", "plugin tool counts", r"(\d+) MCP tools", "tools"),
    (
        "docs/getting-started/quickstart-plugin.md",
        "quickstart skill count",
        r"\*\*(\d+) auto-triggering skills\*\*",
        "skills",
    ),
    (
        "docs/getting-started/quickstart-plugin.md",
        "quickstart tool count",
        r"\((\d+) tools\)",
        "tools",
    ),
    (
        "docs/getting-started/mcp-integration.md",
        "tools heading",
        r"## (?:<!-- cap:[a-z_]+ -->)?Available Tools \((\d+)\)",
        "tools",
    ),
    (
        "docs/getting-started/first-steps.md",
        "built-in workflow count",
        r"(\d+) built-in workflows",
        "workflows",
    ),
    (".claude/CLAUDE.md", "header version", r"# Attune AI Framework v(\d+\.\d+\.\d+)", "version"),
    (".claude/CLAUDE.md", "footer version", r"\*\*Version:\*\* (\d+\.\d+\.\d+)", "version"),
)


@pytest.mark.parametrize(
    ("rel_path", "label", "pattern", "key"),
    MANIFEST,
    ids=[f"{m[0]}::{m[1]}" for m in MANIFEST],
)
def test_claim_matches_live_value(rel_path: str, label: str, pattern: str, key: str):
    text = (REPO / rel_path).read_text(encoding="utf-8")
    matches = re.findall(pattern, text)
    assert matches, (
        f"{rel_path}: claim site {label!r} (/{pattern}/) matched nothing — "
        "the claim vanished or was reworded; update the manifest WITH the wording"
    )
    expected = live_values()[key]
    stale = [m for m in matches if m != expected]
    assert not stale, (
        f"{rel_path}: {label} claims {stale} but the live {key} value is "
        f"{expected} — update the claim (or the registry moved and docs "
        "must follow)"
    )


def test_live_values_are_sane():
    """Guard the gate itself: derivation returning zeros would let every
    claim 'drift' to zero silently on an import regression."""
    values = live_values()
    assert int(values["skills"]) > 10
    assert int(values["tools"]) > 20
    assert int(values["workflows"]) > 10
    assert int(values["workflow_slugs"]) >= int(values["workflows"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", values["version"])
