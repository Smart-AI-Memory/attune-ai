# Enhanced Feedback Loop Escalation — Architecture Sketch

## Overview

Extends the existing `EscalationChain` with two new capabilities:

1. **Retry-with-feedback** before escalating to a costlier model
2. **Evaluator LLM layer** for semantic validation after structural checks pass

The core philosophy stays the same: start cheap, escalate only when necessary.
The feedback loop makes smarter use of each model tier before giving up on it.

---

## Flow Summary

```text
Request
  → Select model tier (Haiku → Sonnet → Opus)
    → Generate response
      → Layer 1: Rule-based validators (fast, structural)
        → FAIL? → Inject feedback → Retry on same model (up to N)
        → PASS? → Layer 2: Evaluator LLM (semantic quality)
          → FAIL? → Inject feedback → Retry on same model (up to N)
          → PASS? → Return success + audit trail
      → Retries exhausted? → Escalate to next tier (carry failure summary)
  → All tiers exhausted? → Return best failed attempt + audit trail
```

---

## Enhanced Data Structures

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeedbackType(Enum):
    """What kind of feedback triggered the retry/escalation."""
    STRUCTURAL = "structural"       # Rule-based validator caught it
    SEMANTIC = "semantic"           # Evaluator LLM caught it
    PARSE_FAILURE = "parse_failure" # Couldn't parse response format
    EXCEPTION = "exception"         # API or processing error


@dataclass
class ValidationFeedback:
    """Structured feedback from a validation step."""
    feedback_type: FeedbackType
    validator_name: str
    message: str
    severity: str = "error"  # "error" | "warning"
    suggestion: str | None = None  # Optional fix suggestion for retry prompt


@dataclass
class AttemptResult:
    """Enhanced attempt result with feedback history."""
    model: str
    attempt_number: int              # Which attempt on THIS model (1, 2, ...)
    raw_response: str
    parsed_response: Any | None
    success: bool
    feedback: list[ValidationFeedback] = field(default_factory=list)
    is_retry: bool = False           # Was this a retry on the same model?
    evaluator_model: str | None = None  # Which model did the semantic eval
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class EscalationResult:
    """Final result with full audit trail."""
    success: bool
    response: Any | None
    final_model: str
    attempts: list[AttemptResult] = field(default_factory=list)
    total_retries: int = 0           # Same-model retries
    total_escalations: int = 0       # Model tier jumps
    total_cost_estimate: float = 0.0 # Accumulated token cost

    def summary(self) -> str:
        if self.success:
            retries = f", {self.total_retries} retry(ies)" if self.total_retries else ""
            escalations = f", {self.total_escalations} escalation(s)" if self.total_escalations else ""
            return f"✓ {self.final_model}{retries}{escalations}"
        return f"✗ Failed after {len(self.attempts)} attempt(s)"
```

---

## Evaluator LLM Interface

```python
import json
from abc import ABC, abstractmethod


class Evaluator(ABC):
    """Base class for LLM-based semantic evaluation."""

    @abstractmethod
    async def evaluate(
        self,
        prompt: str,
        response: Any,
        context: dict | None = None,
    ) -> tuple[bool, ValidationFeedback | None]:
        """
        Returns (passed, feedback_if_failed).

        Args:
            prompt: The original user prompt
            response: The parsed model response
            context: Optional metadata (model used, attempt number, etc.)
        """
        pass

    def should_run(self, is_last_tier: bool) -> bool:
        """Return True if the evaluator should run for this tier.

        Override in subclasses to control when evaluation is triggered.
        Default: always run.
        """
        return True


