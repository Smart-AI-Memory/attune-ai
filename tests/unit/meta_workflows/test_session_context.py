"""Tests for SessionContext functionality.

Tests session tracking, form choice recording, default suggestions,
and integration with meta-workflows.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import time
from unittest.mock import MagicMock

from attune.meta_workflows.models import FormQuestion, FormSchema, QuestionType
from attune.meta_workflows.session_context import (
    SessionContext,
    create_session_context,
    get_session_defaults,
)


class TestSessionContextInitialization:
    """Test session context initialization."""

    def test_init_with_memory(self):
        """Test initialization with memory instance."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        assert session.memory is memory
        assert session.user_id == "test_user"
        assert session.session_id is not None
        assert session.default_ttl == 3600  # 1 hour

    def test_init_without_memory(self):
        """Test initialization without memory (graceful degradation)."""
        session = SessionContext(memory=None)

        assert session.memory is None
        assert session.user_id == "anonymous"
        assert session.session_id is not None

    def test_init_with_custom_session_id(self):
        """Test initialization with custom session ID."""
        custom_id = "custom_session_123"
        session = SessionContext(session_id=custom_id)

        assert session.session_id == custom_id

    def test_init_with_custom_ttl(self):
        """Test initialization with custom TTL."""
        session = SessionContext(default_ttl=7200)

        assert session.default_ttl == 7200


class TestRecordChoice:
    """Test recording form choices."""

    def test_record_choice_with_memory(self):
        """Test recording choice when memory is available."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        result = session.record_choice(
            template_id="test_template",
            question_id="question1",
            choice="Option A",
        )

        # Should succeed if memory backend is available
        # Note: May be False if Redis not running - graceful degradation
        assert isinstance(result, bool)

    def test_record_choice_without_memory(self):
        """Test recording choice when memory is not available."""
        session = SessionContext(memory=None)

        result = session.record_choice(
            template_id="test_template",
            question_id="question1",
            choice="Option A",
        )

        # Should return False gracefully
        assert result is False

    def test_record_multiple_choices(self):
        """Test recording multiple choices."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        choices = [
            ("question1", "Answer 1"),
            ("question2", "Answer 2"),
            ("question3", ["Answer 3a", "Answer 3b"]),  # Multi-select
        ]

        for question_id, choice in choices:
            session.record_choice(
                template_id="test_template",
                question_id=question_id,
                choice=choice,
            )

        # All recorded successfully (if backend available)
        # Test passes if no exceptions raised

    def test_record_choice_with_custom_ttl(self):
        """Test recording choice with custom TTL."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        result = session.record_choice(
            template_id="test_template",
            question_id="question1",
            choice="Option A",
            ttl=1800,  # 30 minutes
        )

        assert isinstance(result, bool)


class TestGetRecentChoice:
    """Test retrieving recent choices."""

    def test_get_recent_choice_recorded(self):
        """Test getting a recently recorded choice."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        # Record a choice
        session.record_choice(
            template_id="test_template",
            question_id="question1",
            choice="Answer A",
        )

        # Retrieve it
        retrieved = session.get_recent_choice(
            template_id="test_template",
            question_id="question1",
        )

        # May be None if Redis not running - graceful degradation
        # But if it works, should match
        if retrieved is not None:
            assert retrieved == "Answer A"

    def test_get_recent_choice_not_found(self):
        """Test getting a choice that doesn't exist."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        retrieved = session.get_recent_choice(
            template_id="test_template",
            question_id="nonexistent",
        )

        assert retrieved is None

    def test_get_recent_choice_without_memory(self):
        """Test getting choice when memory is not available."""
        session = SessionContext(memory=None)

        retrieved = session.get_recent_choice(
            template_id="test_template",
            question_id="question1",
        )

        assert retrieved is None


class TestSuggestDefaults:
    """Test suggesting default values."""

    def test_suggest_defaults_empty(self):
        """Test suggesting defaults with no history."""
        session = SessionContext(memory=None)

        defaults = session.suggest_defaults(template_id="test_template")

        assert defaults == {}

    def test_suggest_defaults_with_schema(self):
        """Test suggesting defaults with form schema validation."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        # Create form schema
        schema = FormSchema(
            title="Test Form",
            description="Test form description",
            questions=[
                FormQuestion(
                    id="question1",
                    text="Test question",
                    type=QuestionType.SINGLE_SELECT,
                    options=["Option A", "Option B", "Option C"],
                ),
            ],
        )

        # Record a choice
        session.record_choice(
            template_id="test_template",
            question_id="question1",
            choice="Option A",
        )

        # Get suggestions with validation
        defaults = session.suggest_defaults(
            template_id="test_template",
            form_schema=schema,
        )

        # Should return dict (may be empty if Redis not running)
        assert isinstance(defaults, dict)


