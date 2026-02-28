"""Socratic Workflow Builder - Main Engine

The core engine that orchestrates Socratic questioning for agent generation.

Flow:
1. User provides initial goal (free text)
2. Engine analyzes goal and generates clarifying questions
3. User answers questions (forms)
4. Engine determines if more clarification needed
5. When ready, generates optimized workflow with agents
6. Defines success criteria for measuring completion

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from .domain import (
    DOMAIN_PATTERNS,
    DomainPattern,
    detect_domain,
    extract_keywords,
    identify_ambiguities,
    identify_assumptions,
)
from .forms import Form, create_goal_text_field
from .generator import AgentGenerator, GeneratedWorkflow
from .questions import generate_followup_questions, generate_initial_questions
from .session import GoalAnalysis, SessionState, SocraticSession
from .success import (
    MetricType,
    SuccessCriteria,
    SuccessMetric,
    code_review_criteria,
    security_audit_criteria,
    test_generation_criteria,
)

# Re-export domain symbols for backward compatibility.
# External code (tests, llm_analyzer, etc.) imports these from
# attune.socratic.engine, so they must remain available here.
__all__ = [
    "DOMAIN_PATTERNS",
    "DomainPattern",
    "SocraticWorkflowBuilder",
    "detect_domain",
    "extract_keywords",
    "generate_followup_questions",
    "generate_initial_questions",
    "identify_ambiguities",
    "identify_assumptions",
]

logger = logging.getLogger(__name__)


class SocraticWorkflowBuilder:
    """Main engine for Socratic agent/workflow generation.

    Example:
        >>> builder = SocraticWorkflowBuilder()
        >>>
        >>> # Start with a goal
        >>> session = builder.start_session("I want to automate security reviews")
        >>>
        >>> # Get questions
        >>> form = builder.get_next_questions(session)
        >>> print(form.title)
        >>>
        >>> # Submit answers
        >>> session = builder.submit_answers(session, {
        ...     "languages": ["python"],
        ...     "quality_focus": ["security"],
        ...     "automation_level": "semi_auto"
        ... })
        >>>
        >>> # Check if ready
        >>> if builder.is_ready_to_generate(session):
        ...     workflow = builder.generate_workflow(session)
        ...     print(workflow.describe())

    """

    def __init__(self) -> None:
        """Initialize the builder."""
        self.generator = AgentGenerator()
        self._sessions: dict[str, SocraticSession] = {}

    def start_session(self, goal: str = "") -> SocraticSession:
        """Start a new Socratic session.

        Args:
            goal: Optional initial goal (can be set later)

        Returns:
            New SocraticSession

        """
        session = SocraticSession()

        if goal:
            session = self.set_goal(session, goal)

        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> SocraticSession | None:
        """Retrieve a session by ID.

        Args:
            session_id: The session identifier

        Returns:
            The session, or None if not found

        """
        return self._sessions.get(session_id)

    def set_goal(self, session: SocraticSession, goal: str) -> SocraticSession:
        """Set or update the session goal.

        Args:
            session: The session to update
            goal: The user's goal statement

        Returns:
            Updated session with goal analysis

        """
        session.goal = goal
        session.state = SessionState.ANALYZING_GOAL
        session.touch()

        # Analyze the goal
        domain, confidence = detect_domain(goal)
        keywords = extract_keywords(goal)
        ambiguities = identify_ambiguities(goal, domain)
        assumptions = identify_assumptions(goal, domain)

        session.goal_analysis = GoalAnalysis(
            raw_goal=goal,
            intent=self._extract_intent(goal, domain),
            domain=domain,
            confidence=confidence,
            ambiguities=ambiguities,
            assumptions=assumptions,
            keywords=keywords,
        )

        # Transition to awaiting answers
        session.state = SessionState.AWAITING_ANSWERS
        return session

    def _extract_intent(self, goal: str, domain: str) -> str:
        """Extract the core intent from the goal.

        Args:
            goal: User's goal statement
            domain: Detected domain

        Returns:
            Human-readable intent description

        """
        intent_patterns = {
            "code_review": "Automated code review",
            "security": "Security vulnerability analysis",
            "testing": "Automated test generation",
            "documentation": "Documentation generation",
            "performance": "Performance optimization",
            "refactoring": "Code refactoring",
            "general": "Code analysis and improvement",
        }
        return intent_patterns.get(domain, "Code analysis")

    def get_initial_form(self) -> Form:
        """Get the initial goal capture form.

        Returns:
            Form for capturing the user's goal

        """
        return Form(
            id="initial_goal",
            title="What would you like to accomplish?",
            description=(
                "Describe your goal in your own words. Be as specific as you like - "
                "we'll ask clarifying questions to understand exactly what you need."
            ),
            fields=[create_goal_text_field()],
            round_number=0,
            progress=0.1,
        )

    def get_next_questions(self, session: SocraticSession) -> Form | None:
        """Get the next set of questions for a session.

        Args:
            session: The current session

        Returns:
            Form with questions, or None if ready to generate

        """
        if session.state == SessionState.AWAITING_GOAL:
            return self.get_initial_form()

        if session.state == SessionState.READY_TO_GENERATE:
            return None

        if session.state == SessionState.COMPLETED:
            return None

        if session.goal_analysis is None:
            return self.get_initial_form()

        # First round of questions
        if session.current_round == 0:
            return generate_initial_questions(session.goal_analysis, session)

        # Follow-up questions
        return generate_followup_questions(session)

    def submit_answers(
        self,
        session: SocraticSession,
        answers: dict[str, Any],
    ) -> SocraticSession:
        """Submit answers to the current questions.

        Args:
            session: The current session
            answers: Dictionary mapping field IDs to values

        Returns:
            Updated session

        """
        session.state = SessionState.PROCESSING_ANSWERS
        session.touch()

        # Record this round
        current_form = self.get_next_questions(session)
        questions_data = []
        if current_form:
            questions_data = [{"id": f.id, "label": f.label} for f in current_form.fields]

        session.add_question_round(questions_data, answers)

        # Update requirements from answers
        self._update_requirements(session, answers)

        # Check if we can generate
        if session.can_generate():
            session.state = SessionState.READY_TO_GENERATE
        else:
            session.state = SessionState.AWAITING_ANSWERS

        return session

    def _update_requirements(
        self,
        session: SocraticSession,
        answers: dict[str, Any],
    ) -> None:
        """Update session requirements from answers.

        Args:
            session: The current session
            answers: Dictionary mapping field IDs to values

        """
        reqs = session.requirements

        # Languages
        if "languages" in answers:
            reqs.technical_constraints["languages"] = answers["languages"]

        # Quality focus
        if "quality_focus" in answers:
            reqs.quality_attributes = dict.fromkeys(answers["quality_focus"], 1.0)
            # Add to must-haves
            for quality in answers["quality_focus"]:
                req = f"Optimize for {quality}"
                if req not in reqs.must_have:
                    reqs.must_have.append(req)

        # Automation level
        if "automation_level" in answers:
            reqs.preferences["automation_level"] = answers["automation_level"]

        # Team size
        if "team_size" in answers:
            reqs.preferences["team_size"] = answers["team_size"]

        # Domain-specific
        if "review_scope" in answers:
            reqs.domain_specific["review_scope"] = answers["review_scope"]

        if "security_focus" in answers:
            reqs.domain_specific["security_focus"] = answers["security_focus"]

        if "test_type" in answers:
            reqs.domain_specific["test_type"] = answers["test_type"]

        # Additional context
        if answers.get("additional_context"):
            reqs.domain_specific["additional_context"] = answers["additional_context"]

        # Priorities
        if "priorities" in answers:
            priorities = answers["priorities"]
            if isinstance(priorities, str):
                # Parse priorities from text
                for line in priorities.split("\n"):
                    line = line.strip()
                    if line and line not in reqs.must_have:
                        reqs.must_have.append(line)

    def is_ready_to_generate(self, session: SocraticSession) -> bool:
        """Check if session is ready for workflow generation.

        Args:
            session: The current session

        Returns:
            True if the session is ready to generate a workflow

        """
        return session.state == SessionState.READY_TO_GENERATE or session.can_generate()

    def generate_workflow(
        self,
        session: SocraticSession,
    ) -> GeneratedWorkflow:
        """Generate workflow from the session.

        Args:
            session: Session with complete requirements

        Returns:
            Generated workflow ready for execution

        Raises:
            ValueError: If session not ready for generation

        """
        if not self.is_ready_to_generate(session):
            raise ValueError("Session not ready for generation. Answer more questions.")

        session.state = SessionState.GENERATING
        session.touch()

        # Build requirements dict for generator
        reqs = session.requirements
        requirements = {
            "quality_focus": list(reqs.quality_attributes.keys()),
            "languages": reqs.technical_constraints.get("languages", []),
            "automation_level": reqs.preferences.get("automation_level", "semi_auto"),
            "domain": session.goal_analysis.domain if session.goal_analysis else "general",
        }

        # Generate agents
        agents = self.generator.generate_agents_for_requirements(requirements)

        # Determine workflow name
        domain = session.goal_analysis.domain if session.goal_analysis else "general"
        name = self._generate_workflow_name(domain, requirements)

        # Generate success criteria
        success_criteria = self._generate_success_criteria(domain, requirements)

        # Create blueprint
        blueprint = self.generator.create_workflow_blueprint(
            name=name,
            description=session.goal or "Generated workflow",
            agents=agents,
            quality_focus=requirements["quality_focus"],
            automation_level=requirements["automation_level"],
            success_criteria=success_criteria,
        )

        blueprint.source_session_id = session.session_id
        blueprint.supported_languages = requirements["languages"]

        # Generate workflow
        workflow = self.generator.generate_workflow(blueprint)

        # Update session
        session.blueprint = blueprint
        session.workflow = workflow
        session.state = SessionState.COMPLETED
        session.touch()

        return workflow

    def _generate_workflow_name(
        self,
        domain: str,
        requirements: dict[str, Any],
    ) -> str:
        """Generate a descriptive workflow name.

        Args:
            domain: Detected domain
            requirements: Workflow requirements

        Returns:
            Human-readable workflow name

        """
        domain_names = {
            "code_review": "Code Review",
            "security": "Security Audit",
            "testing": "Test Generation",
            "documentation": "Documentation",
            "performance": "Performance Analysis",
            "refactoring": "Refactoring",
            "general": "Code Analysis",
        }

        base_name = domain_names.get(domain, "Custom Workflow")

        # Add qualifier
        qualities = requirements.get("quality_focus", [])
        if qualities:
            qualifier = qualities[0].title()
            return f"{qualifier}-Focused {base_name}"

        return f"Automated {base_name}"

    def _generate_success_criteria(
        self,
        domain: str,
        requirements: dict[str, Any],
    ) -> SuccessCriteria:
        """Generate appropriate success criteria for the workflow.

        Args:
            domain: Detected domain
            requirements: Workflow requirements

        Returns:
            SuccessCriteria for the generated workflow

        """
        # Use predefined criteria based on domain
        if domain == "code_review":
            return code_review_criteria()
        if domain == "security":
            return security_audit_criteria()
        if domain == "testing":
            return test_generation_criteria()
        # Generic criteria
        return SuccessCriteria(
            id=f"{domain}_success",
            name=f"{domain.title()} Success Criteria",
            metrics=[
                SuccessMetric(
                    id="task_completed",
                    name="Task Completed",
                    metric_type=MetricType.BOOLEAN,
                    is_primary=True,
                    extraction_path="success",
                ),
                SuccessMetric(
                    id="findings_count",
                    name="Findings",
                    metric_type=MetricType.COUNT,
                    extraction_path="findings_count",
                ),
            ],
            success_threshold=0.7,
        )

    def get_session_summary(self, session: SocraticSession) -> dict[str, Any]:
        """Get a summary of the session state for display.

        Args:
            session: The current session

        Returns:
            Dictionary with session summary information

        """
        return {
            "session_id": session.session_id,
            "state": session.state.value,
            "goal": session.goal,
            "domain": session.goal_analysis.domain if session.goal_analysis else None,
            "confidence": session.goal_analysis.confidence if session.goal_analysis else 0,
            "rounds_completed": session.current_round,
            "requirements_completeness": session.requirements.completeness_score(),
            "ready_to_generate": self.is_ready_to_generate(session),
            "ambiguities_remaining": (
                len(session.goal_analysis.ambiguities) if session.goal_analysis else 0
            ),
        }
