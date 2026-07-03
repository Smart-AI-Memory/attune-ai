"""Tests for the v5.1 "report" style of the progress construct.

``progress_style: "report"`` renders a PROGRESS question as a neutral
digest: item ``status`` is a free-form category tag (no task semantics,
no strikethrough), and ``options`` may be any subset of item labels,
offered as a "go deeper" picker. Pure presentation — the answer is one
selected option, validated exactly as the default style. First consumer:
the curated-memory recall digest
(``attune.memory.recall_digest``, curated-memory-productionization R3).
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_widget_html,
)
from attune.elicitation.bridge import form_to_askuserquestion
from attune.meta_workflows.models import FormQuestion, QuestionType


def _report(**override) -> dict:
    """Build a one-field report-style progress form dict."""
    field = {
        "id": "digest",
        "text": "Pull more on a topic?",
        "type": "progress",
        "progress_style": "report",
        "required": False,
        "options": ["Memory architecture", "Goal framing"],
        "rationale": "3 curated nodes, live from Redis.",
        "progress_items": [
            {"label": "Memory architecture", "status": "project context", "detail": "git + Redis"},
            {"label": "Goal framing", "status": "user context"},
            {"label": "Recall benchmarks", "status": "reference", "detail": "86us medians"},
        ],
    }
    field.update(override)
    return {"title": "Memory digest", "fields": [field]}


class TestReportStyleModel:
    def test_progress_style_defaults_none(self) -> None:
        q = FormQuestion(id="a", text="t", type=QuestionType.PROGRESS)
        assert q.progress_style is None


class TestReportStyleFormFromDict:
    def test_builds_report_style(self) -> None:
        form = form_from_dict(_report())
        q = form.questions[0]
        assert q.progress_style == "report"
        assert q.progress_items is not None and len(q.progress_items) == 3

    def test_style_value_must_be_report(self) -> None:
        with pytest.raises(FormValidationError, match="'progress_style' must be 'report'"):
            form_from_dict(_report(progress_style="fancy"))

    def test_style_only_valid_on_progress(self) -> None:
        bad = {
            "title": "x",
            "fields": [
                {
                    "id": "a",
                    "text": "t",
                    "type": "single_select",
                    "options": ["A"],
                    "progress_style": "report",
                }
            ],
        }
        with pytest.raises(FormValidationError, match="only valid on progress"):
            form_from_dict(bad)

    def test_free_form_status_accepted(self) -> None:
        # "project context" / "reference" are not task statuses — report
        # style accepts any non-empty tag.
        form = form_from_dict(_report())
        assert form.questions[0].progress_items[2]["status"] == "reference"

    def test_status_must_be_non_empty_in_report_style(self) -> None:
        bad = [{"label": "X", "status": ""}]
        with pytest.raises(FormValidationError, match="non-empty tag string"):
            form_from_dict(_report(options=[], progress_items=bad))

    def test_options_may_be_subset_of_labels(self) -> None:
        # Only one of three items pickable — invalid in task style, fine here.
        form = form_from_dict(_report(options=["Goal framing"]))
        assert form.questions[0].options == ["Goal framing"]

    def test_options_must_be_item_labels(self) -> None:
        with pytest.raises(FormValidationError, match="options must be item labels"):
            form_from_dict(_report(options=["Ghost node"]))

    def test_task_style_unchanged_by_default(self) -> None:
        # Without progress_style, the original invariants still enforce.
        task = {
            "title": "x",
            "fields": [
                {
                    "id": "a",
                    "text": "t",
                    "type": "progress",
                    "options": ["B"],
                    "progress_items": [{"label": "B", "status": "held"}],
                }
            ],
        }
        with pytest.raises(FormValidationError, match="'status' must be one of"):
            form_from_dict(task)


class TestReportStyleAnswer:
    def test_collect_accepts_picked_option(self) -> None:
        form = form_from_dict(_report())
        resp = collect_form_response(form, {"digest": "Goal framing"})
        assert resp.responses == {"digest": "Goal framing"}

    def test_collect_rejects_non_option_item(self) -> None:
        # "Recall benchmarks" is displayed but not in options.
        form = form_from_dict(_report(options=["Goal framing"]))
        with pytest.raises(FormValidationError, match="not in options"):
            collect_form_response(form, {"digest": "Recall benchmarks"})

    def test_optional_report_needs_no_answer(self) -> None:
        form = form_from_dict(_report())
        resp = collect_form_response(form, {})
        assert resp.responses == {}

    def test_fallback_maps_to_single_select(self) -> None:
        payload = form_to_askuserquestion(form_from_dict(_report()))[0][0]
        assert payload["type"] == "single_select"
        assert payload["options"] == ["Memory architecture", "Goal framing"]


class TestReportStyleWidget:
    def test_pickable_items_render_as_tagged_cards(self) -> None:
        html = form_to_widget_html(form_from_dict(_report()))
        assert "Pick one to go deeper:" in html
        assert 'role="radiogroup"' in html
        assert html.count('class="ae-prog-tag"') == 3  # every item tagged
        assert "project context" in html
        assert html.count('type="radio"') == 2  # only options pickable

    def test_non_option_items_render_as_rows(self) -> None:
        html = form_to_widget_html(form_from_dict(_report()))
        assert 'class="ae-prog-row ae-prog-report"' in html
        assert "Recall benchmarks" in html

    def test_no_task_semantics(self) -> None:
        html = form_to_widget_html(form_from_dict(_report()))
        # No strikethrough bucket rows rendered, no blocked header. (The
        # static CSS block always carries the task-style classes.)
        assert 'class="ae-prog-row ae-prog-done"' not in html
        assert "Blocked — pick one to tackle:" not in html

    def test_display_only_report(self) -> None:
        html = form_to_widget_html(form_from_dict(_report(options=[])))
        assert "radiogroup" not in html
        assert html.count('class="ae-prog-row ae-prog-report"') == 3

    def test_recommended_badge_and_order(self) -> None:
        html = form_to_widget_html(form_from_dict(_report(recommended="Goal framing")))
        assert "suggested next" in html
        assert html.index('value="Goal framing"') < html.index('value="Memory architecture"')

    def test_escapes_tag_and_detail(self) -> None:
        items = [{"label": "A", "status": "t & <b>", "detail": "d & <i>"}]
        html = form_to_widget_html(form_from_dict(_report(options=["A"], progress_items=items)))
        assert "t &amp; &lt;b&gt;" in html
        assert "d &amp; &lt;i&gt;" in html
        assert "<b>" not in html
