"""bug-predict must hand the adapter findings it can turn into sections.

Root cause of the 6/6 scored-but-sectionless runs (census 2026-08-22,
marked by the #2191 callout): bug-predict was the only subagent
workflow NOT passing ``output_format=WORKFLOW_OUTPUT_SCHEMA``, so the
adapter parsed its markdown — and its prompt asks for ``## Bugs``
"organized by severity", which the agent renders as ``### HIGH`` /
``### MEDIUM`` sub-headers. The parser treated every ``##``-prefixed
line as a category terminator, so ``## Bugs`` opened the category,
``### HIGH`` closed it, and every bullet beneath was dropped:
``{"bugs": []}`` — truthy enough to build a report, empty enough to
have no sections, scored because ``## Summary`` parsed fine.

Two layers are pinned here, because either alone leaves the class
open: the workflow requests structured output (the path code-review
already used), and the text parser keeps sub-headers inside their
category for any workflow still on the markdown path.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import claude_agent_sdk

from attune.workflows.agent_sdk_adapter import AgentRunResult, AgentSDKResultAdapter
from attune.workflows.bug_predict import BugPredictionWorkflow
from attune.workflows.output_schemas import WORKFLOW_OUTPUT_SCHEMA

# The markdown shape a live bug-predict agent emits for its prompt.
_SEVERITY_GROUPED_REPORT = """\
## Summary
**Overall Risk Score: 60 / 100 (Moderate)**

Risk is concentrated in a few I/O hubs.

## Bugs
### HIGH
- `src/attune/ops/data.py:42` — resource leak: file handle never closed
### MEDIUM
- `src/attune/cli.py:88` — unchecked `int()` on user input

## Suggestions
- Add a context manager around the handle in ops/data.py
"""


def _callouts(report):
    return [s for s in report["sections"] if s.get("kind") == "callout"]


class TestTextParserKeepsSubHeadersInsideCategory:
    def test_severity_sub_headers_do_not_drop_the_bullets(self) -> None:
        findings = AgentSDKResultAdapter._parse_findings(_SEVERITY_GROUPED_REPORT)

        assert len(findings["bugs"]) == 2
        assert "resource leak" in findings["bugs"][0]
        assert "int()" in findings["bugs"][1]

    def test_h2_header_still_ends_the_category(self) -> None:
        """Only h3+ nests; the next ``##`` still closes the category."""
        findings = AgentSDKResultAdapter._parse_findings(_SEVERITY_GROUPED_REPORT)

        # The "Add a context manager" bullet lives under ## Suggestions,
        # which is not a findings category — it must not leak into bugs.
        assert not any("context manager" in item for item in findings["bugs"])

    def test_the_recorded_defect_shape_no_longer_reproduces(self) -> None:
        """Scored + empty-sections was the census signature; it must be gone."""
        started = datetime(2026, 8, 22, 12, 0, 0)
        result = AgentSDKResultAdapter.from_agent_output(
            report_title="Bug prediction",
            result_text=_SEVERITY_GROUPED_REPORT,
            subagent_names=["pattern-scanner"],
            started_at=started,
            completed_at=started + timedelta(seconds=5),
        )

        report = result.final_output
        assert isinstance(report, dict), "findings parsed → report dict"
        assert report["score"] == 60
        assert report["sections"], "a scored report must carry sections"
        assert not _callouts(report), "the #2191 defect marker must not fire"


class TestBugPredictRequestsStructuredOutput:
    @patch("attune.workflows.bug_predict.claude_agent_sdk.query")
    def test_output_format_is_the_shared_workflow_schema(self, mock_query) -> None:
        """Same structured path code-review and security-audit already use."""
        captured: dict = {}

        async def capturing_query(*args, **kwargs):
            captured["options"] = kwargs.get("options")
            result = claude_agent_sdk.ResultMessage(
                subtype="success",
                duration_ms=1,
                duration_api_ms=1,
                is_error=False,
                num_turns=1,
                session_id="s",
                total_cost_usd=0.0,
                usage={},
                result="done",
                structured_output=None,
            )
            yield result

        mock_query.side_effect = capturing_query
        asyncio.run(BugPredictionWorkflow()._run_agent_predict("/tmp/proj", 20, "standard"))

        assert captured["options"].output_format is WORKFLOW_OUTPUT_SCHEMA

    def test_structured_bugs_become_a_findings_section(self) -> None:
        """The shape the schema yields renders as a FindingsSection."""
        started = datetime(2026, 8, 22, 12, 0, 0)
        run = AgentRunResult(
            result_text="ignored when structured output is present",
            structured_output={
                "summary": {"score": 60, "text": "Risk is concentrated."},
                "findings": {
                    "bugs": [
                        {
                            "file": "src/attune/ops/data.py",
                            "line": 42,
                            "severity": "HIGH",
                            "description": "resource leak",
                        }
                    ]
                },
                "suggestions": [{"description": "close the handle", "priority": "high"}],
            },
        )
        result = AgentSDKResultAdapter.from_agent_output(
            report_title="Bug prediction",
            result_text=run.result_text,
            subagent_names=["pattern-scanner"],
            started_at=started,
            completed_at=started + timedelta(seconds=5),
            agent_run_result=run,
        )

        report = result.final_output
        assert isinstance(report, dict)
        assert report["score"] == 60
        kinds = [s.get("kind") for s in report["sections"]]
        assert "findings" in kinds
        assert not _callouts(report)
        assert result.suggestions and "close the handle" in result.suggestions[0].description
