"""LLM-Powered Goal Analysis

Uses LLM calls to provide sophisticated goal understanding, ambiguity detection,
and intelligent question generation.

Data types live in llm_analyzer_types.py; prompts in llm_analyzer_prompts.py.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from .forms import FieldOption, FieldType, FieldValidation, Form, FormField
from .llm_analyzer_prompts import (
    AGENT_RECOMMENDATION_PROMPT,
    GOAL_ANALYSIS_PROMPT,
    QUESTION_REFINEMENT_PROMPT,
)
from .llm_analyzer_types import (
    LLMAgentRecommendation,
    LLMAnalysisResult,
    LLMQuestionResult,
)
from .session import SocraticSession

logger = logging.getLogger(__name__)


class LLMGoalAnalyzer:
    """Uses LLM to analyze goals and generate questions.

    Supports two modes:
    1. Direct Anthropic API (preferred when api_key is provided)
    2. EmpathyLLMExecutor integration (fallback)

    Example:
        >>> analyzer = LLMGoalAnalyzer(api_key="sk-...")
        >>> result = await analyzer.analyze_goal("I want to automate code reviews")
        >>> print(result.domain)  # "code_review"
        >>> print(result.suggested_questions)

    """

    # Model selection by tier
    MODELS = {
        "cheap": "claude-haiku-4-5-20251001",
        "capable": "claude-sonnet-4-6",
        "premium": "claude-opus-4-6",
    }

    def __init__(
        self,
        api_key: str | None = None,
        provider: str = "anthropic",
        model_tier: str = "capable",
    ):
        """Initialize the analyzer.

        Args:
            api_key: Anthropic API key (enables direct API access)
            provider: LLM provider to use (for executor mode)
            model_tier: Model tier (cheap, capable, premium)

        """
        import os

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.provider = provider
        self.model_tier = model_tier
        self._client = None
        self._executor = None

    def _get_client(self):
        """Lazy-load the Anthropic client for direct API access."""
        if self._client is None and self.api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic package not installed")
        return self._client

    async def _get_executor(self):
        """Get or create LLM executor (fallback mode)."""
        if self._executor is None:
            try:
                from ..models.empathy_executor import EmpathyLLMExecutor

                self._executor = EmpathyLLMExecutor(provider=self.provider)
            except ImportError:
                logger.warning("EmpathyLLMExecutor not available, using mock")
                self._executor = MockLLMExecutor()
        return self._executor

    async def _call_llm(
        self,
        prompt: str,
        system: str,
        max_tokens: int = 2000,
    ) -> str:
        """Call LLM using direct API or executor.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum tokens in response

        Returns:
            Response content as string

        """
        # Try direct Anthropic API first (preferred)
        client = self._get_client()
        if client:
            try:
                model = self.MODELS.get(self.model_tier, self.MODELS["capable"])
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text if response.content else "{}"
            except Exception as e:
                logger.warning(f"Direct API call failed: {e}")

        # Fall back to executor
        executor = await self._get_executor()
        response = await executor.run(
            task_type="analysis",
            prompt=prompt,
            system=system,
        )
        return response.content if hasattr(response, "content") else str(response)

    async def analyze_goal(self, goal: str) -> LLMAnalysisResult:
        """Analyze a goal using LLM.

        Args:
            goal: The user's goal statement

        Returns:
            LLMAnalysisResult with structured analysis

        """
        prompt = GOAL_ANALYSIS_PROMPT.format(goal=goal)
        system = "You are an expert requirements analyst. Respond only with valid JSON."

        try:
            content = await self._call_llm(prompt, system)
            data = self._parse_json_response(content)

            return LLMAnalysisResult(
                intent=data.get("intent", ""),
                domain=data.get("domain", "general"),
                confidence=float(data.get("confidence", 0.5)),
                ambiguities=data.get("ambiguities", []),
                assumptions=data.get("assumptions", []),
                constraints=data.get("constraints", []),
                keywords=data.get("keywords", []),
                suggested_agents=data.get("suggested_agents", []),
                suggested_questions=data.get("suggested_questions", []),
                raw_response=content,
            )

        except Exception as e:
            logger.warning(f"LLM analysis failed, using fallback: {e}")
            return self._fallback_analysis(goal)

    async def generate_questions(
        self,
        session: SocraticSession,
    ) -> LLMQuestionResult:
        """Generate follow-up questions using LLM.

        Args:
            session: Current Socratic session

        Returns:
            LLMQuestionResult with questions

        """
        # Gather context
        previous_answers = {}
        for round_data in session.question_rounds:
            previous_answers.update(round_data.get("answers", {}))

        requirements = {
            "must_have": session.requirements.must_have,
            "technical": session.requirements.technical_constraints,
            "quality": session.requirements.quality_attributes,
        }

        ambiguities = []
        if session.goal_analysis:
            ambiguities = session.goal_analysis.ambiguities

        prompt = QUESTION_REFINEMENT_PROMPT.format(
            goal=session.goal,
            previous_answers=json.dumps(previous_answers, indent=2),
            requirements=json.dumps(requirements, indent=2),
            ambiguities=json.dumps(ambiguities, indent=2),
        )
        system = "You are an expert at gathering requirements. Respond only with valid JSON."

        try:
            content = await self._call_llm(prompt, system)
            data = self._parse_json_response(content)

            return LLMQuestionResult(
                questions=data.get("questions", []),
                confidence_after_answers=float(data.get("confidence_after_answers", 0.7)),
                ready_to_generate=data.get("ready_to_generate", False),
                reasoning=data.get("reasoning", ""),
            )

        except Exception as e:
            logger.warning(f"LLM question generation failed: {e}")
            return LLMQuestionResult(
                questions=[],
                confidence_after_answers=0.5,
                ready_to_generate=False,
                reasoning="Fallback due to LLM error",
            )

    async def recommend_agents(
        self,
        session: SocraticSession,
    ) -> LLMAgentRecommendation:
        """Get agent recommendations using LLM.

        Args:
            session: Current Socratic session

        Returns:
            LLMAgentRecommendation with agent configuration

        """
        requirements = {
            "must_have": session.requirements.must_have,
            "technical": session.requirements.technical_constraints,
            "quality": session.requirements.quality_attributes,
            "preferences": session.requirements.preferences,
            "domain_specific": session.requirements.domain_specific,
        }

        prompt = AGENT_RECOMMENDATION_PROMPT.format(
            goal=session.goal,
            requirements=json.dumps(requirements, indent=2),
        )
        system = "You are an expert at designing agent workflows. Respond only with valid JSON."

        try:
            content = await self._call_llm(prompt, system)
            data = self._parse_json_response(content)

            return LLMAgentRecommendation(
                agents=data.get("agents", []),
                workflow_stages=data.get("workflow_stages", []),
                estimated_cost_tier=data.get("estimated_cost_tier", "moderate"),
                estimated_duration=data.get("estimated_duration", "moderate"),
            )

        except Exception as e:
            logger.warning(f"LLM agent recommendation failed: {e}")
            return self._fallback_agent_recommendation(session)

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling common issues."""
        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in content
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Could not parse JSON from: {content[:200]}")
        return {}

    def _fallback_analysis(self, goal: str) -> LLMAnalysisResult:
        """Fallback analysis when LLM is unavailable."""
        from .engine import (
            detect_domain,
            extract_keywords,
            identify_ambiguities,
            identify_assumptions,
        )

        domain, confidence = detect_domain(goal)
        keywords = extract_keywords(goal)
        ambiguities = identify_ambiguities(goal, domain)
        assumptions = identify_assumptions(goal, domain)

        # Map domain to suggested agents
        domain_agents = {
            "code_review": ["code_quality_reviewer", "result_synthesizer"],
            "security": ["security_reviewer", "result_synthesizer"],
            "testing": ["test_generator", "result_synthesizer"],
            "documentation": ["documentation_writer"],
            "performance": ["performance_analyzer", "result_synthesizer"],
            "refactoring": ["code_quality_reviewer", "result_synthesizer"],
            "general": ["code_quality_reviewer"],
        }

        return LLMAnalysisResult(
            intent=f"Automated {domain.replace('_', ' ')}",
            domain=domain,
            confidence=confidence,
            ambiguities=ambiguities,
            assumptions=assumptions,
            constraints=[],
            keywords=keywords,
            suggested_agents=domain_agents.get(domain, ["code_quality_reviewer"]),
            suggested_questions=[],
        )

    def _fallback_agent_recommendation(
        self,
        session: SocraticSession,
    ) -> LLMAgentRecommendation:
        """Fallback agent recommendation."""
        domain = session.goal_analysis.domain if session.goal_analysis else "general"

        # Default configurations by domain
        configs = {
            "security": {
                "agents": [
                    {"template_id": "security_reviewer", "priority": 1},
                    {"template_id": "result_synthesizer", "priority": 2},
                ],
                "stages": [
                    {"name": "Analysis", "agents": ["security_reviewer"], "parallel": False},
                    {"name": "Synthesis", "agents": ["result_synthesizer"], "parallel": False},
                ],
            },
            "code_review": {
                "agents": [
                    {"template_id": "code_quality_reviewer", "priority": 1},
                    {"template_id": "result_synthesizer", "priority": 2},
                ],
                "stages": [
                    {"name": "Analysis", "agents": ["code_quality_reviewer"], "parallel": False},
                    {"name": "Synthesis", "agents": ["result_synthesizer"], "parallel": False},
                ],
            },
            "testing": {
                "agents": [
                    {"template_id": "test_generator", "priority": 1},
                ],
                "stages": [
                    {"name": "Generation", "agents": ["test_generator"], "parallel": False},
                ],
            },
        }

        config = configs.get(domain, configs["code_review"])

        return LLMAgentRecommendation(
            agents=config["agents"],
            workflow_stages=config["stages"],
            estimated_cost_tier="moderate",
            estimated_duration="moderate",
        )


