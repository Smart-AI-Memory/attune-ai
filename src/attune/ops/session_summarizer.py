"""Haiku-summarized starter prompts for the /sessions page.

S3b of the ops-sessions-page spec. Wires three already-shipped
pieces together — :mod:`attune.ops.session_redaction`,
:mod:`attune.ops.session_summary_cache`, and the Anthropic SDK —
behind a single :func:`summarize_session` entry point.

Discipline (decisions.md Decision 3): **redact first, then send,
then cache.** Sensitive material never enters the LLM provider's
context and never lands on disk in the cache. Cache hits inherit
the redacted form for free.

Failure mode: any error (missing API key, missing SDK, network
flake, redaction failure) returns ``None``. The caller falls
back to the heuristic that ``data.list_recent_sessions`` already
produced. This keeps the page useful even when Haiku is
unavailable.

Env gates:

- ``ATTUNE_OPS_SESSIONS_LLM`` — set to ``"0"`` to disable the
  Haiku path entirely. Default behavior is enabled when an
  ``ANTHROPIC_API_KEY`` is present.
- ``ANTHROPIC_API_KEY`` — required for live calls. When absent,
  :func:`summarize_session` returns ``None`` without raising.
- ``ATTUNE_OPS_SESSIONS_BUDGET_USD`` — per-page-load cap. Read
  by the caller (see :func:`new_budget`), not enforced here.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from attune.ops import session_redaction, session_summary_cache

logger = logging.getLogger(__name__)

# Haiku 4.5 pricing as of 2026-05. Mirrors ``MODEL_REGISTRY`` in
# ``src/attune/models/registry.py`` — the per-million-tokens rates
# the planning math assumes (~$0.001/session typical, well under
# the $0.05 per-load cap with N=20).
HAIKU_MODEL_ID = "claude-haiku-4-5-20251001"
_INPUT_COST_PER_MILLION = 1.00
_OUTPUT_COST_PER_MILLION = 5.00

# Per-page-load budget. Sized for N=20 × ~$0.001/session ≈ $0.02
# typical, with ~2.5× headroom for prompt growth + input-size
# variance. Decisions.md Decision 5 + the budget-cap math note.
DEFAULT_BUDGET_USD = 0.05

# Bytes of session content we send to Haiku per session. Enough to
# capture the opening intent plus a few exchanges; bounded so a
# 50MB transcript can't blow out the per-session cost. ~4KB is
# roughly 1K input tokens at Haiku rates → $0.001/session input.
_MAX_INPUT_CHARS = 4_000

# Cap on Haiku's output tokens. The target shape is a ~60-word
# summary + 0-3 bullet points + 1-sentence resume prompt — well
# under 200 tokens. 256 leaves slack for variation without
# blowing out cost.
_MAX_OUTPUT_TOKENS = 256

# Haiku summarization prompt. Calibrated against the target shape
# in decisions.md Decision 2:
#
#   1. Names what was being worked on (1 short sentence).
#   2. Lists any open threads (bullets, 0-3 items).
#   3. Suggests a 1-sentence resume prompt the user can paste.
#
# Kept as a constant rather than threaded through args so the
# calibration harness (scripts/build_session_fixtures.py +
# eventual snapshot test) has a single source of truth to diff
# against.
SUMMARY_PROMPT = (
    "You are summarizing the start of a Claude Code session so the user "
    "can decide whether to resume it. The user pasted the first ~4KB of "
    "their session transcript below.\n\n"
    "Produce a starter summary with exactly this shape:\n\n"
    "1. One short sentence (max ~20 words) naming what was being worked "
    "on. Concrete: cite a file, feature, or task. No filler like "
    "'discussion of' or 'work on'.\n"
    "2. Open threads as 0-3 bullets, one line each, max ~12 words each. "
    "Skip the bullets section entirely if no threads are obvious — "
    "don't invent them.\n"
    "3. One sentence the user could paste to resume the work, prefixed "
    "with 'Resume:'. Action-oriented, max ~20 words.\n\n"
    "Format as plain text. No headings, no markdown beyond the bullet "
    "dashes. Be terse. The user is reading 20 of these in a list — "
    "every word counts.\n\n"
    "If the transcript is too short or noisy to summarize, output "
    "exactly: 'Resume: pick up where you left off.'\n"
)


@dataclass(frozen=True)
class SummaryResult:
    """One Haiku-or-cache result, ready to slot into a :class:`Session`.

    ``source`` is one of ``"haiku"`` (fresh call this load) or
    ``"cached"`` (loaded from on-disk cache). The heuristic source
    is owned by the data layer; this module never returns it. A
    failure returns ``None`` rather than a SummaryResult with
    ``source="heuristic"`` — distinguishing the two lets the
    caller decide whether to retry, fall back, or surface a
    "summary unavailable" marker.
    """

    text: str
    source: str  # "haiku" | "cached"
    tokens_in: int
    tokens_out: int
    cost_usd: float


@dataclass
class Budget:
    """Mutable spend ledger for one page-load summarization loop.

    Mutable on purpose — the loop passes one instance through
    every :func:`summarize_session` call and tracks cumulative
    spend in ``spent_usd``. Subsequent calls check
    :meth:`should_skip` before incurring any cost.

    The breach is a soft cap: a fresh call that would push
    ``spent_usd`` over ``cap_usd`` is skipped and the caller
    falls back to the heuristic. Cached reads are free and
    proceed regardless of the cap (they were paid for on a
    prior load).

    A ``cap_usd <= 0`` value latches the budget as breached at
    construction — useful as an effective off-switch in tests
    and for users who want heuristic-only mode without unsetting
    ``ANTHROPIC_API_KEY``.
    """

    cap_usd: float
    spent_usd: float = 0.0
    breached: bool = False

    def __post_init__(self) -> None:
        # Cap of 0 (or negative) is an effective off-switch — every
        # call would otherwise breach on its first record, but with
        # the latch set at construction the first call is skipped
        # too and the marker fires from row one.
        if self.cap_usd <= 0:
            self.breached = True

    def should_skip(self) -> bool:
        """Return True once the cap has been breached.

        Latches at ``breached=True`` so the caller can render a
        single "over budget" marker for the trailing sessions
        rather than flipping back and forth as cache hits come in.
        """
        return self.breached

    def record(self, cost_usd: float) -> None:
        """Add a successful fresh call's cost to the ledger.

        If the cumulative spend crosses ``cap_usd``, latches
        ``breached=True``. Callers should NOT call this for cache
        hits — those are free and don't count against the budget.
        """
        self.spent_usd += cost_usd
        if self.spent_usd >= self.cap_usd:
            self.breached = True


def new_budget(cap_usd: float | None = None) -> Budget:
    """Build a :class:`Budget` from the env override or default.

    ``cap_usd`` arg wins over the env var, which wins over the
    module default. Negative values clamp to 0 (immediate
    breach — useful for tests that want to assert the
    over-budget code path without spending real money).
    """
    if cap_usd is not None:
        cap = cap_usd
    else:
        raw = os.environ.get("ATTUNE_OPS_SESSIONS_BUDGET_USD")
        if raw:
            try:
                cap = float(raw)
            except ValueError:
                logger.warning(
                    "ops.sessions: invalid ATTUNE_OPS_SESSIONS_BUDGET_USD=%r,"
                    " using default %.3f",
                    raw,
                    DEFAULT_BUDGET_USD,
                )
                cap = DEFAULT_BUDGET_USD
        else:
            cap = DEFAULT_BUDGET_USD
    return Budget(cap_usd=max(0.0, cap))


def llm_enabled() -> bool:
    """Return True iff the Haiku path is enabled this run.

    Off when ``ATTUNE_OPS_SESSIONS_LLM=0`` is explicitly set OR
    when no ``ANTHROPIC_API_KEY`` is in the environment. The
    second condition means a vanilla install without an API key
    falls cleanly back to the heuristic without ever attempting
    a network call (no spurious WARN logs).
    """
    if os.environ.get("ATTUNE_OPS_SESSIONS_LLM") == "0":
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _extract_content_for_summary(jsonl_path: Path, *, char_budget: int) -> str:
    """Read up to ``char_budget`` chars of user-prompt content from the JSONL.

    Walks the file line-by-line, picks events that have a string
    ``content`` field (the user's prompts), and concatenates with
    a blank line between turns. Stops as soon as the accumulated
    length crosses ``char_budget`` — Haiku only needs enough to
    name the work, not the whole transcript.

    Returns ``""`` on any I/O failure or when no content events
    are present. The caller treats empty as "no summary
    possible" and skips Haiku.
    """
    chunks: list[str] = []
    used = 0
    try:
        with jsonl_path.open(encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                content = event.get("content")
                if not isinstance(content, str) or not content:
                    continue
                # Truncate this turn if it alone exceeds the
                # remaining budget — better to include a head
                # slice than skip the whole turn.
                remaining = char_budget - used
                if remaining <= 0:
                    break
                slice_ = content if len(content) <= remaining else content[:remaining]
                chunks.append(slice_)
                used += len(slice_) + 2  # +2 for the separator
    except OSError:
        return ""
    return "\n\n".join(chunks)


def _compute_cost_usd(tokens_in: int, tokens_out: int) -> float:
    """Cost in USD for one Haiku-4.5 call at registry rates."""
    return (
        tokens_in * _INPUT_COST_PER_MILLION / 1_000_000.0
        + tokens_out * _OUTPUT_COST_PER_MILLION / 1_000_000.0
    )


def _call_haiku(redacted_text: str) -> tuple[str, int, int] | None:
    """One Haiku synchronous call. Returns ``(text, tokens_in, tokens_out)``.

    Returns ``None`` on any failure — missing SDK, missing API
    key, network error, empty response. Failure is logged at
    WARN; the caller treats ``None`` as "fall back to heuristic."
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("ops.sessions: anthropic SDK not installed; skipping Haiku")
        return None

    client = Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=HAIKU_MODEL_ID,
            max_tokens=_MAX_OUTPUT_TOKENS,
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": redacted_text}],
        )
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: Haiku failure must never crash a page render.
        # Anthropic SDK raises a handful of exception types
        # (APIError, RateLimitError, APIConnectionError, ...). Catching
        # broadly + logging is the right shape; the caller falls back.
        logger.warning("ops.sessions: Haiku call failed: %s", exc)
        return None

    if not response.content:
        return None
    block = response.content[0]
    text = getattr(block, "text", None)
    if not isinstance(text, str) or not text:
        return None

    usage = getattr(response, "usage", None)
    tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
    return text.strip(), tokens_in, tokens_out


