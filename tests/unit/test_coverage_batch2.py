"""Coverage Batch 2 - Comprehensive tests for trust_building, templates, and code_review_adapters.

Targets coverage for:
- src/attune/trust_building.py (~146 stmts, 0% -> high coverage)
- src/attune/templates.py (~75 stmts, 0% -> high coverage)
- src/attune/workflows/code_review_adapters.py (~84 stmts, 0% -> high coverage)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from attune.templates import (
    TEMPLATES,
    cmd_new,
    list_templates,
    scaffold_project,
)
from attune.trust_building import (
    COORDINATION_ROLES,
    EXECUTIVE_ROLES,
    HIGH_STRESS_LEVELS,
    TECHNICAL_ROLES,
    TrustBuildingBehaviors,
    TrustSignal,
)


class TestTrustSignalDataclass:
    """Tests for TrustSignal dataclass creation and defaults."""

    def test_creation_with_required_fields(self) -> None:
        """Test creating TrustSignal with only required fields."""
        signal = TrustSignal(signal_type="building", behavior="proactive_help")
        assert signal.signal_type == "building"
        assert signal.behavior == "proactive_help"

    def test_default_evidence_is_none(self) -> None:
        """Test TrustSignal evidence defaults to None."""
        signal = TrustSignal(signal_type="eroding", behavior="missed")
        assert signal.evidence is None

    def test_default_impact_is_half(self) -> None:
        """Test TrustSignal impact defaults to 0.5."""
        signal = TrustSignal(signal_type="building", behavior="test")
        assert signal.impact == 0.5

    def test_default_timestamp_is_datetime(self) -> None:
        """Test TrustSignal timestamp defaults to a datetime instance."""
        signal = TrustSignal(signal_type="building", behavior="test")
        assert isinstance(signal.timestamp, datetime)

    def test_custom_values(self) -> None:
        """Test TrustSignal with fully specified values."""
        ts = datetime(2025, 1, 15, 10, 30)
        signal = TrustSignal(
            signal_type="building",
            behavior="clarify_ambiguity",
            timestamp=ts,
            evidence="Asked 3 clarifying questions",
            impact=0.8,
        )
        assert signal.timestamp == ts
        assert signal.evidence == "Asked 3 clarifying questions"
        assert signal.impact == 0.8

    def test_eroding_signal_type(self) -> None:
        """Test creating a TrustSignal with eroding type."""
        signal = TrustSignal(signal_type="eroding", behavior="ignored_warning", impact=0.9)
        assert signal.signal_type == "eroding"
        assert signal.impact == 0.9


class TestRoleFrozensets:
    """Tests for role category frozensets used for O(1) lookups."""

    def test_executive_roles_contains_expected(self) -> None:
        """Test EXECUTIVE_ROLES contains all expected roles."""
        expected = {"executive", "ceo", "cto", "manager", "director", "vp"}
        assert expected == EXECUTIVE_ROLES

    def test_technical_roles_contains_expected(self) -> None:
        """Test TECHNICAL_ROLES contains all expected roles."""
        expected = {"developer", "engineer", "architect", "devops", "sre"}
        assert expected == TECHNICAL_ROLES

    def test_coordination_roles_contains_expected(self) -> None:
        """Test COORDINATION_ROLES contains all expected roles."""
        expected = {"team_lead", "project_manager", "scrum_master", "coordinator"}
        assert expected == COORDINATION_ROLES

    def test_high_stress_levels_contains_expected(self) -> None:
        """Test HIGH_STRESS_LEVELS contains all expected levels."""
        expected = {"critical", "high", "severe"}
        assert expected == HIGH_STRESS_LEVELS

    def test_all_role_sets_are_frozenset(self) -> None:
        """Test that all role sets are frozensets (immutable)."""
        assert isinstance(EXECUTIVE_ROLES, frozenset)
        assert isinstance(TECHNICAL_ROLES, frozenset)
        assert isinstance(COORDINATION_ROLES, frozenset)
        assert isinstance(HIGH_STRESS_LEVELS, frozenset)

    def test_role_sets_are_disjoint(self) -> None:
        """Test role sets do not overlap with each other."""
        assert EXECUTIVE_ROLES.isdisjoint(TECHNICAL_ROLES)
        assert EXECUTIVE_ROLES.isdisjoint(COORDINATION_ROLES)
        assert TECHNICAL_ROLES.isdisjoint(COORDINATION_ROLES)


class TestTrustBuildingBehaviorsInit:
    """Tests for TrustBuildingBehaviors initialization."""

    def test_init_creates_empty_trust_signals(self) -> None:
        """Test __init__ creates an empty trust_signals list."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors.trust_signals == []
        assert isinstance(behaviors.trust_signals, list)


class TestPreFormatForHandoff:
    """Tests for pre_format_for_handoff method covering all role branches."""

    def test_executive_role_creates_executive_summary(self) -> None:
        """Test pre-formatting for an executive role creates executive summary."""
        behaviors = TrustBuildingBehaviors()
        data = {"revenue": 1000000, "growth": 15.5, "users": 500}
        result = behaviors.pre_format_for_handoff(
            data=data,
            recipient_role="executive",
            context="quarterly_review",
        )
        assert result["format"] == "executive_summary"
        assert result["summary"]["type"] == "executive_summary"
        assert result["original_data"] == data
        assert "timestamp" in result
        assert "key_metrics" in result["summary"]
        assert "highlights" in result["summary"]
        assert "recommendations" in result["summary"]

    def test_ceo_role_uses_executive_branch(self) -> None:
        """Test CEO role (member of EXECUTIVE_ROLES) goes through executive branch."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={"items": [1, 2]},
            recipient_role="ceo",
            context="board",
        )
        assert result["summary"]["type"] == "executive_summary"

    def test_cto_role_uses_executive_branch(self) -> None:
        """Test CTO role (member of EXECUTIVE_ROLES) goes through executive branch."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={},
            recipient_role="cto",
            context="tech_review",
        )
        assert result["summary"]["type"] == "executive_summary"

    def test_manager_role_uses_executive_branch(self) -> None:
        """Test manager role uses executive formatting."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={},
            recipient_role="manager",
            context="review",
        )
        assert result["format"] == "executive_summary"

    def test_developer_role_creates_technical_summary(self) -> None:
        """Test pre-formatting for developer creates technical summary."""
        behaviors = TrustBuildingBehaviors()
        data = {"function": "parse_config", "complexity": 12}
        result = behaviors.pre_format_for_handoff(
            data=data,
            recipient_role="developer",
            context="code_review",
        )
        assert result["format"] == "technical_detail"
        assert result["summary"]["type"] == "technical_detail"
        assert result["summary"]["details"] == data
        assert "technical_notes" in result["summary"]

    def test_engineer_role_uses_technical_branch(self) -> None:
        """Test engineer role (member of TECHNICAL_ROLES) uses technical branch."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={"module": "auth"},
            recipient_role="engineer",
            context="debug",
        )
        assert result["summary"]["type"] == "technical_detail"

    def test_architect_role_uses_technical_branch(self) -> None:
        """Test architect role uses technical branch."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={},
            recipient_role="architect",
            context="design",
        )
        assert result["summary"]["type"] == "technical_detail"

    def test_team_lead_role_creates_action_oriented_summary(self) -> None:
        """Test pre-formatting for team_lead creates action-oriented summary."""
        behaviors = TrustBuildingBehaviors()
        data = {"actions": ["deploy", "review", "test"], "priorities": ["p1", "p2"]}
        result = behaviors.pre_format_for_handoff(
            data=data,
            recipient_role="team_lead",
            context="sprint_planning",
        )
        assert result["format"] == "action_oriented"
        assert result["summary"]["type"] == "action_oriented"
        assert "immediate_actions" in result["summary"]
        assert "priorities" in result["summary"]

    def test_coordinator_role_uses_coordination_branch(self) -> None:
        """Test coordinator (member of COORDINATION_ROLES) uses action branch."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={"tasks": [1, 2, 3]},
            recipient_role="coordinator",
            context="standup",
        )
        assert result["summary"]["type"] == "action_oriented"

    def test_project_manager_role_uses_coordination_branch(self) -> None:
        """Test project_manager uses coordination branch."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={},
            recipient_role="project_manager",
            context="planning",
        )
        assert result["summary"]["type"] == "action_oriented"

    def test_unknown_role_creates_generic_summary(self) -> None:
        """Test pre-formatting for unknown role creates generic summary."""
        behaviors = TrustBuildingBehaviors()
        data = {"key": "value"}
        result = behaviors.pre_format_for_handoff(
            data=data,
            recipient_role="intern",
            context="onboarding",
        )
        assert result["format"] == "general"
        assert result["summary"]["type"] == "general"
        assert "summary" in result["summary"]

    def test_handoff_records_building_trust_signal(self) -> None:
        """Test that pre_format_for_handoff records a building trust signal."""
        behaviors = TrustBuildingBehaviors()
        behaviors.pre_format_for_handoff(
            data={"x": 1},
            recipient_role="developer",
            context="review",
        )
        assert len(behaviors.trust_signals) == 1
        assert behaviors.trust_signals[0].signal_type == "building"
        assert behaviors.trust_signals[0].behavior == "pre_format_handoff"
        assert "developer" in behaviors.trust_signals[0].evidence

    def test_handoff_reasoning_includes_role(self) -> None:
        """Test the reasoning field mentions the recipient role."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.pre_format_for_handoff(
            data={},
            recipient_role="devops",
            context="incident",
        )
        assert "devops" in result["reasoning"]


