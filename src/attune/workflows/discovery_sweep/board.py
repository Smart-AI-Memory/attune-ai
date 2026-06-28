"""Render a discovery-sweep ``SweepResult`` as an HTML triage board.

The board is the *output* half of the discovery-sweep rich surface
(spec: ``docs/specs/discovery-sweep-rich-surface/``). It mirrors the
injection-safety contract of ``attune.elicitation.widget.form_to_widget_html``
(D11): every finding-derived string is ``html.escape``d, no data is
interpolated into executable JS (the board is display-only — it carries
no ``<script>`` at all), styling uses CDS design tokens, the background
is transparent, and nothing uses ``position: fixed``.

The agent passes the returned HTML straight to
``mcp__visualize__show_widget``.
"""

from __future__ import annotations

import html
from typing import Any

# Severity → accent colour. Mid-tone hues that stay legible on both
# light and dark backgrounds; used only for a small dot + left border,
# never as text colour, so contrast never depends on the hue.
_SEV_COLOUR: dict[str, str] = {
    "critical": "#e5484d",
    "high": "#f76808",
    "medium": "#ffb224",
    "low": "#46a758",
    "info": "#8b8d98",
}
_SEV_ORDER = ["critical", "high", "medium", "low", "info"]


def _esc(value: Any) -> str:
    """HTML-escape any value (None → empty string)."""
    return html.escape("" if value is None else str(value))


def _location(finding: dict[str, Any]) -> str:
    """``file:line`` (escaped) or ``"—"`` when the finding has no location."""
    file = finding.get("file")
    if not file:
        return "—"
    line = finding.get("line")
    loc = f"{file}:{line}" if line else str(file)
    return _esc(loc)


def _finding_card(finding: dict[str, Any], extra: str = "") -> str:
    sev = str(finding.get("severity", "info")).lower()
    colour = _SEV_COLOUR.get(sev, _SEV_COLOUR["info"])
    conf = finding.get("confidence")
    conf_txt = f" · {round(float(conf) * 100)}% conf" if conf is not None else ""
    return (
        f'<div class="ds-card" style="border-left:3px solid {colour};">'
        f'<div class="ds-card-head">'
        f'<span class="ds-dot" style="background:{colour};"></span>'
        f'<span class="ds-sev">{_esc(sev)}</span>'
        f'<span class="ds-src">{_esc(finding.get("source"))}{conf_txt}</span>'
        f"</div>"
        f'<div class="ds-title">{_esc(finding.get("title"))}</div>'
        f'<div class="ds-loc">{_location(finding)}</div>'
        f"{extra}"
        f"</div>"
    )


def _column(title: str, count: int, body: str) -> str:
    return (
        f'<div class="ds-col">'
        f'<div class="ds-col-head">{_esc(title)} '
        f'<span class="ds-count">{count}</span></div>'
        f"{body}"
        f"</div>"
    )