class SemanticEvaluator(Evaluator):
    """
    Uses a lightweight LLM to judge response quality.

    Design decisions:
    - Always uses Haiku for evaluation (cheap, fast)
    - Asks structured yes/no questions, not open-ended critique
    - Returns actionable feedback the generator can use on retry
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
    "passed": true/false,
    "failed_criteria": [],
    "feedback": "specific, actionable feedback if failed"
}}"""

    def __init__(
        self,
        evaluator_model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 256,
        gate: str = "always",  # "always" | "last_tier" | "never"
    ):
        self.evaluator_model = evaluator_model
        self.max_tokens = max_tokens
        self.gate = gate

    def should_run(self, is_last_tier: bool) -> bool:
        """Return True if this evaluator should run for the current tier."""
        if self.gate == "never":
            return False
        if self.gate == "last_tier":
            return is_last_tier
        return True  # "always"

    async def evaluate(
        self,
        prompt: str,
        response: Any,
        context: dict | None = None,
    ) -> tuple[bool, ValidationFeedback | None]:
        eval_prompt = self.EVAL_PROMPT_TEMPLATE.format(
            prompt=prompt,
            response=json.dumps(response) if isinstance(response, dict) else str(response),
        )

        result = await self._call_evaluator(eval_prompt)

        if result.get("passed", False):
            return True, None

        return False, ValidationFeedback(
            feedback_type=FeedbackType.SEMANTIC,
            validator_name="SemanticEvaluator",
            message=result.get("feedback", "Semantic evaluation failed"),
            suggestion=result.get("feedback"),
        )
