"""Empathy Levels Mixin for EmpathyOS.

Extracted from EmpathyOS to improve maintainability.
Provides the 5 empathy level methods (level_1_reactive through level_5_systems).

Expected attributes on the host class:
    user_id (str): User identifier
    logger (logging.Logger): Logger instance
    current_empathy_level (int): Current empathy level
    collaboration_state (CollaborationState): Collaboration state
    leverage_analyzer (LeveragePointAnalyzer): Leverage point analyzer
    _process_request(request): Process a request (from EmpathyHelpersMixin)
    _ask_calibrated_questions(request): Ask clarifying questions (from EmpathyHelpersMixin)
    _refine_request(original, clarification): Refine request (from EmpathyHelpersMixin)
    _detect_active_patterns(context): Detect patterns (from EmpathyHelpersMixin)
    _design_proactive_action(pattern): Design action (from EmpathyHelpersMixin)
    _is_safe_to_execute(action): Safety check (from EmpathyHelpersMixin)
    _execute_proactive_actions(actions): Execute actions (from EmpathyHelpersMixin)
    _predict_future_bottlenecks(trajectory): Predict bottlenecks (from EmpathyHelpersMixin)
    _should_anticipate(bottleneck): Should anticipate (from EmpathyHelpersMixin)
    _design_anticipatory_intervention(bottleneck): Design intervention (from EmpathyHelpersMixin)
    _execute_anticipatory_interventions(interventions): Execute (from EmpathyHelpersMixin)
    _identify_problem_classes(domain_context): Identify classes (from EmpathyHelpersMixin)
    _design_framework(leverage_point): Design framework (from EmpathyHelpersMixin)
    _implement_frameworks(frameworks): Implement frameworks (from EmpathyHelpersMixin)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

from ..exceptions import ValidationError


class EmpathyLevelsMixin:
    """Mixin providing the 5 empathy levels (reactive through systems)."""

    # Expected attributes (set by EmpathyOS.__init__)
    user_id: str
    logger: Any  # logging.Logger
    current_empathy_level: int
    collaboration_state: Any  # CollaborationState

    # =========================================================================
    # LEVEL 1: REACTIVE EMPATHY
    # =========================================================================

    async def level_1_reactive(self, user_request: str) -> dict:
        """Level 1: Reactive Empathy

        Respond to explicit request accurately and helpfully.
        No anticipation, no proactive action.

        Args:
            user_request: User's explicit request

        Returns:
            Dict with result and reasoning

        Raises:
            ValueError: If user_request is empty or not a string

        """
        # Input validation
        if not isinstance(user_request, str):
            raise ValidationError(
                f"user_request must be a string, got {type(user_request).__name__}",
            )
        if not user_request.strip():
            raise ValidationError("user_request cannot be empty")

        self.logger.info(
            "Level 1 reactive request started",
            extra={
                "user_id": self.user_id,
                "empathy_level": 1,
                "request_length": len(user_request),
            },
        )

        self.current_empathy_level = 1

        # Process request (implement your domain logic here)
        result = await self._process_request(user_request)  # type: ignore[attr-defined]

        self.logger.info(
            "Level 1 reactive request completed",
            extra={"user_id": self.user_id, "success": result.get("status") == "success"},
        )

        # Update collaboration state
        self.collaboration_state.total_interactions += 1

        return {
            "level": 1,
            "type": "reactive",
            "result": result,
            "reasoning": "Responding to explicit request",
            "empathy_level": "Reactive: Help after being asked",
        }

    # =========================================================================
    # LEVEL 2: GUIDED EMPATHY
    # =========================================================================

    async def level_2_guided(self, user_request: str) -> dict:
        """Level 2: Guided Empathy

        Use calibrated questions (Voss) to clarify intent before acting.
        Collaborative exploration to uncover hidden needs.

        Args:
            user_request: User's request (potentially ambiguous)

        Returns:
            Dict with clarification questions or refined result

        Raises:
            ValueError: If user_request is empty or not a string

        """
        # Input validation
        if not isinstance(user_request, str):
            raise ValidationError(
                f"user_request must be a string, got {type(user_request).__name__}",
            )
        if not user_request.strip():
            raise ValidationError("user_request cannot be empty")

        self.current_empathy_level = 2

        self.logger.info(
            "Level 2 guided request started",
            extra={
                "user_id": self.user_id,
                "empathy_level": 2,
                "request_length": len(user_request),
            },
        )

        # Use Voss's calibrated questions
        clarification = await self._ask_calibrated_questions(user_request)  # type: ignore[attr-defined]

        if clarification["needs_clarification"]:
            return {
                "level": 2,
                "type": "guided",
                "action": "clarify_first",
                "questions": clarification["questions"],
                "reasoning": "Asking clarifying questions to understand true intent",
                "empathy_level": "Guided: Collaborative exploration",
            }

        # Refine request based on clarification
        refined_request = self._refine_request(user_request, clarification)  # type: ignore[attr-defined]

        # Process refined request
        result = await self._process_request(refined_request)  # type: ignore[attr-defined]

        # Update collaboration state
        self.collaboration_state.total_interactions += 1
        self.collaboration_state.shared_context.update(clarification)

        self.logger.info(
            "Level 2 guided request completed",
            extra={
                "user_id": self.user_id,
                "empathy_level": 2,
                "action": "proceed",
                "clarification_applied": True,
            },
        )

        return {
            "level": 2,
            "type": "guided",
            "action": "proceed",
            "result": result,
            "clarification": clarification,
            "reasoning": "Collaborated to refine understanding before execution",
            "empathy_level": "Guided: Clarified through questions",
        }

    # =========================================================================
    # LEVEL 3: PROACTIVE EMPATHY
    # =========================================================================

    async def level_3_proactive(self, context: dict) -> dict:
        """Level 3: Proactive Empathy

        Detect patterns, act on leading indicators.
        Take initiative without being asked.

        Args:
            context: Current context (user activity, system state, etc.)

        Returns:
            Dict with proactive actions taken

        Raises:
            ValueError: If context is not a dict or is empty

        """
        # Input validation
        if not isinstance(context, dict):
            raise ValidationError(f"context must be a dict, got {type(context).__name__}")
        if not context:
            raise ValidationError("context cannot be empty")

        self.current_empathy_level = 3

        self.logger.info(
            "Level 3 proactive analysis started",
            extra={
                "user_id": self.user_id,
                "empathy_level": 3,
                "context_keys": list(context.keys()),
            },
        )

        # Detect current patterns
        active_patterns = self._detect_active_patterns(context)  # type: ignore[attr-defined]

        # Select proactive actions based on patterns
        proactive_actions = []

        for pattern in active_patterns:
            if pattern["confidence"] > 0.8:  # High confidence required
                action = self._design_proactive_action(pattern)  # type: ignore[attr-defined]

                # Safety check
                if self._is_safe_to_execute(action):  # type: ignore[attr-defined]
                    proactive_actions.append(action)

        # Execute proactive actions
        results = await self._execute_proactive_actions(proactive_actions)  # type: ignore[attr-defined]

        # Update collaboration state
        for result in results:
            outcome = "success" if result["success"] else "failure"
            self.collaboration_state.update_trust(outcome)

        self.logger.info(
            "Level 3 proactive actions completed",
            extra={
                "user_id": self.user_id,
                "empathy_level": 3,
                "patterns_detected": len(active_patterns),
                "actions_taken": len(proactive_actions),
                "success_rate": (
                    sum(1 for r in results if r["success"]) / len(results) if results else 0
                ),
            },
        )

        return {
            "level": 3,
            "type": "proactive",
            "patterns_detected": len(active_patterns),
            "actions_taken": len(proactive_actions),
            "results": results,
            "reasoning": "Acting on detected patterns without being asked",
            "empathy_level": "Proactive: Act before being asked",
        }

    # =========================================================================
    # LEVEL 4: ANTICIPATORY EMPATHY
    # =========================================================================

    async def level_4_anticipatory(self, system_trajectory: dict) -> dict:
        """Level 4: Anticipatory Empathy (THE INNOVATION)

        Predict future bottlenecks, design relief in advance.

        This is STRATEGIC CARE:
        - Timing + Prediction + Initiative
        - Solve tomorrow's pain today
        - Act without being told (but without overstepping)

        Args:
            system_trajectory: System state + growth trends + constraints

        Returns:
            Dict with predicted bottlenecks and interventions

        Raises:
            ValueError: If system_trajectory is not a dict or is empty

        """
        # Input validation
        if not isinstance(system_trajectory, dict):
            raise ValidationError(
                f"system_trajectory must be a dict, got {type(system_trajectory).__name__}",
            )
        if not system_trajectory:
            raise ValidationError("system_trajectory cannot be empty")

        self.current_empathy_level = 4

        self.logger.info(
            "Level 4 anticipatory prediction started",
            extra={
                "user_id": self.user_id,
                "empathy_level": 4,
                "trajectory_keys": list(system_trajectory.keys()),
            },
        )

        # Analyze system trajectory
        predicted_bottlenecks = self._predict_future_bottlenecks(system_trajectory)  # type: ignore[attr-defined]

        # Design structural relief for each bottleneck
        interventions = []

        for bottleneck in predicted_bottlenecks:
            # Only intervene if:
            # 1. High confidence (>75%)
            # 2. Appropriate time horizon (30-120 days)
            # 3. Reversible action
            if self._should_anticipate(bottleneck):  # type: ignore[attr-defined]
                intervention = self._design_anticipatory_intervention(bottleneck)  # type: ignore[attr-defined]
                interventions.append(intervention)

        # Execute anticipatory interventions
        results = await self._execute_anticipatory_interventions(interventions)  # type: ignore[attr-defined]

        # Update collaboration state
        for result in results:
            outcome = "success" if result["success"] else "failure"
            self.collaboration_state.update_trust(outcome)

        self.logger.info(
            "Level 4 anticipatory interventions completed",
            extra={
                "user_id": self.user_id,
                "empathy_level": 4,
                "bottlenecks_predicted": len(predicted_bottlenecks),
                "interventions_executed": len(interventions),
                "success_rate": (
                    sum(1 for r in results if r["success"]) / len(results) if results else 0
                ),
            },
        )

        return {
            "level": 4,
            "type": "anticipatory",
            "bottlenecks_predicted": predicted_bottlenecks,
            "interventions_designed": len(interventions),
            "results": results,
            "reasoning": "Predicting future bottlenecks and designing relief in advance",
            "empathy_level": "Anticipatory: Predict and prevent problems",
            "formula": "Timing + Prediction + Initiative = Anticipatory Empathy",
        }

    # =========================================================================
    # LEVEL 5: SYSTEMS EMPATHY
    # =========================================================================

    async def level_5_systems(self, domain_context: dict) -> dict:
        """Level 5: Systems Empathy

        Build structures that help at scale.
        Design leverage points, frameworks, self-sustaining systems.

        This is ARCHITECTURAL CARE:
        - One framework -> infinite applications
        - Solve entire problem class, not individual instances
        - Design for emergence of desired properties

        Args:
            domain_context: Domain information, recurring problems, patterns

        Returns:
            Dict with designed frameworks and leverage points

        Raises:
            ValueError: If domain_context is not a dict or is empty

        """
        # Input validation
        if not isinstance(domain_context, dict):
            raise ValidationError(
                f"domain_context must be a dict, got {type(domain_context).__name__}",
            )
        if not domain_context:
            raise ValidationError("domain_context cannot be empty")

        self.current_empathy_level = 5

        self.logger.info(
            "Level 5 systems framework design started",
            extra={
                "user_id": self.user_id,
                "empathy_level": 5,
                "domain_keys": list(domain_context.keys()),
            },
        )

        # Identify problem class (not individual problem)
        problem_classes = self._identify_problem_classes(domain_context)  # type: ignore[attr-defined]

        # Find leverage points (Meadows's framework)
        leverage_points = []
        for problem_class in problem_classes:
            points = self.leverage_analyzer.find_leverage_points(problem_class)  # type: ignore[attr-defined]
            leverage_points.extend(points)

        # Design structural interventions at highest leverage points
        frameworks = []
        for lp in leverage_points:
            if lp.level.value >= 8:  # High leverage points only (Rules and above)
                framework = self._design_framework(lp)  # type: ignore[attr-defined]
                frameworks.append(framework)

        # Implement frameworks
        results = await self._implement_frameworks(frameworks)  # type: ignore[attr-defined]

        self.logger.info(
            "Level 5 systems frameworks implemented",
            extra={
                "user_id": self.user_id,
                "empathy_level": 5,
                "problem_classes": len(problem_classes),
                "leverage_points_found": len(leverage_points),
                "frameworks_deployed": len(frameworks),
            },
        )

        return {
            "level": 5,
            "type": "systems",
            "problem_classes": len(problem_classes),
            "leverage_points": leverage_points,
            "frameworks_designed": len(frameworks),
            "results": results,
            "reasoning": "Building structural solutions that scale to entire problem class",
            "empathy_level": "Systems: Build structures that help at scale",
        }
