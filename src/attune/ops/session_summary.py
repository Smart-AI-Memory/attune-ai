"""Orchestrator: redact → cache-or-Haiku → return summary text.

Glue layer between the JSONL parser, the redaction module, the
on-disk cache, and the Haiku summarizer. Tests cover each leg
independently; this module wires them in the order the spec calls
for and tracks per-page-load budget.

Discipline (decisions.md Decision 3):

    Redact FIRST, then summarize, then cache. The cache never holds
    a sensitive prompt; subsequent reads inherit the redaction for
    free.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from attune.ops import session_redaction, session_summary_cache, session_summary_llm

logger = logging.getLogger(__name__)


# Per-page-load soft budget cap. Decisions.md Decision 5 + the
# 2026-05-15 PR-B Q1 answer: "soft warning" — once breached, keep
# summarizing but log a WARN once per page load. The cap is sized
# around the N=20 list limit at ~$0.001/session = ~$0.02/uncached
# load; $0.05 has comfortable headroom.
DEFAULT_BUDGET_CAP_USD = 0.05


@dataclass
class BudgetTracker:
    """Per-page-load spend tracker for Haiku calls.

    Not frozen — ``spend`` is mutated as summaries are computed.
    Construct one tracker per page load and pass it through the
    per-session calls; reset on each new request.
    """

    cap_usd: float = DEFAULT_BUDGET_CAP_USD
    spend_usd: float = 0.0
    _warned: bool = False

    def charge(self, cost_usd: float) -> None:
        """Add a call's cost to the running total. Logs once on breach."""
        self.spend_usd += cost_usd
        if self.spend_usd > self.cap_usd and not self._warned:
            logger.warning(
                "ops.sessions: per-page-load budget cap exceeded — "
                "spend=$%.4f cap=$%.4f. Continuing to summarize "
                "(soft cap); reduce list cap or disable "
                "ATTUNE_OPS_SESSIONS_LLM if this recurs.",
                self.spend_usd,
                self.cap_usd,
            )
            self._warned = True


@dataclass(frozen=True)
class SummarizedPrompt:
    """One session's starter prompt + provenance.

    ``source`` mirrors the :class:`attune.ops.data.Session` field
    so the dashboard's "summarized by Haiku · cached" badge can
    distinguish a fresh Haiku call from a cache hit from the
    pre-Haiku heuristic fallback.
    """

    text: str
    source: str  # "heuristic" | "haiku" | "cached"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


def summarize_for_session(
    jsonl_path: Path,
    raw_text: str,
    *,
    attune_home: Path,
    budget: BudgetTracker,
    api_key: str | None = None,
    summarize_fn=None,
    redact_fn=None,
) -> SummarizedPrompt | None:
    """Return a Haiku-or-cached summary, or ``None`` to signal heuristic fallback.

    Sequence:

    1. Compute the cache key for ``jsonl_path``. On I/O failure
       return ``None`` and let the caller fall back to the
       heuristic prompt.
    2. Try the cache. On hit return the cached text marked
       ``source="cached"``. Cache hits do NOT count against the
       per-page budget (no fresh LLM spend incurred).
    3. On miss, redact ``raw_text``, then call the Haiku
       summarizer. Catch every exception from the call and return
       ``None`` so the caller can fall back to heuristic — one bad
       call shouldn't blank the whole page.
    4. Charge the call's cost to ``budget``. Write the redacted
       summary to the cache. Return marked ``source="haiku"``.

    Args:
        jsonl_path: Source JSONL file (for cache key).
        raw_text: Pre-extracted text to summarize. Caller chooses
            what content to send — typically the first ~6 KB of
            user prompts + assistant turns.
        attune_home: Cache root.
        budget: Shared :class:`BudgetTracker` for the request.
        api_key: Override for ``ANTHROPIC_API_KEY``. Test hook.
        summarize_fn: Override for
            :func:`session_summary_llm.summarize`. Test hook.
        redact_fn: Override for
            :func:`session_redaction.redact`. Test hook.

    Returns:
        A :class:`SummarizedPrompt` or ``None`` if anything went
        wrong (cache-key I/O failure, missing API key, LLM error).
        ``None`` is the explicit "use heuristic" signal.
    """
    do_redact = redact_fn or session_redaction.redact
    do_summarize = summarize_fn or session_summary_llm.summarize

    key = session_summary_cache.compute_cache_key(jsonl_path)
    if key is None:
        # Can't key the cache → no point caching the result. Fall
        # through to heuristic; bypassing the LLM also avoids spending
        # tokens on an unrecoverable session.
        return None

    cached = session_summary_cache.load(attune_home, jsonl_path.stem, expected=key)
    if cached is not None:
        return SummarizedPrompt(
            text=cached.summary,
            source=cached.source,  # "cached"
            tokens_in=cached.tokens_in,
            tokens_out=cached.tokens_out,
            cost_usd=cached.cost_usd,
        )

    redacted = do_redact(raw_text)
    try:
        result = do_summarize(redacted.text, api_key=api_key)
    except session_summary_llm.MissingApiKeyError:
        # Re-raised by the route so it can render a one-time
        # "config missing" banner. Distinct from runtime LLM errors
        # which should silently fall back to heuristic.
        raise
    except Exception:  # noqa: BLE001
        # INTENTIONAL: one bad LLM call falls back to heuristic for
        # that session; the rest of the page renders normally. The
        # alternative (raise) blanks the whole page when a single
        # session trips a rate limit or network blip.
        logger.exception(
            "ops.sessions: Haiku summarize failed for %s — falling back to heuristic",
            jsonl_path.name,
        )
        return None

    budget.charge(result.cost_usd)

    try:
        session_summary_cache.save(
            attune_home,
            jsonl_path.stem,
            key=key,
            summary=result.text,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
        )
    except OSError:
        # INTENTIONAL: cache write failure is non-fatal — return the
        # fresh summary anyway. Worst case: this session re-summarizes
        # on next page load (extra spend, no correctness impact).
        logger.warning(
            "ops.sessions: cache write failed for %s — summary returned uncached",
            jsonl_path.stem,
        )

    return SummarizedPrompt(
        text=result.text,
        source="haiku",
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
    )


def extract_summarizable_text(jsonl_path: Path, *, max_chars: int = 6000) -> str:
    """Read the JSONL and extract the conversation text Haiku should see.

    Concatenates ``content`` fields from events into a single
    string with role hints. Caps at ``max_chars`` to keep
    per-call cost predictable — :func:`session_summary_llm.summarize`
    also caps internally as a defense-in-depth.

    Returns an empty string on any I/O failure. Callers should
    treat empty as "skip the LLM call, render heuristic."
    """
    import json

    out: list[str] = []
    total = 0
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
                # Role hint helps the LLM distinguish prompts from
                # responses. The Claude Code JSONL we've observed
                # only carries user prompts via queue-operation
                # enqueue events; assistant turns are absent. We
                # default to "user" but leave the prefix path open
                # for when the JSONL schema gains assistant content.
                role = event.get("role") or "user"
                chunk = f"[{role}] {content}\n\n"
                if total + len(chunk) > max_chars:
                    remaining = max_chars - total
                    if remaining > 0:
                        out.append(chunk[:remaining])
                    break
                out.append(chunk)
                total += len(chunk)
    except OSError:
        return ""
    return "".join(out).strip()
