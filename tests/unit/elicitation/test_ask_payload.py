"""Host-local AskUserQuestion conventions, applied by construction.

The two rules under test are enforced by a user-level hook
(``ask_question_format_guard``), not by ``attune-forms`` — so nothing in
the shared package can apply them and every caller had to remember both.
On 2026-08-22 a single form cost two consecutive guard rejections, which
is the friction this adapter removes.

The receipt that matters is :class:`TestAgainstTheRealGuard`: the
adapter's output is fed to the ACTUAL hook. Unit tests prove the shape;
only the real script proves the shape is the one the guard wants.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from attune.elicitation import form_from_dict
from attune.elicitation.ask_payload import (
    RECOMMENDED_SUFFIX,
    form_to_ask_payload,
    mark_recommended,
)

GUARD = Path.home() / ".claude" / "hooks" / "ask_question_format_guard.py"


def _form(n_questions: int = 2, n_options: int = 3):
    return form_from_dict(
        {
            "title": "t",
            "fields": [
                {
                    "id": f"q{i}",
                    "type": "single_select" if i else "multi_select",
                    "label": f"Question {i} text?",
                    "options": [f"opt{i}-{j}" for j in range(n_options)],
                }
                for i in range(n_questions)
            ],
        }
    )


class TestTheTwoGuardRules:
    def test_multi_question_batch_opts_in_via_metadata_source(self):
        payload = form_to_ask_payload(_form(2))[0]

        assert (
            "form" in payload["metadata"]["source"]
        ), "a batch of >1 question is blocked by default without this"
        assert len(payload["questions"]) == 2

    def test_first_option_carries_the_recommendation_marker(self):
        payload = form_to_ask_payload(_form(1))[0]
        labels = [o["label"] for o in payload["questions"][0]["options"]]

        assert labels[0].endswith(RECOMMENDED_SUFFIX)
        assert not any(
            x.endswith(RECOMMENDED_SUFFIX) for x in labels[1:]
        ), "exactly one option may claim the recommendation"

    def test_ordering_is_never_changed_only_labelled(self):
        """First-is-recommended means the CALLER's order is the answer."""
        form = _form(1, n_options=3)
        payload = form_to_ask_payload(form)[0]
        labels = [o["label"] for o in payload["questions"][0]["options"]]

        assert labels[0].startswith("opt0-0")
        assert labels[1] == "opt0-1" and labels[2] == "opt0-2"

    def test_a_source_that_would_be_rejected_fails_here_instead(self):
        """Fail at build time, not at a wasted tool call."""
        with pytest.raises(ValueError, match="does not contain 'form'"):
            form_to_ask_payload(_form(2), source="manual")

    def test_marker_is_not_doubled_when_already_present(self):
        assert mark_recommended(f"x {RECOMMENDED_SUFFIX}") == f"x {RECOMMENDED_SUFFIX}"
        assert mark_recommended("x") == f"x {RECOMMENDED_SUFFIX}"


class TestPayloadShape:
    def test_multi_select_flag_tracks_the_field_type(self):
        payload = form_to_ask_payload(_form(2))[0]
        by_header = {q["question"]: q["multiSelect"] for q in payload["questions"]}

        assert by_header["Question 0 text?"] is True  # multi_select
        assert by_header["Question 1 text?"] is False  # single_select

    def test_header_fits_the_chip_budget(self):
        payload = form_to_ask_payload(_form(2))[0]

        for q in payload["questions"]:
            assert 0 < len(q["header"]) <= 12, q["header"]

    def test_descriptions_are_passed_through_never_invented(self):
        payload = form_to_ask_payload(_form(1), descriptions={"opt0-1": "why"})[0]
        options = {
            o["label"].replace(f" {RECOMMENDED_SUFFIX}", ""): o["description"]
            for o in payload["questions"][0]["options"]
        }

        assert options["opt0-1"] == "why"
        assert options["opt0-2"] == "", "unmapped options must not get invented prose"


@pytest.mark.skipif(not GUARD.exists(), reason="user-level hook not on this machine")
class TestAgainstTheRealGuard:
    """The receipt: the actual hook accepts what the adapter emits.

    Machine-local by design — the guard is personal infra outside this
    repo, so this class runs where it exists and skips elsewhere (CI
    included), matching the session-hydrate fail-open test's pattern.
    """

    def _run(self, tool_input: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(GUARD)],
            input=json.dumps({"tool_name": "AskUserQuestion", "tool_input": tool_input}),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_adapter_output_passes_the_guard_first_try(self):
        payload = form_to_ask_payload(_form(2))[0]

        result = self._run(payload)

        assert result.returncode == 0, result.stderr

    def test_the_guard_still_rejects_a_hand_written_batch(self):
        """Proves the test above is not vacuous — the guard does bite."""
        hand_written = {
            "questions": [
                {
                    "question": "a?",
                    "header": "a",
                    "multiSelect": False,
                    "options": [{"label": "one", "description": ""}],
                },
                {
                    "question": "b?",
                    "header": "b",
                    "multiSelect": False,
                    "options": [{"label": "two", "description": ""}],
                },
            ]
        }

        result = self._run(hand_written)

        assert result.returncode == 2, "guard should block an un-opted-in batch"
