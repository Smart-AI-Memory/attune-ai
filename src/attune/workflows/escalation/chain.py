"""EscalationChain — retry-with-feedback LLM wrapper.

Starts on the cheapest model tier, retries with injected feedback on
failure, and escalates to the next tier only after retries are exhausted.
An optional evaluator LLM provides semantic quality checks after
structural validators pass.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from attune.model_tiers import resolve_model
from attune.workflows.escalation.evaluator import Evaluator
from attune.workflows.escalation.models import (
    AttemptResult,
    EscalationResult,
    FeedbackType,
    ValidationFeedback,
)
from attune.workflows.escalation.validators import Validator

logger = logging.getLogger(__name__)


class EscalationChain:
    """Retry-with-feedback escalation across model tiers.

    Runs a prompt through a sequence of model tiers (cheap → capable →
    premium). On each tier it retries up to ``retries_per_model`` times,
    injecting structured failure feedback into each retry prompt. When all
    retries for a tier are exhausted it escalates, carrying a summary of
    prior failures into the first prompt of the next tier.

    Args:
        models: Ordered list of model IDs to try. Defaults to
            Haiku → Sonnet → premium tier (via attune.model_tiers).
        validators: Rule-based validators (Layer 1). Run on every attempt
            before the evaluator.
        evaluator: Optional LLM-based semantic evaluator (Layer 2). Runs
            after validators pass. Gate controls when it fires.
        retries_per_model: How many same-model retries to attempt before
            escalating. 0 = escalate immediately on first failure.
        expect_json: When True, parse the raw response as JSON. When False,
            return the raw string.
        system_prompt: Optional system prompt sent with every LLM call.
        max_tokens: Max tokens for each generator call.
        executor: EmpathyLLMExecutor instance. Created lazily if not provided.

    Example:
        >>> chain = EscalationChain(
        ...     validators=[StructureValidator(["answer"])],
        ...     retries_per_model=1,
        ... )
        >>> result = await chain.run("What is 2+2?")
        >>> print(result.summary())
        '✓ claude-haiku-4-5'

    """

    def __init__(
        self,
        models: list[str] | None = None,
        validators: list[Validator] | None = None,
        evaluator: Evaluator | None = None,
        retries_per_model: int = 1,
        expect_json: bool = True,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        executor: Any | None = None,
    ) -> None:
        """Initialize EscalationChain.

        Args:
            models: Ordered model IDs. Defaults to Haiku → Sonnet →
                premium tier.
            validators: Rule-based validators applied before the evaluator.
            evaluator: Optional semantic evaluator with gate control.
            retries_per_model: Same-model retries before escalation (0 = none).
            expect_json: Parse raw response as JSON when True.
            system_prompt: System prompt sent with every generator call.
            max_tokens: Max tokens for each generator call.
            executor: EmpathyLLMExecutor. Created lazily if omitted.

        """
        # Built per instance so the premium tier honors env overrides at
        # call time (a class attribute would freeze the env read at import).
        self.models = models or [
            "claude-haiku-4-5",
            "claude-sonnet-4-5",
            resolve_model("premium"),
        ]
        self.validators: list[Validator] = validators or []
        self.evaluator = evaluator
        self.retries_per_model = retries_per_model
        self.expect_json = expect_json
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self._executor = executor

    def _get_executor(self) -> Any:
        """Lazy-initialize EmpathyLLMExecutor."""
        if self._executor is None:
            from attune.models.empathy_executor import EmpathyLLMExecutor

            self._executor = EmpathyLLMExecutor(provider="anthropic")
        return self._executor

    async def run(self, prompt: str) -> EscalationResult:
        """Run the prompt through the escalation chain.

        Args:
            prompt: User prompt to send to the LLM.

        Returns:
            EscalationResult with the final response and full audit trail.

        """
        all_attempts: list[AttemptResult] = []
        total_retries = 0
        total_escalations = 0
        prior_tier_feedback: list[ValidationFeedback] = []

        for tier_index, model in enumerate(self.models):
            is_last_tier = tier_index == len(self.models) - 1
            accumulated_feedback: list[ValidationFeedback] = []

            for attempt_num in range(1, self.retries_per_model + 2):  # 1 initial + N retries
                is_retry = attempt_num > 1

                # First attempt of a new tier: inject summary of prior failures
                escalation_context = (
                    prior_tier_feedback if (tier_index > 0 and not is_retry) else []
                )

                effective_prompt = self._build_prompt(
                    original_prompt=prompt,
                    feedback=accumulated_feedback if is_retry else escalation_context,
                )

                attempt = await self._try_model(model, effective_prompt, attempt_num, is_retry)
                all_attempts.append(attempt)

                if is_retry:
                    total_retries += 1

                # Bail early if the API call itself failed
                if any(
                    f.feedback_type in (FeedbackType.EXCEPTION, FeedbackType.PARSE_FAILURE)
                    for f in attempt.feedback
                ):
                    accumulated_feedback.extend(attempt.feedback)
                    if attempt_num <= self.retries_per_model:
                        continue
                    break

                # Layer 1: structural validators
                structural_passed, structural_feedback = self._run_validators(
                    attempt.parsed_response,
                )
                if not structural_passed:
                    accumulated_feedback.extend(structural_feedback)
                    attempt.feedback = structural_feedback
                    attempt.success = False
                    if attempt_num <= self.retries_per_model:
                        continue
                    break

                # Layer 2: semantic evaluator (optional)
                if self.evaluator is not None and self.evaluator.should_run(is_last_tier):
                    eval_passed, eval_feedback = await self.evaluator.evaluate(  # type: ignore[union-attr]
                        prompt=prompt,
                        response=attempt.parsed_response,
                        context={"model": model, "attempt": attempt_num},
                    )
                    attempt.evaluator_model = self.evaluator.evaluator_model  # type: ignore[union-attr]

                    if not eval_passed and eval_feedback:
                        accumulated_feedback.append(eval_feedback)
                        attempt.feedback = [eval_feedback]
                        attempt.success = False
                        if attempt_num <= self.retries_per_model:
                            continue
                        break

                # All checks passed
                attempt.success = True
                return EscalationResult(
                    success=True,
                    response=attempt.parsed_response,
                    final_model=model,
                    attempts=all_attempts,
                    total_retries=total_retries,
                    total_escalations=total_escalations,
                    total_cost_estimate=self._total_cost(all_attempts),
                )

            # Tier exhausted — carry failure summary to next tier
            prior_tier_feedback = self._summarize_prior_failures(all_attempts)
            if not is_last_tier:
                total_escalations += 1

        return self._best_failure(all_attempts, total_retries, total_escalations)

    async def _try_model(
        self,
        model: str,
        prompt: str,
        attempt_num: int,
        is_retry: bool,
    ) -> AttemptResult:
        """Call the model and return an AttemptResult.

        Catches exceptions and records them as EXCEPTION or PARSE_FAILURE
        feedback rather than propagating, so the chain can keep escalating.

        Args:
            model: Model ID to call.
            prompt: Prompt to send (may include injected feedback).
            attempt_num: Attempt number on the current tier.
            is_retry: True when this is a same-model retry.

        Returns:
            AttemptResult with success=False (caller sets True if checks pass).

        """
        from attune.models.executor import ExecutionContext

        start = time.monotonic()
        executor = self._get_executor()

        try:
            response = await executor.run(
                task_type="escalation",
                prompt=prompt,
                system=self.system_prompt,
                context=ExecutionContext(metadata={"model_override": model}),
                model=model,
                max_tokens=self.max_tokens,
            )
            latency_ms = (time.monotonic() - start) * 1000
            raw_response = response.content

            try:
                parsed_response = json.loads(raw_response) if self.expect_json else raw_response
            except json.JSONDecodeError as exc:
                return AttemptResult(
                    model=model,
                    attempt_number=attempt_num,
                    raw_response=raw_response,
                    parsed_response=None,
                    success=False,
                    is_retry=is_retry,
                    latency_ms=latency_ms,
                    input_tokens=response.tokens_input,
                    output_tokens=response.tokens_output,
                    feedback=[
                        ValidationFeedback(
                            feedback_type=FeedbackType.PARSE_FAILURE,
                            validator_name="_try_model",
                            message=f"JSON parse failed: {exc}",
                            suggestion="Respond with valid JSON only.",
                        ),
                    ],
                )

            return AttemptResult(
                model=model,
                attempt_number=attempt_num,
                raw_response=raw_response,
                parsed_response=parsed_response,
                success=False,  # Set True by caller if all checks pass
                is_retry=is_retry,
                latency_ms=latency_ms,
                input_tokens=response.tokens_input,
                output_tokens=response.tokens_output,
            )

        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: API errors keep the chain alive for escalation.
            logger.warning(
                "EscalationChain: API error on %s attempt %d: %s",
                model,
                attempt_num,
                exc,
            )
            return AttemptResult(
                model=model,
                attempt_number=attempt_num,
                raw_response="",
                parsed_response=None,
                success=False,
                is_retry=is_retry,
                latency_ms=(time.monotonic() - start) * 1000,
                feedback=[
                    ValidationFeedback(
                        feedback_type=FeedbackType.EXCEPTION,
                        validator_name="_try_model",
                        message=f"API error: {exc}",
                    ),
                ],
            )

    def _summarize_prior_failures(self, attempts: list[AttemptResult]) -> list[ValidationFeedback]:
        """Collect deduplicated failure feedback from all prior attempts.

        Injected into the first prompt of the next tier so the better model
        starts informed rather than repeating the same mistakes.

        Args:
            attempts: All attempts recorded so far.

        Returns:
            Deduplicated list of ValidationFeedback items.

        """
        seen: set[str] = set()
        summary: list[ValidationFeedback] = []
        for attempt in attempts:
            for fb in attempt.feedback:
                if fb.message not in seen:
                    seen.add(fb.message)
                    summary.append(fb)
        return summary

    def _build_prompt(
        self,
        original_prompt: str,
        feedback: list[ValidationFeedback],
    ) -> str:
        """Inject validation feedback into the retry or escalation prompt.

        Args:
            original_prompt: The original user prompt.
            feedback: Feedback items to inject (empty list = no injection).

        Returns:
            Original prompt unchanged, or prompt with appended feedback block.

        """
        if not feedback:
            return original_prompt

        feedback_block = "\n".join(
            f"- [{fb.feedback_type.value}] {fb.message}"
            + (f" Suggestion: {fb.suggestion}" if fb.suggestion else "")
            for fb in feedback
        )

        return (
            f"{original_prompt}\n\n"
            "<previous_attempt_feedback>\n"
            "Your previous response had the following issues:\n"
            f"{feedback_block}\n"
            "Please address these issues in your response.\n"
            "</previous_attempt_feedback>"
        )

    def _run_validators(self, response: Any) -> tuple[bool, list[ValidationFeedback]]:
        """Run all structural validators against the parsed response.

        Args:
            response: Parsed LLM response.

        Returns:
            (all_passed, list_of_feedback) — feedback is empty when all pass.

        """
        all_feedback: list[ValidationFeedback] = []
        all_passed = True

        for validator in self.validators:
            passed, message = validator.validate(response)
            if not passed:
                all_passed = False
                all_feedback.append(
                    ValidationFeedback(
                        feedback_type=FeedbackType.STRUCTURAL,
                        validator_name=type(validator).__name__,
                        message=message or "Validation failed",
                    ),
                )

        return all_passed, all_feedback

    def _best_failure(
        self,
        attempts: list[AttemptResult],
        retries: int,
        escalations: int,
    ) -> EscalationResult:
        """Return the best failed attempt when all tiers are exhausted.

        Prefers attempts that at least produced a parsed response.

        Args:
            attempts: All recorded attempts.
            retries: Total same-model retries.
            escalations: Total tier escalations.

        Returns:
            EscalationResult with success=False and the best partial response.

        """
        parsed = [a for a in attempts if a.parsed_response is not None]
        best = parsed[-1] if parsed else attempts[-1]

        return EscalationResult(
            success=False,
            response=best.parsed_response,
            final_model=best.model,
            attempts=attempts,
            total_retries=retries,
            total_escalations=escalations,
            total_cost_estimate=self._total_cost(attempts),
        )

    def _total_cost(self, attempts: list[AttemptResult]) -> float:
        """Sum cost estimates across all attempts using registry pricing.

        Args:
            attempts: Attempts to sum cost for.

        Returns:
            Total estimated cost in USD.

        """
        from attune.models.registry import get_model

        total = 0.0
        for attempt in attempts:
            model_info = get_model("anthropic", attempt.model)
            if model_info:
                total += (
                    attempt.input_tokens / 1_000_000 * model_info.input_cost_per_million
                    + attempt.output_tokens / 1_000_000 * model_info.output_cost_per_million
                )
        return total
