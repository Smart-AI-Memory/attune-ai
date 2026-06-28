"""Render a serialized ``WorkflowReport`` as an HTML panel for show_widget.

This is the UNIVERSAL output surface for SDK-native analysis workflows
(spec: docs/specs/analysis-workflow-output-widgets/ D4). Every such
workflow (security-audit, code-review, perf-audit, bug-predict,
test-audit, refactor-plan, dependency-check, deep-review, …) emits a
``WorkflowReport`` whose ``sections`` are some mix of:

- ``findings`` — structured ``Finding{severity,file,line,message}`` (rare;
  the structured-output path).
- ``list`` — category bullets (the common case — what
  ``agent_sdk_adapter._parse_findings`` produces: security / quality /
  performance / architecture → bullet strings).
- ``next-steps`` — forward actions (``text`` + optional ``command``).

So ONE panel renders any of them — no per-finding-shape assumptions
(the mistake the security severity dashboard made). Wired into the shared
``_workflow_response`` report path, it lights up every report workflow at
once.

Same injection-safety contract as the other widgets: display-only (no
``<script>``), every report-derived string ``html.escape``d, CDS tokens,
transparent background, no ``position: fixed``.
"""

from __future__ import annotations

from typing import Any

from attune.workflows.findings_widget import colour_for, esc, location, severity_of, severity_rank


def _finding_card(f: dict[str, Any]) -> str:
    colour = colour_for(f)
    return (
        f'<div class="rp-card" style="border-left:3px solid {colour};">'
        f'<div class="rp-card-head">'
        f'<span class="rp-dot" style="background:{colour};"></span>'
        f'<span class="rp-sev">{esc(severity_of(f))}</span>'
        f'<span class="rp-loc">{location(f)}</span>'
        f"</div>"
        f'<div class="rp-msg">{esc(f.get("message"))}</div>'
        f"</div>"
    )


def _section_html(section: dict[str, Any]) -> str:
    kind = section.get("kind")
    title = esc(section.get("title"))
    head = f'<div class="rp-sec-head">{title}</div>' if title else ""

    if kind == "findings":
        findings = section.get("findings") or []
        body = "".join(_finding_card(f) for f in sorted(findings, key=severity_rank))
        body = body or '<div class="rp-empty">none</div>'
        return f'<div class="rp-sec">{head}{body}</div>'

    if kind == "list":
        items = section.get("items") or []
        lis = "".join(f"<li>{esc(i)}</li>" for i in items) or '<li class="rp-empty">none</li>'
        return f'<div class="rp-sec">{head}<ul class="rp-list">{lis}</ul></div>'

    if kind == "next-steps":
        items = section.get("items") or []
        lis = ""
        for a in items:
            text = a.get("text") if isinstance(a, dict) else str(a)
            cmd = a.get("command") if isinstance(a, dict) else None
            cmd_html = f' <code class="rp-cmd">{esc(cmd)}</code>' if cmd else ""
            lis += f"<li>{esc(text)}{cmd_html}</li>"
        lis = lis or '<li class="rp-empty">none</li>'
        return f'<div class="rp-sec">{head}<ul class="rp-list">{lis}</ul></div>'

    # Generic fallback for any other section kind (callout/prose/table):
    # render the title plus any string items, escaped. Never produced by
    # the analysis-workflow path today, but keeps the panel robust.
    items = section.get("items") or []
    if items:
        lis = "".join(f"<li>{esc(i)}</li>" for i in items)
        return f'<div class="rp-sec">{head}<ul class="rp-list">{lis}</ul></div>'
    text = section.get("text") or section.get("body") or ""
    return f'<div class="rp-sec">{head}<div class="rp-prose">{esc(text)}</div></div>'


