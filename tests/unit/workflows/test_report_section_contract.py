"""Report section-contract tests for the SDK-native workflows.

Regression cover for the 2026-08-21 defect: ``bug-predict`` rendered
only ``## Summary`` — no ``## Bugs``, no ``## Suggestions`` — and
exited 0 while doing so. Four run records on disk showed
``sections: []`` with a populated summary, so the report the user saw
named no file and no line number.

Two independent faults produced it, and both are covered here:

1. **The parser accepted one markdown dialect.** Items were collected
   only from flat ``-``/``*`` bullets sitting directly under an ``##``
   header. The prompt asks for bugs "organized by severity (HIGH,
   MEDIUM, LOW)" and suggestions "ordered by priority", which the model
   renders as ``###`` sub-headings, numbered lists, or tables — every
   one of which parsed to nothing.
2. **A contract violation reported success.** Nothing compared the
   synthesized report against the sections its own prompt mandates.

These drive the REAL workflow and the REAL adapter. A test that mocks
the renderer cannot see either fault (class-M ruling: exercise the
real boundary).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import claude_agent_sdk
import pytest

from attune.workflows.agent_sdk_adapter import (
    AgentSDKResultAdapter,
    required_sections_from_prompt,
)
from attune.workflows.bug_predict import _TASK_PROMPT_TEMPLATE, BugPredictionWorkflow


def _result_message(text: str) -> claude_agent_sdk.ResultMessage:
    """A real, cleanly-successful ResultMessage carrying ``text``."""
    return claude_agent_sdk.ResultMessage(
        subtype="success",
        duration_ms=1000,
        duration_api_ms=900,
        is_error=False,
        num_turns=3,
        session_id="sess-contract",
        total_cost_usd=0.5,
        usage={"input_tokens": 100, "output_tokens": 100},
        result=text,
        structured_output=None,
    )


def _run(text: str):
    """Run the real bug-predict workflow over a synthesized report."""

    async def fake_query(*args, **kwargs):
        yield _result_message(text)

    with patch("attune.workflows.bug_predict.claude_agent_sdk.query", side_effect=fake_query):
        return asyncio.run(BugPredictionWorkflow().execute(path="/tmp/proj"))


# The exact shape observed on 2026-08-21 and in four archived runs.
SUMMARY_ONLY = (
    "## Summary\n"
    "Overall risk score: 42/100. The single highest-value fix is the "
    "non-atomic distributed unlock.\n"
)

SEVERITY_GROUPED = (
    "## Summary\n"
    "Overall risk score: 42/100.\n\n"
    "## Bugs\n\n"
    "### HIGH\n"
    "- `cross_session/coordinator.py:384` — TOCTOU in distributed unlock\n"
    "- `store.py:120` — unbounded read\n\n"
    "### MEDIUM\n"
    "- `index.py:44` — off-by-one\n\n"
    "## Suggestions\n\n"
    "### Priority 1\n"
    "- Make the unlock atomic with a Lua script\n"
)


@pytest.mark.unit
class TestSummaryOnlyIsNotSuccess:
    """A report missing its declared sections is a FAILED run."""

    def test_summary_only_synthesis_does_not_report_success(self) -> None:
        """The original defect: three sections promised, one delivered."""
        result = _run(SUMMARY_ONLY)

        assert result.success is False
        assert result.error is not None
        assert "Bugs" in result.error
        assert "Suggestions" in result.error

    def test_summary_only_keeps_the_agent_text_for_the_user(self) -> None:
        """Failing the run must not also swallow what the agent DID say."""
        result = _run(SUMMARY_ONLY)

        assert "non-atomic distributed unlock" in result.metadata["raw_result_text"]

    def test_contract_error_recorded_in_metadata(self) -> None:
        """The dashboard needs the reason, not just a red chip."""
        result = _run(SUMMARY_ONLY)

        assert "never emitted" in result.metadata["section_contract_error"]


@pytest.mark.unit
class TestDeclaredSectionsSurviveParsing:
    """The dialects the prompt actually elicits must reach the report."""

    def test_severity_grouped_bugs_reach_the_report(self) -> None:
        """``### HIGH`` sub-headings used to zero out the whole section."""
        result = _run(SEVERITY_GROUPED)

        assert result.success is True
        titles = [s["title"] for s in result.final_output["sections"]]
        assert titles == ["Bugs", "Next steps"]

    def test_file_and_line_survive(self) -> None:
        """A finding with no location is not actionable — that was the cost."""
        result = _run(SEVERITY_GROUPED)

        items = result.final_output["sections"][0]["items"]
        assert any("coordinator.py:384" in item for item in items)
        assert len(items) == 3

    def test_severity_label_is_preserved_from_the_subheading(self) -> None:
        """Flattening must not discard which group a finding came from."""
        result = _run(SEVERITY_GROUPED)

        items = result.final_output["sections"][0]["items"]
        assert items[0].startswith("HIGH — ")
        assert items[2].startswith("MEDIUM — ")

    def test_numbered_suggestions_are_extracted(self) -> None:
        """ "Ordered by priority" is what the prompt asks for."""
        text = SUMMARY_ONLY.replace(
            "## Summary",
            "## Bugs\n- a.py:1 boom\n\n## Suggestions\n1. Make it atomic\n2. Add a test\n\n## Summary",
        )
        result = _run(text)

        assert result.success is True
        assert [s.description for s in result.suggestions] == [
            "Make it atomic",
            "Add a test",
        ]

    def test_table_rows_are_extracted(self) -> None:
        """A severity table is a natural rendering of "organized by severity"."""
        text = (
            "## Summary\nx\n\n"
            "## Bugs\n\n"
            "| Severity | Location | Issue |\n"
            "|---|---|---|\n"
            "| HIGH | a.py:1 | boom |\n"
            "| LOW | b.py:9 | meh |\n\n"
            "## Suggestions\n- fix it\n"
        )
        result = _run(text)

        assert result.success is True
        items = result.final_output["sections"][0]["items"]
        assert items == ["HIGH — a.py:1 — boom", "LOW — b.py:9 — meh"]

    def test_fenced_code_is_not_mistaken_for_findings(self) -> None:
        """Sample code inside the report must not become a bug entry."""
        text = (
            "## Summary\nx\n\n"
            "## Bugs\n- real finding at a.py:1\n\n"
            "```python\n- not a finding\n```\n\n"
            "## Suggestions\n- fix it\n"
        )
        result = _run(text)

        assert result.final_output["sections"][0]["items"] == ["real finding at a.py:1"]


