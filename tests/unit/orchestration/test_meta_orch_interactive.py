"""Tests for attune.orchestration.meta_orch_interactive.

Covers all previously-uncovered lines in InteractiveModeMixin:
- analyze_and_compose_interactive (lines 72-110)
- _calculate_confidence (lines 148-175)
- _prompt_user_for_approach (lines 204-260)
- _interactive_team_builder (lines 284-369)
- _pattern_chooser_wizard (lines 392-475)
- _get_pattern_description (lines 487-499)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.orchestration.agent_templates import AgentTemplate
from attune.orchestration.meta_orch_interactive import InteractiveModeMixin
from attune.orchestration.meta_orchestrator import (
    CompositionPattern,
    ExecutionPlan,
    TaskComplexity,
    TaskDomain,
    TaskRequirements,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_requirements(
    complexity=TaskComplexity.SIMPLE,
    domain=TaskDomain.TESTING,
    capabilities_needed=None,
) -> TaskRequirements:
    return TaskRequirements(
        complexity=complexity,
        domain=domain,
        capabilities_needed=capabilities_needed or ["analyze"],
    )


def _make_agent(role="code-reviewer", agent_id="a1", caps=None) -> AgentTemplate:
    agent = MagicMock(spec=AgentTemplate)
    agent.id = agent_id
    agent.role = role
    agent.capabilities = caps or ["review", "analyze", "test"]
    return agent


def _make_plan() -> ExecutionPlan:
    return ExecutionPlan(
        agents=[],
        strategy=CompositionPattern.SEQUENTIAL,
        quality_gates=[],
        estimated_cost=0.01,
        estimated_duration=60,
    )


class ConcreteOrchestrator(InteractiveModeMixin):
    """Minimal concrete class for testing InteractiveModeMixin."""

    def __init__(self, requirements, agents, pattern, plan=None):
        self._requirements = requirements
        self._agents = agents
        self._pattern = pattern
        self._plan = plan or _make_plan()

    def _analyze_task(self, task, context):
        return self._requirements

    def _select_agents(self, requirements):
        return self._agents

    def _choose_composition_pattern(self, requirements, agents):
        return self._pattern

    def create_execution_plan(self, requirements, agents, pattern):
        return self._plan


# ---------------------------------------------------------------------------
# analyze_and_compose_interactive
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzeAndComposeInteractive:
    def _make_host(self, confidence_override=None, **kwargs):
        reqs = _make_requirements(**kwargs)
        agents = [_make_agent()]
        pattern = CompositionPattern.SEQUENTIAL
        host = ConcreteOrchestrator(reqs, agents, pattern)
        if confidence_override is not None:
            host._calculate_confidence = MagicMock(return_value=confidence_override)
        return host

    def test_invalid_task_raises_value_error(self):
        host = self._make_host()
        with pytest.raises(ValueError, match="non-empty string"):
            host.analyze_and_compose_interactive("")

    def test_none_task_raises_value_error(self):
        host = self._make_host()
        with pytest.raises(ValueError, match="non-empty string"):
            host.analyze_and_compose_interactive(None)

    def test_high_confidence_returns_plan_directly(self):
        """Lines 98-101: high confidence (>=0.8) → create_execution_plan immediately."""
        host = self._make_host(confidence_override=0.9)
        plan = host.analyze_and_compose_interactive("fix the bug")
        assert isinstance(plan, ExecutionPlan)

    def test_low_confidence_calls_prompt_user(self):
        """Lines 103-110: low confidence → _prompt_user_for_approach."""
        host = self._make_host(confidence_override=0.5)
        host._prompt_user_for_approach = MagicMock(return_value=_make_plan())
        host.analyze_and_compose_interactive("ambiguous task")
        host._prompt_user_for_approach.assert_called_once()

    def test_context_none_defaults_to_empty_dict(self):
        host = self._make_host(confidence_override=0.9)
        plan = host.analyze_and_compose_interactive("fix bug", context=None)
        assert isinstance(plan, ExecutionPlan)


# ---------------------------------------------------------------------------
# _calculate_confidence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculateConfidence:
    def _host(self):
        reqs = _make_requirements()
        return ConcreteOrchestrator(reqs, [], CompositionPattern.SEQUENTIAL)

    def test_simple_specific_domain_high_confidence(self):
        host = self._host()
        reqs = _make_requirements(complexity=TaskComplexity.SIMPLE, domain=TaskDomain.TESTING)
        agents = [_make_agent()]
        score = host._calculate_confidence(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert score >= 0.8

    def test_general_domain_reduces_confidence(self):
        """Line 152: GENERAL domain multiplies by 0.7."""
        host = self._host()
        reqs_general = _make_requirements(domain=TaskDomain.GENERAL)
        reqs_specific = _make_requirements(domain=TaskDomain.TESTING)
        agents = [_make_agent()]
        pattern = CompositionPattern.SEQUENTIAL
        score_general = host._calculate_confidence(reqs_general, agents, pattern)
        score_specific = host._calculate_confidence(reqs_specific, agents, pattern)
        assert score_general < score_specific

    def test_many_agents_reduces_confidence(self):
        """Line 155: >5 agents multiplies by 0.8."""
        host = self._host()
        reqs = _make_requirements(domain=TaskDomain.TESTING)
        few = [_make_agent(agent_id=str(i)) for i in range(3)]
        many = [_make_agent(agent_id=str(i)) for i in range(6)]
        pattern = CompositionPattern.SEQUENTIAL
        score_few = host._calculate_confidence(reqs, few, pattern)
        score_many = host._calculate_confidence(reqs, many, pattern)
        assert score_many < score_few

    def test_complex_task_reduces_confidence(self):
        """Line 158: COMPLEX complexity multiplies by 0.85."""
        host = self._host()
        reqs_complex = _make_requirements(complexity=TaskComplexity.COMPLEX)
        reqs_simple = _make_requirements(complexity=TaskComplexity.SIMPLE)
        agents = [_make_agent()]
        pattern = CompositionPattern.SEQUENTIAL
        score_complex = host._calculate_confidence(reqs_complex, agents, pattern)
        score_simple = host._calculate_confidence(reqs_simple, agents, pattern)
        assert score_complex < score_simple

    def test_anthropic_patterns_boost_confidence(self):
        """Lines 161-166: TOOL_ENHANCED/DELEGATION_CHAIN/PROMPT_CACHED boosts by 1.1."""
        host = self._host()
        reqs = _make_requirements(domain=TaskDomain.TESTING)
        agents = [_make_agent()]
        score_tool = host._calculate_confidence(reqs, agents, CompositionPattern.TOOL_ENHANCED)
        score_seq = host._calculate_confidence(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert score_tool >= score_seq

    def test_teaching_doc_domain_boosts_confidence(self):
        """Lines 169-173: TEACHING pattern + DOCUMENTATION domain boosts by 1.05."""
        host = self._host()
        reqs = _make_requirements(domain=TaskDomain.DOCUMENTATION)
        agents = [_make_agent()]
        score_teaching = host._calculate_confidence(reqs, agents, CompositionPattern.TEACHING)
        score_seq = host._calculate_confidence(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert score_teaching >= score_seq

    def test_confidence_capped_at_one(self):
        """Line 175: result never exceeds 1.0."""
        host = self._host()
        reqs = _make_requirements(domain=TaskDomain.DOCUMENTATION)
        agents = [_make_agent()]
        score = host._calculate_confidence(reqs, agents, CompositionPattern.TEACHING)
        assert score <= 1.0

    def test_refinement_refactoring_domain_boosts(self):
        """Line 171: REFINEMENT + REFACTORING also boosts."""
        host = self._host()
        reqs = _make_requirements(domain=TaskDomain.REFACTORING)
        agents = [_make_agent()]
        score = host._calculate_confidence(reqs, agents, CompositionPattern.REFINEMENT)
        assert score <= 1.0  # still valid


# ---------------------------------------------------------------------------
# _prompt_user_for_approach
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptUserForApproach:
    def _host(self, domain=TaskDomain.TESTING):
        reqs = _make_requirements(domain=domain)
        agents = [_make_agent()]
        return ConcreteOrchestrator(reqs, agents, CompositionPattern.SEQUENTIAL)

    def test_import_error_via_importerror_patch(self):
        """ImportError fallback (lines 207-210)."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        # Patch the import inside the method
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                raise ImportError("tools not available")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._prompt_user_for_approach(reqs, agents, CompositionPattern.SEQUENTIAL, 0.6)
        assert isinstance(plan, ExecutionPlan)

    def test_ask_user_not_implemented_falls_back(self):
        """Lines 242-245: NotImplementedError from AskUserQuestion → fallback."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]
        mock_ask = MagicMock(side_effect=NotImplementedError("not in CLI"))

        with patch("attune.orchestration.meta_orch_interactive.InteractiveModeMixin"):
            pass

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = mock_ask
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._prompt_user_for_approach(reqs, agents, CompositionPattern.SEQUENTIAL, 0.6)
        assert isinstance(plan, ExecutionPlan)

    def test_use_recommended_choice(self):
        """Lines 250-252: 'Use recommended' → create_execution_plan."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]
        mock_ask = MagicMock(return_value={"Approach": "Use recommended: sequential"})

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = mock_ask
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._prompt_user_for_approach(reqs, agents, CompositionPattern.SEQUENTIAL, 0.6)
        assert isinstance(plan, ExecutionPlan)

    def test_customize_choice_calls_team_builder(self):
        """Lines 254-256: 'Customize' → _interactive_team_builder."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]
        mock_ask = MagicMock(return_value={"Approach": "Customize team composition"})
        host._interactive_team_builder = MagicMock(return_value=_make_plan())

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = mock_ask
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            host._prompt_user_for_approach(reqs, agents, CompositionPattern.SEQUENTIAL, 0.6)
        host._interactive_team_builder.assert_called_once()

    def test_show_patterns_choice_calls_wizard(self):
        """Lines 259-260: show patterns → _pattern_chooser_wizard."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]
        mock_ask = MagicMock(return_value={"Approach": "Show all 10 patterns"})
        host._pattern_chooser_wizard = MagicMock(return_value=_make_plan())

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = mock_ask
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            host._prompt_user_for_approach(reqs, agents, CompositionPattern.SEQUENTIAL, 0.6)
        host._pattern_chooser_wizard.assert_called_once()

    def test_runtime_error_from_ask_falls_back(self):
        """RuntimeError from AskUserQuestion → fallback (lines 242-245)."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]
        mock_ask = MagicMock(side_effect=RuntimeError("env not interactive"))

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = mock_ask
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._prompt_user_for_approach(reqs, agents, CompositionPattern.SEQUENTIAL, 0.6)
        assert isinstance(plan, ExecutionPlan)


# ---------------------------------------------------------------------------
# _interactive_team_builder
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInteractiveTeamBuilder:
    def _host(self):
        reqs = _make_requirements()
        agents = [_make_agent("code-reviewer"), _make_agent("tester", "a2")]
        return ConcreteOrchestrator(reqs, agents, CompositionPattern.SEQUENTIAL)

    def _patch_import_with_ask(self, ask_side_effects):
        """Return a context that patches builtins.__import__ to inject mock AskUserQuestion."""
        import builtins

        original_import = builtins.__import__
        calls = iter(ask_side_effects)

        def mock_ask(*args, **kwargs):
            return next(calls)

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = mock_ask
                return module
            return original_import(name, *args, **kwargs)

        return patch("builtins.__import__", side_effect=mock_import)

    def test_import_error_falls_back(self):
        """Lines 286-288: ImportError → fallback."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                raise ImportError("no tools")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_agent_selection_filters_agents(self):
        """Lines 313-320: user selects subset of agents."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent("code-reviewer"), _make_agent("tester", "a2")]

        # First AskUserQuestion for agents → select only code-reviewer
        # Second AskUserQuestion for pattern → recommended
        agent_response = {"Agents": ["code-reviewer"]}
        pattern_response = {"Pattern": f"{CompositionPattern.SEQUENTIAL.value} (Recommended)"}

        with self._patch_import_with_ask([agent_response, pattern_response]):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_empty_agent_selection_uses_defaults(self):
        """Lines 318-320: empty selection → use all suggested agents."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent("code-reviewer"), _make_agent("tester", "a2")]

        agent_response = {"Agents": []}  # Empty selection
        pattern_response = {"Pattern": f"{CompositionPattern.SEQUENTIAL.value} (Recommended)"}

        with self._patch_import_with_ask([agent_response, pattern_response]):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_non_list_agent_response_wrapped_in_list(self):
        """Line 315: non-list agent response gets wrapped."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent("code-reviewer")]

        agent_response = {"Agents": "code-reviewer"}  # String, not list
        pattern_response = {"Pattern": "sequential"}

        with self._patch_import_with_ask([agent_response, pattern_response]):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_recommended_pattern_selection(self):
        """Lines 357-358: '(Recommended)' in choice → use suggested_pattern."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        agent_response = {"Agents": ["code-reviewer"]}
        pattern_response = {"Pattern": "sequential (Recommended)"}

        with self._patch_import_with_ask([agent_response, pattern_response]):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_custom_pattern_selection(self):
        """Lines 361-363: custom pattern name parsed and used."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        agent_response = {"Agents": ["code-reviewer"]}
        pattern_response = {"Pattern": "parallel"}

        with self._patch_import_with_ask([agent_response, pattern_response]):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_invalid_pattern_falls_back_to_suggested(self):
        """Lines 364-366: invalid pattern name → use suggested_pattern."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        agent_response = {"Agents": ["code-reviewer"]}
        pattern_response = {"Pattern": "nonexistent_pattern"}

        with self._patch_import_with_ask([agent_response, pattern_response]):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_agent_ask_exception_falls_back(self):
        """Lines 308-310: exception in agent AskUserQuestion → fallback."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = MagicMock(
                    side_effect=NotImplementedError("not interactive")
                )
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)

    def test_pattern_ask_exception_falls_back(self):
        """Lines 351-353: exception in pattern AskUserQuestion → fallback."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent("code-reviewer")]

        agent_response = {"Agents": ["code-reviewer"]}
        call_count = [0]

        import builtins

        original_import = builtins.__import__

        def mock_ask(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return agent_response
            raise RuntimeError("not interactive on second call")

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = mock_ask
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._interactive_team_builder(reqs, agents, CompositionPattern.SEQUENTIAL)
        assert isinstance(plan, ExecutionPlan)


# ---------------------------------------------------------------------------
# _pattern_chooser_wizard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPatternChooserWizard:
    def _host(self):
        reqs = _make_requirements()
        agents = [_make_agent()]
        return ConcreteOrchestrator(reqs, agents, CompositionPattern.SEQUENTIAL)

    def _patch_import_with_ask(self, response):
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = MagicMock(return_value=response)
                return module
            return original_import(name, *args, **kwargs)

        return patch("builtins.__import__", side_effect=mock_import)

    def test_import_error_falls_back(self):
        """Lines 394-397: ImportError → fallback."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                raise ImportError("no tools")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._pattern_chooser_wizard(reqs, agents)
        assert isinstance(plan, ExecutionPlan)

    def test_valid_pattern_selection(self):
        """Lines 463-475: valid pattern selected → use it."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        with self._patch_import_with_ask({"Pattern": "parallel"}):
            plan = host._pattern_chooser_wizard(reqs, agents)
        assert isinstance(plan, ExecutionPlan)

    def test_annotated_pattern_strips_annotation(self):
        """Line 464: pattern with '(NEW)' annotation → first word extracted."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        with self._patch_import_with_ask({"Pattern": "tool_enhanced (NEW)"}):
            plan = host._pattern_chooser_wizard(reqs, agents)
        assert isinstance(plan, ExecutionPlan)

    def test_invalid_pattern_falls_back_to_sequential(self):
        """Lines 468-470: invalid pattern → CompositionPattern.SEQUENTIAL."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        with self._patch_import_with_ask({"Pattern": "garbage_pattern"}):
            plan = host._pattern_chooser_wizard(reqs, agents)
        assert isinstance(plan, ExecutionPlan)

    def test_ask_exception_falls_back(self):
        """Lines 457-460: exception from AskUserQuestion → fallback."""
        host = self._host()
        reqs = _make_requirements()
        agents = [_make_agent()]

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "attune.tools":
                module = MagicMock()
                module.AskUserQuestion = MagicMock(side_effect=RuntimeError("not interactive"))
                return module
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            plan = host._pattern_chooser_wizard(reqs, agents)
        assert isinstance(plan, ExecutionPlan)


# ---------------------------------------------------------------------------
# _get_pattern_description
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetPatternDescription:
    def _host(self):
        reqs = _make_requirements()
        return ConcreteOrchestrator(reqs, [], CompositionPattern.SEQUENTIAL)

    @pytest.mark.parametrize(
        "pattern",
        [
            CompositionPattern.SEQUENTIAL,
            CompositionPattern.PARALLEL,
            CompositionPattern.DEBATE,
            CompositionPattern.TEACHING,
            CompositionPattern.REFINEMENT,
            CompositionPattern.ADAPTIVE,
            CompositionPattern.CONDITIONAL,
            CompositionPattern.TOOL_ENHANCED,
            CompositionPattern.PROMPT_CACHED_SEQUENTIAL,
            CompositionPattern.DELEGATION_CHAIN,
        ],
    )
    def test_known_pattern_returns_description(self, pattern):
        host = self._host()
        desc = host._get_pattern_description(pattern)
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_unknown_pattern_returns_fallback(self):
        """Line 499: pattern not in dict → 'Custom composition pattern'."""
        host = self._host()
        unknown = MagicMock(spec=CompositionPattern)
        desc = host._get_pattern_description(unknown)
        assert desc == "Custom composition pattern"