def report_to_panel_html(report: dict[str, Any], succeeded: bool = True, message: str = "") -> str:
    """Render a serialized ``WorkflowReport`` dict as a panel.

    Args:
        report: ``WorkflowReport.to_dict()`` — ``{title, summary, score,
            metadata, sections, ...}``.
        succeeded: Whether the workflow actually ran. ``False`` renders an
            explicit "did not complete" state — never a false all-clear
            (the security-dashboard false-clean lesson, #1152).
        message: Optional caption above the panel.

    Returns:
        Self-contained HTML for ``mcp__visualize__show_widget``.
    """
    report = report or {}
    caption = f'<p class="rp-msg">{esc(message)}</p>' if message else ""

    if not succeeded:
        return (
            '<div id="rp-panel">'
            + _STYLE
            + caption
            + '<div class="rp-fail">⚠ Workflow did not complete — no results '
            + "to show. This is NOT a clean result; check the run/auth "
            + "status and re-run.</div></div>"
        )

    title = esc(report.get("title") or "Report")
    score = report.get("score")
    score_html = (
        f'<span class="rp-score">score {esc(score)}/100</span>' if score is not None else ""
    )
    summary = report.get("summary")
    summary_html = f'<div class="rp-summary">{esc(summary)}</div>' if summary else ""

    sections = report.get("sections") or []
    sections_html = "".join(_section_html(s) for s in sections)
    if not sections_html:
        sections_html = '<div class="rp-empty">no findings reported</div>'

    return (
        '<div id="rp-panel">'
        + _STYLE
        + caption
        + f'<div class="rp-head"><span class="rp-title">{title}</span>{score_html}</div>'
        + summary_html
        + sections_html
        + "</div>"
    )


_STYLE = """<style>
#rp-panel { display:block; width:100%; padding:1rem 0;
  color:var(--text-primary); line-height:1.45; font-size:14px; }
#rp-panel .rp-msg { margin:0 0 .75rem; color:var(--text-secondary); }
#rp-panel .rp-head { display:flex; align-items:center; gap:.6rem; margin-bottom:.4rem; }
#rp-panel .rp-title { font-size:17px; font-weight:600; }
#rp-panel .rp-score { margin-left:auto; padding:.2rem .55rem; font-size:13px;
  color:var(--text-primary); background:var(--bg-accent);
  border:1px solid var(--border-accent); border-radius:var(--radius); }
#rp-panel .rp-summary { margin:0 0 1rem; color:var(--text-secondary);
  white-space:pre-wrap; }
#rp-panel .rp-sec { margin:0 0 1rem; }
#rp-panel .rp-sec-head { font-weight:600; font-size:13px; text-transform:uppercase;
  letter-spacing:.03em; color:var(--text-secondary); margin-bottom:.4rem; }
#rp-panel .rp-list { margin:0; padding-left:1.2rem; }
#rp-panel .rp-list li { margin:.15rem 0; }
#rp-panel .rp-card { padding:.5rem .6rem; margin:.4rem 0; background:var(--surface-1);
  border:1px solid var(--border); border-radius:var(--radius); }
#rp-panel .rp-card-head { display:flex; align-items:center; gap:.4rem;
  font-size:12px; color:var(--text-muted); margin-bottom:.2rem; }
#rp-panel .rp-dot { width:.55em; height:.55em; border-radius:50%; flex:0 0 auto;
  display:inline-block; }
#rp-panel .rp-sev { font-weight:600; text-transform:uppercase; letter-spacing:.02em; }
#rp-panel .rp-loc { margin-left:auto; font-family:ui-monospace,monospace; }
#rp-panel .rp-msg-card, #rp-panel .rp-msg { color:var(--text-primary); }
#rp-panel .rp-cmd { font-size:12.5px; font-family:ui-monospace,monospace;
  background:var(--surface-2,var(--surface-1)); padding:0 .3em; border-radius:3px; }
#rp-panel .rp-prose { white-space:pre-wrap; color:var(--text-secondary); }
#rp-panel .rp-empty { font-size:13px; color:var(--text-muted); font-style:italic; }
#rp-panel .rp-fail { font-size:13.5px; font-weight:500; color:#e5484d; }
</style>"""