def sweep_to_board_html(result: dict[str, Any], message: str = "") -> str:
    """Render a sweep result dict (``dataclasses.asdict`` shape) as a board.

    Args:
        result: ``{"queue": [...], "questions": [...], "rejected": [...],
            "metadata": {...}}`` — the serialized ``SweepResult``.
        message: Optional caption shown above the board.

    Returns:
        Self-contained HTML for ``mcp__visualize__show_widget``.
    """
    queue = result.get("queue") or []
    questions = result.get("questions") or []
    rejected = result.get("rejected") or []
    meta = result.get("metadata") or {}

    # Queue — sorted by severity (critical first), one card each.
    queue_sorted = sorted(
        queue,
        key=lambda f: (
            _SEV_ORDER.index(str(f.get("severity", "info")).lower())
            if str(f.get("severity", "info")).lower() in _SEV_ORDER
            else len(_SEV_ORDER)
        ),
    )
    queue_body = "".join(_finding_card(f) for f in queue_sorted) or _empty()

    # Questions — finding + why it couldn't auto-route + the next step.
    q_body = (
        "".join(
            _finding_card(
                q.get("finding") or {},
                extra=(
                    f'<div class="ds-meta"><b>why:</b> {_esc(q.get("reason"))}</div>'
                    f'<div class="ds-meta"><b>next:</b> {_esc(q.get("next_step"))}</div>'
                ),
            )
            for q in questions
        )
        or _empty()
    )

    # Rejected — collapsed; native <details>, summarised by rule.
    if rejected:
        rows = "".join(
            f'<div class="ds-rej">{_location(r.get("finding") or {})} '
            f'<span class="ds-rule">{_esc(r.get("rule"))}</span></div>'
            for r in rejected
        )
        rej_body = (
            f"<details><summary>{len(rejected)} filtered out — show</summary>"
            f'<div class="ds-rej-list">{rows}</div></details>'
        )
    else:
        rej_body = _empty()

    sources = ", ".join(_esc(s) for s in (meta.get("sources") or [])) or "—"
    failures = meta.get("failures") or []
    fail_txt = (
        f' · <span class="ds-fail">{len(failures)} source(s) failed</span>' if failures else ""
    )
    spent = meta.get("spent_usd", 0) or 0
    budget = meta.get("budget_usd", 0) or 0
    dur_ms = meta.get("duration_ms", 0) or 0
    footer = (
        f'<div class="ds-foot">${float(spent):.2f} / ${float(budget):.2f} spent · '
        f"{dur_ms} ms · sources: {sources}{fail_txt}</div>"
    )

    caption = f'<p class="ds-msg">{_esc(message)}</p>' if message else ""

    return (
        '<div id="ds-board">'
        + _STYLE
        + caption
        + '<div class="ds-cols">'
        + _column("Queue — act now", len(queue), queue_body)
        + _column("Questions — needs a look", len(questions), q_body)
        + _column("Rejected — filtered", len(rejected), rej_body)
        + "</div>"
        + footer
        + "</div>"
    )


def _empty() -> str:
    return '<div class="ds-empty">none</div>'


_STYLE = """<style>
#ds-board { display:block; width:100%; padding:1rem 0;
  color:var(--text-primary); line-height:1.45; font-size:14px; }
#ds-board .ds-msg { margin:0 0 1rem; color:var(--text-secondary); }
#ds-board .ds-cols { display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:.75rem; }
#ds-board .ds-col { display:flex; flex-direction:column; gap:.5rem; }
#ds-board .ds-col-head { font-weight:600; font-size:13px;
  text-transform:uppercase; letter-spacing:.03em; color:var(--text-secondary); }
#ds-board .ds-count { display:inline-block; min-width:1.4em; text-align:center;
  padding:0 .35em; font-size:12px; color:var(--text-primary);
  background:var(--bg-accent); border:1px solid var(--border-accent);
  border-radius:var(--radius); }
#ds-board .ds-card { padding:.5rem .6rem; background:var(--surface-1);
  border:1px solid var(--border); border-radius:var(--radius); }
#ds-board .ds-card-head { display:flex; align-items:center; gap:.4rem;
  font-size:12px; color:var(--text-muted); margin-bottom:.2rem; }
#ds-board .ds-dot { width:.55em; height:.55em; border-radius:50%; flex:0 0 auto; }
#ds-board .ds-sev { font-weight:600; text-transform:uppercase; letter-spacing:.02em; }
#ds-board .ds-src { margin-left:auto; }
#ds-board .ds-title { font-weight:500; color:var(--text-primary); }
#ds-board .ds-loc { font-size:12.5px; color:var(--text-muted);
  font-family:ui-monospace,monospace; }
#ds-board .ds-meta { font-size:12.5px; color:var(--text-secondary); margin-top:.2rem; }
#ds-board .ds-empty { font-size:13px; color:var(--text-muted); font-style:italic; }
#ds-board details summary { cursor:pointer; color:var(--text-secondary); font-size:13px; }
#ds-board .ds-rej { font-size:12.5px; color:var(--text-muted);
  font-family:ui-monospace,monospace; padding:.15rem 0; }
#ds-board .ds-rule { color:var(--text-secondary); font-family:inherit; }
#ds-board .ds-foot { margin-top:1rem; padding-top:.5rem;
  border-top:1px solid var(--border); font-size:12.5px; color:var(--text-muted); }
#ds-board .ds-fail { color:#e5484d; }
</style>"""
