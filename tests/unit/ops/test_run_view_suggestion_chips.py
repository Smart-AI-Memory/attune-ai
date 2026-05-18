"""Tests for the "What I'd Do Next" suggestion-chip renderer in run_view.js.

The chip renderer parses workflow report output (the voice layer's
"What I'd Do Next" section) and emits clickable chips on the run-view
page. Tests live at the JS-source-grep level (no DOM emulator) since
the production logic is single-file and the parsing rules are
documented in source comments.

Spec context: Patrick's request 2026-05-17 — surface the textual
"I'd run X next" suggestions as one-click chips so users don't have
to copy-paste workflow names into the terminal.
"""

from __future__ import annotations

from pathlib import Path

_RUN_VIEW_JS = (
    Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "js" / "run_view.js"
)


def _read_js() -> str:
    return _RUN_VIEW_JS.read_text(encoding="utf-8")


def test_parser_helper_exists() -> None:
    """``parseSuggestions`` and ``renderSuggestionChipsFromLog`` are
    the two public entry points the SSE handler + disk-loaded branch
    call into. Both must be exported."""
    text = _read_js()
    assert "function parseSuggestions(" in text
    assert "function renderSuggestionChipsFromLog(" in text
    assert "function buildSuggestionChip(" in text
    assert "parseSuggestions: parseSuggestions" in text
    assert "renderSuggestionChipsFromLog: renderSuggestionChipsFromLog" in text
    assert "buildSuggestionChip: buildSuggestionChip" in text


def test_parser_anchored_on_voice_layer_header() -> None:
    """The header literal must match ``HEADER_NEXT_STEPS`` in
    ``attune.voice.personality``. If either side drifts, the chips
    silently stop rendering."""
    text = _read_js()
    assert 'line === "What I\'d Do Next"' in text

    # Confirm the producer side still emits the same string.
    personality = (
        Path(__file__).resolve().parents[3] / "src" / "attune" / "voice" / "personality.py"
    )
    py_text = personality.read_text(encoding="utf-8")
    assert 'HEADER_NEXT_STEPS = "What I\'d Do Next"' in py_text


def test_parser_workflow_name_regex_matches_canonical_shape() -> None:
    """The workflow-name regex matches the same shape used by the
    runner's ``_WORKFLOW_NAME_RE`` — lowercase letters, digits, and
    hyphens, starting with a letter."""
    text = _read_js()
    # JS-side
    assert "/^[a-z][a-z0-9-]+$/" in text
    # The "attune workflow run X" extractor
    assert "/attune workflow run\\s+([a-z][a-z0-9-]+)/i" in text


def test_done_handler_invokes_renderer() -> None:
    """After the SSE ``done`` event fires and the status chip is set,
    the handler scans the buffered log for suggestions."""
    text = _read_js()
    done_idx = text.find('addEventListener("done"')
    assert done_idx > 0
    # Helper called inside the done body (anywhere before the next
    # addEventListener).
    next_handler = text.find("addEventListener(", done_idx + 1)
    done_body = text[done_idx:next_handler]
    assert "renderSuggestionChipsFromLog(logBuffer)" in done_body


def test_disk_loaded_branch_invokes_renderer() -> None:
    """Disk-loaded runs (no SSE — server pre-rendered <pre>) also
    render chips by reading the existing <pre data-log> textContent."""
    text = _read_js()
    # The else branch: STREAM_URL absent path. Both invocations live
    # below the SSE block; assert both function references are present.
    assert 'querySelector("[data-log]")' in text
    assert "renderSuggestionChipsFromLog(preEl.textContent" in text


def test_chip_button_carries_workflow_name_data_attribute() -> None:
    """Each chip is a <button> with data-suggestion-chip="<name>" so
    drift-guard tests + accessibility tooling can locate it."""
    text = _read_js()
    assert 'chip.setAttribute("data-suggestion-chip"' in text
    assert 'chip.className = "suggestion-chip"' in text
    assert 'chip.type = "button"' in text


def test_chip_click_posts_with_inherited_scope_path() -> None:
    """A suggestion chip POSTs to ``/workflows/<name>/run`` with the
    current run's path threaded through as the body's ``path`` key.
    No path = body-less POST, matching the runner's project-wide
    semantics."""
    text = _read_js()
    # The fetch target and the path-inheritance branch
    assert '"/workflows/" + encodeURIComponent(suggestion.name) + "/run"' in text
    assert 'if (DATA && typeof DATA.path === "string" && DATA.path)' in text
    assert "body.path = DATA.path" in text


def test_chip_409_surfaces_inline_error() -> None:
    """A 409 (runner busy) response surfaces the inline error already
    used by Phase 4 pill clicks — same pattern, same UI."""
    text = _read_js()
    # Find the suggestion-chip handler body. The next TOP-LEVEL function
    # definition (two-space indent inside the IIFE) bounds the chip
    # function; nested ``function () { ... }`` fetch callbacks share
    # the keyword but with different indentation.
    chip_idx = text.find("function buildSuggestionChip(")
    next_top = text.find("\n  function ", chip_idx + 1)
    body = text[chip_idx : next_top if next_top != -1 else len(text)]
    assert "resp.status === 409" in body
    assert "showInlineError(" in body


def test_chip_201_navigates_with_from_param() -> None:
    """Successful chip click navigates to the new run with
    ``?from=<source-workflow>`` so the chained-from badge renders."""
    text = _read_js()
    chip_idx = text.find("function buildSuggestionChip(")
    next_top = text.find("\n  function ", chip_idx + 1)
    body = text[chip_idx : next_top if next_top != -1 else len(text)]
    assert "resp.status === 201" in body
    # The literal includes "/view?from=" — match the unique suffix.
    assert '?from=" + encodeURIComponent(DATA.workflow || "")' in body


def test_parser_skips_lines_outside_next_steps_section() -> None:
    """The parser only activates inside the "What I'd Do Next" block.
    A backtick-wrapped workflow name elsewhere in the log (e.g. the
    initial command line, or a description that happens to mention
    a workflow) must not produce a chip."""
    text = _read_js()
    # The implementation uses `inNextSteps = false` as the initial gate
    # and flips to true only on the header line.
    assert "var inNextSteps = false;" in text
    assert "inNextSteps = true;" in text


def test_parser_dedupes_repeated_workflow_names() -> None:
    """Workflow reports occasionally repeat the same suggestion (e.g.
    the same workflow appears with two different justification
    strings). The chip row should show each name once."""
    text = _read_js()
    # The implementation tracks seen names in a flat object map.
    assert "var seen = {};" in text
    assert "if (seen[name]) continue;" in text


def test_css_styles_suggestion_chip() -> None:
    """The chip styles ship with hover + focus-visible + disabled
    states. The base style is a dotted-outline pill (matches Patrick's
    color/hover affordance preference: dotted underline / dotted
    border for clickability)."""
    css_path = _RUN_VIEW_JS.parent.parent / "css" / "main.css"
    text = css_path.read_text(encoding="utf-8")
    assert ".suggestion-chip" in text
    assert ".suggestion-chip:hover" in text
    assert ".suggestion-chip:focus-visible" in text
    assert ".suggestion-chip:disabled" in text
    assert "border: 1px dotted" in text
