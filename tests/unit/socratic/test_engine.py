"""Tests for the Socratic engine module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


class TestSocraticWorkflowBuilder:
    """Tests for SocraticWorkflowBuilder class."""

    def test_create_builder(self):
        """Test creating a workflow builder."""
        from attune.socratic.engine import SocraticWorkflowBuilder

        builder = SocraticWorkflowBuilder()
        assert builder is not None

    def test_start_session(self):
        """Test starting a new session."""
        from attune.socratic.engine import SocraticWorkflowBuilder
        from attune.socratic.session import SessionState

        builder = SocraticWorkflowBuilder()
        session = builder.start_session()

        assert session is not None
        assert session.state == SessionState.AWAITING_GOAL

    def test_start_session_with_goal(self, sample_goal):
        """Test starting a session with initial goal."""
        from attune.socratic.engine import SocraticWorkflowBuilder
        from attune.socratic.session import SessionState

        builder = SocraticWorkflowBuilder()
        session = builder.start_session(sample_goal)

        assert session.goal == sample_goal
        assert session.state in [SessionState.ANALYZING_GOAL, SessionState.AWAITING_ANSWERS]

    def test_set_goal(self):
        """Test setting goal on existing session."""
        from attune.socratic.engine import SocraticWorkflowBuilder

        builder = SocraticWorkflowBuilder()
        session = builder.start_session()

        session = builder.set_goal(session, "I want to automate testing")

        assert session.goal == "I want to automate testing"
        # After set_goal, goal_analysis should be populated
        assert session.goal_analysis is not None
        assert session.goal_analysis.domain is not None

    def test_get_next_questions(self, sample_session):
        """Test getting next questions."""
        from attune.socratic.engine import SocraticWorkflowBuilder
        from attune.socratic.session import SessionState

        builder = SocraticWorkflowBuilder()
        sample_session.state = SessionState.AWAITING_ANSWERS

        form = builder.get_next_questions(sample_session)

        assert form is not None
        assert len(form.fields) > 0

    def test_submit_answers(self, sample_session, sample_answers):
        """Test submitting answers."""
        from attune.socratic.engine import SocraticWorkflowBuilder

        builder = SocraticWorkflowBuilder()
        session = builder.submit_answers(sample_session, sample_answers)

        # After submit_answers, requirements should be updated
        assert session.requirements is not None

    def test_is_ready_to_generate(self, sample_session):
        """Test checking if ready to generate."""
        from attune.socratic.engine import SocraticWorkflowBuilder
        from attune.socratic.session import SessionState

        builder = SocraticWorkflowBuilder()

        # Not ready in AWAITING_ANSWERS state
        sample_session.state = SessionState.AWAITING_ANSWERS
        assert not builder.is_ready_to_generate(sample_session)

        # Ready in READY_TO_GENERATE state
        sample_session.state = SessionState.READY_TO_GENERATE
        assert builder.is_ready_to_generate(sample_session)

    def test_generate_workflow(self):
        """Test generating a workflow."""
        from attune.socratic.engine import SocraticWorkflowBuilder
        from attune.socratic.session import SessionState

        builder = SocraticWorkflowBuilder()

        # Create a session ready for generation
        session = builder.start_session("Automate code reviews for Python")
        session = builder.submit_answers(
            session,
            {
                "languages": ["python"],
                "quality_focus": ["security", "maintainability"],
            },
        )
        session.state = SessionState.READY_TO_GENERATE

        workflow = builder.generate_workflow(session)

        assert workflow is not None
        assert workflow.blueprint is not None
        assert len(workflow.blueprint.agents) > 0

    def test_get_session_summary(self, sample_session):
        """Test getting session summary."""
        from attune.socratic.engine import SocraticWorkflowBuilder

        builder = SocraticWorkflowBuilder()
        summary = builder.get_session_summary(sample_session)

        assert summary is not None
        assert "session_id" in summary
        assert "state" in summary


class TestDetectDomainFunction:
    """Tests for the detect_domain module-level function."""

    def test_detect_code_review_domain(self):
        """Test domain detection for code review."""
        from attune.socratic.engine import detect_domain

        domain, confidence = detect_domain("I want to review code quality")

        assert domain == "code_review"
        assert confidence > 0

    def test_detect_security_domain(self):
        """Test domain detection for security."""
        from attune.socratic.engine import detect_domain

        domain, confidence = detect_domain("Scan for security vulnerabilities")

        assert domain == "security"
        assert confidence > 0

    def test_detect_testing_domain(self):
        """Test domain detection for testing."""
        from attune.socratic.engine import detect_domain

        domain, confidence = detect_domain("Generate unit tests for coverage")

        assert domain == "testing"
        assert confidence > 0

    def test_detect_documentation_domain(self):
        """Test domain detection for documentation."""
        from attune.socratic.engine import detect_domain

        domain, confidence = detect_domain("Write API documentation")

        assert domain == "documentation"
        assert confidence > 0

    def test_detect_performance_domain(self):
        """Test domain detection for performance."""
        from attune.socratic.engine import detect_domain

        domain, confidence = detect_domain("Optimize for performance")

        assert domain == "performance"
        assert confidence > 0

    def test_detect_refactoring_domain(self):
        """Test domain detection for refactoring."""
        from attune.socratic.engine import detect_domain

        domain, confidence = detect_domain("Refactor this module")

        assert domain == "refactoring"
        assert confidence > 0

    def test_returns_general_for_unknown(self):
        """Test that unknown goals return general domain."""
        from attune.socratic.engine import detect_domain

        domain, confidence = detect_domain("Do something vague")

        assert domain == "general"


class TestQuestionGeneration:
    """Tests for question generation functions."""

    def test_generate_initial_questions(self):
        """Test generating initial questions."""
        from attune.socratic.engine import SocraticWorkflowBuilder

        builder = SocraticWorkflowBuilder()
        session = builder.start_session("Code review automation")

        # get_next_questions handles initial question generation internally
        form = builder.get_next_questions(session)

        assert form is not None
        assert form.round_number == 1

    def test_get_initial_form(self):
        """Test getting the initial form template."""
        from attune.socratic.engine import SocraticWorkflowBuilder

        builder = SocraticWorkflowBuilder()
        form = builder.get_initial_form()

        assert form is not None
        assert len(form.fields) > 0


class TestDomainPatterns:
    """Tests for domain pattern configuration."""

    def test_domain_patterns_exist(self):
        """Test that domain patterns are configured."""
        from attune.socratic.engine import DOMAIN_PATTERNS

        assert len(DOMAIN_PATTERNS) > 0

    def test_domain_pattern_has_required_fields(self):
        """Test domain patterns have required fields."""
        from attune.socratic.engine import DOMAIN_PATTERNS

        for pattern in DOMAIN_PATTERNS:
            assert hasattr(pattern, "domain")
            assert hasattr(pattern, "keywords")
            assert hasattr(pattern, "weight")


class TestSessionWorkflow:
    """Integration tests for the full session workflow."""

    def test_full_workflow_happy_path(self):
        """Test complete session workflow from start to generation."""
        from attune.socratic.engine import SocraticWorkflowBuilder
        from attune.socratic.session import SessionState

        builder = SocraticWorkflowBuilder()

        # 1. Start session with goal
        session = builder.start_session("Automate security code review for Python")

        # 2. Get initial questions
        form = builder.get_next_questions(session)
        assert form is not None

        # 3. Submit answers
        session = builder.submit_answers(
            session,
            {
                "languages": ["python"],
                "quality_focus": ["security"],
            },
        )

        # 4. Force ready state for test
        session.state = SessionState.READY_TO_GENERATE

        # 5. Generate workflow
        workflow = builder.generate_workflow(session)

        assert workflow is not None
        assert workflow.blueprint is not None
        assert len(workflow.blueprint.agents) > 0


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestEngineCoverageGaps:
    """Cover branches in get_next_questions, _update_requirements,
    _generate_workflow_name, and _generate_success_criteria."""

    def _make_builder(self):
        from attune.socratic.engine import SocraticWorkflowBuilder

        return SocraticWorkflowBuilder()

    def test_get_session_returns_existing(self):
        """Line 121: get_session returns the stored session."""
        builder = self._make_builder()
        session = builder.start_session()
        retrieved = builder.get_session(session.session_id)
        assert retrieved is session

    def test_get_session_returns_none_for_unknown(self):
        builder = self._make_builder()
        assert builder.get_session("missing") is None

    def test_get_next_questions_awaiting_goal_returns_initial_form(self):
        """Line 210: state AWAITING_GOAL → initial form."""
        from attune.socratic.session import SessionState

        builder = self._make_builder()
        session = builder.start_session()
        # State is AWAITING_GOAL
        assert session.state == SessionState.AWAITING_GOAL
        form = builder.get_next_questions(session)
        assert form is not None
        assert form.id == "initial_goal"

    def test_get_next_questions_ready_returns_none(self):
        """Line 213: state READY_TO_GENERATE → None."""
        from attune.socratic.session import SessionState

        builder = self._make_builder()
        session = builder.start_session()
        session.state = SessionState.READY_TO_GENERATE
        assert builder.get_next_questions(session) is None

    def test_get_next_questions_completed_returns_none(self):
        """Line 216: state COMPLETED → None."""
        from attune.socratic.session import SessionState

        builder = self._make_builder()
        session = builder.start_session()
        session.state = SessionState.COMPLETED
        assert builder.get_next_questions(session) is None

    def test_get_next_questions_no_goal_analysis_returns_initial(self):
        """Line 218-219: goal_analysis None → initial form fallback."""
        from attune.socratic.session import SessionState

        builder = self._make_builder()
        session = builder.start_session()
        session.state = SessionState.AWAITING_ANSWERS
        session.goal_analysis = None
        form = builder.get_next_questions(session)
        assert form is not None
        assert form.id == "initial_goal"

    def test_get_next_questions_followup_round(self):
        """Line 226: current_round > 0 → generate_followup_questions."""
        from unittest.mock import patch

        from attune.socratic.session import SessionState

        builder = self._make_builder()
        session = builder.start_session("Improve test coverage")
        builder.set_goal(session, "Improve test coverage")
        # Bump current_round to non-zero
        session.current_round = 2
        session.state = SessionState.AWAITING_ANSWERS

        with patch(
            "attune.socratic.engine.generate_followup_questions",
            return_value="FAKE-FORM",
        ) as mock_followup:
            result = builder.get_next_questions(session)
        assert result == "FAKE-FORM"
        mock_followup.assert_called_once()

    def test_submit_answers_no_current_form(self, monkeypatch):
        """Line 249->252: get_next_questions returns None → empty questions_data."""
        from attune.socratic.session import SessionState

        builder = self._make_builder()
        session = builder.start_session()
        session.state = SessionState.AWAITING_ANSWERS
        # Force get_next_questions to return None
        monkeypatch.setattr(builder, "get_next_questions", lambda s: None)

        builder.submit_answers(session, {"q1": "yes"})
        # No exception, session updated
        assert session.state in (
            SessionState.AWAITING_ANSWERS,
            SessionState.READY_TO_GENERATE,
        )

    def test_update_requirements_languages(self):
        """Line 280-281: 'languages' answer → technical_constraints set."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"languages": ["python", "rust"]})
        assert session.requirements.technical_constraints["languages"] == ["python", "rust"]

    def test_update_requirements_quality_focus(self):
        """Lines 284-290: quality_focus → quality_attributes + must_have."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"quality_focus": ["security", "performance"]})
        assert "security" in session.requirements.quality_attributes
        assert any("Optimize for security" in r for r in session.requirements.must_have)

    def test_update_requirements_quality_focus_dedup(self):
        """Line 289-290 branch: existing must_have not duplicated."""
        builder = self._make_builder()
        session = builder.start_session()
        session.requirements.must_have.append("Optimize for security")
        builder._update_requirements(session, {"quality_focus": ["security"]})
        # Still only one occurrence
        count = sum(1 for r in session.requirements.must_have if r == "Optimize for security")
        assert count == 1

    def test_update_requirements_automation_level(self):
        """Lines 293-294: automation_level."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"automation_level": "full"})
        assert session.requirements.preferences["automation_level"] == "full"

    def test_update_requirements_team_size(self):
        """Lines 297-298: team_size."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"team_size": "small"})
        assert session.requirements.preferences["team_size"] == "small"

    def test_update_requirements_review_scope(self):
        """Lines 301-302."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"review_scope": "full"})
        assert session.requirements.domain_specific["review_scope"] == "full"

    def test_update_requirements_security_focus(self):
        """Lines 304-305."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"security_focus": "high"})
        assert session.requirements.domain_specific["security_focus"] == "high"

    def test_update_requirements_test_type(self):
        """Lines 307-308."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"test_type": "unit"})
        assert session.requirements.domain_specific["test_type"] == "unit"

    def test_update_requirements_additional_context(self):
        """Lines 311-312: additional_context."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"additional_context": "some notes"})
        assert session.requirements.domain_specific["additional_context"] == "some notes"

    def test_update_requirements_priorities_string(self):
        """Lines 315-322: priorities as string parsed line-by-line."""
        builder = self._make_builder()
        session = builder.start_session()
        builder._update_requirements(session, {"priorities": "Be fast\nBe correct\nBe simple"})
        must = session.requirements.must_have
        assert "Be fast" in must
        assert "Be correct" in must
        assert "Be simple" in must

    def test_update_requirements_priorities_dedup(self):
        """Lines 320-322 branch: priority already in must_have skipped."""
        builder = self._make_builder()
        session = builder.start_session()
        session.requirements.must_have.append("Be fast")
        builder._update_requirements(session, {"priorities": "Be fast\nBe correct"})
        count = sum(1 for r in session.requirements.must_have if r == "Be fast")
        assert count == 1

    def test_update_requirements_priorities_not_string(self):
        """Branch 317->exit: priorities not a string → skip parsing."""
        builder = self._make_builder()
        session = builder.start_session()
        before = list(session.requirements.must_have)
        # Pass a list instead of string → if isinstance check is False
        builder._update_requirements(session, {"priorities": ["item1", "item2"]})
        # Must-have unchanged because parsing skipped
        assert session.requirements.must_have == before

    def test_generate_workflow_raises_when_not_ready(self):
        """Line 353: not ready → ValueError."""
        import pytest

        from attune.socratic.session import SessionState

        builder = self._make_builder()
        session = builder.start_session()
        # Default state is AWAITING_GOAL, not ready
        session.state = SessionState.AWAITING_ANSWERS
        with pytest.raises(ValueError, match="not ready"):
            builder.generate_workflow(session)

    def test_generate_workflow_name_with_qualities(self):
        """Line 432: qualities present → qualified name."""
        builder = self._make_builder()
        name = builder._generate_workflow_name("code_review", {"quality_focus": ["security"]})
        assert name == "Security-Focused Code Review"

    def test_generate_workflow_name_without_qualities(self):
        """Line 434: no qualities → 'Automated <base>'."""
        builder = self._make_builder()
        name = builder._generate_workflow_name("code_review", {})
        assert name == "Automated Code Review"

    def test_generate_workflow_name_unknown_domain(self):
        """Line 426: unknown domain → 'Custom Workflow'."""
        builder = self._make_builder()
        name = builder._generate_workflow_name("weird_domain", {})
        assert name == "Automated Custom Workflow"

    def test_generate_success_criteria_security(self):
        """Line 455: 'security' domain → security_audit_criteria."""
        builder = self._make_builder()
        result = builder._generate_success_criteria("security", {})
        assert result is not None

    def test_generate_success_criteria_testing(self):
        """Line 457: 'testing' domain → test_generation_criteria."""
        builder = self._make_builder()
        result = builder._generate_success_criteria("testing", {})
        assert result is not None

    def test_generate_success_criteria_code_review(self):
        """Line 453: 'code_review' domain → code_review_criteria."""
        builder = self._make_builder()
        result = builder._generate_success_criteria("code_review", {})
        assert result is not None

    def test_generate_success_criteria_generic(self):
        """Line 459+: unknown domain → generic SuccessCriteria with two metrics."""
        from attune.socratic.success import SuccessCriteria

        builder = self._make_builder()
        result = builder._generate_success_criteria("custom_domain", {})
        assert isinstance(result, SuccessCriteria)
        assert result.id == "custom_domain_success"
        assert result.success_threshold == 0.7
        assert len(result.metrics) == 2