class TestClarifyBeforeActing:
    """Tests for clarify_before_acting method."""

    def test_returns_needs_clarification_status(self) -> None:
        """Test clarification returns needs_clarification status."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.clarify_before_acting(
            instruction="Deploy the changes",
            detected_ambiguities=["which environment?", "which branch?"],
        )
        assert result["status"] == "needs_clarification"
        assert result["original_instruction"] == "Deploy the changes"

    def test_generates_question_per_ambiguity(self) -> None:
        """Test each ambiguity generates a corresponding clarifying question."""
        behaviors = TrustBuildingBehaviors()
        ambiguities = ["which system?", "what changes?", "when?"]
        result = behaviors.clarify_before_acting(
            instruction="Update the system",
            detected_ambiguities=ambiguities,
        )
        assert len(result["clarifying_questions"]) == 3
        assert len(result["ambiguities_detected"]) == 3

    def test_question_format_structure(self) -> None:
        """Test each question has ambiguity, question, and context keys."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.clarify_before_acting(
            instruction="Do something",
            detected_ambiguities=["what?"],
            context={"env": "production"},
        )
        question = result["clarifying_questions"][0]
        assert question["ambiguity"] == "what?"
        assert "Could you clarify" in question["question"]
        assert question["context"] != "none"

    def test_no_context_sets_none_string(self) -> None:
        """Test clarification without context sets context to 'none'."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.clarify_before_acting(
            instruction="Do something",
            detected_ambiguities=["what?"],
        )
        assert result["clarifying_questions"][0]["context"] == "none"

    def test_records_trust_signal_with_count(self) -> None:
        """Test that clarify_before_acting records trust signal with ambiguity count."""
        behaviors = TrustBuildingBehaviors()
        behaviors.clarify_before_acting(instruction="Test", detected_ambiguities=["a", "b", "c"])
        assert len(behaviors.trust_signals) == 1
        assert behaviors.trust_signals[0].behavior == "clarify_ambiguity"
        assert "3 ambiguities" in behaviors.trust_signals[0].evidence

    def test_empty_ambiguities_list(self) -> None:
        """Test clarification with empty ambiguities list generates no questions."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.clarify_before_acting(instruction="Something", detected_ambiguities=[])
        assert len(result["clarifying_questions"]) == 0

    def test_has_timestamp(self) -> None:
        """Test result contains a timestamp."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.clarify_before_acting(instruction="Test", detected_ambiguities=["a"])
        assert "timestamp" in result

    def test_reasoning_explains_clarification(self) -> None:
        """Test the reasoning field explains why clarification is needed."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.clarify_before_acting(instruction="Test", detected_ambiguities=["x"])
        assert "ambiguities" in result["reasoning"].lower()


class TestVolunteerStructureDuringStress:
    """Tests for volunteer_structure_during_stress method."""

    def test_critical_stress_with_all_scaffolding(self) -> None:
        """Test critical stress (4+ indicators) offers all matching scaffolding."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2, "c": 3, "d": 4},
            available_scaffolding=["prioritization", "breakdown", "templates"],
        )
        assert result["stress_assessment"]["level"] == "critical"
        support_types = [s["type"] for s in result["offered_support"]]
        assert "prioritization" in support_types
        assert "task_breakdown" in support_types
        assert "templates" in support_types

    def test_high_stress_with_prioritization_and_breakdown(self) -> None:
        """Test high stress (3 indicators) offers prioritization and breakdown."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2, "c": 3},
            available_scaffolding=["prioritization", "breakdown"],
        )
        assert result["stress_assessment"]["level"] == "high"
        support_types = [s["type"] for s in result["offered_support"]]
        assert "prioritization" in support_types
        assert "task_breakdown" in support_types

    def test_moderate_stress_no_high_stress_scaffolding(self) -> None:
        """Test moderate stress (2 indicators) does not offer prioritization."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2},
            available_scaffolding=["prioritization", "breakdown", "templates"],
        )
        assert result["stress_assessment"]["level"] == "moderate"
        support_types = [s["type"] for s in result["offered_support"]]
        assert "prioritization" not in support_types
        assert "task_breakdown" not in support_types
        assert "templates" in support_types

    def test_low_stress_only_templates(self) -> None:
        """Test low stress (1 indicator) only offers templates if available."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"minor": True},
            available_scaffolding=["prioritization", "breakdown", "templates"],
        )
        assert result["stress_assessment"]["level"] == "low"
        support_types = [s["type"] for s in result["offered_support"]]
        assert "prioritization" not in support_types
        assert "task_breakdown" not in support_types
        assert "templates" in support_types

    def test_high_stress_prioritization_immediate_flag(self) -> None:
        """Test prioritization and breakdown are immediate at high stress."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2, "c": 3},
            available_scaffolding=["prioritization", "breakdown"],
        )
        for support in result["offered_support"]:
            if support["type"] in ("prioritization", "task_breakdown"):
                assert support["immediate"] is True

    def test_templates_not_immediate(self) -> None:
        """Test templates support is not marked immediate."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1},
            available_scaffolding=["templates"],
        )
        template_support = [s for s in result["offered_support"] if s["type"] == "templates"]
        assert len(template_support) == 1
        assert template_support[0]["immediate"] is False

    def test_records_trust_signal(self) -> None:
        """Test volunteer_structure_during_stress records a trust signal."""
        behaviors = TrustBuildingBehaviors()
        behaviors.volunteer_structure_during_stress(
            stress_indicators={"x": 1},
            available_scaffolding=["templates"],
        )
        assert len(behaviors.trust_signals) == 1
        assert behaviors.trust_signals[0].behavior == "volunteer_structure"

    def test_high_stress_without_prioritization_available(self) -> None:
        """Test high stress without prioritization in available scaffolding."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2, "c": 3},
            available_scaffolding=["templates"],
        )
        support_types = [s["type"] for s in result["offered_support"]]
        assert "prioritization" not in support_types
        assert "templates" in support_types

    def test_high_stress_without_breakdown_available(self) -> None:
        """Test high stress without breakdown in available scaffolding."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2, "c": 3},
            available_scaffolding=["prioritization"],
        )
        support_types = [s["type"] for s in result["offered_support"]]
        assert "prioritization" in support_types
        assert "task_breakdown" not in support_types

    def test_empty_scaffolding_list(self) -> None:
        """Test with empty available scaffolding returns no support offers."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2, "c": 3},
            available_scaffolding=[],
        )
        assert len(result["offered_support"]) == 0

    def test_reasoning_mentions_stress_level(self) -> None:
        """Test the reasoning includes the stress level."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.volunteer_structure_during_stress(
            stress_indicators={"a": 1, "b": 2, "c": 3},
            available_scaffolding=[],
        )
        assert "high" in result["reasoning"].lower()


