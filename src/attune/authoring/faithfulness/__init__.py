"""Faithfulness judge integration for polished docs.

Phase 3 of the polish-fact-check spec
(``docs/specs/polish-fact-check``). Wraps
:class:`attune_rag.eval.faithfulness.FaithfulnessJudge` as a
post-polish step: score the polished file's claims against the
source files it was generated from. When the score falls below
the configured threshold, append a ``## Faithfulness review``
block to the polished file so a human can review.

The judge is best-effort:

- Returns ``None`` if ``attune-rag[claude]`` isn't installed.
- Returns ``None`` if the active venv has no ``ANTHROPIC_API_KEY``.
- Returns ``None`` when the estimated cost would exceed the
  configured per-file budget cap.
- Catches transient API/network failures and returns ``None``
  rather than failing the polish.

A ``None`` result skips the review block. The polish itself is
never blocked on the judge.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from attune.model_tiers import resolve_model

logger = logging.getLogger(__name__)


#: Approximate cost per 1K input tokens for the judge model.
#: The dict keys match the substrings we search for in the model
#: id; first match wins. "fable" uses opus-class rates — the
#: conservative assumption for the budget gate until real fable
#: pricing telemetry says otherwise.
_COST_PER_1K_INPUT_TOKENS: dict[str, float] = {
    "haiku": 0.001,
    "sonnet": 0.003,
    "opus": 0.015,
    "fable": 0.015,
}

#: Approximate output-token cost. Output is typically ~1/5 of
#: input for the judge but we cap the estimate at a quarter so
#: the budget gate is conservative.
_COST_PER_1K_OUTPUT_TOKENS: dict[str, float] = {
    "haiku": 0.005,
    "sonnet": 0.015,
    "opus": 0.075,
    "fable": 0.075,
}

#: Rough character-per-token estimate used to convert sizes to
#: tokens without invoking a tokenizer. Accurate to within ~20%
#: for English prose — well inside what the budget gate cares
#: about.
_CHARS_PER_TOKEN = 4


@dataclass
class FaithfulnessConfig:
    """Faithfulness-judge configuration.

    Attributes:
        enabled: Master switch. ``False`` skips the judge entirely.
        threshold: Score below this triggers a review block. Range
            ``[0.0, 1.0]``. Default is the spec's pre-calibration
            placeholder; tune via ``[tool.attune-author.fact-check]``.
        budget_per_file_usd: Skip the judge call when the estimated
            cost (input + output tokens × model price) would exceed
            this. Default ``$0.10`` matches the spec.
        model: Judge model name. Defaults to the premium tier
            (``ATTUNE_MODEL_PREMIUM`` env pin respected); Haiku 4.5
            is a fraction of the cost and usable for high-volume runs.
        block_polish_on_unavailable: When ``True``, missing
            ``attune-rag[claude]`` or missing API key raises rather
            than degrading silently. Default ``False`` — the judge is
            best-effort.
    """

    enabled: bool = False
    threshold: float = 0.95
    budget_per_file_usd: float = 0.10
    model: str = field(default_factory=lambda: resolve_model("premium"))
    block_polish_on_unavailable: bool = False


@dataclass
class JudgeOutcome:
    """Outcome of a single judge call.

    ``score`` is ``None`` for skipped runs (disabled, unavailable,
    over-budget) so callers can disambiguate "judge ran, all claims
    supported" from "judge didn't run".
    """

    score: float | None
    threshold_met: bool
    cost_estimate_usd: float
    supported_claims: list[str]
    unsupported_claims: list[str]
    reasoning: str
    skipped_reason: str | None = None


def estimate_cost_usd(input_chars: int, model: str, *, output_chars: int = 2000) -> float:
    """Estimate the judge-call cost from input/output character sizes.

    Uses a coarse chars-per-token approximation and a per-model
    price lookup. The default ``output_chars`` matches the judge's
    typical reply length. Pure: no network, no I/O.
    """
    model_lower = model.lower()
    input_rate = next(
        (rate for key, rate in _COST_PER_1K_INPUT_TOKENS.items() if key in model_lower),
        _COST_PER_1K_INPUT_TOKENS["sonnet"],
    )
    output_rate = next(
        (rate for key, rate in _COST_PER_1K_OUTPUT_TOKENS.items() if key in model_lower),
        _COST_PER_1K_OUTPUT_TOKENS["sonnet"],
    )
    input_tokens = input_chars / _CHARS_PER_TOKEN
    output_tokens = output_chars / _CHARS_PER_TOKEN
    return (input_tokens / 1000.0) * input_rate + (output_tokens / 1000.0) * output_rate


def judge_polished_file(
    polished_path: Path,
    source_paths: list[Path],
    *,
    config: FaithfulnessConfig,
) -> JudgeOutcome:
    """Run the faithfulness judge against a single polished file.

    Args:
        polished_path: Polished markdown file written by the polish pass.
        source_paths: Source ``.py`` files the polish had as context.
            Concatenated and passed as the judge's "passages" argument.
        config: Resolved faithfulness configuration.

    Returns:
        A :class:`JudgeOutcome`. ``score is None`` indicates the judge
        was skipped — see ``skipped_reason``.

    Raises:
        RuntimeError: When ``config.block_polish_on_unavailable`` is
            True and the judge can't run (missing extra or key).
    """
    if not config.enabled:
        return _skipped("disabled")

    answer = ""
    try:
        answer = polished_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("faithfulness: cannot read %s (%s)", polished_path, exc)
        return _skipped("polished file unreadable")

    passages: list[str] = []
    for src in source_paths:
        try:
            passages.append(src.read_text(encoding="utf-8"))
        except OSError as exc:
            logger.debug("faithfulness: skip source %s (%s)", src, exc)
            continue

    if not passages:
        return _skipped("no readable source passages")

    total_chars = len(answer) + sum(len(p) for p in passages)
    cost_est = estimate_cost_usd(total_chars, config.model)
    if cost_est > config.budget_per_file_usd:
        logger.info(
            "faithfulness: skipping %s (estimated $%.4f > budget $%.4f)",
            polished_path.name,
            cost_est,
            config.budget_per_file_usd,
        )
        return JudgeOutcome(
            score=None,
            threshold_met=True,
            cost_estimate_usd=cost_est,
            supported_claims=[],
            unsupported_claims=[],
            reasoning="",
            skipped_reason="over-budget",
        )

    try:
        from attune_rag.eval.faithfulness import FaithfulnessJudge
    except ImportError as exc:
        message = (
            "attune-rag[claude] not installed; " "install with: pip install 'attune-rag[claude]'"
        )
        if config.block_polish_on_unavailable:
            raise RuntimeError(message) from exc
        logger.info("faithfulness: %s", message)
        return JudgeOutcome(
            score=None,
            threshold_met=True,
            cost_estimate_usd=cost_est,
            supported_claims=[],
            unsupported_claims=[],
            reasoning="",
            skipped_reason="attune-rag[claude] not installed",
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        if config.block_polish_on_unavailable:
            raise RuntimeError("ANTHROPIC_API_KEY not set; faithfulness judge cannot run.")
        logger.info("faithfulness: ANTHROPIC_API_KEY not set, skipping judge.")
        return JudgeOutcome(
            score=None,
            threshold_met=True,
            cost_estimate_usd=cost_est,
            supported_claims=[],
            unsupported_claims=[],
            reasoning="",
            skipped_reason="ANTHROPIC_API_KEY missing",
        )

    import asyncio

    try:
        judge = FaithfulnessJudge(model=config.model)
        result = asyncio.run(
            judge.score(
                query=f"Documentation for {polished_path.stem}",
                answer=answer,
                passages=passages,
            )
        )
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: best-effort. Network errors, SDK errors, or
        # transient API failures should not block the polish.
        logger.warning("faithfulness: judge call failed (%s)", exc)
        return JudgeOutcome(
            score=None,
            threshold_met=True,
            cost_estimate_usd=cost_est,
            supported_claims=[],
            unsupported_claims=[],
            reasoning="",
            skipped_reason=f"judge call failed: {exc!s}"[:200],
        )

    threshold_met = result.score >= config.threshold
    return JudgeOutcome(
        score=result.score,
        threshold_met=threshold_met,
        cost_estimate_usd=cost_est,
        supported_claims=list(result.supported_claims),
        unsupported_claims=list(result.unsupported_claims),
        reasoning=result.reasoning,
    )


def format_review_block(outcome: JudgeOutcome, threshold: float) -> str:
    """Render a ``## Faithfulness review`` block for soft-fail output.

    The block matches the Phase 1 ``## Unresolved references`` shape
    so editors find both with the same scan.
    """
    if outcome.score is None:
        return ""
    lines = [
        "## Faithfulness review",
        "",
        f"> Auto-generated by attune-author faithfulness judge. "
        f"Score {outcome.score:.2f} fell below the configured "
        f"threshold of {threshold:.2f}. Review unsupported claims "
        f"and either fix the source code or fix this doc.",
        "",
        f"**Score:** {outcome.score:.2f} "
        f"(supported: {len(outcome.supported_claims)}, "
        f"unsupported: {len(outcome.unsupported_claims)})",
    ]
    if outcome.unsupported_claims:
        lines.extend(["", "### Unsupported claims", ""])
        for claim in outcome.unsupported_claims:
            lines.append(f"- {claim}")
    if outcome.reasoning:
        lines.extend(["", "### Reasoning", "", outcome.reasoning.strip()])
    return "\n".join(lines)


def apply_review_block(polished_path: Path, block: str) -> bool:
    """Append the review block to ``polished_path``.

    Returns True if a block was appended, False if the block was
    empty. Matches the Phase 1 ``apply_soft_fail`` contract.
    """
    if not block:
        return False
    existing = polished_path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    polished_path.write_text(existing + block + "\n", encoding="utf-8")
    return True


def _skipped(reason: str) -> JudgeOutcome:
    return JudgeOutcome(
        score=None,
        threshold_met=True,
        cost_estimate_usd=0.0,
        supported_claims=[],
        unsupported_claims=[],
        reasoning="",
        skipped_reason=reason,
    )


from .config import load_config  # noqa: E402 - re-export, must come after dataclasses

__all__ = [
    "FaithfulnessConfig",
    "JudgeOutcome",
    "apply_review_block",
    "estimate_cost_usd",
    "format_review_block",
    "judge_polished_file",
    "load_config",
]
