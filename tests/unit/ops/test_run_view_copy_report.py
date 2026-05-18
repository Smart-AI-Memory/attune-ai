"""Tests for the run-view "Copy report" button.

The button copies the rendered report (`<pre data-log>` contents) to
the clipboard via `navigator.clipboard.writeText`. Tests live at the
source-grep level since the production logic is single-file JS and
the DOM/clipboard interactions don't lend themselves to a Python
emulator. Behavioral coverage at the browser level is tracked in the
PR's manual-smoke test plan.

Spec context: Patrick's request 2026-05-17 — one-click copy of any
workflow run's report for sharing/pasting into other tools.
"""

from __future__ import annotations

from pathlib import Path

_TEMPLATE = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "templates" / "run_view.html"
)
_JS = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "js" / "run_view.js"
)
_CSS = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "css" / "main.css"
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_template_renders_copy_report_button() -> None:
    """The run-view header includes a button tagged with
    ``data-copy-report`` so the JS wirer can locate it."""
    text = _read(_TEMPLATE)
    assert "data-copy-report" in text
    assert 'class="btn-copy-report"' in text
    assert "Copy report" in text
    # The button should be inside the run-view-head section.
    head_idx = text.find("run-view-head")
    btn_idx = text.find("data-copy-report")
    assert (
        head_idx >= 0 and btn_idx > head_idx
    ), "Copy-report button should live inside .run-view-head"


def test_template_button_has_tooltip_and_aria_label() -> None:
    """Compact UI — the icon-style button needs a tooltip for
    discoverability and an aria-label for screen readers."""
    text = _read(_TEMPLATE)
    assert "data-tooltip=" in text
    assert "Copy the full report to clipboard" in text
    assert 'aria-label="Copy report to clipboard"' in text


def test_js_exports_copy_helpers() -> None:
    """``readReportText``, ``copyReportToClipboard``, and
    ``wireCopyReportButton`` are the three public entry points the
    DOMContentLoaded handler and tests need."""
    text = _read(_JS)
    assert "function readReportText(" in text
    assert "function copyReportToClipboard(" in text
    assert "function wireCopyReportButton(" in text
    assert "readReportText: readReportText" in text
    assert "copyReportToClipboard: copyReportToClipboard" in text
    assert "wireCopyReportButton: wireCopyReportButton" in text


def test_js_reads_from_data_log() -> None:
    """The copy helper reads from the canonical ``[data-log]``
    element so it picks up the live SSE-streamed log AND the
    server-pre-rendered disk-loaded log without branching."""
    text = _read(_JS)
    assert 'querySelector("[data-log]")' in text
    # Read via textContent (not innerHTML — we want the literal text
    # the user sees, not the markup).
    assert "textContent" in text


def test_js_uses_navigator_clipboard_api() -> None:
    """Modern clipboard API — must check feature availability before
    invoking (gracefully degrades on insecure contexts / old browsers
    that disable the API)."""
    text = _read(_JS)
    assert "navigator.clipboard" in text
    assert "navigator.clipboard.writeText" in text
    # Feature-detection guard
    assert "!navigator.clipboard" in text or "navigator.clipboard ||" in text


def test_js_flashes_visual_feedback_on_copy_state() -> None:
    """Successful and failed copies both flash a brief label
    change + class toggle so the user gets immediate feedback.
    Classes are restored to the default state after ~1.5s."""
    text = _read(_JS)
    assert "is-copied" in text
    assert "is-failed" in text
    # The flash helper schedules a cleanup via setTimeout
    assert "setTimeout" in text
    assert "flashCopyState" in text


def test_js_handles_empty_report() -> None:
    """When the report is empty (e.g. SSE hasn't populated yet, or
    the disk record has zero lines), the copy attempt surfaces a
    'Nothing to copy' message rather than calling writeText with
    an empty string."""
    text = _read(_JS)
    assert "Nothing to copy" in text


def test_js_wires_button_on_dom_ready() -> None:
    """The wirer attaches the click listener at DOMContentLoaded
    (or immediately if the document is already past loading state)
    so the button works on both the live-run and disk-loaded
    branches without depending on the SSE stream."""
    text = _read(_JS)
    wire_idx = text.find("wireCopyReportButton")
    assert wire_idx > 0
    # The boot block checks document.readyState and either attaches
    # the DOMContentLoaded listener OR calls the wirer immediately.
    assert 'document.readyState === "loading"' in text
    assert "DOMContentLoaded" in text


def test_css_styles_copy_report_button_states() -> None:
    """Base + hover + focus-visible + is-copied + is-failed —
    dotted-border-becomes-solid-on-hover matches Patrick's existing
    color/hover affordance preference for clickable chips."""
    text = _read(_CSS)
    assert ".btn-copy-report" in text
    assert ".btn-copy-report:hover" in text
    assert ".btn-copy-report:focus-visible" in text
    assert ".btn-copy-report.is-copied" in text
    assert ".btn-copy-report.is-failed" in text
    # Dotted-border-on-rest, solid-on-hover (matches suggestion-chip
    # in the parallel ops-suggestion-chips PR).
    assert "border: 1px dotted" in text
    # Hover transition exists
    assert "transition:" in text
