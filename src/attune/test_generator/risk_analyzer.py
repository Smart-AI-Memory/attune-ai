"""Risk analyzer for test generation.

Analyzes workflow patterns to identify critical paths and determine
appropriate test coverage levels.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from dataclasses import dataclass, field

from patterns import get_pattern_registry
from patterns.behavior import PredictionPattern, RiskAssessmentPattern
from patterns.structural import PhasedProcessingPattern
from patterns.validation import ApprovalPattern, StepValidationPattern

logger = logging.getLogger(__name__)


@dataclass
class RiskAnalysis:
    """Risk analysis results for a workflow."""

    workflow_id: str
    pattern_ids: list[str]
    critical_paths: list[str] = field(default_factory=list)
    high_risk_inputs: list[str] = field(default_factory=list)
    validation_points: list[str] = field(default_factory=list)
    recommended_coverage: int = 80  # Percentage
    test_priorities: dict[str, int] = field(default_factory=dict)  # test_name -> priority (1-5)

    def get_critical_test_cases(self) -> list[str]:
        """Get list of critical test case names.

        Returns:
            List of critical test cases to implement

        """
        test_cases = []

        # Critical paths become test cases
        for path in self.critical_paths:
            test_case = f"test_{path.lower().replace(' ', '_').replace('-', '_')}"
            test_cases.append(test_case)

        # High-risk inputs become test cases
        for input_risk in self.high_risk_inputs:
            test_case = f"test_{input_risk.lower().replace(' ', '_')}_validation"
            test_cases.append(test_case)

        return test_cases

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "pattern_ids": self.pattern_ids,
            "critical_paths": self.critical_paths,
            "high_risk_inputs": self.high_risk_inputs,
            "validation_points": self.validation_points,
            "recommended_coverage": self.recommended_coverage,
            "test_priorities": self.test_priorities,
        }


class RiskAnalyzer:
    """Analyzes workflow patterns to determine testing requirements.

    Uses pattern analysis to identify:
    - Critical execution paths
    - High-risk input scenarios
    - Required validation points
    - Recommended test coverage level
    """

    def __init__(self):
        """Initialize risk analyzer."""
        self.registry = get_pattern_registry()

    def analyze(self, workflow_id: str, pattern_ids: list[str]) -> RiskAnalysis:
        """Analyze workflow patterns for risk.

        Args:
            workflow_id: Workflow identifier
            pattern_ids: List of pattern IDs used by workflow

        Returns:
            RiskAnalysis with recommendations

        """
        logger.info(f"Analyzing risk for workflow: {workflow_id}")

        analysis = RiskAnalysis(
            workflow_id=workflow_id,
            pattern_ids=pattern_ids,
        )

        # Analyze each pattern
        for pattern_id in pattern_ids:
            pattern = self.registry.get(pattern_id)
            if not pattern:
                logger.warning(f"Pattern not found: {pattern_id}")
                continue

            self._analyze_pattern(pattern, analysis)

        # Calculate recommended coverage based on risk
        self._calculate_coverage(analysis)

        # Prioritize tests
        self._prioritize_tests(analysis)

        logger.info(
            f"Risk analysis complete: {len(analysis.critical_paths)} critical paths, "
            f"{analysis.recommended_coverage}% coverage recommended",
        )

        return analysis

    def _analyze_pattern(self, pattern, analysis: RiskAnalysis) -> None:
        """Analyze a specific pattern for risks.

        Args:
            pattern: Pattern to analyze
            analysis: RiskAnalysis to update

        """
        # Approval patterns are CRITICAL - must test preview → approval flow
        if isinstance(pattern, ApprovalPattern):
            analysis.critical_paths.append("approval_workflow")
            analysis.high_risk_inputs.append("save_without_preview")
            analysis.high_risk_inputs.append("save_without_approval")
            analysis.validation_points.append("preview_generated")
            analysis.validation_points.append("user_approved")

        # Step validation patterns - test step sequencing
        elif isinstance(pattern, StepValidationPattern):
            analysis.critical_paths.append("step_sequence_validation")
            analysis.high_risk_inputs.append("skip_step")
            analysis.high_risk_inputs.append("wrong_step_number")
            analysis.validation_points.append("current_step")

        # Phased processing - each phase is a critical path
        elif isinstance(pattern, PhasedProcessingPattern):
            for phase in pattern.phases:
                analysis.critical_paths.append(f"phase_{phase.name}")
                if phase.required:
                    analysis.validation_points.append(f"{phase.name}_completed")

        # Risk assessment patterns - test risk detection
        elif isinstance(pattern, RiskAssessmentPattern):
            analysis.critical_paths.append("risk_assessment")
            analysis.validation_points.append("alert_level")
            for level in pattern.risk_levels:
                analysis.high_risk_inputs.append(f"{level.name}_threshold")

        # Prediction patterns - test predictions
        elif isinstance(pattern, PredictionPattern):
            analysis.critical_paths.append("prediction_generation")
            for pred_type in pattern.prediction_types:
                analysis.validation_points.append(pred_type)

    def _calculate_coverage(self, analysis: RiskAnalysis) -> None:
        """Calculate recommended test coverage.

        Args:
            analysis: RiskAnalysis to update

        """
        # Base coverage
        base_coverage = 70

        # Add 5% for each critical path
        critical_bonus = min(20, len(analysis.critical_paths) * 5)

        # Add 3% for each validation point
        validation_bonus = min(10, len(analysis.validation_points) * 3)

        # Cap at 95%
        analysis.recommended_coverage = min(
            95,
            base_coverage + critical_bonus + validation_bonus,
        )

    def _prioritize_tests(self, analysis: RiskAnalysis) -> None:
        """Assign priorities to test cases.

        Args:
            analysis: RiskAnalysis to update

        """
        # Priority levels: 1 (critical) to 5 (nice-to-have)

        # Critical paths = Priority 1
        for path in analysis.critical_paths:
            test_name = f"test_{path}"
            analysis.test_priorities[test_name] = 1

        # High-risk inputs = Priority 2
        for input_risk in analysis.high_risk_inputs:
            test_name = f"test_{input_risk}_validation"
            analysis.test_priorities[test_name] = 2

        # Validation points = Priority 3
        for validation in analysis.validation_points:
            test_name = f"test_{validation}"
            if test_name not in analysis.test_priorities:
                analysis.test_priorities[test_name] = 3

        # Success path = Priority 4
        analysis.test_priorities["test_success_path"] = 4
        analysis.test_priorities["test_happy_path"] = 4

        # Edge cases = Priority 5
        analysis.test_priorities["test_edge_cases"] = 5
