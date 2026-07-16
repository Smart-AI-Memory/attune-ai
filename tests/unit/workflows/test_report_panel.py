"""Tests for the universal report panel (spec analysis-workflow-output-widgets D4).

Built against the REAL producer: reports are constructed via the
production ``AgentSDKResultAdapter._to_workflow_report`` from the exact
``{category: [strings]}`` shape ``_parse_findings`` emits — not synthetic
dicts (the verification gap that let #1149 ship the wrong widget).
"""

from __future__ import annotations

import pytest

from attune.workflows.agent_sdk_adapter import AgentSDKResultAdapter as A
from attune.workflows.report_panel import markdown_to_panel_html, report_to_panel_html

pytestmark = pytest.mark.unit


def _report(findings, *, title="Security audit", summary="s", score=72, suggestions=None):
    return A._to_workflow_report(
        title=title,
        summary=summary,
        score=score,
        findings=findings,
        suggestions=suggestions or [],
        total_cost=None,
        duration_ms=1500,
    ).to_dict()


class TestCategoryBullets:
    """The common SDK-native case: category → bullet strings → list sections."""

    def test_renders_category_list_sections(self):
        d = _report({"security": ["Hardcoded key in config.py:88"], "quality": ["bare except"]})
        # the real producer makes these `list` sections, not `findings`
        assert [s["kind"] for s in d["sections"]] == ["list", "list"]
        html = report_to_panel_html(d)
        assert "Security" in html and "Quality" in html
        assert "Hardcoded key in" in html
        # file:line refs are accented into their own span
        assert 'class="rp-ref">config.py:88' in html
        assert "bare except" in html
        assert "<ul" in html

    def test_list_bullets_render_inline_bold_and_code(self):
        # text-tier bullets often carry markdown; render it, don't leave
        # literal **asterisks** / `backticks` (the Family-B follow-up)
        d = _report({"security": ["Use **parameterized** queries, never `eval`"]})
        html = report_to_panel_html(d)
        assert "<strong>parameterized</strong>" in html
        assert '<code class="rp-cmd">eval</code>' in html
        assert "**parameterized**" not in html

    def test_score_and_summary_in_header(self):
        html = report_to_panel_html(_report({"security": ["x"]}, summary="2 issues found."))
        assert "score 72/100" in html
        assert "2 issues found." in html

    def test_empty_category_skipped(self):
        d = _report({"security": ["real"], "performance": []})
        html = report_to_panel_html(d)
        assert "Performance" not in html
        assert "Security" in html


class TestPolish:
    """The 'wonderful' touches — category accents, CWE badges, file refs."""

    def test_cwe_codes_badged(self):
        html = report_to_panel_html(_report({"security": ["leak (CWE-798) bad"]}))
        assert 'class="rp-cwe">CWE-798</span>' in html

    def test_file_line_refs_accented(self):
        html = report_to_panel_html(_report({"security": ["issue at src/app.py:42 here"]}))
        assert 'class="rp-ref">src/app.py:42</span>' in html

    def test_category_dot_and_count(self):
        html = report_to_panel_html(_report({"security": ["a", "b", "c"]}))
        assert "rp-cat-dot" in html
        assert 'class="rp-cat-n">3</span>' in html

    def test_known_category_gets_colour(self):
        # security category → red accent on the section border
        html = report_to_panel_html(_report({"security": ["x"]}))
        assert "border-left:3px solid #e5484d" in html

    def test_highlight_escapes_before_wrapping(self):
        # a CWE inside an injection attempt: tag escaped, CWE still badged
        html = report_to_panel_html(_report({"security": ["<b>x</b> CWE-1"]}))
        assert "<b>x</b>" not in html
        assert "&lt;b&gt;" in html
        assert 'class="rp-cwe">CWE-1</span>' in html


class TestStructuredFindings:
    """When a workflow DOES emit dict findings, they render as cards."""

    def test_dict_findings_render_as_cards(self):
        d = _report(
            {
                "security": [
                    {"severity": "critical", "file": "a.py", "line": 5, "description": "eval()"}
                ]
            }
        )
        assert d["sections"][0]["kind"] == "findings"
        html = report_to_panel_html(d)
        assert "rp-card" in html
        assert "critical" in html
        assert "a.py:5" in html
        assert "eval()" in html


class TestNextSteps:
    def test_next_steps_section(self):
        from attune.workflows.data_classes import NextAction

        d = _report(
            {"security": ["x"]},
            suggestions=[
                NextAction(
                    workflow_name="security-audit",
                    description="Rotate the leaked key",
                    reasoning="hardcoded secret found",
                )
            ],
        )
        html = report_to_panel_html(d)
        assert "Rotate the leaked key" in html


class TestFailureState:
    def test_failed_run_not_clean(self):
        d = _report({"security": ["x"]})
        html = report_to_panel_html(d, succeeded=False)
        assert "did not complete" in html
        assert "NOT a clean" in html
        # the normal section elements are NOT rendered on failure
        # (".rp-sec-head" appears in the <style> block, so match the element)
        assert '<div class="rp-sec">' not in html

    def test_empty_report_says_none(self):
        html = report_to_panel_html({"title": "X", "summary": "", "score": None, "sections": []})
        assert "no findings reported" in html


class TestInjectionSafety:
    def test_bullet_text_escaped(self):
        d = _report({"security": ["<script>alert(1)</script>"]})
        html = report_to_panel_html(d)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_no_script_tag(self):
        html = report_to_panel_html(_report({"security": ["x"]}))
        assert "<script" not in html.lower()


class TestMarkdownPanel:
    """Family-B: prose-only workflows render markdown through a panel."""

    def test_headings_lists_and_paragraphs_render(self):
        md = "# Deep Review\n\nCode is fine.\n\n- item one\n- item two\n\n## Next\n1. do a thing"
        html = markdown_to_panel_html(md, title="Deep Review")
        assert 'id="rp-panel"' in html
        # title head + both ATX headings become rp-md-h blocks
        assert html.count("rp-md-h") >= 2
        assert "Deep Review" in html and "Next" in html
        # bullets AND the numbered item both become <li>
        assert html.count("<li>") == 3
        assert "item one" in html and "do a thing" in html
        # a plain line becomes a paragraph
        assert 'class="rp-md-p"' in html and "Code is fine." in html

    def test_inline_bold_and_code(self):
        html = markdown_to_panel_html("Overall **solid** work in `config.py`")
        assert "<strong>solid</strong>" in html
        assert '<code class="rp-cmd">config.py</code>' in html

    def test_cwe_and_file_ref_accents_reused(self):
        html = markdown_to_panel_html("- Hardcoded key in config.py:88 (CWE-798)")
        assert 'class="rp-ref"' in html  # file:line accent
        assert 'class="rp-cwe"' in html  # CWE accent

    def test_escapes_html_never_emits_raw_markup(self):
        html = markdown_to_panel_html("A `<script>alert(1)</script>` snippet")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_no_script_tag(self):
        assert "<script" not in markdown_to_panel_html("# H\n\ntext").lower()

    def test_failure_state_never_a_false_all_clear(self):
        html = markdown_to_panel_html("looks fine", succeeded=False)
        assert "did not complete" in html
        assert "NOT a clean result" in html

    def test_empty_input_renders_placeholder_not_crash(self):
        html = markdown_to_panel_html("")
        assert 'id="rp-panel"' in html
        assert "no content" in html

    def test_message_caption_rendered(self):
        html = markdown_to_panel_html("body", message="deep-review of src/")
        assert "deep-review of src/" in html
