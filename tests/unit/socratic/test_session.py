"""Tests for the Socratic session module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


class TestSocraticSession:
    """Tests for SocraticSession class."""

    def test_create_session(self):
        """Test creating a new session."""
        from attune.socratic.session import SessionState, SocraticSession

        session = SocraticSession()

        assert session.session_id is not None
        # Session IDs are UUIDs (36 chars with hyphens)
        assert len(session.session_id) == 36
        assert session.state == SessionState.AWAITING_GOAL
        assert session.goal == ""  # Empty string, not None
        assert session.created_at is not None

    def test_create_session_with_id(self):
        """Test creating a session with specific ID."""
        from attune.socratic.session import SocraticSession

        session = SocraticSession(session_id="custom-id-123")
        assert session.session_id == "custom-id-123"

    def test_session_serialization(self, sample_session):
        """Test session serialization to dict."""
        data = sample_session.to_dict()

        assert data["session_id"] == sample_session.session_id
        assert data["goal"] == sample_session.goal
        assert data["state"] == sample_session.state.value
        # Session uses question_rounds, not answers
        assert "question_rounds" in data

    def test_session_deserialization(self, sample_session):
        """Test session deserialization from dict."""
        from attune.socratic.session import SocraticSession

        data = sample_session.to_dict()
        restored = SocraticSession.from_dict(data)

        assert restored.session_id == sample_session.session_id
        assert restored.goal == sample_session.goal
        assert restored.state == sample_session.state

    def test_session_touch(self):
        """Test updating the last activity timestamp."""
        import time

        from attune.socratic.session import SocraticSession

        session = SocraticSession()
        original_updated = session.updated_at

        time.sleep(0.01)  # Small delay
        session.touch()

        assert session.updated_at >= original_updated

    def test_session_is_active(self):
        """Test checking if session is active."""
        from attune.socratic.session import SessionState, SocraticSession

        session = SocraticSession()
        assert session.is_active() is True

        session.state = SessionState.COMPLETED
        assert session.is_active() is False

        session.state = SessionState.CANCELLED
        assert session.is_active() is False

    def test_session_can_generate(self):
        """Test checking if session can generate."""
        from attune.socratic.session import GoalAnalysis, SocraticSession

        session = SocraticSession()

        # No goal analysis - cannot generate
        assert session.can_generate() is False

        # Add goal analysis with high confidence
        session.goal_analysis = GoalAnalysis(
            raw_goal="Test goal",
            intent="Test intent",
            domain="testing",
            confidence=0.9,
        )
        assert session.can_generate() is True

    def test_session_add_question_round(self):
        """Test adding a question round."""
        from attune.socratic.session import SocraticSession

        session = SocraticSession()
        assert session.current_round == 0

        session.add_question_round(
            questions=[{"id": "q1", "text": "What language?"}],
            answers={"q1": "python"},
        )

        assert session.current_round == 1
        assert len(session.question_rounds) == 1
        assert session.question_rounds[0]["round"] == 0


class TestSessionState:
    """Tests for SessionState enum."""

    def test_state_values(self):
        """Test all state values exist."""
        from attune.socratic.session import SessionState

        assert SessionState.AWAITING_GOAL.value == "awaiting_goal"
        assert SessionState.ANALYZING_GOAL.value == "analyzing_goal"
        assert SessionState.AWAITING_ANSWERS.value == "awaiting_answers"
        assert SessionState.READY_TO_GENERATE.value == "ready_to_generate"
        assert SessionState.COMPLETED.value == "completed"

    def test_state_processing_answers(self):
        """Test PROCESSING_ANSWERS state exists."""
        from attune.socratic.session import SessionState

        assert SessionState.PROCESSING_ANSWERS.value == "processing_answers"

    def test_state_generating(self):
        """Test GENERATING state exists."""
        from attune.socratic.session import SessionState

        assert SessionState.GENERATING.value == "generating"

    def test_state_cancelled(self):
        """Test CANCELLED state exists."""
        from attune.socratic.session import SessionState

        assert SessionState.CANCELLED.value == "cancelled"


class TestGoalAnalysis:
    """Tests for GoalAnalysis dataclass."""

    def test_create_goal_analysis(self):
        """Test creating a GoalAnalysis."""
        from attune.socratic.session import GoalAnalysis

        analysis = GoalAnalysis(
            raw_goal="Automate code reviews",
            intent="Automated code quality review for Python",  # Not refined_goal
            domain="code_review",
            confidence=0.85,
            keywords=["code", "review", "python"],
            ambiguities=["Which languages?"],
        )

        assert analysis.domain == "code_review"
        assert analysis.confidence == 0.85
        assert "code" in analysis.keywords
        assert analysis.intent == "Automated code quality review for Python"

    def test_goal_analysis_needs_clarification(self):
        """Test needs_clarification method."""
        from attune.socratic.session import GoalAnalysis

        # Low confidence - needs clarification
        analysis = GoalAnalysis(
            raw_goal="Do something",
            intent="Unclear",
            domain="general",
            confidence=0.5,
        )
        assert analysis.needs_clarification() is True

        # High confidence but has ambiguities
        analysis = GoalAnalysis(
            raw_goal="Review code",
            intent="Code review",
            domain="code_review",
            confidence=0.9,
            ambiguities=["Which language?"],
        )
        assert analysis.needs_clarification() is True

        # High confidence, no ambiguities
        analysis = GoalAnalysis(
            raw_goal="Review Python code",
            intent="Python code review",
            domain="code_review",
            confidence=0.9,
        )
        assert analysis.needs_clarification() is False

    def test_goal_analysis_assumptions(self):
        """Test GoalAnalysis with assumptions."""
        from attune.socratic.session import GoalAnalysis

        analysis = GoalAnalysis(
            raw_goal="Test",
            intent="Test",
            domain="testing",
            confidence=0.8,
            assumptions=["Using pytest", "Python 3.10+"],
        )

        assert len(analysis.assumptions) == 2
        assert "Using pytest" in analysis.assumptions


class TestRequirementSet:
    """Tests for RequirementSet dataclass."""

    def test_create_empty_requirement_set(self):
        """Test creating an empty RequirementSet."""
        from attune.socratic.session import RequirementSet

        reqs = RequirementSet()

        assert reqs.must_have == []
        assert reqs.should_have == []  # Not nice_to_have
        assert reqs.technical_constraints == {}  # Dict, not list

    def test_add_requirements(self):
        """Test adding requirements."""
        from attune.socratic.session import RequirementSet

        reqs = RequirementSet(
            must_have=["Security scanning"],
            should_have=["Performance analysis"],  # Not nice_to_have
            technical_constraints={"language": "python"},  # Dict, not list
        )

        assert len(reqs.must_have) == 1
        assert "Security scanning" in reqs.must_have
        assert reqs.technical_constraints["language"] == "python"

    def test_requirement_set_must_not_have(self):
        """Test must_not_have field."""
        from attune.socratic.session import RequirementSet

        reqs = RequirementSet(
            must_not_have=["Deprecated APIs"],
        )

        assert "Deprecated APIs" in reqs.must_not_have

    def test_completeness_score(self):
        """Test completeness_score method."""
        from attune.socratic.session import RequirementSet

        # Empty requirements - low score
        reqs = RequirementSet()
        assert reqs.completeness_score() < 0.5

        # With must_have
        reqs = RequirementSet(must_have=["Security"])
        assert reqs.completeness_score() > 0.3

        # With technical constraints
        reqs = RequirementSet(
            must_have=["Security"],
            technical_constraints={"lang": "py", "version": "3.10", "framework": "pytest"},
        )
        assert reqs.completeness_score() > 0.5

    def test_quality_attributes(self):
        """Test quality_attributes field."""
        from attune.socratic.session import RequirementSet

        reqs = RequirementSet(
            quality_attributes={"security": 0.9, "performance": 0.8},
        )

        assert reqs.quality_attributes["security"] == 0.9
        assert reqs.quality_attributes["performance"] == 0.8

    def test_domain_specific(self):
        """Test domain_specific field."""
        from attune.socratic.session import RequirementSet

        reqs = RequirementSet(
            domain_specific={"code_review": {"severity_threshold": "high"}},
        )

        assert "code_review" in reqs.domain_specific


class TestSessionContextSummary:
    """Tests for session context summary."""

    def test_get_context_summary(self):
        """Test getting context summary."""
        from attune.socratic.session import GoalAnalysis, SocraticSession

        session = SocraticSession()
        session.goal = "Review code"
        session.goal_analysis = GoalAnalysis(
            raw_goal="Review code",
            intent="Code review",
            domain="code_review",
            confidence=0.8,
        )

        summary = session.get_context_summary()

        assert summary["session_id"] == session.session_id
        assert summary["goal"] == "Review code"
        assert summary["confidence"] == 0.8
        assert "ready_to_generate" in summary

    def test_can_generate_max_rounds_reached(self):
        """can_generate returns True once max_rounds is reached (line 200)."""
        from attune.socratic.session import GoalAnalysis, SocraticSession

        session = SocraticSession()
        session.goal_analysis = GoalAnalysis(
            raw_goal="g",
            intent="i",
            domain="d",
            confidence=0.4,  # below 0.8
        )
        session.max_rounds = 2
        session.current_round = 2  # at max
        assert session.can_generate() is True

    def test_from_dict_parses_goal_analysis(self):
        """from_dict reconstructs goal_analysis when present (lines 288-296)."""
        from attune.socratic.session import SocraticSession

        data = {
            "session_id": "s1",
            "goal": "review",
            "state": "awaiting_answers",
            "goal_analysis": {
                "intent": "code review",
                "domain": "code_review",
                "confidence": 0.85,
                "ambiguities": ["scope"],
                "assumptions": ["python"],
            },
        }
        session = SocraticSession.from_dict(data)
        assert session.goal_analysis is not None
        assert session.goal_analysis.intent == "code review"
        assert session.goal_analysis.confidence == 0.85
        assert session.goal_analysis.ambiguities == ["scope"]
