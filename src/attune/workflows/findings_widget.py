"""Shared primitives for findings-based ``show_widget`` surfaces.

Extracted (spec: docs/specs/analysis-workflow-output-widgets/ FR-1) from
the discovery-sweep triage board (``discovery_sweep.board``), which had a
private copy of the severity palette + escaping + location helpers. Now
shared by the board and the universal ``report_panel`` (findings-section
cards). This is the one place to change them.

All consumers keep the same injection-safety contract: display-only (no
``<script>``), every finding-derived string ``html.escape``d, CDS design
tokens, transparent background, no ``position: fixed``.
"""

from __future__ import annotations

import html
from typing import Any

# Severity → accent colour. Mid-tone hues that stay legible on both
# light and dark backgrounds; used only for a dot / left border / chip
# border, never as text colour, so contrast never depends on the hue.
SEV_COLOUR: dict[str, str] = {
    "critical": "#e5484d",
    "high": "#f76808",
    "medium": "#ffb224",
    "low": "#46a758",
    "info": "#8b8d98",
}

# Canonical severity ordering, most-severe first.
SEV_ORDER: list[str] = ["critical", "high", "medium", "low", "info"]


def esc(value: Any) -> str:
    """HTML-escape any value (``None`` → empty string)."""
    return html.escape("" if value is None else str(value))


def severity_of(finding: dict[str, Any]) -> str:
    """Lower-cased severity of a finding dict, defaulting to ``info``."""
    return str(finding.get("severity", "info")).lower()


def severity_rank(finding: dict[str, Any]) -> int:
    """Sort key: index into :data:`SEV_ORDER`, unknown severities last."""
    sev = severity_of(finding)
    return SEV_ORDER.index(sev) if sev in SEV_ORDER else len(SEV_ORDER)


def colour_for(finding: dict[str, Any]) -> str:
    """Accent colour for a finding's severity."""
    return SEV_COLOUR.get(severity_of(finding), SEV_COLOUR["info"])


def location(finding: dict[str, Any]) -> str:
    """``file:line`` (escaped) or ``"—"`` when the finding has no file."""
    file = finding.get("file")
    if not file:
        return "—"
    line = finding.get("line")
    loc = f"{file}:{line}" if line else str(file)
    return esc(loc)
