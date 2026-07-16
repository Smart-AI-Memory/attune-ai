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

import re
from typing import Any

from attune.workflows.findings_widget import colour_for, esc, location, severity_of, severity_rank

# Accent colour per analysis category. Mid-tone hues legible in both
# light and dark; used only on a left border + heading dot, never as text.
_CAT_COLOUR: dict[str, str] = {
    "security": "#e5484d",
    "quality": "#0090ff",
    "performance": "#f76808",
    "architecture": "#8e4ec6",
}
_CAT_DEFAULT = "#8b8d98"

_CWE_RE = re.compile(r"\b(CWE-\d+)\b")
# A file reference with a line number, e.g. ``pkg/mod.py:88``.
_REF_RE = re.compile(r"\b([\w./-]+\.[A-Za-z]\w*:\d+)\b")


def _cat_colour(title: str) -> str:
    return _CAT_COLOUR.get(title.strip().lower(), _CAT_DEFAULT)


def _highlight(text: Any) -> str:
    """Escape a bullet, then accent CWE codes and ``file:line`` refs.

    Injection-safe: ``esc`` runs first, so the regexes only ever wrap
    already-escaped alphanumeric/punctuation runs in our own markup.
    """
    t = esc(text)
    t = _CWE_RE.sub(r'<span class="rp-cwe">\1</span>', t)
    t = _REF_RE.sub(r'<span class="rp-ref">\1</span>', t)
    return t


def _sec_head(title: str, colour: str, count: int) -> str:
    return (
        f'<div class="rp-sec-head">'
        f'<span class="rp-cat-dot" style="background:{colour};"></span>'
        f'{esc(title)} <span class="rp-cat-n">{count}</span></div>'
    )


def _finding_card(f: dict[str, Any]) -> str:
    colour = colour_for(f)
    return (
        f'<div class="rp-card" style="border-left:3px solid {colour};">'
        f'<div class="rp-card-head">'
        f'<span class="rp-dot" style="background:{colour};"></span>'
        f'<span class="rp-sev">{esc(severity_of(f))}</span>'
        f'<span class="rp-loc">{location(f)}</span>'
        f"</div>"
        f'<div class="rp-msg">{_highlight(f.get("message"))}</div>'
        f"</div>"
    )


def _section_html(section: dict[str, Any]) -> str:
    kind = section.get("kind")
    raw_title = str(section.get("title") or "")
    colour = _cat_colour(raw_title)

    def _wrap(count: int, body: str) -> str:
        head = _sec_head(raw_title, colour, count) if raw_title else ""
        return f'<div class="rp-sec" style="border-left:3px solid {colour};">{head}{body}</div>'

    if kind == "findings":
        findings = sorted(section.get("findings") or [], key=severity_rank)
        body = "".join(_finding_card(f) for f in findings) or '<div class="rp-empty">none</div>'
        return _wrap(len(findings), body)

    if kind == "list":
        items = section.get("items") or []
        lis = (
            "".join(f"<li>{_md_inline(i)}</li>" for i in items) or '<li class="rp-empty">none</li>'
        )
        return _wrap(len(items), f'<ul class="rp-list">{lis}</ul>')

    if kind == "next-steps":
        items = section.get("items") or []
        lis = ""
        for a in items:
            text = a.get("text") if isinstance(a, dict) else str(a)
            cmd = a.get("command") if isinstance(a, dict) else None
            cmd_html = f' <code class="rp-cmd">{esc(cmd)}</code>' if cmd else ""
            lis += f"<li>{_md_inline(text)}{cmd_html}</li>"
        lis = lis or '<li class="rp-empty">none</li>'
        return _wrap(len(items), f'<ul class="rp-list">{lis}</ul>')

    # Generic fallback for any other section kind (callout/prose/table):
    # render the title plus any string items, escaped. Never produced by
    # the analysis-workflow path today, but keeps the panel robust.
    items = section.get("items") or []
    if items:
        lis = "".join(f"<li>{_md_inline(i)}</li>" for i in items)
        return _wrap(len(items), f'<ul class="rp-list">{lis}</ul>')
    text = section.get("text") or section.get("body") or ""
    return _wrap(0, f'<div class="rp-prose">{esc(text)}</div>')


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


# ------------------------------------------------------------------
# Family-B: prose-only workflows (deep-review, test-audit,
# refactor-plan, dependency-check, code-review) yield no parseable
# findings, so their final_output stays raw markdown text rather than
# a WorkflowReport. Render that prose as a panel too — same chrome and
# injection-safety contract — instead of dumping raw markdown.
# ------------------------------------------------------------------

_MD_H_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_MD_NUM_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_CODE_RE = re.compile(r"`([^`]+)`")


