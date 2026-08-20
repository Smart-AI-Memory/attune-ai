"""Evaluator ABC and SemanticEvaluator for EscalationChain.

Evaluators run as Layer 2 (semantic quality checks) after structural
validators pass. They use a lightweight LLM to judge response quality.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from attune.workflows.escalation.models import FeedbackType, ValidationFeedback

logger = logging.getLogger(__name__)


class Evaluator(ABC):
    """Base class for LLM-based semantic evaluation.

    Subclasses implement ``evaluate()`` and may override ``should_run()``
    to control when evaluation is triggered (e.g. only on the last tier).

    Example:
        >>> class MyEvaluator(Evaluator):
        ...     async def evaluate(self, prompt, response, context=None):
        ...         passed = len(str(response)) > 10
        ...         if passed:
        ...             return True, None
        ...         return False, ValidationFeedback(
        ...             feedback_type=FeedbackType.SEMANTIC,
        ...             validator_name="MyEvaluator",
        ...             message="Response too short",
        ...         )

    """

    @abstractmethod
    async def evaluate(
        self,
        prompt: str,
        response: Any,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, ValidationFeedback | None]:
        """Evaluate the response and return (passed, feedback_if_failed).

        Args:
            prompt: The original user prompt sent to the generator.
            response: The parsed model response to evaluate.
            context: Optional metadata (model used, attempt number, etc.).

        Returns:
            (True, None) on pass or (False, ValidationFeedback) on fail.

        """
        ...

    def should_run(self, is_last_tier: bool) -> bool:
        """Return True if this evaluator should run for the current tier.

        Override in subclasses to control when evaluation fires.
        Default: always run regardless of tier.

        Args:
            is_last_tier: True when the chain is on its final model tier.

        Returns:
            True to run evaluation, False to skip it.

        """
        return True


class SemanticEvaluator(Evaluator):
    """Uses a lightweight LLM to judge response quality.

    Calls Haiku (cheap, fast) with a structured yes/no prompt. Returns
    actionable feedback the generator can use on retry.

    Args:
        evaluator_model: Model ID for the evaluator LLM (default: Haiku).
        max_tokens: Max tokens for the evaluation response.
        gate: When to run — "always", "last_tier", or "never".

    Example:
        >>> evaluator = SemanticEvaluator(gate="last_tier")
        >>> evaluator.should_run(is_last_tier=False)
        False
        >>> evaluator.should_run(is_last_tier=True)
        True

    """

    EVAL_PROMPT_TEMPLATE = """You are evaluating an AI response for quality.

<original_task>
{prompt}
</original_task>

<response_to_evaluate>
{response}
</response_to_evaluate>

Evaluate on these criteria:
1. Does the response actually answer the question asked?
2. Is the information complete (no critical gaps)?
3. Is it internally consistent (no contradictions)?

Respond with JSON only:
{{
    "passed": true,
    "failed_criteria": [],
    "feedback": ""
}}"""

    def __init__(
        self,
        evaluator_model: str = "claude-haiku-4-5",
        max_tokens: int = 256,
        gate: str = "always",
    ) -> None:
        """Initialize SemanticEvaluator.

        Args:
            evaluator_model: Model ID to use for evaluation calls.
            max_tokens: Maximum tokens for the evaluator response.
            gate: Controls when evaluation runs:
                "always" — run on every attempt (default),
                "last_tier" — only on the final model tier,
                "never" — disable semantic evaluation entirely.

        """
        self.evaluator_model = evaluator_model
        self.max_tokens = max_tokens
        self.gate = gate
        self._executor: Any | None = None

    def should_run(self, is_last_tier: bool) -> bool:
        """Return True if evaluation should run for the current tier.

        Args:
            is_last_tier: True when the chain is on its final model tier.

        Returns:
            True to run evaluation, False to skip.

        """
        if self.gate == "never":
            return False
        if self.gate == "last_tier":
            return is_last_tier
        return True  # "always"

    def _get_executor(self) -> Any:
        """Lazy-initialize a dedicated EmpathyLLMExecutor for evaluation."""
        if self._executor is None:
            from attune.models.empathy_executor import EmpathyLLMExecutor

            self._executor = EmpathyLLMExecutor(provider="anthropic")
        return self._executor

    async def evaluate(
        self,
        prompt: str,
        response: Any,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, ValidationFeedback | None]:
        """Evaluate response quality using a Haiku LLM call.

        Args:
            prompt: The original user prompt.
            response: The parsed model response to evaluate.
            context: Optional metadata (model used, attempt number, etc.).

        Returns:
            (True, None) if evaluation passes, (False, ValidationFeedback) otherwise.

        """
        response_str = json.dumps(response) if isinstance(response, dict) else str(response)
        eval_prompt = self.EVAL_PROMPT_TEMPLATE.format(
            prompt=prompt,
            response=response_str,
        )

        try:
            executor = self._get_executor()
            llm_response = await executor.run(
                task_type="evaluate",
                prompt=eval_prompt,
                model=self.evaluator_model,
                max_tokens=self.max_tokens,
            )
            result = json.loads(llm_response.content)
            if not isinstance(result, dict):
                # An evaluator that answers with a JSON array or scalar
                # is an evaluator failure, not a verdict: the .get calls
                # below sit outside this try, so without the guard a
                # non-object answer breaks the chain that the handler
                # right here promises never to block (library-review C3).
                raise ValueError(f"evaluator returned {type(result).__name__}, not an object")
        except ValueError:  # includes json.JSONDecodeError
            logger.warning("SemanticEvaluator: evaluator response was not a JSON object")
            return True, None  # Don't block on evaluator failure
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Evaluator errors should not block the chain.
            logger.exception("SemanticEvaluator: evaluation call failed")
            return True, None

        if result.get("passed", True):
            return True, None

        return False, ValidationFeedback(
            feedback_type=FeedbackType.SEMANTIC,
            validator_name="SemanticEvaluator",
            message=result.get("feedback", "Semantic evaluation failed"),
            suggestion=result.get("feedback") or None,
        )