class TestOfferProactiveHelp:
    """Tests for offer_proactive_help method."""

    def test_execution_struggle_with_debugging(self) -> None:
        """Test repeated_errors indicator triggers execution struggle with debugging help."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.offer_proactive_help(
            struggle_indicators={"repeated_errors": 5},
            available_help=["debugging", "guidance"],
        )
        assert result["struggle_assessment"]["type"] == "execution"
        help_types = [h["type"] for h in result["help_offered"]]
        assert "debugging" in help_types

    def test_execution_struggle_with_guidance(self) -> None:
        """Test execution struggle offers step_by_step guidance when available."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.offer_proactive_help(
            struggle_indicators={"repeated_errors": 3},
            available_help=["guidance"],
        )
        help_types = [h["type"] for h in result["help_offered"]]
        assert "step_by_step" in help_types

    def test_comprehension_struggle_with_explanation_and_examples(self) -> None:
        """Test time_on_task indicator triggers comprehension struggle."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.offer_proactive_help(
            struggle_indicators={"time_on_task": 60},
            available_help=["explanation", "examples"],
        )
        assert result["struggle_assessment"]["type"] == "comprehension"
        help_types = [h["type"] for h in result["help_offered"]]
        assert "explanation" in help_types
        assert "examples" in help_types

    def test_comprehension_without_matching_help(self) -> None:
        """Test comprehension struggle with unmatched help types offers nothing."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.offer_proactive_help(
            struggle_indicators={"time_on_task": 30},
            available_help=["debugging"],
        )
        assert result["struggle_assessment"]["type"] == "comprehension"
        assert len(result["help_offered"]) == 0

    def test_general_struggle_no_matching_help(self) -> None:
        """Test other indicators trigger general struggle with no help offered."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.offer_proactive_help(
            struggle_indicators={"frustration_level": "high"},
            available_help=["debugging"],
        )
        assert result["struggle_assessment"]["type"] == "general"
        assert len(result["help_offered"]) == 0

    def test_tone_is_supportive_not_condescending(self) -> None:
        """Test help offer has supportive_not_condescending tone."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.offer_proactive_help(
            struggle_indicators={"repeated_errors": 3},
            available_help=[],
        )
        assert result["tone"] == "supportive_not_condescending"

    def test_records_trust_signal(self) -> None:
        """Test offer_proactive_help records a trust signal."""
        behaviors = TrustBuildingBehaviors()
        behaviors.offer_proactive_help(
            struggle_indicators={"time_on_task": 30},
            available_help=[],
        )
        assert len(behaviors.trust_signals) == 1
        assert behaviors.trust_signals[0].behavior == "proactive_help"
        assert "comprehension" in behaviors.trust_signals[0].evidence

    def test_repeated_errors_takes_precedence_over_time(self) -> None:
        """Test repeated_errors takes precedence over time_on_task."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.offer_proactive_help(
            struggle_indicators={"repeated_errors": 3, "time_on_task": 60},
            available_help=["debugging"],
        )
        assert result["struggle_assessment"]["type"] == "execution"


class TestGetTrustTrajectory:
    """Tests for get_trust_trajectory method."""

    def test_empty_signals_returns_insufficient_data(self) -> None:
        """Test empty signals returns insufficient_data status."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors.get_trust_trajectory()
        assert result["status"] == "insufficient_data"
        assert result["trajectory"] == "unknown"
        assert result["signal_count"] == 0

    def test_strongly_building_over_70_percent(self) -> None:
        """Test >70% building signals returns strongly_building trajectory."""
        behaviors = TrustBuildingBehaviors()
        for _ in range(8):
            behaviors.trust_signals.append(TrustSignal(signal_type="building", behavior="test"))
        for _ in range(2):
            behaviors.trust_signals.append(TrustSignal(signal_type="eroding", behavior="test"))
        result = behaviors.get_trust_trajectory()
        assert result["status"] == "active"
        assert result["trajectory"] == "strongly_building"
        assert result["building_ratio"] == 0.8
        assert result["building_signals"] == 8
        assert result["eroding_signals"] == 2

    def test_building_trajectory_51_to_70_percent(self) -> None:
        """Test 51-70% building signals returns building trajectory."""
        behaviors = TrustBuildingBehaviors()
        for _ in range(6):
            behaviors.trust_signals.append(TrustSignal(signal_type="building", behavior="test"))
        for _ in range(4):
            behaviors.trust_signals.append(TrustSignal(signal_type="eroding", behavior="test"))
        result = behaviors.get_trust_trajectory()
        assert result["trajectory"] == "building"

    def test_mixed_trajectory_31_to_50_percent(self) -> None:
        """Test 31-50% building signals returns mixed trajectory."""
        behaviors = TrustBuildingBehaviors()
        for _ in range(4):
            behaviors.trust_signals.append(TrustSignal(signal_type="building", behavior="test"))
        for _ in range(6):
            behaviors.trust_signals.append(TrustSignal(signal_type="eroding", behavior="test"))
        result = behaviors.get_trust_trajectory()
        assert result["trajectory"] == "mixed"

    def test_eroding_trajectory_30_percent_or_below(self) -> None:
        """Test <=30% building signals returns eroding trajectory."""
        behaviors = TrustBuildingBehaviors()
        for _ in range(2):
            behaviors.trust_signals.append(TrustSignal(signal_type="building", behavior="test"))
        for _ in range(8):
            behaviors.trust_signals.append(TrustSignal(signal_type="eroding", behavior="test"))
        result = behaviors.get_trust_trajectory()
        assert result["trajectory"] == "eroding"

    def test_all_building_signals(self) -> None:
        """Test 100% building signals returns strongly_building."""
        behaviors = TrustBuildingBehaviors()
        for _ in range(5):
            behaviors.trust_signals.append(TrustSignal(signal_type="building", behavior="test"))
        result = behaviors.get_trust_trajectory()
        assert result["trajectory"] == "strongly_building"
        assert result["building_ratio"] == 1.0

    def test_all_eroding_signals(self) -> None:
        """Test 0% building signals returns eroding."""
        behaviors = TrustBuildingBehaviors()
        for _ in range(5):
            behaviors.trust_signals.append(TrustSignal(signal_type="eroding", behavior="test"))
        result = behaviors.get_trust_trajectory()
        assert result["trajectory"] == "eroding"
        assert result["building_ratio"] == 0.0

    def test_recent_behaviors_returns_last_five(self) -> None:
        """Test recent_behaviors returns last 5 behavior names."""
        behaviors = TrustBuildingBehaviors()
        for i in range(7):
            behaviors.trust_signals.append(
                TrustSignal(signal_type="building", behavior=f"action_{i}"),
            )
        result = behaviors.get_trust_trajectory()
        assert result["recent_behaviors"] == [
            "action_2",
            "action_3",
            "action_4",
            "action_5",
            "action_6",
        ]

    def test_single_signal(self) -> None:
        """Test trajectory with single building signal."""
        behaviors = TrustBuildingBehaviors()
        behaviors.trust_signals.append(TrustSignal(signal_type="building", behavior="test"))
        result = behaviors.get_trust_trajectory()
        assert result["signal_count"] == 1
        assert result["trajectory"] == "strongly_building"


class TestDetermineFormat:
    """Tests for _determine_format helper method."""

    def test_executive_roles(self) -> None:
        """Test executive, manager, director return executive_summary."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._determine_format("executive", "any") == "executive_summary"
        assert behaviors._determine_format("manager", "any") == "executive_summary"
        assert behaviors._determine_format("director", "any") == "executive_summary"

    def test_technical_roles(self) -> None:
        """Test developer, engineer, analyst return technical_detail."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._determine_format("developer", "any") == "technical_detail"
        assert behaviors._determine_format("engineer", "any") == "technical_detail"
        assert behaviors._determine_format("analyst", "any") == "technical_detail"

    def test_coordination_roles(self) -> None:
        """Test team_lead, coordinator return action_oriented."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._determine_format("team_lead", "any") == "action_oriented"
        assert behaviors._determine_format("coordinator", "any") == "action_oriented"

    def test_unknown_role_returns_general(self) -> None:
        """Test unknown role returns general format."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._determine_format("intern", "any") == "general"
        assert behaviors._determine_format("unknown_role", "any") == "general"


