"""Feedback Management Mixin for EmpathyOS.

Extracted from EmpathyOS to improve maintainability.
Provides feedback loop detection and trust management methods.

Expected attributes on the host class:
    feedback_detector (FeedbackLoopDetector): Feedback loop detector

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any


class FeedbackManagementMixin:
    """Mixin providing feedback loop monitoring and trust management."""

    # Expected attributes (set by EmpathyOS.__init__)
    feedback_detector: Any  # FeedbackLoopDetector

    def monitor_feedback_loops(self, session_history: list) -> dict:
        """Detect and manage feedback loops in collaboration"""
        active_loops = self.feedback_detector.detect_active_loop(session_history)

        # Take action based on loop type
        if active_loops.get("dominant_loop") == "R2_trust_erosion":
            # URGENT: Break vicious cycle
            return self._break_trust_erosion_loop()

        if active_loops.get("dominant_loop") == "R1_trust_building":
            # MAINTAIN: Keep virtuous cycle going
            return self._maintain_trust_building_loop()

        return active_loops  # type: ignore[no-any-return]

    def _break_trust_erosion_loop(self) -> dict:
        """Intervention to break vicious cycle of trust erosion"""
        return {
            "action": "transparency_intervention",
            "steps": [
                "Acknowledge misalignment explicitly",
                "Ask calibrated questions (Level 2)",
                "Reduce initiative temporarily (drop to Level 1-2)",
                "Rebuild trust through consistent small wins",
            ],
        }

    def _maintain_trust_building_loop(self) -> dict:
        """Maintain virtuous cycle of trust building"""
        return {
            "action": "maintain_momentum",
            "steps": [
                "Continue current approach",
                "Gradually increase initiative (Level 3 \u2192 4)",
                "Document successful patterns",
            ],
        }