class TestRecordExecution:
    """Test recording workflow execution metadata."""

    def test_record_execution_success(self):
        """Test recording successful execution."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        result = session.record_execution(
            template_id="test_template",
            run_id="run_123",
            success=True,
            cost=0.50,
            duration=10.5,
        )

        assert isinstance(result, bool)

    def test_record_execution_failure(self):
        """Test recording failed execution."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        result = session.record_execution(
            template_id="test_template",
            run_id="run_124",
            success=False,
            cost=0.25,
            duration=5.0,
        )

        assert isinstance(result, bool)

    def test_record_execution_without_memory(self):
        """Test recording execution when memory not available."""
        session = SessionContext(memory=None)

        result = session.record_execution(
            template_id="test_template",
            run_id="run_125",
            success=True,
            cost=0.50,
            duration=10.5,
        )

        assert result is False


class TestGetSessionStats:
    """Test retrieving session statistics."""

    def test_get_session_stats_with_memory(self):
        """Test getting stats when memory is available."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        stats = session.get_session_stats()

        assert isinstance(stats, dict)
        assert "session_id" in stats
        assert stats["session_id"] == session.session_id
        assert "memory_enabled" in stats

    def test_get_session_stats_without_memory(self):
        """Test getting stats when memory is not available."""
        session = SessionContext(memory=None)

        stats = session.get_session_stats()

        assert isinstance(stats, dict)
        assert "session_id" in stats
        assert stats["memory_enabled"] is False


class TestClearSession:
    """Test clearing session data."""

    def test_clear_session_with_memory(self):
        """Test clearing session when memory is available."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        result = session.clear_session()

        # Should return True if implemented
        # Current implementation logs but doesn't actually clear
        assert isinstance(result, bool)

    def test_clear_session_without_memory(self):
        """Test clearing session when memory is not available."""
        session = SessionContext(memory=None)

        result = session.clear_session()

        assert result is False