def _md_inline(text: Any) -> str:
    """Escape a line, then apply safe inline markdown plus shared accents.

    Runs ``_highlight`` first (``esc`` + CWE / ``file:line`` accents), so the
    bold/code regexes only ever wrap already-escaped text — a raw ``<script>``
    in the source can never survive as markup. Injection-safe by construction.
    """
    t = _highlight(text)
    t = _MD_BOLD_RE.sub(r"<strong>\1</strong>", t)
    t = _MD_CODE_RE.sub(r'<code class="rp-cmd">\1</code>', t)
    return t


def markdown_to_panel_html(
    markdown: str, title: str = "", succeeded: bool = True, message: str = ""
) -> str:
    """Render a prose markdown string as a panel for ``show_widget``.

    Supports a lightweight subset — ATX headings (``#``..``######``),
    bullet / numbered lists, paragraphs, inline ``**bold**`` and
    ``` `code` ```. Unknown syntax degrades to escaped text, never raw HTML.

    Args:
        markdown: The raw agent markdown (an analysis workflow's
            ``final_output`` when no findings parsed).
        title: Optional panel heading.
        succeeded: ``False`` renders an explicit "did not complete" state —
            never a false all-clear (the security-dashboard lesson, #1152).
        message: Optional caption above the panel.

    Returns:
        Self-contained HTML for ``mcp__visualize__show_widget``.
    """
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

    head = f'<div class="rp-head"><span class="rp-title">{esc(title)}</span></div>' if title else ""

    blocks: list[str] = []
    para: list[str] = []
    items: list[str] = []

    def flush_para() -> None:
        if para:
            blocks.append(f'<p class="rp-md-p">{"<br>".join(_md_inline(x) for x in para)}</p>')
            para.clear()

    def flush_list() -> None:
        if items:
            lis = "".join(f"<li>{i}</li>" for i in items)
            blocks.append(f'<ul class="rp-list">{lis}</ul>')
            items.clear()

    for line in (markdown or "").splitlines():
        h = _MD_H_RE.match(line)
        b = _MD_BULLET_RE.match(line) or _MD_NUM_RE.match(line)
        if h:
            flush_para()
            flush_list()
            level = min(len(h.group(1)), 6)
            blocks.append(f'<div class="rp-md-h rp-md-h{level}">{_md_inline(h.group(2))}</div>')
        elif b:
            flush_para()
            items.append(_md_inline(b.group(1)))
        elif not line.strip():
            flush_para()
            flush_list()
        else:
            flush_list()
            para.append(line)
    flush_para()
    flush_list()

    body = "".join(blocks) or '<div class="rp-empty">no content</div>'
    return (
        '<div id="rp-panel">' + _STYLE + caption + head + f'<div class="rp-md">{body}</div></div>'
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
#rp-panel .rp-sec { margin:0 0 1rem; padding:.1rem 0 .1rem .7rem; }
#rp-panel .rp-sec-head { display:flex; align-items:center; gap:.4rem;
  font-weight:600; font-size:13px; text-transform:uppercase;
  letter-spacing:.03em; color:var(--text-secondary); margin-bottom:.4rem; }
#rp-panel .rp-cat-dot { width:.55em; height:.55em; border-radius:50%;
  flex:0 0 auto; display:inline-block; }
#rp-panel .rp-cat-n { min-width:1.4em; text-align:center; padding:0 .35em;
  font-size:11px; color:var(--text-primary); background:var(--surface-1);
  border:1px solid var(--border); border-radius:var(--radius); }
#rp-panel .rp-cwe { font-size:11.5px; font-weight:600; padding:0 .35em;
  color:#e5484d; background:var(--surface-1); border:1px solid var(--border);
  border-radius:3px; white-space:nowrap; }
#rp-panel .rp-ref { font-family:ui-monospace,monospace; font-size:12.5px;
  color:var(--text-primary); background:var(--surface-2,var(--surface-1));
  padding:0 .25em; border-radius:3px; }
#rp-panel .rp-list { margin:0; padding-left:1.2rem; }
#rp-panel .rp-list li { margin:.25rem 0; }
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
#rp-panel .rp-md { color:var(--text-secondary); }
#rp-panel .rp-md-p { margin:.5rem 0; }
#rp-panel .rp-md-h { font-weight:600; color:var(--text-primary); margin:.9rem 0 .35rem; }
#rp-panel .rp-md-h1, #rp-panel .rp-md-h2 { font-size:15px; }
#rp-panel .rp-md-h3, #rp-panel .rp-md-h4,
#rp-panel .rp-md-h5, #rp-panel .rp-md-h6 { font-size:13.5px; }
#rp-panel .rp-md strong { color:var(--text-primary); }
</style>"""