def summarize_session(
    jsonl_path: Path,
    *,
    attune_home: Path,
    budget: Budget | None = None,
) -> SummaryResult | None:
    """Return a Haiku-or-cached summary for one session JSONL.

    Flow (decisions.md Decisions 3 + 6 + 7):

    1. Compute cache key from the file's tail (last 4KB SHA-256).
    2. Probe the on-disk cache; return ``CachedSummary`` if hit.
       Cache hits are free and bypass the budget check.
    3. If the budget is already breached, return ``None`` —
       caller falls back to the heuristic that the data layer
       already produced.
    4. Extract up to ``_MAX_INPUT_CHARS`` of user-prompt content.
    5. Run the redaction pass.
    6. Call Haiku with the redacted text.
    7. Compute cost, record against the budget, write to the
       cache, return.

    Any I/O or LLM failure short-circuits to ``None``. The route
    treats ``None`` as "use the heuristic starter prompt that
    ``data.list_recent_sessions`` already populated."

    Args:
        jsonl_path: Path to the session's JSONL file under
            ``~/.claude/projects/<encoded>/``.
        attune_home: ``~/.attune`` (or ``$ATTUNE_HOME``). The
            cache lives under ``<attune_home>/ops/session_summaries/``.
        budget: Optional :class:`Budget` ledger. When ``None`` a
            fresh one with the env-or-default cap is created
            (useful for one-off calls outside the page-load loop).

    Returns:
        A :class:`SummaryResult` (source ``"haiku"`` or
        ``"cached"``), or ``None`` on any failure / over-budget /
        LLM-disabled state.
    """
    if budget is None:
        budget = new_budget()

    # Step 1+2: cache probe BEFORE the LLM-enabled check. A prior
    # write may still be useful even if the current load has
    # ATTUNE_OPS_SESSIONS_LLM=0 — the user can opt out of fresh
    # calls without throwing away yesterday's results.
    cache_key = session_summary_cache.compute_cache_key(jsonl_path)
    if cache_key is None:
        # I/O failure reading the source — nothing to summarize
        # and nothing to cache against. Caller falls back.
        return None

    session_id = jsonl_path.stem
    cached = session_summary_cache.load(attune_home, session_id, cache_key)
    if cached is not None:
        return SummaryResult(
            text=cached.summary,
            source="cached",
            tokens_in=cached.tokens_in,
            tokens_out=cached.tokens_out,
            cost_usd=cached.cost_usd,
        )

    # No cache hit. Need a fresh call — check the gates.
    if not llm_enabled():
        return None
    if budget.should_skip():
        return None

    # Step 4: extract content.
    raw = _extract_content_for_summary(jsonl_path, char_budget=_MAX_INPUT_CHARS)
    if not raw:
        return None

    # Step 5: redact. This is the load-bearing step for the
    # "no sensitive material in the LLM provider's context"
    # invariant; if redaction itself raises we treat the
    # session as un-summarizable rather than send the raw text.
    try:
        redacted = session_redaction.redact(raw).text
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: redaction failure must not leak raw text.
        # Caller falls back to the heuristic (which has its own
        # truncation but no LLM exposure).
        logger.warning("ops.sessions: redaction failed for %s: %s", session_id, exc)
        return None
    if not redacted:
        return None

    # Step 6: Haiku call.
    call_result = _call_haiku(redacted)
    if call_result is None:
        return None
    text, tokens_in, tokens_out = call_result
    cost_usd = _compute_cost_usd(tokens_in, tokens_out)

    # Step 7: record against budget + persist to cache. Cache
    # write failure is best-effort — we still return the result.
    budget.record(cost_usd)
    try:
        session_summary_cache.save(
            attune_home,
            session_id,
            key=cache_key,
            summary=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )
    except OSError as exc:
        logger.warning(
            "ops.sessions: cache write failed for %s: %s — returning fresh result",
            session_id,
            exc,
        )

    return SummaryResult(
        text=text,
        source="haiku",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
    )