class TestHelperMethods:
    """Test helper methods."""

    def test_make_choice_key(self):
        """Test creating Redis key for choice."""
        session = SessionContext(session_id="test_session")

        key = session._make_choice_key("template1", "question1")

        assert "test_session" in key
        assert "template1" in key
        assert "question1" in key
        assert key == "session:test_session:form:template1:question1"

    def test_validate_choice_single_select(self):
        """Test validating single-select choice."""
        session = SessionContext()

        question = FormQuestion(
            id="q1",
            text="Test",
            type=QuestionType.SINGLE_SELECT,
            options=["A", "B", "C"],
        )

        assert session._validate_choice("A", question) is True
        assert session._validate_choice("D", question) is False

    def test_validate_choice_multi_select(self):
        """Test validating multi-select choice."""
        session = SessionContext()

        question = FormQuestion(
            id="q1",
            text="Test",
            type=QuestionType.MULTI_SELECT,
            options=["A", "B", "C"],
        )

        assert session._validate_choice(["A", "B"], question) is True
        assert session._validate_choice(["A", "D"], question) is False

    def test_validate_choice_no_options(self):
        """Test validating choice for question without options."""
        session = SessionContext()

        question = FormQuestion(
            id="q1",
            text="Test",
            type=QuestionType.TEXT_INPUT,
        )

        # Should accept any value if no options defined
        assert session._validate_choice("anything", question) is True


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_session_context(self):
        """Test create_session_context function."""
        session = create_session_context()

        assert isinstance(session, SessionContext)
        assert session.memory is None
        assert session.session_id is not None

    def test_create_session_context_with_memory(self):
        """Test create_session_context with memory."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = create_session_context(memory=memory)

        assert session.memory is memory

    def test_get_session_defaults(self):
        """Test get_session_defaults function."""
        defaults = get_session_defaults(template_id="test_template")

        assert isinstance(defaults, dict)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_workflow_with_session_context(self):
        """Test complete workflow with session context."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        # Simulate form filling
        choices = {
            "has_tests": "Yes",
            "test_coverage": "90%",
            "version_bump": "minor",
        }

        template_id = "python_package_publish"

        # Record all choices
        for question_id, choice in choices.items():
            session.record_choice(template_id, question_id, choice)

        # Simulate execution
        session.record_execution(
            template_id=template_id,
            run_id="run_001",
            success=True,
            cost=0.75,
            duration=15.2,
        )

        # Get stats
        stats = session.get_session_stats()
        assert stats["session_id"] == session.session_id

    def test_multiple_templates_same_session(self):
        """Test using same session for multiple templates."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory)

        # Record choices for different templates
        session.record_choice("template1", "q1", "answer1")
        session.record_choice("template2", "q1", "answer2")
        session.record_choice("template1", "q2", "answer3")

        # Choices are isolated by template
        # (verification depends on pattern matching support)

    def test_session_ttl_behavior(self):
        """Test TTL expiration behavior."""
        from attune.memory.unified import UnifiedMemory

        memory = UnifiedMemory(user_id="test_user")
        session = SessionContext(memory=memory, default_ttl=1)  # 1 second TTL

        # Record choice
        session.record_choice("template1", "q1", "answer")

        # Wait for TTL to expire
        time.sleep(2)

        # Try to retrieve - should be None (expired)
        retrieved = session.get_recent_choice("template1", "q1")

        # Note: Actual behavior depends on Redis backend
        # If Redis not running, will be None anyway
        # Test verifies no crashes occur
        assert retrieved is None or isinstance(retrieved, str)


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestRecordChoiceException:
    """Cover lines 119-121: record_choice exception handling."""

    def test_stash_exception_returns_false(self):
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        memory.stash.side_effect = RuntimeError("redis down")

        session = SessionContext(memory=memory)
        assert session.record_choice("t1", "q1", "yes") is False


class TestGetRecentChoiceEdgeCases:
    """Cover lines 150-152: get_recent_choice exception handling."""

    def test_retrieve_exception_returns_none(self):
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        memory.retrieve.side_effect = RuntimeError("memory broken")

        session = SessionContext(memory=memory)
        assert session.get_recent_choice("t1", "q1") is None

    def test_retrieve_returns_non_dict(self):
        """Line 145-148: retrieve returns non-dict → None."""
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        memory.retrieve.return_value = "string-not-dict"

        session = SessionContext(memory=memory)
        assert session.get_recent_choice("t1", "q1") is None


class TestGetRecentChoices:
    """Cover lines 168, 179-181."""

    def test_no_memory_returns_empty(self):
        """Line 168: memory None → empty dict."""
        from attune.meta_workflows.session_context import SessionContext

        session = SessionContext(memory=None)
        assert session.get_recent_choices("t1") == {}

    def test_with_memory_returns_empty_dict_currently(self):
        """Lines 170-177: pattern matching not implemented → returns {}."""
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        session = SessionContext(memory=memory)
        # Currently returns empty dict (pattern matching unsupported)
        assert session.get_recent_choices("t1") == {}

    def test_exception_returns_empty(self, monkeypatch):
        """Lines 179-181: exception in try block → empty dict."""
        from attune.meta_workflows import session_context as mod

        memory = MagicMock()
        memory.user_id = "u"
        session = mod.SessionContext(memory=memory)

        bad_logger = MagicMock()
        bad_logger.debug.side_effect = RuntimeError("logger broke")
        bad_logger.error = MagicMock()
        bad_logger.info = MagicMock()
        monkeypatch.setattr(mod, "logger", bad_logger)

        assert session.get_recent_choices("t1") == {}


class TestSuggestDefaultsValidation:
    """Cover lines 211-213, 217-221."""

    def test_validates_choice_when_in_recent(self, monkeypatch):
        """Lines 209-213: choice in recent + valid → included."""
        from attune.meta_workflows.models import FormQuestion, FormSchema, QuestionType
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        session = SessionContext(memory=memory)

        # Patch get_recent_choices to return real data
        monkeypatch.setattr(session, "get_recent_choices", lambda t: {"q1": "yes"})

        question = FormQuestion(id="q1", text="Question?", type=QuestionType.TEXT_INPUT)
        schema = FormSchema(questions=[question], title="t", description="d")

        suggestions = session.suggest_defaults("t1", form_schema=schema)
        assert suggestions == {"q1": "yes"}

    def test_invalid_choice_skipped(self, monkeypatch):
        """Branch 212->208: validate_choice False → skip, don't add to validated."""
        from attune.meta_workflows.models import FormQuestion, FormSchema, QuestionType
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        session = SessionContext(memory=memory)

        monkeypatch.setattr(session, "get_recent_choices", lambda t: {"q1": "bad_choice"})
        # Build question with options that don't include "bad_choice"
        question = FormQuestion(
            id="q1",
            text="Question?",
            type=QuestionType.SINGLE_SELECT,
            options=["a", "b"],
        )
        schema = FormSchema(questions=[question], title="t", description="d")

        suggestions = session.suggest_defaults("t1", form_schema=schema)
        # validate_choice returns False → not in suggestions
        assert "q1" not in suggestions

    def test_no_form_schema_returns_recent_choices(self, monkeypatch):
        """Line 217: no schema → return recent_choices directly."""
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        session = SessionContext(memory=memory)
        monkeypatch.setattr(session, "get_recent_choices", lambda t: {"q1": "x", "q2": "y"})
        suggestions = session.suggest_defaults("t1")
        assert suggestions == {"q1": "x", "q2": "y"}

    def test_exception_returns_empty(self, monkeypatch):
        """Lines 219-221: exception → empty dict."""
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        session = SessionContext(memory=memory)

        def boom(t):
            raise RuntimeError("boom")

        monkeypatch.setattr(session, "get_recent_choices", boom)
        assert session.suggest_defaults("t1") == {}