class MockLLMExecutor:
    """Mock executor for testing without LLM."""

    async def run(self, **kwargs) -> Any:
        """Return mock response."""

        @dataclass
        class MockResponse:
            content: str = "{}"

        return MockResponse()


def llm_questions_to_form(
    questions: list[dict[str, Any]],
    round_number: int,
    session: SocraticSession,
) -> Form:
    """Convert LLM-generated questions to a Form.

    Args:
        questions: Questions from LLM
        round_number: Current round number
        session: Current session

    Returns:
        Form ready for display

    """
    fields = []

    for q in questions:
        q_id = q.get("id", f"q_{len(fields)}")
        q_type = q.get("type", "text")
        q_options = q.get("options", [])

        # Map type to FieldType
        field_type_map = {
            "single_select": FieldType.SINGLE_SELECT,
            "multi_select": FieldType.MULTI_SELECT,
            "text": FieldType.TEXT,
            "text_area": FieldType.TEXT_AREA,
            "boolean": FieldType.BOOLEAN,
        }
        field_type = field_type_map.get(q_type, FieldType.TEXT)

        # Build options
        options = []
        for opt in q_options:
            if isinstance(opt, str):
                options.append(FieldOption(value=opt.lower().replace(" ", "_"), label=opt))
            elif isinstance(opt, dict):
                options.append(
                    FieldOption(
                        value=opt.get("value", opt.get("label", "").lower().replace(" ", "_")),
                        label=opt.get("label", ""),
                        description=opt.get("description", ""),
                    ),
                )

        fields.append(
            FormField(
                id=q_id,
                field_type=field_type,
                label=q.get("question", ""),
                options=options,
                validation=FieldValidation(required=q.get("required", False)),
                category=q.get("category", "general"),
                order=q.get("priority", 5),
            ),
        )

    # Sort by priority (higher priority = lower order number = appears first)
    fields.sort(key=lambda f: f.order, reverse=True)

    progress = min(0.3 + (round_number * 0.15), 0.9)

    return Form(
        id=f"llm_round_{round_number}",
        title="A Few More Questions",
        description=f"Help us understand your needs better. (Round {round_number})",
        fields=fields,
        round_number=round_number,
        progress=progress,
    )
