"""Tests for the resolution-complexity classifier.

Each trigger gets a positive fixture (must fire → needs_patrick)
and a negative fixture (must not fire → routine).
"""

from __future__ import annotations

from typing import Any

import pytest

from attune.workflows.discovery_sweep import (
    Finding,
    ResolutionComplexity,
    Severity,
    VerificationStatus,
)
from attune.workflows.discovery_sweep.complexity import (
    ComplexityClassifier,
    ContradictsLessonTrigger,
    CrossCuttingTrigger,
    LowConfidenceTrigger,
    MocksProductionTrigger,
    SecurityAdjacentTrigger,
    TierOrBudgetTrigger,
)


def _make_accepted_finding(
    *,
    file_path: str = "src/attune/example.py",
    message: str = "example",
    verification_reasoning: str = "",
    raw_finding: dict[str, Any] | None = None,
) -> Finding:
    return Finding(
        source_workflow="bug_predict",
        file_path=file_path,
        severity=Severity.MEDIUM,
        message=message,
        raw_finding=raw_finding if raw_finding is not None else {"pattern": "x"},
        sweep_id="sweep1234abcd",
        line=10,
        verification_status=VerificationStatus.ACCEPT,
        verification_reasoning=verification_reasoning,
    )


# ---------------------------------------------------------------------------
# CrossCuttingTrigger
# ---------------------------------------------------------------------------


class TestCrossCuttingTrigger:
    trigger = CrossCuttingTrigger()

    def test_fires_on_three_or_more_paths(self):
        finding = _make_accepted_finding(
            message=(
                "fix would also touch src/attune/a.py, src/attune/b.py and " "src/attune/c.py"
            ),
        )
        assert self.trigger.applies(finding)

    def test_fires_on_public_api_mention(self):
        finding = _make_accepted_finding(
            message="changes the public API of attune.workflows.base",
        )
        assert self.trigger.applies(finding)

    def test_fires_on_base_class_mention(self):
        finding = _make_accepted_finding(
            message="modifies a shared base class signature",
        )
        assert self.trigger.applies(finding)

    def test_does_not_fire_on_single_file_finding(self):
        finding = _make_accepted_finding(
            message="local refactor inside src/attune/example.py only",
        )
        assert not self.trigger.applies(finding)

    def test_does_not_count_self_path(self):
        finding = _make_accepted_finding(
            file_path="src/attune/example.py",
            message="finding in src/attune/example.py — minor cleanup",
        )
        assert not self.trigger.applies(finding)


# ---------------------------------------------------------------------------
# SecurityAdjacentTrigger
# ---------------------------------------------------------------------------


class TestSecurityAdjacentTrigger:
    trigger = SecurityAdjacentTrigger()

    def test_fires_on_security_path(self):
        finding = _make_accepted_finding(
            file_path="src/attune/security/path_validation.py",
            message="minor cleanup",
        )
        assert self.trigger.applies(finding)

    def test_fires_on_eval_keyword(self):
        finding = _make_accepted_finding(
            file_path="src/attune/util.py",
            message="dangerous eval( pattern detected",
        )
        assert self.trigger.applies(finding)

    def test_fires_on_webhook_keyword(self):
        finding = _make_accepted_finding(
            file_path="src/attune/monitoring/validators.py",
            message="webhook URL validation missing",
        )
        assert self.trigger.applies(finding)

    def test_does_not_fire_on_unrelated(self):
        finding = _make_accepted_finding(
            file_path="src/attune/formatter.py",
            message="style: prefer f-strings",
        )
        assert not self.trigger.applies(finding)


# ---------------------------------------------------------------------------
# ContradictsLessonTrigger
# ---------------------------------------------------------------------------


class TestContradictsLessonTrigger:
    trigger = ContradictsLessonTrigger()

    def test_fires_on_dirs_slice_mention(self):
        finding = _make_accepted_finding(message="found dirs[:] pattern that could be simplified")
        assert self.trigger.applies(finding)

    def test_fires_on_subprocess_exec(self):
        finding = _make_accepted_finding(message="create_subprocess_exec usage should be audited")
        assert self.trigger.applies(finding)

    def test_fires_on_structlog_kwargs(self):
        finding = _make_accepted_finding(
            message="logger.info with kwargs — verify structlog binding"
        )
        assert self.trigger.applies(finding)

    def test_does_not_fire_on_unrelated(self):
        finding = _make_accepted_finding(message="missing docstring on public function")
        assert not self.trigger.applies(finding)


# ---------------------------------------------------------------------------
# TierOrBudgetTrigger
# ---------------------------------------------------------------------------


class TestTierOrBudgetTrigger:
    trigger = TierOrBudgetTrigger()

    def test_fires_on_model_tier(self):
        finding = _make_accepted_finding(message="ModelTier.CHEAP mapping should be reconsidered")
        assert self.trigger.applies(finding)

    def test_fires_on_budget_cap(self):
        finding = _make_accepted_finding(
            message="budget cap may be too tight for premium workflows"
        )
        assert self.trigger.applies(finding)

    def test_fires_on_cost_model(self):
        finding = _make_accepted_finding(message="finding affects the cost model assumptions")
        assert self.trigger.applies(finding)

    def test_does_not_fire_on_unrelated(self):
        finding = _make_accepted_finding(message="rename variable for clarity")
        assert not self.trigger.applies(finding)


