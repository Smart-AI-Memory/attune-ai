"""Tests for the Socratic question generation module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock

import pytest

from attune.socratic.questions import generate_followup_questions, generate_initial_questions


def _make_goal_analysis(domain="general", ambiguities=None, raw_goal="Test goal for analysis"):
    """Create a mock GoalAnalysis for testing."""
    ga = MagicMock()
    ga.domain = domain
    ga.ambiguities = ambiguities or []
    ga.raw_goal = raw_goal
    return ga


def _make_session(current_round=0, max_rounds=3, goal_analysis=None, requirements=None):
    """Create a mock SocraticSession for testing."""
    s = MagicMock()
    s.current_round = current_round
    s.max_rounds = max_rounds
    s.goal_analysis = goal_analysis
    s.question_rounds = []
    if requirements is None:
        reqs = MagicMock()
        reqs.completeness_score.return_value = 0.5
        reqs.must_have = []
        reqs.technical_constraints = {}
        s.requirements = reqs
    else:
        s.requirements = requirements
    return s


class TestGenerateInitialQuestions:
    """Tests for generate_initial_questions()."""

    def test_includes_language_field_when_ambiguous(self):
        """Test language field added when language not specified."""
        ga = _make_goal_analysis(ambiguities=["Programming language not specified"])
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "languages" in field_ids

    def test_excludes_language_field_when_specified(self):
        """Test language field omitted when no ambiguity."""
        ga = _make_goal_analysis(ambiguities=[])
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "languages" not in field_ids

    def test_always_includes_quality_focus(self):
        """Test quality_focus field is always present."""
        ga = _make_goal_analysis()
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "quality_focus" in field_ids

    def test_code_review_domain_adds_review_scope(self):
        """Test code_review domain adds review_scope field."""
        ga = _make_goal_analysis(domain="code_review")
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "review_scope" in field_ids

    def test_security_domain_adds_security_focus(self):
        """Test security domain adds security_focus field."""
        ga = _make_goal_analysis(domain="security")
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "security_focus" in field_ids

    def test_testing_domain_adds_test_type(self):
        """Test testing domain adds test_type field."""
        ga = _make_goal_analysis(domain="testing")
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "test_type" in field_ids

    def test_generic_domain_no_extra_fields(self):
        """Test generic domain does not add domain-specific fields."""
        ga = _make_goal_analysis(domain="documentation")
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "review_scope" not in field_ids
        assert "security_focus" not in field_ids
        assert "test_type" not in field_ids

    def test_always_includes_automation_level(self):
        """Test automation_level field is always present."""
        ga = _make_goal_analysis()
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "automation_level" in field_ids

    def test_always_includes_team_size(self):
        """Test team_size field is always present."""
        ga = _make_goal_analysis()
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "team_size" in field_ids

    def test_always_includes_additional_context(self):
        """Test additional_context field is always present."""
        ga = _make_goal_analysis()
        session = _make_session()
        form = generate_initial_questions(ga, session)
        field_ids = [f.id for f in form.fields]
        assert "additional_context" in field_ids

    def test_form_metadata_correct(self):
        """Test form has correct ID, title, and progress."""
        ga = _make_goal_analysis()
        session = _make_session(current_round=0)
        form = generate_initial_questions(ga, session)
        assert form.id == "round_1"
        assert form.round_number == 1
        assert form.progress == pytest.approx(0.3)


class TestGenerateFollowupQuestions:
    """Tests for generate_followup_questions()."""

    def test_returns_none_when_completeness_high(self):
        """Test returns None when requirements are sufficiently complete."""
        reqs = MagicMock()
        reqs.completeness_score.return_value = 0.85
        session = _make_session(requirements=reqs)
        assert generate_followup_questions(session) is None

    def test_returns_none_when_max_rounds_reached(self):
        """Test returns None when max question rounds reached."""
        reqs = MagicMock()
        reqs.completeness_score.return_value = 0.4
        session = _make_session(current_round=3, max_rounds=3, requirements=reqs)
        assert generate_followup_questions(session) is None

    def test_asks_priorities_when_no_must_haves(self):
        """Test priorities field added when must_have list is empty."""
        reqs = MagicMock()
        reqs.completeness_score.return_value = 0.4
        reqs.must_have = []
        reqs.technical_constraints = {"languages": ["python"]}
        session = _make_session(requirements=reqs)
        form = generate_followup_questions(session)
        assert form is not None
        field_ids = [f.id for f in form.fields]
        assert "priorities" in field_ids

    def test_asks_language_when_missing(self):
        """Test language field added when technical constraints lack languages."""
        reqs = MagicMock()
        reqs.completeness_score.return_value = 0.4
        reqs.must_have = ["something"]
        reqs.technical_constraints = {}
        session = _make_session(requirements=reqs)
        form = generate_followup_questions(session)
        assert form is not None
        field_ids = [f.id for f in form.fields]
        assert "languages" in field_ids

    def test_code_review_adds_review_depth(self):
        """Test code_review domain adds review_depth follow-up."""
        ga = _make_goal_analysis(domain="code_review")
        reqs = MagicMock()
        reqs.completeness_score.return_value = 0.4
        reqs.must_have = ["something"]
        reqs.technical_constraints = {"languages": ["python"]}
        session = _make_session(goal_analysis=ga, requirements=reqs)
        session.question_rounds = []
        form = generate_followup_questions(session)
        assert form is not None
        field_ids = [f.id for f in form.fields]
        assert "review_depth" in field_ids

    def test_returns_none_when_no_fields_needed(self):
        """Test returns None when all requirements are met but score is low."""
        ga = _make_goal_analysis(domain="documentation")
        reqs = MagicMock()
        reqs.completeness_score.return_value = 0.5
        reqs.must_have = ["doc generation"]
        reqs.technical_constraints = {"languages": ["python"]}
        session = _make_session(goal_analysis=ga, requirements=reqs)
        form = generate_followup_questions(session)
        assert form is None
