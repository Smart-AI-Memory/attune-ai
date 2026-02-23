"""Tests for lessons injection into workflow prompts.

Tests that LessonsManager output is injected into the system
prompt built by PromptMixin._build_cached_system_prompt().

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import patch

from attune.workflows.prompt_mixin import PromptMixin


class StubWorkflow(PromptMixin):
    """Minimal stub satisfying PromptMixin expected attributes."""

    def __init__(self) -> None:
        self.name = "test-workflow"
        self.description = "Test workflow"
        self.stages = []
        self._config = None


_LESSONS_MGR = "attune.memory.lessons.LessonsManager"


class TestLessonsInjection:
    """Tests for _get_project_lessons and prompt injection."""

    def test_lessons_injected_into_prompt(self) -> None:
        """Lessons text appears in the system prompt."""
        wf = StubWorkflow()

        with patch.object(
            wf,
            "_get_project_lessons",
            return_value="- Always run tests\n- Check edge cases",
        ):
            prompt = wf._build_cached_system_prompt(role="code reviewer")

        assert "# Lessons Learned" in prompt
        assert "- Always run tests" in prompt
        assert "- Check edge cases" in prompt

    def test_no_lessons_no_section(self) -> None:
        """No lessons produces no 'Lessons Learned' section."""
        wf = StubWorkflow()

        with patch.object(wf, "_get_project_lessons", return_value=None):
            prompt = wf._build_cached_system_prompt(role="code reviewer")

        assert "Lessons Learned" not in prompt

    def test_lessons_appear_between_guidelines_and_docs(self) -> None:
        """Lessons section appears after guidelines, before docs."""
        wf = StubWorkflow()

        with patch.object(
            wf,
            "_get_project_lessons",
            return_value="- Lesson one",
        ):
            prompt = wf._build_cached_system_prompt(
                role="reviewer",
                guidelines=["Follow PEP 8"],
                documentation="Reference: coding standards",
            )

        guidelines_idx = prompt.index("# Guidelines")
        lessons_idx = prompt.index("# Lessons Learned")
        docs_idx = prompt.index("# Reference Documentation")

        assert guidelines_idx < lessons_idx < docs_idx

    @patch(_LESSONS_MGR)
    def test_get_project_lessons_returns_text(self, MockManager) -> None:
        """_get_project_lessons delegates to LessonsManager."""
        mock_mgr = MockManager.return_value
        mock_mgr.format_for_prompt.return_value = "- Lesson A"

        wf = StubWorkflow()
        result = wf._get_project_lessons()

        assert result == "- Lesson A"
        mock_mgr.format_for_prompt.assert_called_once()

    @patch(_LESSONS_MGR)
    def test_get_project_lessons_returns_none_on_no_lessons(self, MockManager) -> None:
        """_get_project_lessons returns None when no lessons exist."""
        mock_mgr = MockManager.return_value
        mock_mgr.format_for_prompt.return_value = None

        wf = StubWorkflow()
        result = wf._get_project_lessons()

        assert result is None

    @patch(_LESSONS_MGR, side_effect=RuntimeError("unexpected"))
    def test_get_project_lessons_handles_exception(self, _mock) -> None:
        """_get_project_lessons returns None on unexpected error."""
        wf = StubWorkflow()
        result = wf._get_project_lessons()

        assert result is None

    def test_prompt_structure_preserved(self) -> None:
        """Full prompt structure intact with all sections."""
        wf = StubWorkflow()

        with patch.object(
            wf,
            "_get_project_lessons",
            return_value="- Test lesson",
        ):
            prompt = wf._build_cached_system_prompt(
                role="reviewer",
                guidelines=["Guideline 1"],
                documentation="Some docs",
                examples=[{"input": "code", "output": "review"}],
            )

        # All sections present in correct order
        assert "You are a reviewer." in prompt
        assert "# Guidelines" in prompt
        assert "# Lessons Learned" in prompt
        assert "# Reference Documentation" in prompt
        assert "# Examples" in prompt
        assert "# Instructions" in prompt
