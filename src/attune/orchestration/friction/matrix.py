"""Adaptive Friction Matrix Controller for Attune AI.

Maps 2D (Blast Radius, Intent Clarity) scores into 4 Friction Zones and emits execution directives.
"""

from enum import Enum
from typing import Any

from .ambiguity import AmbiguityEvaluator
from .blast_radius import BlastRadiusClassifier


class FrictionZone(str, Enum):
    """Enumeration of the 4 Adaptive Friction Zones."""

    ZONE_1_AUTONOMOUS = "zone_1_autonomous"
    ZONE_2_INFORM_PROCEED = "zone_2_inform_proceed"
    ZONE_3_PLAN_GATE = "zone_3_plan_gate"
    ZONE_4_SOCRATIC_GATE = "zone_4_socratic_gate"


class FrictionDirective(str, Enum):
    """Actionable execution directive for tool hooks and agent loops."""

    ALLOW_AUTONOMOUS = "allow_autonomous"
    INFORM_AND_PROCEED = "inform_and_proceed"
    PLAN_REVIEW_GATE = "plan_review_gate"
    SOCRATIC_GATE = "socratic_gate"


class FrictionMatrix:
    """Evaluates proposed actions against the 2D Adaptive Friction Matrix."""

    def __init__(
        self,
        classifier: BlastRadiusClassifier | None = None,
        evaluator: AmbiguityEvaluator | None = None,
    ) -> None:
        """Initialize FrictionMatrix controller.

        Args:
            classifier: Optional BlastRadiusClassifier instance.
            evaluator: Optional AmbiguityEvaluator instance.
        """
        self.classifier = classifier or BlastRadiusClassifier()
        self.evaluator = evaluator or AmbiguityEvaluator()

    def evaluate_action(
        self,
        user_prompt: str,
        target_path: str | None = None,
        command_line: str | None = None,
        is_deletion: bool = False,
    ) -> dict[str, Any]:
        """Evaluates an action and returns the friction zone and directive.

        Args:
            user_prompt: User request context.
            target_path: Optional file path target.
            command_line: Optional command line string target.
            is_deletion: Whether action is destructive file deletion.

        Returns:
            Dictionary containing blast_radius, clarity, zone, directive, and reasoning.
        """
        # Calculate Blast Radius (R)
        if command_line:
            blast_radius = self.classifier.evaluate_command(command_line)
        elif target_path:
            blast_radius = self.classifier.evaluate_file_path(target_path, is_deletion=is_deletion)
        else:
            blast_radius = 1

        # Calculate Intent Clarity (C)
        clarity = self.evaluator.evaluate_prompt(user_prompt, target_path=target_path)

        # Map to Zone
        zone, directive, reason = self._map_to_zone(blast_radius, clarity)

        return {
            "blast_radius": blast_radius,
            "clarity": clarity,
            "zone": zone.value,
            "directive": directive.value,
            "reason": reason,
        }

    def _map_to_zone(self, R: int, C: int) -> tuple[FrictionZone, FrictionDirective, str]:
        """Maps (R, C) to a Friction Zone and Directive."""
        if R <= 2 and C >= 4:
            return (
                FrictionZone.ZONE_1_AUTONOMOUS,
                FrictionDirective.ALLOW_AUTONOMOUS,
                f"Low risk (R={R}) & high clarity (C={C}): Autonomous execution permitted.",
            )
        elif R <= 2 and C <= 3:
            return (
                FrictionZone.ZONE_2_INFORM_PROCEED,
                FrictionDirective.INFORM_AND_PROCEED,
                f"Low risk (R={R}) & moderate/low clarity (C={C}): Inform user of assumption and proceed.",
            )
        elif R >= 3 and C >= 4:
            return (
                FrictionZone.ZONE_3_PLAN_GATE,
                FrictionDirective.PLAN_REVIEW_GATE,
                f"High risk (R={R}) & high clarity (C={C}): Require plan preview & probe verification receipt before execution.",
            )
        else:  # R >= 3 and C <= 3
            return (
                FrictionZone.ZONE_4_SOCRATIC_GATE,
                FrictionDirective.SOCRATIC_GATE,
                f"High risk (R={R}) & low clarity (C={C}): Hard gate. Require interactive Socratic elicitation form.",
            )
