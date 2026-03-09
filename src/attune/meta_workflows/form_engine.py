"""Socratic form engine for requirements gathering.

Uses AskUserQuestion tool to interactively collect user requirements
through structured question flows.

Created: 2026-01-17
Updated: 2026-01-18 (v4.3.0 - Real AskUserQuestion integration)
Purpose: Interactive requirements gathering for meta-workflows
"""

import logging
from collections.abc import Callable
from typing import Any

from attune.meta_workflows.models import FormQuestion, FormResponse, FormSchema

logger = logging.getLogger(__name__)

# Type alias for the AskUserQuestion callback function
AskUserQuestionCallback = Callable[[list[dict[str, Any]]], dict[str, Any]]


class SocraticFormEngine:
    """Engine for collecting user requirements through Socratic questioning.

    Uses the AskUserQuestion tool to present forms to users and
    collect structured responses.

    The engine supports two modes:
    1. **Interactive mode**: Provide an `ask_user_callback` to invoke the real
       AskUserQuestion tool (e.g., when running in Claude Code context)
    2. **Default mode**: Uses default values from questions when no callback
       is provided (useful for testing or batch processing)

    Example:
        >>> # Interactive mode with callback
        >>> def my_callback(questions):
        ...     # This would invoke the real AskUserQuestion tool
        ...     return {"q1": "user answer"}
        >>> engine = SocraticFormEngine(ask_user_callback=my_callback)

        >>> # Default mode (no interaction)
        >>> engine = SocraticFormEngine()

    """

    def __init__(
        self,
        ask_user_callback: AskUserQuestionCallback | None = None,
        use_defaults_when_no_callback: bool = True,
    ):
        """Initialize the Socratic form engine.

        Args:
            ask_user_callback: Optional callback function that invokes the
                AskUserQuestion tool. When provided, enables interactive mode.
                The callback should accept a list of question dicts and return
                a dict mapping question IDs to user answers.
            use_defaults_when_no_callback: If True and no callback is provided,
                use default values from questions. If False, raise an error
                when trying to ask questions without a callback.

        """
        self.responses_cache: dict[str, FormResponse] = {}
        self._ask_user_callback = ask_user_callback
        self._use_defaults_when_no_callback = use_defaults_when_no_callback

    def ask_questions(self, form_schema: FormSchema, template_id: str) -> FormResponse:
        """Ask all questions in the form schema and collect responses.

        Args:
            form_schema: Schema defining questions to ask
            template_id: ID of template these questions are for

        Returns:
            FormResponse with user's answers

        Raises:
            ValueError: If form_schema is invalid

        """
        if not form_schema.questions:
            logger.warning(f"Form schema for {template_id} has no questions")
            return FormResponse(template_id=template_id, responses={})

        # Batch questions (AskUserQuestion supports max 4 at once)
        batches = form_schema.get_question_batches(batch_size=4)
        all_responses = {}

        logger.info(f"Asking {len(form_schema.questions)} questions in {len(batches)} batch(es)")

        for batch_idx, batch in enumerate(batches, 1):
            logger.debug(f"Processing batch {batch_idx}/{len(batches)}")

            # Convert batch to AskUserQuestion format
            batch_questions = self._convert_batch_to_ask_user_format(batch)

            # In real usage, this would call AskUserQuestion tool
            # For now, this is a placeholder that tests can mock
            batch_responses = self._ask_batch(batch_questions, template_id)

            # Merge responses
            all_responses.update(batch_responses)

        # Create FormResponse
        response = FormResponse(template_id=template_id, responses=all_responses)

        # Cache response
        self.responses_cache[response.response_id] = response

        logger.info(f"Collected {len(all_responses)} responses for template {template_id}")
        return response

    def _convert_batch_to_ask_user_format(self, batch: list[FormQuestion]) -> list[dict[str, Any]]:
        """Convert a batch of FormQuestions to AskUserQuestion format.

        Args:
            batch: List of FormQuestion objects

        Returns:
            List of question dictionaries compatible with AskUserQuestion

        """
        return [q.to_ask_user_format() for q in batch]

    def _ask_batch(self, questions: list[dict[str, Any]], template_id: str) -> dict[str, Any]:
        """Ask a batch of questions using AskUserQuestion tool.

        Args:
            questions: Questions in AskUserQuestion format
            template_id: Template ID for context

        Returns:
            Dictionary mapping question_id → user's answer

        Raises:
            RuntimeError: If no callback is set and use_defaults_when_no_callback
                is False

        Note:
            When a callback is provided, invokes the real AskUserQuestion tool.
            Otherwise, uses default values from questions or raises an error.

        """
        logger.debug(f"_ask_batch called with {len(questions)} questions")

        # If we have a callback, use it for interactive mode
        if self._ask_user_callback is not None:
            try:
                logger.info(f"Invoking AskUserQuestion callback for {len(questions)} questions")
                result = self._ask_user_callback(questions)
                logger.debug(f"Received {len(result)} responses from callback")
                return result
            except Exception as e:  # noqa: BLE001
                logger.error(f"AskUserQuestion callback failed: {e}")
                if self._use_defaults_when_no_callback:
                    logger.warning("Falling back to default values")
                    return self._get_defaults_from_questions(questions)
                raise RuntimeError(f"AskUserQuestion callback failed: {e}") from e

        # No callback - use defaults or raise error
        if self._use_defaults_when_no_callback:
            logger.debug("No callback provided, using default values")
            return self._get_defaults_from_questions(questions)

        raise RuntimeError(
            "No AskUserQuestion callback provided and use_defaults_when_no_callback=False. "
            "Either provide a callback or set use_defaults_when_no_callback=True.",
        )

    def _get_defaults_from_questions(self, questions: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract default values from question definitions.

        Args:
            questions: Questions in AskUserQuestion format

        Returns:
            Dictionary mapping question_id → default value

        """
        defaults = {}
        for q in questions:
            # Get question identifier - prefer question_id for agent rule matching
            key = q.get("question_id", q.get("header", q.get("question", "unknown")))

            # Check for explicit default value first
            if q.get("default"):
                defaults[key] = q["default"]
                logger.debug(f"Default for '{key}': {defaults[key]} (explicit)")
                continue

            # Get default from options (first option is typically recommended)
            options = q.get("options", [])
            if options:
                # Use first option's label as default
                first_option = options[0]
                if isinstance(first_option, dict):
                    defaults[key] = first_option.get("label", "")
                else:
                    defaults[key] = str(first_option)
            else:
                defaults[key] = ""

            logger.debug(f"Default for '{key}': {defaults[key]} (from options)")

        return defaults

    def set_callback(self, callback: AskUserQuestionCallback | None) -> None:
        """Set or update the AskUserQuestion callback.

        Args:
            callback: The callback function to use, or None to disable

        """
        self._ask_user_callback = callback
        logger.debug(f"AskUserQuestion callback {'set' if callback else 'cleared'}")

    def get_cached_response(self, response_id: str) -> FormResponse | None:
        """Retrieve a cached response by ID.

        Args:
            response_id: ID of response to retrieve

        Returns:
            FormResponse if found, None otherwise

        """
        return self.responses_cache.get(response_id)

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self.responses_cache.clear()
        logger.debug("Response cache cleared")


# =============================================================================
# Helper functions for converting between formats
# =============================================================================


def convert_ask_user_response_to_form_response(
    ask_user_result: dict[str, Any],
    template_id: str,
) -> FormResponse:
    """Convert AskUserQuestion tool result to FormResponse.

    Args:
        ask_user_result: Result from AskUserQuestion tool
        template_id: Template ID

    Returns:
        FormResponse object

    Example:
        >>> result = {"q1": "Answer 1", "q2": ["Option A", "Option B"]}
        >>> response = convert_ask_user_response_to_form_response(result, "test")
        >>> response.get("q1")
        'Answer 1'

    """
    return FormResponse(template_id=template_id, responses=ask_user_result)


def create_header_from_question(question: FormQuestion) -> str:
    """Create a short header for a question (max 12 chars for AskUserQuestion).

    Args:
        question: FormQuestion to create header for

    Returns:
        Short header string (≤12 chars)

    Example:
        >>> q = FormQuestion(id="has_tests", text="Do you have tests?", type=QuestionType.BOOLEAN)
        >>> create_header_from_question(q)
        'Tests'

    """
    # Extract key words from question text
    text = question.text.lower()

    # Common patterns
    if "test" in text:
        return "Tests"
    if "coverage" in text:
        return "Coverage"
    if "version" in text:
        return "Version"
    if "publish" in text:
        return "Publishing"
    if "quality" in text:
        return "Quality"
    if "security" in text:
        return "Security"
    if "name" in text:
        return "Name"
    if "changelog" in text:
        return "Changelog"
    if "git" in text:
        return "Git"

    # Fallback: use question ID (truncated to 12 chars)
    return question.id[:12].title()
