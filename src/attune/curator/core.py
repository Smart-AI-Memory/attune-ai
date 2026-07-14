"""``run_curator`` orchestrator — the curator's headless public API.

Reads every source, checks the TTL cache, invokes a single Opus call
with forced tool-use for a guaranteed-schema briefing, validates the
cited sources, and caches the result.

The synthesis is one LLM call (no subagents, no agent loop, no file
tools), so it uses the raw ``anthropic`` SDK with forced ``tool_choice``
— the canonical CLAUDE.md "Forced Anthropic tool-use" pattern, the same
one ``attune_rag``'s ``FaithfulnessJudge`` uses. (The agent SDK's
``ClaudeAgentOptions`` has no ``tool_choice`` field and its ``tools`` is
a name-allowlist, so it can't force a single guaranteed-schema call —
see ``docs/specs/bulletin-curator/decisions.md``.)
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from attune.llm.fable_call import acreate_with_fable
from attune.model_tiers import ModelRefusalError, resolve_model

from .cache import CuratorCache
from .prompt import _CURATOR_SYSTEM_PROMPT, build_curator_prompt
from .result import (
    CuratorItem,
    CuratorResult,
    Severity,
    SourceSummary,
    SuggestedAction,
)
from .schema import output_schema
from .sources import bulletin, git_state, recommendations, specs, sweep, telemetry

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


def _curator_model() -> str:
    """Premium-tier synthesis model, resolved per call.

    Routed through :mod:`attune.model_tiers` so ``ATTUNE_MODEL_PREMIUM``
    is honored at call time. (The spec drafted "claude-opus-4-7", which
    never existed here — see decisions.md.)
    """
    return resolve_model("premium")


# Output token budget for the briefing reply. Input is bounded by the
# source readers (≤50 rows × ≤500 chars each); this caps the reply.
_MAX_OUTPUT_TOKENS = 4096

# Readers, in ranking-prompt order. Every module exports
# ``read(*, project_root, since=None) -> SourceSummary``.
_SOURCE_MODULES = [
    bulletin,
    specs,
    sweep,
    telemetry,
    recommendations,
    git_state,
]

_CURATION_TOOL_DESCRIPTION = (
    "Emit the ranked attention briefing. Call exactly once with the "
    "executive summary and ranked items."
)


def _safe_read(module: Any, project_root: Path) -> SourceSummary:
    """Call one reader, returning an empty summary on any failure.

    Readers promise not to raise, but the curator must survive a buggy
    reader regardless — one source crashing must not abort the run.
    """
    try:
        summary: SourceSummary = module.read(project_root=project_root)
        return summary
    except Exception:  # noqa: BLE001
        # INTENTIONAL: one source must never crash the whole briefing.
        source_id = getattr(module, "_SOURCE_ID", module.__name__.rsplit(".", 1)[-1])
        logger.exception("curator: source %s failed; returning empty", source_id)
        return SourceSummary(source_id=source_id, state_hash="", items=[])


async def _read_all_sources(project_root: Path) -> list[SourceSummary]:
    """Read every source concurrently. Never raises."""
    tasks = [asyncio.to_thread(_safe_read, mod, project_root) for mod in _SOURCE_MODULES]
    return list(await asyncio.gather(*tasks))


def _compute_cost(model: str, usage: Any) -> float:
    """Compute USD cost from an Anthropic ``usage`` object.

    Falls back to "capable" tier pricing for unknown models. Returns
    ``0.0`` if usage is missing or pricing can't be resolved.
    """
    if usage is None:
        return 0.0
    try:
        from attune.cost_tracker import MODEL_PRICING

        pricing = MODEL_PRICING.get(model) or MODEL_PRICING.get("capable")
        if not pricing:
            return 0.0
        in_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        out_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return (in_tokens / 1_000_000) * pricing["input"] + (out_tokens / 1_000_000) * pricing[
            "output"
        ]
    except Exception:  # noqa: BLE001
        # INTENTIONAL: cost is telemetry, not correctness — never fail
        # the briefing because pricing lookup hiccuped.
        logger.debug("curator: cost computation failed", exc_info=True)
        return 0.0


def _extract_curation_payload(response: Any) -> dict[str, Any]:
    """Pull the structured payload from a forced-tool-use response.

    Walks ``response.content``: a ``tool_use`` block's ``input`` is the
    guaranteed-schema happy path. Forced ``tool_choice`` makes the text
    fallback rare, but it's handled for robustness.
    """
    text_fallback: str | None = None
    for block in getattr(response, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "tool_use":
            data = getattr(block, "input", None)
            if isinstance(data, dict):
                return data
        elif btype == "text" and text_fallback is None:
            text_fallback = getattr(block, "text", None)
    if text_fallback:
        try:
            parsed = json.loads(text_fallback)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "curator: model returned unparseable text instead of a "
                f"tool call. First 200 chars: {text_fallback[:200]!r}"
            ) from exc
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError(
        "curator: response had no tool_use or JSON text block. Check the "
        "API version or tool_choice support."
    )


def _coerce_severity(value: Any) -> Severity:
    if value == "nudge":
        return "nudge"
    if value == "warn":
        return "warn"
    if value == "block":
        return "block"
    return "info"


def _parse_action(raw: Any) -> SuggestedAction | None:
    if not isinstance(raw, dict) or not raw.get("kind"):
        return None
    kind = raw["kind"]
    if kind not in ("ask", "open", "run", "dismiss"):
        return None
    return SuggestedAction(
        kind=kind,
        label=raw.get("label"),
        question=raw.get("question"),
        choices=[str(c) for c in (raw.get("choices") or [])],
        url=raw.get("url"),
        workflow=raw.get("workflow"),
        scope=raw.get("scope"),
    )


def _payload_to_items(payload: dict[str, Any]) -> list[CuratorItem]:
    items: list[CuratorItem] = []
    for entry in payload.get("items") or []:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        items.append(
            CuratorItem(
                id=str(entry["id"]),
                title=str(entry.get("title") or ""),
                severity=_coerce_severity(entry.get("severity")),
                rationale=str(entry.get("rationale") or ""),
                sources=[str(s) for s in (entry.get("sources") or [])],
                suggested_action=_parse_action(entry.get("suggested_action")),
            )
        )
    return items


def _validate_sources(
    result: CuratorResult,
    summaries: list[SourceSummary],
) -> CuratorResult:
    """Drop items citing unknown ``item_id``s (LLM-fabricated rows).

    An item survives only if every id in its ``sources`` resolves to a
    real :class:`SourceItem` from the inputs. Drops are logged.
    """
    known = {item.item_id for s in summaries for item in s.items}
    kept: list[CuratorItem] = []
    for item in result.items:
        unknown = [s for s in item.sources if s not in known]
        if unknown:
            logger.warning(
                "curator: dropping item %r — cites unknown sources %s",
                item.id,
                unknown,
            )
            continue
        kept.append(item)
    if len(kept) == len(result.items):
        return result
    return dataclasses.replace(result, items=kept)


async def _query_opus(
    prompt: str,
    schema: dict[str, Any],
    *,
    client: AsyncAnthropic,
    model: str,
) -> CuratorResult:
    """Run the single forced-tool-use synthesis call.

    Returns a :class:`CuratorResult` with summary, items, cost, and
    model populated. ``sources_consulted`` and ``cached_at`` are set by
    the caller.
    """
    tool = {
        "name": "emit_curation",
        "description": _CURATION_TOOL_DESCRIPTION,
        "input_schema": schema,
    }
    # Build kwargs as a plain dict and splat — the raw-dict tool param
    # doesn't match the SDK's ToolParam TypedDict overloads, and the
    # splat sidesteps that (same approach as FaithfulnessJudge).
    request_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "system": _CURATOR_SYSTEM_PROMPT,
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": "emit_curation"},
        "messages": [{"role": "user", "content": prompt}],
    }
    # Premium default is fable — the helper routes fable models via the
    # beta namespace (+ server-side opus fallback) and surfaces a
    # refusal as ModelRefusalError; non-fable models take the exact
    # pre-tier path. (_extract_curation_payload already walks all
    # content blocks, so the leading-thinking-block gotcha from the
    # fable_call docstring doesn't apply here.)
    response = await acreate_with_fable(client, **request_kwargs)
    payload = _extract_curation_payload(response)
    return CuratorResult(
        summary=str(payload.get("summary") or ""),
        items=_payload_to_items(payload),
        cost_usd=_compute_cost(model, getattr(response, "usage", None)),
        model=model,
    )


def _offline_summary(exc: Exception) -> str:
    """Map an LLM/transport failure to a clean, actionable offline message.

    Deliberately does NOT interpolate the raw exception into the
    dashboard-facing summary: SDK errors carry a ``request_id`` and other
    internals that shouldn't surface in the UI. The full exception is logged
    separately for debugging.

    Args:
        exc: The exception raised while reaching Anthropic.

    Returns:
        A user-facing sentence beginning with "The curator is offline".
    """
    status = getattr(exc, "status_code", None)
    text = str(exc).lower()

    if status == 401 or "authentication" in text or "x-api-key" in text:
        return (
            "The curator is offline: the ANTHROPIC_API_KEY is missing or "
            "invalid. Set a valid key (e.g. in ~/.attune/anthropic.env)."
        )
    if "credit balance" in text or "plans & billing" in text or "billing" in text:
        return (
            "The curator is offline: the Anthropic account has no API credit "
            "balance. The curator makes a direct API call, which needs "
            "pay-as-you-go credits — the Claude subscription does not include "
            "raw API access. Add credits to enable AI briefings."
        )
    if status == 429 or "rate limit" in text:
        return "The curator is offline: Anthropic rate limit reached. " "Try again shortly."
    return (
        "The curator is offline due to a temporary error reaching Anthropic. "
        "See the server logs for details."
    )


async def run_curator(
    *,
    project_root: Path,
    max_items: int = 5,
    cache_ttl_seconds: int = 300,
    max_budget_usd: float = 0.50,
    force_refresh: bool = False,
    client: AsyncAnthropic | None = None,
    model: str | None = None,
) -> CuratorResult:
    """Synthesize an executive briefing across all project sources.

    Reads every source, returns a cached briefing when fresh, else runs
    one Opus call and caches the result. Any LLM failure degrades to an
    "offline" :class:`CuratorResult` (empty items) rather than raising —
    the dashboard / CLI render that gracefully.

    Args:
        project_root: Project to curate (bounds every source reader).
        max_items: Soft ceiling on attention items in the briefing.
        cache_ttl_seconds: Cache freshness window.
        max_budget_usd: Advisory cost ceiling. A single call is bounded
            by the readers' row caps and ``_MAX_OUTPUT_TOKENS``; a cost
            above this only logs a warning (v1 has no hard mid-call
            cap — see decisions.md).
        force_refresh: Bypass both cache read and write.
        client: Injected ``AsyncAnthropic`` (tests pass a fake). When
            None, a default client is constructed lazily.
        model: Override the synthesis model (default: the premium
            tier via attune.model_tiers).

    Returns:
        The synthesized :class:`CuratorResult`. Never raises.
    """
    if model is None:
        model = _curator_model()

    summaries = await _read_all_sources(project_root)
    sources_consulted = [s.source_id for s in summaries]

    cache = CuratorCache(ttl_seconds=cache_ttl_seconds)
    key = cache.key(summaries)
    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached

    if client is None:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()

    prompt = build_curator_prompt(summaries, max_items=max_items)
    schema = output_schema(max_items=max_items)

    try:
        result = await _query_opus(prompt, schema, client=client, model=model)
    except ModelRefusalError as exc:
        # The whole fable -> opus fallback chain refused: record the
        # fable_refusal telemetry event, then degrade gracefully
        # (run_curator never raises).
        from attune.models.telemetry import log_fable_refusal

        log_fable_refusal(exc, workflow="curator", model=model)
        logger.warning("curator: synthesis refused: %s", exc)
        return CuratorResult(
            summary=(
                "The curator briefing was refused by the model "
                f"(category: {exc.category or 'unspecified'}). "
                "Recorded as a fable_refusal telemetry event."
            ),
            items=[],
            sources_consulted=sources_consulted,
            model=model,
            cached_at=datetime.now(timezone.utc),
        )
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: an LLM outage / missing key / API error degrades
        # to an offline briefing rather than crashing the dashboard.
        logger.warning("curator: synthesis failed: %s", exc)
        return CuratorResult(
            summary=_offline_summary(exc),
            items=[],
            sources_consulted=sources_consulted,
            model=model,
            cached_at=datetime.now(timezone.utc),
        )

    result = _validate_sources(result, summaries)
    result = dataclasses.replace(
        result,
        sources_consulted=sources_consulted,
        cached_at=datetime.now(timezone.utc),
    )

    if result.cost_usd > max_budget_usd:
        logger.warning(
            "curator: call cost $%.4f exceeded advisory budget $%.4f",
            result.cost_usd,
            max_budget_usd,
        )

    if not force_refresh:
        cache.put(key, result)
    return result