```

---

## Enhanced EscalationChain

```python
class EscalationChain:
    """
    Enhanced escalation with feedback loop.

    New parameters:
    - retries_per_model: How many same-model retries before escalating
    - evaluator: Optional Evaluator for semantic validation (Layer 2)
    - evaluator_gate: When to run the evaluator ("always", "last_tier", "never")
    """

    DEFAULT_MODELS = [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-8",
    ]

    def __init__(
        self,
        models: list[str] | None = None,
        validators: list[Validator] | None = None,
        evaluator: Evaluator | None = None,
        retries_per_model: int = 1,           # 0 = no retries, go straight to escalation
        expect_json: bool = True,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        executor: EmpathyLLMExecutor | None = None,
    ):
        self.models = models or self.DEFAULT_MODELS
        self.validators = validators or []
        self.evaluator = evaluator
        self.retries_per_model = retries_per_model
        self.expect_json = expect_json
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.executor = executor or EmpathyLLMExecutor()

    async def run(self, prompt: str) -> EscalationResult:
        all_attempts: list[AttemptResult] = []
        total_retries = 0
        total_escalations = 0
        prior_tier_feedback: list[ValidationFeedback] = []

        for tier_index, model in enumerate(self.models):
            is_last_tier = (tier_index == len(self.models) - 1)
            accumulated_feedback: list[ValidationFeedback] = []

            for attempt_num in range(1, self.retries_per_model + 2):  # 1 initial + N retries
                is_retry = attempt_num > 1

                # On the first attempt of a new tier, inject a summary of
                # why prior tiers failed so the better model starts informed.
                escalation_context = (
                    prior_tier_feedback if (tier_index > 0 and not is_retry) else []
                )

                effective_prompt = self._build_prompt(
                    original_prompt=prompt,
                    feedback=accumulated_feedback if is_retry else escalation_context,
                )

                # Generate — exceptions recorded as EXCEPTION feedback
                attempt = await self._try_model(model, effective_prompt, attempt_num, is_retry)
                all_attempts.append(attempt)

                if is_retry:
                    total_retries += 1

                # Bail early if _try_model recorded an exception
                if any(f.feedback_type == FeedbackType.EXCEPTION for f in attempt.feedback):
                    accumulated_feedback.extend(attempt.feedback)
                    if attempt_num <= self.retries_per_model:
                        continue
                    else:
                        break

                # --- Layer 1: Rule-based validation ---
                structural_passed, structural_feedback = self._run_validators(
                    attempt.parsed_response
                )

                if not structural_passed:
                    accumulated_feedback.extend(structural_feedback)
                    attempt.feedback = structural_feedback
                    attempt.success = False

                    if attempt_num <= self.retries_per_model:
                        continue
                    else:
                        break

                # --- Layer 2: Evaluator LLM (if configured) ---
                if self._should_evaluate(is_last_tier):
                    eval_passed, eval_feedback = await self.evaluator.evaluate(
                        prompt=prompt,
                        response=attempt.parsed_response,
                        context={"model": model, "attempt": attempt_num},
                    )
                    attempt.evaluator_model = self.evaluator.evaluator_model

                    if not eval_passed and eval_feedback:
                        accumulated_feedback.append(eval_feedback)
                        attempt.feedback = [eval_feedback]
                        attempt.success = False

                        if attempt_num <= self.retries_per_model:
                            continue
                        else:
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

            # Model tier exhausted — carry feedback summary to next tier
            prior_tier_feedback = self._summarize_prior_failures(all_attempts)
            if not is_last_tier:
                total_escalations += 1

        return self._best_failure(all_attempts, total_retries, total_escalations)

    def _total_cost(self, attempts: list[AttemptResult]) -> float:
        """Sum cost estimates across all attempts using registry pricing."""
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

    async def _try_model(
        self,
        model: str,
        prompt: str,
        attempt_num: int,
        is_retry: bool,
    ) -> AttemptResult:
        """Call the model and return an AttemptResult.

        Exceptions are caught and recorded as EXCEPTION feedback rather than
        propagated, keeping the chain alive for escalation.
        """
        try:
            from attune.models.empathy_executor import EmpathyLLMExecutor
            from attune.models.executor import ExecutionContext

            response = await self.executor.run(
                task_type="escalation",
                prompt=prompt,
                system=self.system_prompt,
                context=ExecutionContext(metadata={"model_override": model}),
                # Pass model explicitly so EmpathyLLM uses it instead of
                # routing via task_type tier resolution.
                model=model,
                max_tokens=self.max_tokens,
            )

            raw_response = response.content
            parsed_response = json.loads(raw_response) if self.expect_json else raw_response

            return AttemptResult(
                model=model,
                attempt_number=attempt_num,
                raw_response=raw_response,
                parsed_response=parsed_response,
                success=False,  # Will be set True if all checks pass
                is_retry=is_retry,
                input_tokens=response.tokens_input,
                output_tokens=response.tokens_output,
            )
        except json.JSONDecodeError as e:
            return AttemptResult(
                model=model,
                attempt_number=attempt_num,
                raw_response="",
                parsed_response=None,
                success=False,
                is_retry=is_retry,
                feedback=[ValidationFeedback(
                    feedback_type=FeedbackType.PARSE_FAILURE,
                    validator_name="_try_model",
                    message=f"JSON parse failed: {e}",
                    suggestion="Respond with valid JSON only.",
                )],
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: API errors should not crash the chain — record and
            # allow escalation to the next tier.
            return AttemptResult(
                model=model,
                attempt_number=attempt_num,
                raw_response="",
                parsed_response=None,
                success=False,
                is_retry=is_retry,
                feedback=[ValidationFeedback(
                    feedback_type=FeedbackType.EXCEPTION,
                    validator_name="_try_model",
                    message=f"API error: {e}",
                )],
            )

    def _summarize_prior_failures(
        self, attempts: list[AttemptResult]
    ) -> list[ValidationFeedback]:
        """Collect unique failure feedback from all prior attempts.

        Passed to the first prompt of the next tier so the better model
        starts informed rather than repeating the same mistakes.
        """
        seen: set[str] = set()
        summary: list[ValidationFeedback] = []
        for attempt in attempts:
            for fb in attempt.feedback:
                if fb.message not in seen:
                    seen.add(fb.message)
                    summary.append(fb)
        return summary

    def _should_evaluate(self, is_last_tier: bool) -> bool:
        """Decide whether to run the evaluator LLM."""
        if self.evaluator is None:
            return False
        return self.evaluator.should_run(is_last_tier)

    def _build_prompt(
        self,
        original_prompt: str,
        feedback: list[ValidationFeedback],
    ) -> str:
        """Inject validation feedback into the retry or escalation prompt."""
        if not feedback:
            return original_prompt

        feedback_block = "\n".join(
            f"- [{fb.feedback_type.value}] {fb.message}"
            + (f" Suggestion: {fb.suggestion}" if fb.suggestion else "")
            for fb in feedback
        )

        return f"""{original_prompt}

<previous_attempt_feedback>
Your previous response had the following issues:
{feedback_block}
Please address these issues in your response.
</previous_attempt_feedback>"""

    def _run_validators(
        self, response: Any
    ) -> tuple[bool, list[ValidationFeedback]]:
        """Run all rule-based validators. Returns (all_passed, feedback_list)."""
        all_feedback = []
        all_passed = True

        for validator in self.validators:
            passed, message = validator.validate(response)
            if not passed:
                all_passed = False
                all_feedback.append(ValidationFeedback(
                    feedback_type=FeedbackType.STRUCTURAL,
                    validator_name=type(validator).__name__,
                    message=message or "Validation failed",
                ))

        return all_passed, all_feedback

    def _best_failure(
        self, attempts: list[AttemptResult], retries: int, escalations: int
    ) -> EscalationResult:
        """Return the best failed attempt (one that at least parsed)."""
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
```

---

## Convenience API

```python
async def escalate(
    prompt: str,
    required_fields: list[str] | None = None,
    min_confidence: float | None = None,
    system_prompt: str | None = None,
    retries: int = 0,
    use_evaluator: bool = False,
) -> EscalationResult:
    """
    Quick-start API. Backward compatible — retries defaults to 0.

    Usage:
        # Minimal — same behavior as before
        result = await escalate("What is 2+2?", required_fields=["answer"])

        # Opt in to retry-with-feedback
        result = await escalate(
            "What is 2+2?",
            required_fields=["answer"],
            retries=1,
        )

        # With semantic evaluation
        result = await escalate(
            "Analyze this dataset...",
            required_fields=["analysis", "conclusion"],
            use_evaluator=True,
            retries=2,
        )
    """
    validators = []
    if required_fields:
        validators.append(StructureValidator(required_fields))
    if min_confidence is not None:
        validators.append(ConfidenceValidator(min_confidence=min_confidence))

    evaluator = SemanticEvaluator() if use_evaluator else None

    chain = EscalationChain(
        validators=validators,
        evaluator=evaluator,
        retries_per_model=retries,
        system_prompt=system_prompt,
    )

    return await chain.run(prompt)
```

---

## Key Design Decisions

### 1. Evaluator Gate (`gate` on the evaluator)

Running the evaluator LLM on every attempt costs tokens. The `gate` parameter
lives on the evaluator, not the chain — it controls when that evaluator fires:

- `"always"` — Maximum quality, highest cost. Use for high-stakes tasks.
- `"last_tier"` — Only run semantic eval on the most expensive model. Cheap
  models get structural checks only. Good balance.
- `"never"` — Rule-based only. Same as current behavior. Fastest, cheapest.

```python
# Always evaluate (default)
evaluator = SemanticEvaluator()

# Only evaluate at the premium tier
evaluator = SemanticEvaluator(gate="last_tier")
```

Note: `gate="last_tier"` with `retries_per_model > 1` means the evaluator
runs on every retry of the last tier. For large retry counts this can
accumulate cost — set `retries_per_model=1` when using `"last_tier"`.

### 2. Cross-Tier Feedback (`_summarize_prior_failures`)

When escalating to a new tier, a deduplicated summary of prior failures is
injected into the first prompt. The better model starts informed rather than
repeating mistakes the cheaper model already made.

### 3. Feedback Injection Format

Uses XML tags (`<previous_attempt_feedback>`) to clearly separate feedback
from the original prompt, preventing the model from confusing task
instructions with correction instructions.

### 4. Exception Handling in `_try_model`

API errors and JSON parse failures are caught inside `_try_model` and
returned as `EXCEPTION` / `PARSE_FAILURE` feedback rather than propagated.
This keeps the chain alive for escalation even when a tier's API call fails.
Broad `except Exception` is intentional here — annotated with `# noqa: BLE001`.

### 5. Best Failure Fallback

When all tiers are exhausted, returns the "best" failed attempt (one that
at least parsed) rather than nothing. The caller can decide what to do
with a partial result.

### 6. Backward Compatibility

`escalate()` defaults to `retries=0` — identical to the current behavior.
Retry-with-feedback is opt-in. Existing callers are unaffected.

### 7. Evaluator Model Choice

`SemanticEvaluator` defaults to Haiku — the cheapest option. Evaluation is
a structured yes/no judgment, not generation. Haiku handles this well.

---

## Migration Path from Current Implementation

The enhanced chain is **backward compatible**:

- `retries_per_model=0` + `evaluator=None` = exact current behavior
- Adding `retries_per_model=1` = feedback loop, no evaluator
- Adding `evaluator=SemanticEvaluator()` = full two-layer validation

```python
# Before (unchanged behavior)
result = await escalate("...", required_fields=["answer"])

# After — opt in to retries
result = await escalate("...", required_fields=["answer"], retries=1)

# After — full feedback loop with semantic eval
result = await escalate("...", required_fields=["answer"], retries=2, use_evaluator=True)
```