@pytest.mark.unit
class TestCleanRunsStillPass:
    """The gate must not manufacture failures on healthy runs."""

    def test_empty_but_present_sections_are_a_clean_result(self) -> None:
        """ "No bugs found." honors the contract — a clean scan is success."""
        text = (
            "## Summary\nRisk 5/100.\n\n"
            "## Bugs\nNo bugs found.\n\n"
            "## Suggestions\nNothing to do.\n"
        )
        result = _run(text)

        assert result.success is True
        assert result.error is None
        # Nothing parsed, so the agent's own markdown must pass through
        # intact. Rewriting it into a sectionless report stub on a
        # matched-but-empty category ({"bugs": []} is truthy) is what
        # erased the findings in the first place.
        assert isinstance(result.final_output, str)
        assert "No bugs found." in result.final_output


@pytest.mark.unit
class TestUnparsableSectionFailsLoudly:
    """Structure we cannot parse is OUR defect and must not report green."""

    def test_list_markup_that_yields_no_items_fails(self) -> None:
        text = "## Summary\nx\n\n## Bugs\n- \n\n## Suggestions\n- fix it\n"
        result = _run(text)

        assert result.success is False
        assert "emitted but unparsable" in result.error


@pytest.mark.unit
class TestContractIsDerivedNotRestated:
    """The prompt IS the contract, so the two can never drift apart."""

    def test_required_sections_come_from_the_live_prompt_template(self) -> None:
        assert required_sections_from_prompt(_TASK_PROMPT_TEMPLATE) == (
            "Summary",
            "Bugs",
            "Suggestions",
        )

    def test_editing_the_prompt_moves_the_contract(self) -> None:
        """Add a section to a prompt and it becomes required automatically."""
        assert required_sections_from_prompt("## Alpha\nx\n\n## Beta\ny\n") == (
            "Alpha",
            "Beta",
        )

    def test_subheadings_are_not_sections(self) -> None:
        assert required_sections_from_prompt("## Alpha\n### Nested\n") == ("Alpha",)

    def test_no_required_sections_disables_the_gate(self) -> None:
        """Callers that have not opted in keep their prior behavior."""
        assert AgentSDKResultAdapter._check_section_contract(SUMMARY_ONLY, ()) is None
