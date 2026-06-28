"""Render security-audit findings as an HTML severity dashboard.

The dashboard is the rich-output surface for the security-audit workflow
(the show_widget "enhanced feature"). It consumes the structured
``findings`` list the ``security_audit`` MCP tool already returns
(``attune.workflows.output.Finding`` → ``{severity, file, line, message,
code}``) plus the optional health score, and renders a counts-by-severity
header over a severity-sorted findings list.

Same injection-safety contract as the discovery-sweep board: display-only
(no ``<script>``), every finding string ``html.escape``d, CDS design
tokens, transparent background, no ``position: fixed``. The agent passes
the returned HTML to ``mcp__visualize__show_widget``.

NOTE (follow-up): the severity palette + ``_esc``/``_location`` helpers
are intentionally duplicated from
``attune.workflows.discovery_sweep.board`` for now; once both land on
main they collapse into one shared ``findings_widget`` primitive
(tracked in docs/specs/security-audit-rich-output/).
"""

from __future__ import annotations

from typing import Any

# Shared findings-widget primitives (spec FR-1). Private aliases keep the
# rest of this module unchanged — a pure de-dup, no behaviour change.
from attune.workflows.findings_widget import SEV_COLOUR as _SEV_COLOUR
from attune.workflows.findings_widget import SEV_ORDER as _SEV_ORDER
from attune.workflows.findings_widget import esc as _esc
from attune.workflows.findings_widget import location as _location
from attune.workflows.findings_widget import severity_of as _sev
from attune.workflows.findings_widget import severity_rank as _sev_rank


def _normalize(finding: Any) -> dict[str, Any]:
    """Coerce a finding to a dict.

    ``security_audit`` usually yields structured ``Finding`` dicts, but
    the legacy flat-dict response path (and some callers) can hand back a
    bare string per finding. Wrap those as a minimal ``info`` card rather
    than crashing on ``.get``.
    """
    if isinstance(finding, dict):
        return finding
    return {
        "severity": "info",
        "message": str(finding),
        "file": None,
        "line": None,
        "code": None,
    }


def _chip(label: str, count: int, colour: str) -> str:
    return (
        f'<span class="sa-chip">'
        f'<span class="sa-dot" style="background:{colour};"></span>'
        f"{_esc(label)} <b>{count}</b></span>"
    )


def _card(finding: dict[str, Any]) -> str:
    sev = _sev(finding)
    colour = _SEV_COLOUR.get(sev, _SEV_COLOUR["info"])
    code = finding.get("code")
    code_html = f'<pre class="sa-code">{_esc(code)}</pre>' if code else ""
    return (
        f'<div class="sa-card" style="border-left:3px solid {colour};">'
        f'<div class="sa-card-head">'
        f'<span class="sa-dot" style="background:{colour};"></span>'
        f'<span class="sa-sev">{_esc(sev)}</span>'
        f'<span class="sa-loc">{_location(finding)}</span>'
        f"</div>"
        f'<div class="sa-msg">{_esc(finding.get("message"))}</div>'
        f"{code_html}"
        f"</div>"
    )


def security_findings_dashboard_html(
    findings: list[dict[str, Any]],
    score: int | None = None,
    message: str = "",
) -> str:
    """Render a list of security findings as a severity dashboard.

    Args:
        findings: ``[{severity, file, line, message, code}, ...]`` — the
            ``security_audit`` tool's ``findings`` list (already dicts).
        score: Optional health score (0-100) for the header chip.
        message: Optional caption shown above the dashboard.

    Returns:
        Self-contained HTML for ``mcp__visualize__show_widget``.
    """
    findings = [_normalize(f) for f in (findings or [])]

    # Counts by severity, in canonical order; skip zero-count severities.
    counts: dict[str, int] = {}
    for f in findings:
        counts[_sev(f)] = counts.get(_sev(f), 0) + 1
    chips = "".join(
        _chip(sev, counts[sev], _SEV_COLOUR[sev]) for sev in _SEV_ORDER if counts.get(sev)
    )
    if not chips:
        chips = '<span class="sa-empty">no findings — clean</span>'

    score_html = ""
    if score is not None:
        score_html = f'<span class="sa-score">health {_esc(score)}/100</span>'

    cards = "".join(_card(f) for f in sorted(findings, key=_sev_rank))

    caption = f'<p class="sa-msg-top">{_esc(message)}</p>' if message else ""

    return (
        '<div id="sa-dash">'
        + _STYLE
        + caption
        + '<div class="sa-summary">'
        + chips
        + score_html
        + "</div>"
        + f'<div class="sa-list">{cards}</div>'
        + "</div>"
    )


_STYLE = """<style>
#sa-dash { display:block; width:100%; padding:1rem 0;
  color:var(--text-primary); line-height:1.45; font-size:14px; }
#sa-dash .sa-msg-top { margin:0 0 .75rem; color:var(--text-secondary); }
#sa-dash .sa-summary { display:flex; flex-wrap:wrap; align-items:center;
  gap:.5rem; margin-bottom:1rem; }
#sa-dash .sa-chip { display:inline-flex; align-items:center; gap:.35rem;
  padding:.2rem .55rem; font-size:13px; text-transform:capitalize;
  color:var(--text-primary); background:var(--surface-1);
  border:1px solid var(--border); border-radius:var(--radius); }
#sa-dash .sa-score { margin-left:auto; padding:.2rem .55rem; font-size:13px;
  color:var(--text-primary); background:var(--bg-accent);
  border:1px solid var(--border-accent); border-radius:var(--radius); }
#sa-dash .sa-empty { font-size:13px; color:var(--text-muted); font-style:italic; }
#sa-dash .sa-dot { width:.55em; height:.55em; border-radius:50%; flex:0 0 auto;
  display:inline-block; }
#sa-dash .sa-list { display:flex; flex-direction:column; gap:.5rem; }
#sa-dash .sa-card { padding:.5rem .6rem; background:var(--surface-1);
  border:1px solid var(--border); border-radius:var(--radius); }
#sa-dash .sa-card-head { display:flex; align-items:center; gap:.4rem;
  font-size:12px; color:var(--text-muted); margin-bottom:.2rem; }
#sa-dash .sa-sev { font-weight:600; text-transform:uppercase;
  letter-spacing:.02em; }
#sa-dash .sa-loc { margin-left:auto; font-family:ui-monospace,monospace; }
#sa-dash .sa-msg { color:var(--text-primary); }
#sa-dash .sa-code { margin:.35rem 0 0; padding:.4rem .5rem; overflow-x:auto;
  font-size:12.5px; font-family:ui-monospace,monospace; color:var(--text-secondary);
  background:var(--surface-2,var(--surface-1)); border:1px solid var(--border);
  border-radius:var(--radius); white-space:pre-wrap; }
</style>"""