class TestAssessStressLevel:
    """Tests for _assess_stress_level helper method."""

    def test_zero_indicators_returns_low(self) -> None:
        """Test empty dict returns low stress."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._assess_stress_level({}) == "low"

    def test_one_indicator_returns_low(self) -> None:
        """Test 1 indicator returns low stress."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._assess_stress_level({"a": 1}) == "low"

    def test_two_indicators_returns_moderate(self) -> None:
        """Test 2 indicators returns moderate stress."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._assess_stress_level({"a": 1, "b": 2}) == "moderate"

    def test_three_indicators_returns_high(self) -> None:
        """Test 3 indicators returns high stress."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._assess_stress_level({"a": 1, "b": 2, "c": 3}) == "high"

    def test_four_indicators_returns_critical(self) -> None:
        """Test 4 indicators returns critical stress."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._assess_stress_level({"a": 1, "b": 2, "c": 3, "d": 4}) == "critical"

    def test_five_indicators_returns_critical(self) -> None:
        """Test 5+ indicators still returns critical."""
        behaviors = TrustBuildingBehaviors()
        assert (
            behaviors._assess_stress_level({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}) == "critical"
        )


class TestClassifyStruggle:
    """Tests for _classify_struggle helper method."""

    def test_repeated_errors_returns_execution(self) -> None:
        """Test repeated_errors indicator returns execution type."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._classify_struggle({"repeated_errors": 5}) == "execution"

    def test_time_on_task_returns_comprehension(self) -> None:
        """Test time_on_task indicator returns comprehension type."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._classify_struggle({"time_on_task": 45}) == "comprehension"

    def test_other_indicators_returns_general(self) -> None:
        """Test other indicators return general type."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._classify_struggle({"frustration": 1}) == "general"

    def test_repeated_errors_precedence(self) -> None:
        """Test repeated_errors takes precedence over time_on_task."""
        behaviors = TrustBuildingBehaviors()
        assert (
            behaviors._classify_struggle({"repeated_errors": 3, "time_on_task": 60}) == "execution"
        )

    def test_empty_indicators_returns_general(self) -> None:
        """Test empty indicators dict returns general."""
        behaviors = TrustBuildingBehaviors()
        assert behaviors._classify_struggle({}) == "general"


class TestExtractHelpers:
    """Tests for _extract helper methods."""

    def test_extract_key_metrics_numeric_values(self) -> None:
        """Test _extract_key_metrics extracts numeric fields."""
        behaviors = TrustBuildingBehaviors()
        data = {"revenue": 1000, "growth": 15.5, "name": "test", "count": 42}
        metrics = behaviors._extract_key_metrics(data)
        assert len(metrics) == 3
        assert "revenue: 1000" in metrics

    def test_extract_key_metrics_max_five(self) -> None:
        """Test _extract_key_metrics returns at most 5 items."""
        behaviors = TrustBuildingBehaviors()
        data = {f"metric_{i}": i for i in range(10)}
        metrics = behaviors._extract_key_metrics(data)
        assert len(metrics) <= 5

    def test_extract_key_metrics_no_numeric(self) -> None:
        """Test _extract_key_metrics with no numeric values returns empty."""
        behaviors = TrustBuildingBehaviors()
        data = {"name": "test", "status": "ok"}
        metrics = behaviors._extract_key_metrics(data)
        assert metrics == []

    def test_extract_highlights(self) -> None:
        """Test _extract_highlights returns field count message."""
        behaviors = TrustBuildingBehaviors()
        highlights = behaviors._extract_highlights({"a": 1, "b": 2, "c": 3})
        assert len(highlights) == 1
        assert "3 fields" in highlights[0]

    def test_extract_recommendations(self) -> None:
        """Test _extract_recommendations returns default recommendation."""
        behaviors = TrustBuildingBehaviors()
        recs = behaviors._extract_recommendations({})
        assert len(recs) == 1
        assert "Review" in recs[0]

    def test_extract_technical_notes(self) -> None:
        """Test _extract_technical_notes returns data type info."""
        behaviors = TrustBuildingBehaviors()
        notes = behaviors._extract_technical_notes({"x": 1})
        assert len(notes) == 1
        assert "dict" in notes[0]

    def test_extract_immediate_actions_with_key(self) -> None:
        """Test _extract_immediate_actions with actions key returns top 5."""
        behaviors = TrustBuildingBehaviors()
        data = {"actions": ["a1", "a2", "a3", "a4", "a5", "a6"]}
        result = behaviors._extract_immediate_actions(data)
        assert len(result) == 5
        assert result == ["a1", "a2", "a3", "a4", "a5"]

    def test_extract_immediate_actions_without_key(self) -> None:
        """Test _extract_immediate_actions without actions key returns default."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors._extract_immediate_actions({"other": "data"})
        assert result == ["Review data and determine next steps"]

    def test_extract_priorities_with_key(self) -> None:
        """Test _extract_priorities with priorities key."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors._extract_priorities({"priorities": ["p1", "p2"]})
        assert result == ["p1", "p2"]

    def test_extract_priorities_without_key(self) -> None:
        """Test _extract_priorities without priorities key returns empty list."""
        behaviors = TrustBuildingBehaviors()
        result = behaviors._extract_priorities({"other": "data"})
        assert result == []


class TestReset:
    """Tests for reset method."""

    def test_reset_clears_signals(self) -> None:
        """Test reset clears all trust signals."""
        behaviors = TrustBuildingBehaviors()
        behaviors.trust_signals.append(TrustSignal(signal_type="building", behavior="test"))
        assert len(behaviors.trust_signals) == 1
        behaviors.reset()
        assert len(behaviors.trust_signals) == 0

    def test_reset_on_empty(self) -> None:
        """Test reset on already empty signals list is safe."""
        behaviors = TrustBuildingBehaviors()
        behaviors.reset()
        assert behaviors.trust_signals == []


class TestRecordTrustSignal:
    """Tests for _record_trust_signal helper method."""

    def test_records_signal_with_evidence(self) -> None:
        """Test recording a trust signal with evidence."""
        behaviors = TrustBuildingBehaviors()
        behaviors._record_trust_signal(
            signal_type="building",
            behavior="test_behavior",
            evidence="test evidence",
        )
        assert len(behaviors.trust_signals) == 1
        signal = behaviors.trust_signals[0]
        assert signal.signal_type == "building"
        assert signal.behavior == "test_behavior"
        assert signal.evidence == "test evidence"

    def test_records_signal_without_evidence(self) -> None:
        """Test recording a trust signal without evidence."""
        behaviors = TrustBuildingBehaviors()
        behaviors._record_trust_signal(signal_type="eroding", behavior="missed")
        assert len(behaviors.trust_signals) == 1
        assert behaviors.trust_signals[0].evidence is None


# =============================================================================
# MODULE 2: templates.py
# =============================================================================


class TestTemplatesConstant:
    """Tests for the TEMPLATES constant dict."""

    def test_templates_has_four_entries(self) -> None:
        """Test TEMPLATES contains exactly 4 templates."""
        assert len(TEMPLATES) == 4

    def test_templates_keys(self) -> None:
        """Test TEMPLATES has expected keys."""
        assert set(TEMPLATES.keys()) == {
            "minimal",
            "python-cli",
            "python-fastapi",
            "python-agent",
        }

    def test_each_template_has_name_description_files(self) -> None:
        """Test each template has name, description, and files keys."""
        for tid, template in TEMPLATES.items():
            assert "name" in template, f"Template {tid} missing 'name'"
            assert "description" in template, f"Template {tid} missing 'description'"
            assert "files" in template, f"Template {tid} missing 'files'"

    def test_each_template_files_is_dict(self) -> None:
        """Test each template's files value is a dict."""
        for tid, template in TEMPLATES.items():
            assert isinstance(template["files"], dict), f"Template {tid} files not dict"