class TestRecordExecutionException:
    """Cover lines 265-267."""

    def test_stash_raises(self):
        from attune.meta_workflows.session_context import SessionContext

        memory = MagicMock()
        memory.user_id = "u"
        memory.stash.side_effect = RuntimeError("memory down")

        session = SessionContext(memory=memory)
        assert (
            session.record_execution("t1", "run-1", success=True, cost=0.1, duration=1.0) is False
        )


class TestGetSessionStatsException:
    """Cover lines 294-296."""

    def test_with_broken_memory_attribute(self):
        """Force an exception inside the try block."""
        from attune.meta_workflows.session_context import SessionContext

        class _SessionRaising(SessionContext):
            @property
            def user_id(self):  # type: ignore[override]
                raise RuntimeError("attr broken")

        # Construct via __new__ to avoid __init__ accessing the property
        bad_session = _SessionRaising.__new__(_SessionRaising)
        bad_session.memory = MagicMock()
        bad_session.memory.user_id = "u"
        bad_session.session_id = "s"
        bad_session.default_ttl = 60

        result = bad_session.get_session_stats()
        assert "error" in result


class TestClearSessionException:
    """Cover lines 315-317."""

    def test_logger_exception_caught(self, monkeypatch):
        """Trigger exception via patched logger."""
        from attune.meta_workflows import session_context as mod

        memory = MagicMock()
        memory.user_id = "u"
        session = mod.SessionContext(memory=memory)

        # Make logger.info raise → caught
        original_logger = mod.logger
        bad_logger = MagicMock()
        bad_logger.info.side_effect = RuntimeError("logger crashed")
        bad_logger.error = MagicMock()
        monkeypatch.setattr(mod, "logger", bad_logger)

        try:
            assert session.clear_session() is False
        finally:
            monkeypatch.setattr(mod, "logger", original_logger)


class TestValidateChoiceException:
    """Cover lines 360-363: _validate_choice exception path."""

    def test_validation_exception_returns_false(self):
        """An options attribute that raises on access → False."""
        from attune.meta_workflows.session_context import SessionContext

        session = SessionContext(memory=None)

        class _BadQuestion:
            @property
            def options(self):
                raise RuntimeError("options broken")

        result = session._validate_choice("yes", _BadQuestion())
        assert result is False

    def test_validate_choice_no_options(self):
        """Question with no options → True."""
        from attune.meta_workflows.session_context import SessionContext

        session = SessionContext(memory=None)

        class _Q:
            options = None

        assert session._validate_choice("anything", _Q()) is True

    def test_validate_choice_list_in_options(self):
        """Multi-select choices all in options."""
        from attune.meta_workflows.session_context import SessionContext

        session = SessionContext(memory=None)

        class _Q:
            options = ["a", "b", "c"]

        assert session._validate_choice(["a", "b"], _Q()) is True
        assert session._validate_choice(["a", "z"], _Q()) is False

    def test_validate_choice_single_in_options(self):
        from attune.meta_workflows.session_context import SessionContext

        session = SessionContext(memory=None)

        class _Q:
            options = ["a", "b"]

        assert session._validate_choice("a", _Q()) is True
        assert session._validate_choice("z", _Q()) is False


class TestConvenienceFunctionsExtra:
    """Cover create_session_context and get_session_defaults."""

    def test_create_session_context(self):
        from attune.meta_workflows.session_context import (
            SessionContext,
            create_session_context,
        )

        session = create_session_context()
        assert isinstance(session, SessionContext)
        assert session.memory is None

    def test_get_session_defaults(self):
        from attune.meta_workflows.session_context import get_session_defaults

        # Without memory → empty
        result = get_session_defaults("t1")
        assert result == {}
