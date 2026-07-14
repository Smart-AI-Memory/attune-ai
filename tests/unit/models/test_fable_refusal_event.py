"""Tests for the ``fable_refusal`` telemetry event helper (task 8).

``log_fable_refusal`` is the one place the fable-refusal event shape
lives: an LLMCallRecord with ``task_type="fable_refusal"`` carrying the
refusal category/explanation in metadata (feeds the batch Option B
revisit — docs/specs/fable-premium-tier design §5). Best-effort by
contract: it must never raise.
"""

from unittest.mock import patch

from attune.model_tiers import ModelRefusalError
from attune.models.telemetry import log_fable_refusal


class TestLogFableRefusal:
    def test_writes_llm_call_record_with_event_shape(self):
        err = ModelRefusalError("nope", category="safety", explanation="why")
        with patch("attune.models.telemetry.log_llm_call") as mock_log:
            log_fable_refusal(err, workflow="wf", model="claude-fable-5")

        record = mock_log.call_args.args[0]
        assert record.task_type == "fable_refusal"
        assert record.error_type == "fable_refusal"
        assert record.error_message == "nope"
        assert record.workflow_name == "wf"
        assert record.model_id == "claude-fable-5"
        assert record.tier == "premium"
        assert record.success is False
        assert record.metadata == {"category": "safety", "explanation": "why"}

    def test_defaults_when_workflow_and_model_unknown(self):
        err = ModelRefusalError("nope")
        with patch("attune.models.telemetry.log_llm_call") as mock_log:
            log_fable_refusal(err)

        record = mock_log.call_args.args[0]
        assert record.workflow_name is None
        assert record.model_id == ""
        assert record.metadata == {"category": None, "explanation": None}

    def test_never_raises_when_store_fails(self):
        err = ModelRefusalError("nope")
        with patch(
            "attune.models.telemetry.log_llm_call",
            side_effect=OSError("disk full"),
        ):
            log_fable_refusal(err)  # must not raise