class TestListTemplates:
    """Tests for list_templates function."""

    def test_returns_all_four_templates(self) -> None:
        """Test list_templates returns exactly 4 templates."""
        templates = list_templates()
        assert len(templates) == 4

    def test_each_has_id_name_description(self) -> None:
        """Test each template dict has id, name, and description keys."""
        for t in list_templates():
            assert "id" in t
            assert "name" in t
            assert "description" in t

    def test_template_ids_match_expected(self) -> None:
        """Test template IDs match expected set."""
        ids = {t["id"] for t in list_templates()}
        assert ids == {"minimal", "python-cli", "python-fastapi", "python-agent"}


class TestScaffoldProject:
    """Tests for scaffold_project function using tmp_path for file operations."""

    def test_minimal_creates_config_file(self, tmp_path: Path) -> None:
        """Test scaffold minimal template creates attune.config.yml."""
        target = tmp_path / "my_project"
        result = scaffold_project("minimal", "my_project", str(target))
        assert result["success"] is True
        assert result["template"] == "minimal"
        assert result["project_name"] == "my_project"
        assert (target / "attune.config.yml").exists()

    def test_minimal_creates_claude_md(self, tmp_path: Path) -> None:
        """Test scaffold minimal template creates .claude/CLAUDE.md."""
        target = tmp_path / "proj"
        scaffold_project("minimal", "proj", str(target))
        assert (target / ".claude" / "CLAUDE.md").exists()

    def test_minimal_creates_patterns_directory(self, tmp_path: Path) -> None:
        """Test scaffold creates patterns directory."""
        target = tmp_path / "proj"
        scaffold_project("minimal", "proj", str(target))
        assert (target / "patterns").is_dir()

    def test_unknown_template_returns_error(self, tmp_path: Path) -> None:
        """Test scaffold with unknown template returns error with available list."""
        result = scaffold_project("nonexistent", "test_proj", str(tmp_path / "out"))
        assert result["success"] is False
        assert "Unknown template" in result["error"]
        assert "available" in result
        assert isinstance(result["available"], list)

    def test_nonempty_dir_without_force_returns_error(self, tmp_path: Path) -> None:
        """Test scaffold to non-empty dir without force returns error."""
        target = tmp_path / "existing"
        target.mkdir()
        (target / "somefile.txt").write_text("content")
        result = scaffold_project("minimal", "test_proj", str(target))
        assert result["success"] is False
        assert "not empty" in result["error"]

    def test_nonempty_dir_with_force_succeeds(self, tmp_path: Path) -> None:
        """Test scaffold to non-empty dir with force=True succeeds."""
        target = tmp_path / "existing"
        target.mkdir()
        (target / "somefile.txt").write_text("content")
        result = scaffold_project("minimal", "test_proj", str(target), force=True)
        assert result["success"] is True

    def test_empty_dir_works(self, tmp_path: Path) -> None:
        """Test scaffold to empty existing dir works without force."""
        target = tmp_path / "empty_dir"
        target.mkdir()
        result = scaffold_project("minimal", "test_proj", str(target))
        assert result["success"] is True

    def test_replaces_project_name_placeholder(self, tmp_path: Path) -> None:
        """Test scaffold replaces {{project_name}} in file content."""
        target = tmp_path / "my_app"
        scaffold_project("minimal", "my_app", str(target))
        config_content = (target / "attune.config.yml").read_text()
        assert "my_app" in config_content
        assert "{{project_name}}" not in config_content

    def test_replaces_project_name_class_placeholder(self, tmp_path: Path) -> None:
        """Test scaffold replaces {{project_name_class}} in python-agent template."""
        target = tmp_path / "my_agent"
        result = scaffold_project("python-agent", "my_agent", str(target))
        assert result["success"] is True
        agent_file = target / "my_agent" / "agent.py"
        assert agent_file.exists()
        content = agent_file.read_text()
        assert "MyAgent" in content
        assert "{{project_name_class}}" not in content

    def test_project_name_class_with_hyphens(self, tmp_path: Path) -> None:
        """Test project name with hyphens gets converted to CamelCase class name."""
        target = tmp_path / "my-cool-agent"
        result = scaffold_project("python-agent", "my-cool-agent", str(target))
        assert result["success"] is True
        agent_file = target / "my-cool-agent" / "agent.py"
        content = agent_file.read_text()
        assert "MyCoolAgent" in content

    def test_gitignore_additions_append_existing(self, tmp_path: Path) -> None:
        """Test scaffold appends .gitignore_additions to existing .gitignore."""
        target = tmp_path / "proj_with_gitignore"
        target.mkdir(parents=True)
        gitignore = target / ".gitignore"
        gitignore.write_text("# existing\n*.pyc\n")
        result = scaffold_project("minimal", "test_proj", str(target), force=True)
        assert result["success"] is True
        content = gitignore.read_text()
        assert "# existing" in content
        assert ".attune/" in content

    def test_gitignore_additions_create_new(self, tmp_path: Path) -> None:
        """Test scaffold creates .gitignore from additions when none exists."""
        target = tmp_path / "new_proj"
        result = scaffold_project("minimal", "new_proj", str(target))
        assert result["success"] is True
        assert ".gitignore" in result["files_created"]

    def test_python_cli_creates_cli_module(self, tmp_path: Path) -> None:
        """Test python-cli template creates the CLI module files."""
        target = tmp_path / "mycli"
        result = scaffold_project("python-cli", "mycli", str(target))
        assert result["success"] is True
        assert (target / "mycli" / "__init__.py").exists()
        assert (target / "mycli" / "cli.py").exists()
        assert (target / "pyproject.toml").exists()
        assert (target / "README.md").exists()

    def test_python_fastapi_creates_main_module(self, tmp_path: Path) -> None:
        """Test python-fastapi template creates main.py."""
        target = tmp_path / "myapi"
        result = scaffold_project("python-fastapi", "myapi", str(target))
        assert result["success"] is True
        assert (target / "myapi" / "main.py").exists()
        assert (target / "myapi" / "__init__.py").exists()

    def test_python_agent_creates_agent_and_tests(self, tmp_path: Path) -> None:
        """Test python-agent template creates agent.py and test files."""
        target = tmp_path / "mybot"
        result = scaffold_project("python-agent", "mybot", str(target))
        assert result["success"] is True
        assert (target / "mybot" / "agent.py").exists()
        assert (target / "tests" / "__init__.py").exists()
        assert (target / "tests" / "test_agent.py").exists()

    def test_returns_next_steps(self, tmp_path: Path) -> None:
        """Test scaffold result includes next_steps list."""
        target = tmp_path / "proj"
        result = scaffold_project("minimal", "proj", str(target))
        assert "next_steps" in result
        assert len(result["next_steps"]) > 0

    def test_returns_target_dir(self, tmp_path: Path) -> None:
        """Test scaffold result includes target_dir."""
        target = tmp_path / "proj"
        result = scaffold_project("minimal", "proj", str(target))
        assert result["target_dir"] == str(target)

    def test_default_target_dir_uses_project_name(self, tmp_path: Path, monkeypatch) -> None:
        """Test scaffold uses project_name as default target dir when none given."""
        monkeypatch.chdir(tmp_path)
        result = scaffold_project("minimal", "auto_dir")
        assert result["success"] is True
        assert result["target_dir"] == "auto_dir"

    def test_files_created_list_not_empty(self, tmp_path: Path) -> None:
        """Test files_created list is populated."""
        target = tmp_path / "proj"
        result = scaffold_project("minimal", "proj", str(target))
        assert len(result["files_created"]) > 0

    def test_invalid_template_structure_returns_error(self, tmp_path: Path) -> None:
        """Test invalid template files structure returns error."""
        with patch.dict(
            "attune.templates.TEMPLATES",
            {"bad": {"name": "Bad", "description": "Bad template", "files": "not_a_dict"}},
        ):
            result = scaffold_project("bad", "proj", str(tmp_path / "proj"))
            assert result["success"] is False
            assert "Invalid template structure" in result["error"]


