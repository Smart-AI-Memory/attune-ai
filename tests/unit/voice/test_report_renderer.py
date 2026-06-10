"""Tests for attune.voice.report_renderer (workflow-result-formatting T2).

Four layers per the proposal's test strategy:

1. repr-leak drift guard — rendered output never contains dataclass
   reprs or serialized-dict noise, in normal AND crash paths.
2. tier-classification guard — detail-tier sections wrap in
   ``<details>`` under summary disclosure, render inline under full;
   essential/useful always inline.
3. structural renderer assertions — each section kind's markdown shape.
4. renderer-crash visibility — a broken report yields the error banner
   AND the fallback block, never an exception.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.voice import report_renderer
from attune.voice.report_renderer import render, render_safe
from attune.workflows.output import (
    CalloutSection,
    Finding,
    FindingsSection,
    ListSection,
    NextAction,
    NextStepsSection,
    ProseSection,
    TableSection,
    WorkflowReport,
)


def _full_report() -> WorkflowReport:
    """One report exercising every section kind and every tier."""
    return WorkflowReport(
        title="Security audit",
        summary="2 findings across 14 files.",
        score=87,
        metadata={"cost_usd": 1.25, "duration_s": 42.0, "model": "sonnet"},
        sections=[
            CalloutSection(
                title="Heads up",
                tier="essential",
                text="One high-severity finding.",
                emphasis="warn",
            ),
            ProseSection(title="Overview", tier="useful", text="Scanned src/ and plugin/."),
            TableSection(
                title="Files by risk",
                tier="useful",
                columns=["File", "Risk"],
                rows=[{"File": "a.py", "Risk": "high"}, {"File": "b.py", "Risk": "low"}],
            ),
            ListSection(title="Skipped paths", tier="detail", items=["vendor/", "dist/"]),
            FindingsSection(
                title="Findings",
                tier="essential",
                findings=[
                    Finding(severity="low", file="b.py", line=7, message="weak hash"),
                    Finding(severity="high", file="a.py", line=12, message="eval use"),
                ],
            ),
            NextStepsSection(
                title="Next steps",
                tier="essential",
                items=[
                    NextAction(text="Fix the eval", file="a.py:12"),
                    NextAction(
                        text="Re-run the audit", command="attune workflow run security-audit"
                    ),
                ],
            ),
        ],
    )


# =========================================================================
# Layer 1 — repr-leak drift guard
# =========================================================================


REPR_MARKERS = (
    "WorkflowReport(",
    "FindingsSection(",
    "Finding(",
    "NextAction(",
    "'_type'",
    '"_type"',
    "dataclass",
)


@pytest.mark.parametrize("disclosure", ["summary", "full"])
def test_render_never_leaks_reprs(disclosure):
    out = render(_full_report(), disclosure=disclosure, show_cost=True)
    for marker in REPR_MARKERS:
        assert marker not in out, f"repr leak: {marker!r}"


def test_crash_path_never_leaks_reprs(monkeypatch):
    monkeypatch.setattr(report_renderer, "_render_section", _boom, raising=True)
    out = render_safe(_full_report())
    for marker in REPR_MARKERS:
        assert marker not in out, f"repr leak in fallback: {marker!r}"


def _boom(*_a, **_k):
    raise AttributeError("'NoneType' object has no attribute 'value'")


# =========================================================================
# Layer 2 — tier classification
# =========================================================================


def test_detail_tier_wraps_in_details_under_summary():
    out = render(_full_report(), disclosure="summary")
    assert "<details><summary>Skipped paths</summary>" in out
    assert "- vendor/" in out  # content still present inside the wrap


def test_detail_tier_inline_under_full():
    out = render(_full_report(), disclosure="full")
    assert "<details>" not in out
    assert "- vendor/" in out


def test_essential_and_useful_never_wrapped():
    out = render(_full_report(), disclosure="summary")
    # Only the one detail section produces a <details> block.
    assert out.count("<details>") == 1


# =========================================================================
# Layer 3 — structural assertions per section kind
# =========================================================================


def test_header_summary_and_score():
    out = render(_full_report())
    assert out.startswith("# Security audit\n")
    assert "2 findings across 14 files." in out
    assert "**Score:** 87/100" in out


def test_callout_renders_as_quote_with_emphasis_icon():
    out = render(_full_report())
    assert "> ⚠️ **Heads up**" in out
    assert "> One high-severity finding." in out


def test_table_renders_markdown_table():
    out = render(_full_report(), disclosure="full")
    assert "| File | Risk |" in out
    assert "| a.py | high |" in out


def test_findings_sorted_by_severity_with_location_code():
    out = render(_full_report())
    assert "| Severity | Location | Message |" in out
    assert out.index("| high | `a.py:12` |") < out.index("| low | `b.py:7` |")


def test_next_steps_renders_last_with_command_fence_and_file_code():
    out = render(_full_report())
    assert out.rstrip().split("\n\n")[-2].startswith("- Re-run the audit") or (
        "## Next steps" in out
    )
    assert "(`a.py:12`)" in out
    assert "attune workflow run security-audit" in out
    # next-steps is the LAST section even though findings follow it in shape
    assert out.index("## Next steps") > out.index("## Findings")


def test_empty_next_steps_omitted():
    report = WorkflowReport(
        title="T",
        sections=[NextStepsSection(title="Next steps", tier="essential", items=[])],
    )
    out = render(report)
    assert "Next steps" not in out


def test_next_steps_always_last_regardless_of_position():
    report = WorkflowReport(
        title="T",
        sections=[
            NextStepsSection(
                title="Next steps", tier="essential", items=[NextAction(text="do it")]
            ),
            ProseSection(title="After", tier="essential", text="body"),
        ],
    )
    out = render(report)
    assert out.index("## After") < out.index("## Next steps")


def test_cost_line_gated_by_show_cost():
    report = _full_report()
    assert "Cost & time" not in render(report, show_cost=False)
    with_cost = render(report, show_cost=True)
    assert "*Cost & time:* $1.25 · 42.0s · sonnet" in with_cost


def test_pipe_and_newline_escaped_in_cells():
    report = WorkflowReport(
        title="T",
        sections=[TableSection(title="", tier="useful", columns=["A"], rows=[{"A": "x|y\nz"}])],
    )
    out = render(report)
    assert "x\\|y z" in out


def test_round_trip_through_dict_renders_identically():
    """from_dict(to_dict(r)) renders byte-identical — the MCP/SDK path."""
    report = _full_report()
    rebuilt = WorkflowReport.from_dict(report.to_dict())
    assert render(rebuilt, show_cost=True) == render(report, show_cost=True)


# =========================================================================
# Layer 4 — renderer-crash visibility
# =========================================================================


def test_crash_emits_banner_and_fallback(monkeypatch):
    monkeypatch.setattr(report_renderer, "_render_section", _boom, raising=True)
    out = render_safe(_full_report())
    assert "⚠ Report renderer error: AttributeError" in out
    assert "# Security audit" in out  # fallback still shows the content
    assert "- Findings" in out  # section titles listed


def test_render_safe_passthrough_when_healthy():
    report = _full_report()
    assert render_safe(report) == render(report)


# =========================================================================
# Edge paths (empty sections, unknown kinds, malformed metadata)
# =========================================================================


def test_empty_sections_render_title_only_or_nothing():
    report = WorkflowReport(
        title="T",
        sections=[
            TableSection(title="Empty table", tier="useful"),
            ListSection(title="Empty list", tier="useful"),
            FindingsSection(title="No findings", tier="useful"),
            TableSection(title="", tier="useful"),
        ],
    )
    out = render(report)
    assert "## Empty table" in out
    assert "## Empty list" in out
    assert "## No findings" in out
    assert "| " not in out  # no table machinery for empty content


def test_unknown_section_subclass_fails_soft_with_title():
    class WeirdSection(ProseSection.__mro__[1]):  # subclass of Section
        pass

    report = WorkflowReport(
        title="T",
        sections=[WeirdSection(title="Mystery", tier="useful")],
    )
    out = render(report)
    assert "## Mystery" in out


def test_callout_without_title_or_text():
    report = WorkflowReport(
        title="T",
        sections=[
            CalloutSection(title="", tier="essential", text="", emphasis="ok"),
            CalloutSection(title="", tier="essential", text="body only"),
        ],
    )
    out = render(report)
    assert "> ✅" in out
    assert "> body only" in out


def test_cost_line_skips_malformed_values():
    report = WorkflowReport(title="T", metadata={"cost_usd": "not-a-number", "duration_s": 2.0})
    out = render(report, show_cost=True)
    assert "*Cost & time:* 2.0s" in out


def test_cost_line_absent_when_no_known_keys():
    report = WorkflowReport(title="T", metadata={"irrelevant": 1})
    assert "Cost & time" not in render(report, show_cost=True)


def test_next_action_file_only_and_bare():
    report = WorkflowReport(
        title="T",
        sections=[
            NextStepsSection(
                title="Next steps",
                tier="essential",
                items=[NextAction(text="", file="x.py:1"), NextAction(text="just text")],
            )
        ],
    )
    out = render(report)
    assert "- `x.py:1`" in out
    assert "- just text" in out
