"""Haiku-summarized starter prompts for the /sessions page.

Defined by the ops-sessions-page spec (decisions.md, Decision 2 +
Decision 3). The orchestration:

    raw_session_text
        → redact(text)               (session_redaction.py)
        → claude-haiku-4-5 summarize (this module)
        → cache.save(redacted summ.) (session_summary_cache.py)

The summary text is what ends up in the dashboard's Starter Prompt
column and on disk. Redaction runs FIRST so neither the LLM
provider nor the on-disk cache ever sees sensitive material.

The prompt template targets the 3-part output shape from decisions.md
Decision 2:

    1. Names what was being worked on (1 short sentence).
    2. Lists any open threads (bullets, 0–3 items).
    3. Suggests a 1-sentence resume prompt the user can paste.

The text returned by :func:`summarize` is the LLM's verbatim output;
no parsing or restructuring at this layer. Callers render it as-is.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Model id — Haiku 4.5. Pricing per attune.llm.providers.anthropic
# (verified 2026-05-15): $1.00/M input, $5.00/M output.
_MODEL = "claude-haiku-4-5-20251001"
_INPUT_COST_PER_1M = 1.00
_OUTPUT_COST_PER_1M = 5.00

# Per-call output cap. Decisions.md Decision 2 wants a 3-part
# summary (one sentence + ≤3 bullets + one sentence) — 400 output
# tokens is plenty even with verbose phrasing.
_MAX_OUTPUT_TOKENS = 400

# Cap on the input text we send. A long session JSONL could easily
# be tens of KB; we truncate to bound spend per call. The target is
# a starter-prompt summary, not a full conversation distillation —
# the first ~6 KB of conversation captures the original ask and a
# few turns of context, which is the right material for a starter.
_INPUT_TEXT_CAP_CHARS = 6000

_SYSTEM_PROMPT = (
    "You are summarizing a developer's Claude Code session into a "
    "short starter prompt that helps them resume the work later. "
    "Produce EXACTLY three sections, formatted as Markdown:\n\n"
    "**What was being worked on.** One short sentence (≤25 words) "
    "naming the task. Use concrete nouns — file paths, feature "
    "names, bug shapes — not vague descriptors.\n\n"
    "**Open threads.** A bulleted list of 0–3 items. Each bullet "
    "names a specific unresolved decision, in-flight task, or "
    "blocker visible in the conversation. Skip this section "
    "entirely if there are no open threads — write the heading "
    "with no bullets below it.\n\n"
    "**Resume prompt.** One sentence (≤30 words) the user can "
    "paste into a fresh Claude Code session to pick up where they "
    "left off. Phrase it as a directive to Claude, not a "
    "description of what to do.\n\n"
    'Constraints: no preamble ("Sure, here\'s a summary..."). '
    "No closing remarks. If the conversation is too short or "
    "incoherent to summarize meaningfully, write a single line: "
    '"(session too short to summarize)" and stop.'
)


@dataclass(frozen=True)
class SummaryResult:
    """One LLM call's output plus the accounting needed for caching + budget."""

    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class MissingApiKeyError(RuntimeError):
    """Raised when ``ANTHROPIC_API_KEY`` is required but unset.

    Distinct exception type so callers can branch cleanly:
    surface "LLM gate is on but no key" as a config error vs
    other LLM-call failures (network, rate limit, etc.).
    """


def _truncate_input(text: str, *, cap: int = _INPUT_TEXT_CAP_CHARS) -> str:
    """Bound the input character count so per-call cost is predictable.

    Truncates at a paragraph or line boundary inside the last 10%
    of the cap, falling back to a hard cut when no boundary is
    found. Appends a sentinel so the LLM knows the input was cut.
    """
    if len(text) <= cap:
        return text
    cut = text[:cap]
    boundary = max(cut.rfind("\n\n"), cut.rfind("\n"))
    soft_floor = int(cap * 0.9)
    if boundary >= soft_floor:
        cut = cut[:boundary]
    return cut.rstrip() + "\n\n[...session truncated for summarization...]"


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Convert token counts to USD using Haiku 4.5 list pricing."""
    return (
        input_tokens / 1_000_000 * _INPUT_COST_PER_1M
        + output_tokens / 1_000_000 * _OUTPUT_COST_PER_1M
    )


def summarize(
    text: str,
    *,
    api_key: str | None = None,
    client_factory=None,
) -> SummaryResult:
    """Send ``text`` to Haiku and return a starter-prompt summary.

    Args:
        text: Session content. **Caller is responsible for running
            :func:`attune.ops.session_redaction.redact` first.** This
            function does NOT redact — it would be a security
            footgun to have two different code paths where one might
            forget to redact. The redaction discipline lives at the
            orchestrator layer (in the dashboard route) and applies
            uniformly before this function is ever reached.
        api_key: Override for ``ANTHROPIC_API_KEY``. Used by tests.
        client_factory: Override for the ``anthropic.Anthropic``
            constructor. Test hook — pass a callable that returns
            a mock client. The default uses the real SDK.

    Returns:
        :class:`SummaryResult` with the LLM's verbatim text plus
        token + cost accounting.

    Raises:
        MissingApiKeyError: ``api_key`` is None and the env var is unset.
        Exception: Any error from the Anthropic SDK (network, rate
            limit, malformed response). Callers should catch and fall
            back to the heuristic prompt — the dashboard route does
            this at the per-session level so one bad call doesn't
            blank the whole page.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise MissingApiKeyError(
            "ANTHROPIC_API_KEY not set — required when " "ATTUNE_OPS_SESSIONS_LLM is enabled."
        )

    if client_factory is None:
        from anthropic import Anthropic

        client = Anthropic(api_key=key)
    else:
        client = client_factory(api_key=key)

    truncated = _truncate_input(text)
    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_OUTPUT_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": truncated}],
    )

    # Anthropic returns content as a list of blocks; the first text
    # block carries the summary. Empty content (rare) falls back to
    # a sentinel string so the route's downstream code paths never
    # see ``None``.
    summary_text = ""
    if response.content:
        first = response.content[0]
        summary_text = getattr(first, "text", "") or ""
    if not summary_text:
        summary_text = "(no summary returned)"

    # Pricing: Anthropic returns input/output token counts on
    # ``response.usage``. Token counters are integers; missing
    # fields default to 0 so the cost calc never blows up on
    # an unfamiliar SDK shape.
    usage = getattr(response, "usage", None)
    tokens_in = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    tokens_out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    cost = _estimate_cost(tokens_in, tokens_out)

    return SummaryResult(
        text=summary_text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost,
    )