class TestCmdNew:
    """Tests for cmd_new CLI command handler."""

    def test_list_only_prints_templates(self, capsys) -> None:
        """Test cmd_new with list=True prints templates and returns 0."""
        args = SimpleNamespace(template=None, name=None, output=None, force=False, list=True)
        result = cmd_new(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Available Templates" in captured.out

    def test_no_template_or_name_returns_1(self, capsys) -> None:
        """Test cmd_new without template or name returns 1."""
        args = SimpleNamespace(template=None, name=None, output=None, force=False, list=False)
        result = cmd_new(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_template_without_name_returns_1(self, capsys) -> None:
        """Test cmd_new with template but no name returns 1."""
        args = SimpleNamespace(template="minimal", name=None, output=None, force=False, list=False)
        result = cmd_new(args)
        assert result == 1

    def test_valid_args_returns_0(self, tmp_path: Path, capsys) -> None:
        """Test cmd_new with valid template and name returns 0."""
        args = SimpleNamespace(
            template="minimal",
            name="test_project",
            output=str(tmp_path / "test_project"),
            force=False,
            list=False,
        )
        result = cmd_new(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Project created" in captured.out
        assert "Files created" in captured.out
        assert "Next steps" in captured.out

    def test_unknown_template_returns_1(self, capsys) -> None:
        """Test cmd_new with unknown template returns 1 and shows error."""
        args = SimpleNamespace(
            template="nonexistent",
            name="proj",
            output=None,
            force=False,
            list=False,
        )
        result = cmd_new(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "Available templates" in captured.out

    def test_getattr_defaults_for_missing_attrs(self, capsys) -> None:
        """Test cmd_new handles SimpleNamespace without expected attributes."""
        args = SimpleNamespace()
        result = cmd_new(args)
        assert result == 1

    def test_list_only_shows_all_template_ids(self, capsys) -> None:
        """Test listing shows template IDs for each known template."""
        args = SimpleNamespace(template=None, name=None, output=None, force=False, list=True)
        cmd_new(args)
        captured = capsys.readouterr()
        assert "minimal" in captured.out
        assert "python-cli" in captured.out


# =============================================================================
# MODULE 3: code_review_adapters.py
# =============================================================================


class TestCheckCrewAvailable:
    """Tests for _check_crew_available function."""

    def test_returns_false_when_import_fails(self) -> None:
        """Test _check_crew_available returns False when crew can't be imported."""
        from attune.workflows.code_review_adapters import _check_crew_available

        # Force an ImportError by patching builtins.__import__
        original_import = (
            __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
        )

        def mock_import(name, *args, **kwargs):
            if "agent_factory.crews" in name:
                raise ImportError("No module named 'attune.agent_factory.crews'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = _check_crew_available()
            assert result is False

    def test_returns_true_when_import_succeeds(self) -> None:
        """Test _check_crew_available returns True when crew can be imported."""
        from attune.workflows.code_review_adapters import _check_crew_available

        mock_module = MagicMock()
        with patch.dict("sys.modules", {"attune.agent_factory.crews": mock_module}):
            mock_module.CodeReviewCrew = MagicMock()
            result = _check_crew_available()
            assert result is True


class TestGetCrewReview:
    """Tests for _get_crew_review async function."""

    @staticmethod
    def _run_async(coro):
        """Run an async coroutine in a fresh event loop to avoid pollution."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_returns_none_when_crew_unavailable(self) -> None:
        """Test _get_crew_review returns None when crew is not available."""
        from attune.workflows.code_review_adapters import _get_crew_review

        with patch(
            "attune.workflows.code_review_adapters._check_crew_available",
            return_value=False,
        ):
            result = self._run_async(_get_crew_review(diff="some diff"))
            assert result is None

    def test_returns_none_on_timeout(self) -> None:
        """Test _get_crew_review returns None on timeout."""
        from attune.workflows.code_review_adapters import _get_crew_review

        mock_crew = MagicMock()

        async def slow_review(**kwargs):
            await asyncio.sleep(100)

        mock_crew.return_value.review = slow_review
        mock_config = MagicMock()

        mock_module = MagicMock()
        mock_module.CodeReviewCrew = mock_crew
        mock_module.CodeReviewConfig = mock_config

        with (
            patch(
                "attune.workflows.code_review_adapters._check_crew_available",
                return_value=True,
            ),
            patch.dict(
                "sys.modules",
                {"attune.agent_factory.crews": mock_module},
            ),
        ):
            result = self._run_async(_get_crew_review(diff="diff", timeout=0.01))
            assert result is None

    def test_returns_none_on_exception(self) -> None:
        """Test _get_crew_review returns None when crew raises an exception."""
        from attune.workflows.code_review_adapters import _get_crew_review

        mock_crew = MagicMock()

        async def failing_review(**kwargs):
            raise RuntimeError("Crew failed")

        mock_crew.return_value.review = failing_review
        mock_config = MagicMock()

        mock_module = MagicMock()
        mock_module.CodeReviewCrew = mock_crew
        mock_module.CodeReviewConfig = mock_config

        with (
            patch(
                "attune.workflows.code_review_adapters._check_crew_available",
                return_value=True,
            ),
            patch.dict(
                "sys.modules",
                {"attune.agent_factory.crews": mock_module},
            ),
        ):
            result = self._run_async(_get_crew_review(diff="diff"))
            assert result is None

    def test_returns_report_on_success(self) -> None:
        """Test _get_crew_review returns report on successful review."""
        from attune.workflows.code_review_adapters import _get_crew_review

        mock_report = MagicMock()

        async def good_review(**kwargs):
            return mock_report

        mock_crew_cls = MagicMock()
        mock_crew_cls.return_value.review = good_review
        mock_config_cls = MagicMock()

        mock_module = MagicMock()
        mock_module.CodeReviewCrew = mock_crew_cls
        mock_module.CodeReviewConfig = mock_config_cls

        with (
            patch(
                "attune.workflows.code_review_adapters._check_crew_available",
                return_value=True,
            ),
            patch.dict(
                "sys.modules",
                {"attune.agent_factory.crews": mock_module},
            ),
        ):
            result = self._run_async(
                _get_crew_review(diff="diff", files_changed=["a.py"], config={"strict": True}),
            )
            assert result is mock_report


class TestCrewReportToWorkflowFormat:
    """Tests for crew_report_to_workflow_format function."""

    @staticmethod
    def _make_mock_report(
        findings: list | None = None,
        verdict: str = "approve",
        quality_score: int = 85,
        has_blocking: bool = False,
        summary: str = "Looks good",
        agents_used: list | None = None,
        memory_graph_hits: int = 0,
        duration: float = 1.5,
        metadata: dict | None = None,
    ) -> MagicMock:
        """Create a mock CodeReviewReport for testing.

        Args:
            findings: List of mock findings
            verdict: Verdict value string
            quality_score: Quality score integer
            has_blocking: Whether blocking issues exist
            summary: Summary text
            agents_used: List of agent names
            memory_graph_hits: Count of memory graph hits
            duration: Review duration in seconds
            metadata: Metadata dict

        Returns:
            MagicMock configured as a CodeReviewReport

        """
        report = MagicMock()
        report.findings = findings or []
        report.verdict = MagicMock()
        report.verdict.value = verdict
        report.quality_score = quality_score
        report.has_blocking_issues = has_blocking
        report.summary = summary
        report.agents_used = agents_used or ["reviewer"]
        report.memory_graph_hits = memory_graph_hits
        report.review_duration_seconds = duration
        report.metadata = metadata or {}
        return report

    @staticmethod
    def _make_mock_finding(
        category: str = "security",
        title: str = "SQL Injection",
        description: str = "Possible SQL injection",
        severity: str = "high",
        file_path: str = "app.py",
        line_number: int = 42,
        code_snippet: str = "query = f'SELECT * FROM {table}'",
        suggestion: str = "Use parameterized queries",
        before_code: str = "old_code",
        after_code: str = "new_code",
        confidence: float = 0.95,
    ) -> MagicMock:
        """Create a mock ReviewFinding.

        Args:
            category: Finding category value
            title: Finding title
            description: Finding description
            severity: Severity level value
            file_path: File path of finding
            line_number: Line number of finding
            code_snippet: Relevant code snippet
            suggestion: Fix suggestion
            before_code: Code before fix
            after_code: Code after fix
            confidence: Confidence score

        Returns:
            MagicMock configured as a ReviewFinding

        """
        finding = MagicMock()
        finding.category = MagicMock()
        finding.category.value = category
        finding.title = title
        finding.description = description
        finding.severity = MagicMock()
        finding.severity.value = severity
        finding.file_path = file_path
        finding.line_number = line_number
        finding.code_snippet = code_snippet
        finding.suggestion = suggestion
        finding.before_code = before_code
        finding.after_code = after_code
        finding.confidence = confidence
        return finding

    def test_empty_findings(self) -> None:
        """Test conversion with no findings."""
        from attune.workflows.code_review_adapters import crew_report_to_workflow_format

        report = self._make_mock_report()
        result = crew_report_to_workflow_format(report)
        assert result["crew_enabled"] is True
        assert result["findings"] == []
        assert result["finding_count"] == 0
        assert result["verdict"] == "approve"
        assert result["quality_score"] == 85

    def test_single_finding_conversion(self) -> None:
        """Test converting a report with a single finding."""
        from attune.workflows.code_review_adapters import crew_report_to_workflow_format

        finding = self._make_mock_finding()
        report = self._make_mock_report(findings=[finding])
        result = crew_report_to_workflow_format(report)

        assert result["finding_count"] == 1
        f = result["findings"][0]
        assert f["type"] == "security"
        assert f["title"] == "SQL Injection"
        assert f["severity"] == "high"
        assert f["file"] == "app.py"
        assert f["line"] == 42
        assert f["confidence"] == 0.95

    def test_multiple_findings_with_severity_counts(self) -> None:
        """Test severity breakdown is calculated correctly."""
        from attune.workflows.code_review_adapters import crew_report_to_workflow_format

        findings = [
            self._make_mock_finding(severity="critical"),
            self._make_mock_finding(severity="high"),
            self._make_mock_finding(severity="high"),
            self._make_mock_finding(severity="medium"),
            self._make_mock_finding(severity="low"),
            self._make_mock_finding(severity="info"),
        ]
        report = self._make_mock_report(findings=findings)
        result = crew_report_to_workflow_format(report)

        severity = result["assessment"]["severity_breakdown"]
        assert severity["critical"] == 1
        assert severity["high"] == 2
        assert severity["medium"] == 1
        assert severity["low"] == 1
        assert severity["info"] == 1

    def test_category_breakdown(self) -> None:
        """Test by_category grouping is calculated correctly."""
        from attune.workflows.code_review_adapters import crew_report_to_workflow_format

        findings = [
            self._make_mock_finding(category="security"),
            self._make_mock_finding(category="security"),
            self._make_mock_finding(category="quality"),
        ]
        report = self._make_mock_report(findings=findings)
        result = crew_report_to_workflow_format(report)

        by_cat = result["assessment"]["by_category"]
        assert by_cat["security"] == 2
        assert by_cat["quality"] == 1

    def test_critical_and_high_findings_in_assessment(self) -> None:
        """Test critical and high findings are extracted in assessment."""
        from attune.workflows.code_review_adapters import crew_report_to_workflow_format

        findings = [
            self._make_mock_finding(severity="critical", title="Critical Bug"),
            self._make_mock_finding(severity="high", title="High Issue"),
            self._make_mock_finding(severity="low", title="Minor"),
        ]
        report = self._make_mock_report(findings=findings)
        result = crew_report_to_workflow_format(report)

        assert len(result["assessment"]["critical_findings"]) == 1
        assert len(result["assessment"]["high_findings"]) == 1

    def test_metadata_passthrough(self) -> None:
        """Test metadata fields are passed through correctly."""
        from attune.workflows.code_review_adapters import crew_report_to_workflow_format

        report = self._make_mock_report(
            agents_used=["agent1", "agent2"],
            memory_graph_hits=3,
            duration=5.2,
            metadata={"cost": 0.05},
        )
        result = crew_report_to_workflow_format(report)
        assert result["agents_used"] == ["agent1", "agent2"]
        assert result["memory_graph_hits"] == 3
        assert result["review_duration_seconds"] == 5.2
        assert result["cost"] == 0.05

    def test_cost_defaults_to_zero(self) -> None:
        """Test cost defaults to 0.0 when not in metadata."""
        from attune.workflows.code_review_adapters import crew_report_to_workflow_format

        report = self._make_mock_report(metadata={})
        result = crew_report_to_workflow_format(report)
        assert result["cost"] == 0.0


class TestWorkflowFindingsToCrewFormat:
    """Tests for workflow_findings_to_crew_format function."""

    def test_empty_findings(self) -> None:
        """Test conversion of empty findings list."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        result = workflow_findings_to_crew_format([])
        assert result == []

    def test_single_finding_conversion(self) -> None:
        """Test converting a single workflow finding to crew format."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [
            {
                "title": "SQL Injection",
                "description": "Possible SQL injection in query",
                "severity": "high",
                "type": "sql_injection",
                "file": "app.py",
                "line": 42,
                "code_snippet": "query = ...",
                "suggestion": "Use parameterized queries",
                "confidence": 0.9,
            },
        ]
        result = workflow_findings_to_crew_format(findings)
        assert len(result) == 1
        f = result[0]
        assert f["title"] == "SQL Injection"
        assert f["description"] == "Possible SQL injection in query"
        assert f["severity"] == "high"
        assert f["category"] == "security"
        assert f["file_path"] == "app.py"
        assert f["line_number"] == 42
        assert f["confidence"] == 0.9

    def test_fallback_title_from_type(self) -> None:
        """Test title falls back to type when title key is missing."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [{"type": "xss"}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["title"] == "xss"

    def test_fallback_title_to_unknown(self) -> None:
        """Test title falls back to 'Unknown' when both title and type are missing."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [{}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["title"] == "Unknown"

    def test_fallback_description_from_match(self) -> None:
        """Test description falls back to 'match' when description key is missing."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [{"match": "found a match"}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["description"] == "found a match"

    def test_fallback_code_snippet_from_match(self) -> None:
        """Test code_snippet falls back to match when code_snippet is None."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [{"match": "some code"}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["code_snippet"] == "some code"

    def test_fallback_suggestion_from_remediation(self) -> None:
        """Test suggestion falls back to remediation when suggestion is None."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [{"remediation": "fix this"}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["suggestion"] == "fix this"

    def test_default_severity_is_medium(self) -> None:
        """Test default severity is 'medium' when not provided."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [{"title": "Test"}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["severity"] == "medium"

    def test_default_confidence_is_one(self) -> None:
        """Test default confidence is 1.0 when not provided."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [{"title": "Test"}]
        result = workflow_findings_to_crew_format(findings)
        assert result[0]["confidence"] == 1.0

    def test_multiple_findings(self) -> None:
        """Test converting multiple findings."""
        from attune.workflows.code_review_adapters import workflow_findings_to_crew_format

        findings = [
            {"type": "sql_injection", "file": "a.py", "line": 10},
            {"type": "xss", "file": "b.py", "line": 20},
            {"type": "performance", "file": "c.py", "line": 30},
        ]
        result = workflow_findings_to_crew_format(findings)
        assert len(result) == 3
        assert result[0]["category"] == "security"
        assert result[1]["category"] == "security"
        assert result[2]["category"] == "performance"


class TestMapTypeToCategory:
    """Tests for _map_type_to_category function."""

    def test_security_types(self) -> None:
        """Test security vulnerability types map to 'security'."""
        from attune.workflows.code_review_adapters import _map_type_to_category

        security_types = [
            "sql_injection",
            "xss",
            "command_injection",
            "path_traversal",
            "hardcoded_secret",
            "insecure_random",
        ]
        for vuln_type in security_types:
            assert _map_type_to_category(vuln_type) == "security", f"Failed for {vuln_type}"

    def test_quality_types(self) -> None:
        """Test quality issue types map to 'quality'."""
        from attune.workflows.code_review_adapters import _map_type_to_category

        assert _map_type_to_category("code_smell") == "quality"
        assert _map_type_to_category("complexity") == "quality"
        assert _map_type_to_category("duplicate") == "quality"

    def test_performance_types(self) -> None:
        """Test performance issue types map to 'performance'."""
        from attune.workflows.code_review_adapters import _map_type_to_category

        assert _map_type_to_category("performance") == "performance"
        assert _map_type_to_category("n_plus_one") == "performance"

    def test_architecture_types(self) -> None:
        """Test architecture issue types map to 'architecture'."""
        from attune.workflows.code_review_adapters import _map_type_to_category

        assert _map_type_to_category("architecture") == "architecture"
        assert _map_type_to_category("design") == "architecture"
        assert _map_type_to_category("solid") == "architecture"

    def test_testing_types(self) -> None:
        """Test testing issue types map to 'testing'."""
        from attune.workflows.code_review_adapters import _map_type_to_category

        assert _map_type_to_category("test") == "testing"
        assert _map_type_to_category("coverage") == "testing"

    def test_unknown_type_maps_to_other(self) -> None:
        """Test unknown type maps to 'other'."""
        from attune.workflows.code_review_adapters import _map_type_to_category

        assert _map_type_to_category("something_random") == "other"
        assert _map_type_to_category("") == "other"

    def test_case_insensitive(self) -> None:
        """Test that type mapping is case insensitive."""
        from attune.workflows.code_review_adapters import _map_type_to_category

        assert _map_type_to_category("SQL_INJECTION") == "security"
        assert _map_type_to_category("XSS") == "security"
        assert _map_type_to_category("Performance") == "performance"


class TestMergeVerdicts:
    """Tests for _merge_verdicts function."""

    def test_approve_approve(self) -> None:
        """Test merging two approve verdicts returns approve."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("approve", "approve") == "approve"

    def test_reject_approve(self) -> None:
        """Test reject + approve returns reject (more severe)."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("reject", "approve") == "reject"

    def test_approve_reject(self) -> None:
        """Test approve + reject returns reject."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("approve", "reject") == "reject"

    def test_request_changes_approve(self) -> None:
        """Test request_changes + approve returns request_changes."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("request_changes", "approve") == "request_changes"

    def test_approve_with_suggestions_approve(self) -> None:
        """Test approve_with_suggestions + approve returns approve_with_suggestions."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("approve_with_suggestions", "approve") == "approve_with_suggestions"

    def test_reject_request_changes(self) -> None:
        """Test reject is more severe than request_changes."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("reject", "request_changes") == "reject"

    def test_hyphenated_verdicts_normalized(self) -> None:
        """Test hyphenated verdict strings are normalized to underscores."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("request-changes", "approve") == "request_changes"

    def test_unknown_verdict_defaults_to_approve(self) -> None:
        """Test unknown verdict defaults to approve index (3)."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("unknown_verdict", "approve") == "approve"

    def test_case_insensitive(self) -> None:
        """Test verdicts are case insensitive."""
        from attune.workflows.code_review_adapters import _merge_verdicts

        assert _merge_verdicts("REJECT", "APPROVE") == "reject"


class TestMergeCodeReviewResults:
    """Tests for merge_code_review_results function."""

    def test_both_none_returns_defaults(self) -> None:
        """Test both inputs None returns default approved result."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        result = merge_code_review_results(None, None)
        assert result["findings"] == []
        assert result["quality_score"] == 100
        assert result["verdict"] == "approve"
        assert result["merged"] is False

    def test_crew_only(self) -> None:
        """Test crew_report only (workflow_findings is None)."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {"crew_enabled": True, "findings": [{"type": "bug"}], "quality_score": 80}
        result = merge_code_review_results(crew, None)
        assert result["merged"] is False
        assert result["crew_enabled"] is True
        assert result["findings"] == [{"type": "bug"}]

    def test_workflow_only(self) -> None:
        """Test workflow_findings only (crew_report is None)."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        wf = {"findings": [{"type": "xss"}], "security_score": 70}
        result = merge_code_review_results(None, wf)
        assert result["merged"] is False
        assert result["crew_enabled"] is False
        assert result["findings"] == [{"type": "xss"}]

    def test_merge_deduplicates_by_file_line_type(self) -> None:
        """Test merging deduplicates findings by (file, line, type)."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [{"file": "a.py", "line": 10, "type": "bug", "source": "crew"}],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "ok",
            "agents_used": ["r1"],
            "assessment": {"severity_breakdown": {"critical": 0, "high": 0, "medium": 1, "low": 0}},
        }
        wf = {
            "findings": [
                {"file": "a.py", "line": 10, "type": "bug", "source": "wf"},
                {"file": "b.py", "line": 20, "type": "xss", "source": "wf"},
            ],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 1}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["merged"] is True
        assert result["finding_count"] == 2
        sources = [f.get("source") for f in result["findings"]]
        assert "crew" in sources
        assert "wf" in sources

    def test_merge_weighted_quality_score(self) -> None:
        """Test merged quality score is weighted average (70% crew, 30% workflow)."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 100,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {}},
        }
        wf = {
            "findings": [],
            "security_score": 50,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        expected_score = 100 * 0.7 + 50 * 0.3
        assert result["quality_score"] == expected_score

    def test_merge_takes_more_severe_verdict(self) -> None:
        """Test merged verdict is the more severe of the two."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "reject",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["verdict"] == "reject"

    def test_merge_severity_sums_counts(self) -> None:
        """Test merged severity counts sum from each source (QLT-05)."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {"critical": 1, "high": 0, "medium": 2, "low": 0}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {"critical": 0, "high": 3, "medium": 1, "low": 5}},
        }
        result = merge_code_review_results(crew, wf)
        severity = result["assessment"]["severity_breakdown"]
        assert severity["critical"] == 1
        assert severity["high"] == 3
        assert severity["medium"] == 3
        assert severity["low"] == 5

    def test_merge_has_blocking_issues_with_critical(self) -> None:
        """Test has_blocking_issues is True when critical > 0."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {"critical": 1, "high": 0, "medium": 0, "low": 0}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["has_blocking_issues"] is True

    def test_merge_has_blocking_issues_with_many_high(self) -> None:
        """Test has_blocking_issues is True when high > 3."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {"critical": 0, "high": 4, "medium": 0, "low": 0}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["has_blocking_issues"] is True

    def test_merge_no_blocking_issues_low_counts(self) -> None:
        """Test has_blocking_issues is False when counts are low."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 90,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {"critical": 0, "high": 2, "medium": 3, "low": 5}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["has_blocking_issues"] is False

    def test_merge_includes_crew_summary_and_agents(self) -> None:
        """Test merged result includes crew_summary and agents_used."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "All good",
            "agents_used": ["reviewer", "security_checker"],
            "assessment": {"severity_breakdown": {}},
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        assert result["crew_summary"] == "All good"
        assert result["agents_used"] == ["reviewer", "security_checker"]

    def test_merge_with_missing_assessment_keys(self) -> None:
        """Test merge handles missing assessment and severity_breakdown keys."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
        }
        wf = {
            "findings": [],
            "security_score": 90,
            "verdict": "approve",
        }
        result = merge_code_review_results(crew, wf)
        assert result["merged"] is True
        assert "severity_breakdown" in result["assessment"]

    def test_merge_with_zero_wf_score(self) -> None:
        """Test merge when workflow security_score is 0 (falsy)."""
        from attune.workflows.code_review_adapters import merge_code_review_results

        crew = {
            "findings": [],
            "quality_score": 80,
            "verdict": "approve",
            "summary": "",
            "agents_used": [],
            "assessment": {"severity_breakdown": {}},
        }
        wf = {
            "findings": [],
            "security_score": 0,
            "verdict": "approve",
            "assessment": {"severity_breakdown": {}},
        }
        result = merge_code_review_results(crew, wf)
        # When wf_score is 0 (falsy), it should use crew_score only
        assert result["quality_score"] == 80