# ---------------------------------------------------------------------------
# MocksProductionTrigger
# ---------------------------------------------------------------------------


class TestMocksProductionTrigger:
    trigger = MocksProductionTrigger()

    def test_fires_when_test_file_mocks_production(self):
        finding = _make_accepted_finding(
            file_path="tests/unit/test_pipeline.py",
            message="mock could replace src/attune/pipeline.py call to real DB",
        )
        assert self.trigger.applies(finding)

    def test_does_not_fire_in_production_path(self):
        finding = _make_accepted_finding(
            file_path="src/attune/pipeline.py",
            message="mock attune.example.Client to skip real API",
        )
        assert not self.trigger.applies(finding)

    def test_does_not_fire_when_no_production_hint(self):
        finding = _make_accepted_finding(
            file_path="tests/unit/test_pipeline.py",
            message="mock is named ambiguously — rename",
        )
        assert not self.trigger.applies(finding)


# ---------------------------------------------------------------------------
# LowConfidenceTrigger
# ---------------------------------------------------------------------------


class TestLowConfidenceTrigger:
    trigger = LowConfidenceTrigger()

    def test_fires_on_ambiguous(self):
        finding = _make_accepted_finding(
            verification_reasoning="rule fired but ambiguous match",
        )
        assert self.trigger.applies(finding)

    def test_fires_on_could_not_determine(self):
        finding = _make_accepted_finding(
            verification_reasoning="could not determine whether the input is reachable",
        )
        assert self.trigger.applies(finding)

    def test_does_not_fire_on_confident(self):
        finding = _make_accepted_finding(
            verification_reasoning="matches eval(user_input) pattern with no test surroundings",
        )
        assert not self.trigger.applies(finding)


# ---------------------------------------------------------------------------
# Classifier integration
# ---------------------------------------------------------------------------


class TestComplexityClassifier:
    def test_default_for_accepted_finding_is_routine(self):
        finding = _make_accepted_finding(
            file_path="src/attune/util.py",
            message="rename variable",
        )
        classified = ComplexityClassifier().classify(finding)
        assert classified.resolution_complexity == ResolutionComplexity.ROUTINE

    def test_security_path_flips_to_needs_patrick(self):
        finding = _make_accepted_finding(
            file_path="src/attune/security/path_validation.py",
            message="cleanup",
        )
        classified = ComplexityClassifier().classify(finding)
        assert classified.resolution_complexity == ResolutionComplexity.NEEDS_PATRICK
        assert "security_adjacent" in classified.verification_reasoning

    def test_unsure_finding_left_alone(self):
        finding = Finding(
            source_workflow="bug_predict",
            file_path="src/attune/util.py",
            severity=Severity.MEDIUM,
            message="x",
            raw_finding={},
            sweep_id="x",
            line=1,
            verification_status=VerificationStatus.UNSURE,
            verification_reasoning="r",
        )
        classified = ComplexityClassifier().classify(finding)
        assert classified.resolution_complexity is None

    def test_rejected_finding_left_alone(self):
        finding = Finding(
            source_workflow="bug_predict",
            file_path="src/attune/util.py",
            severity=Severity.MEDIUM,
            message="x",
            raw_finding={},
            sweep_id="x",
            line=1,
            verification_status=VerificationStatus.REJECT,
            verification_reasoning="known false positive",
        )
        classified = ComplexityClassifier().classify(finding)
        assert classified.resolution_complexity is None

    def test_multiple_triggers_concatenated_in_reasoning(self):
        finding = _make_accepted_finding(
            file_path="src/attune/security/x.py",
            message="dirs[:] in a webhook handler",
        )
        classified = ComplexityClassifier().classify(finding)
        assert classified.resolution_complexity == ResolutionComplexity.NEEDS_PATRICK
        reasoning = classified.verification_reasoning
        assert "security_adjacent" in reasoning
        assert "contradicts_lesson" in reasoning

    def test_classify_many(self):
        routine = _make_accepted_finding(file_path="src/attune/util.py", message="rename")
        sensitive = _make_accepted_finding(
            file_path="src/attune/security/path_validation.py", message="cleanup"
        )
        out = ComplexityClassifier().classify_many([routine, sensitive])
        assert out[0].resolution_complexity == ResolutionComplexity.ROUTINE
        assert out[1].resolution_complexity == ResolutionComplexity.NEEDS_PATRICK


@pytest.mark.parametrize(
    "trigger_cls",
    [
        CrossCuttingTrigger,
        SecurityAdjacentTrigger,
        ContradictsLessonTrigger,
        TierOrBudgetTrigger,
        MocksProductionTrigger,
        LowConfidenceTrigger,
    ],
)
def test_trigger_name_is_str(trigger_cls):
    trigger = trigger_cls()
    assert isinstance(trigger.name, str)
    assert trigger.name
