"""Single-turn LLM calls with subscription-first auth routing.

Absorbed from ``attune_author.auth`` + ``attune_author.doc_gen._anthropic``
(attune-author-consolidation T3, ruling D10): the authoring/polish
machinery now lives in ``attune.authoring`` and its LLM calls route
through attune-ai's own model infrastructure — tier resolution via
:mod:`attune.model_tiers`, fable-aware requests via
:mod:`attune.llm.fable_call`, and the same subprocess isolation the
SDK workflows use.

Mode resolution (first match wins):

1. Explicit ``auth_mode=`` argument.
2. The ``ATTUNE_AUTH_MODE`` environment variable (legacy
   ``ATTUNE_AUTHOR_AUTH_MODE`` honored as a deprecated fallback).
3. ``auto`` — subscription when detectable, else API key.

The subscription path spawns a short-lived ``claude`` CLI subprocess
per call via ``claude_agent_sdk.query()`` with the adapter's
``sdk_isolation_kwargs()`` so user/project settings (SessionStart
hooks, CLAUDE.md injection) never leak into the call or pollute its
stream-json channel.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import logging
import os
import re
import time
from typing import TYPE_CHECKING

from attune.llm.fable_call import create_with_fable
from attune.model_tiers import ModelRefusalError, resolve_model

if TYPE_CHECKING:
    from collections.abc import Callable

    from anthropic import Anthropic

logger = logging.getLogger(__name__)

#: Environment variable that pins the auth mode for every call in
#: the process.
AUTH_MODE_ENV = "ATTUNE_AUTH_MODE"

#: Deprecated pre-consolidation name, still honored when the
#: canonical variable is unset.
LEGACY_AUTH_MODE_ENV = "ATTUNE_AUTHOR_AUTH_MODE"

VALID_AUTH_MODES = ("auto", "api", "sub")

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds; doubles each attempt

# Patterns that could carry credentials through exception text.
_KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}")
_REDACTED = "sk-ant-[REDACTED]"

_NO_CREDENTIALS_MESSAGE = (
    "No LLM credentials available. Either run inside a Claude Code "
    "session (subscription routing via claude-agent-sdk) or set "
    "ANTHROPIC_API_KEY for direct API access."
)


class AnthropicCallError(RuntimeError):
    """Raised when a single-turn LLM call fails.

    The message is always the redacted form of the original
    exception text. The original SDK exception is not chained
    (``from None``) so that callers inspecting ``__cause__``
    can't accidentally surface an unredacted message.
    """


def _redact(text: str) -> str:
    """Replace anything that looks like an Anthropic API key."""
    return _KEY_PATTERN.sub(_REDACTED, text)


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient Anthropic errors that are safe to retry."""
    try:
        from anthropic import APIConnectionError, APIStatusError  # noqa: PLC0415
    except ImportError:
        return False
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in (429, 529)
    return False


def get_client(api_key: str | None = None) -> Anthropic:
    """Instantiate an Anthropic client.

    Args:
        api_key: Explicit key. When ``None``, reads
            ``ANTHROPIC_API_KEY`` from the environment.

    Returns:
        An instantiated ``Anthropic`` client.

    Raises:
        AnthropicCallError: If no API key is available.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise AnthropicCallError("ANTHROPIC_API_KEY not set")
    from anthropic import Anthropic  # noqa: PLC0415

    return Anthropic(api_key=key)


def cache_control() -> dict[str, str]:
    """Resolve the ephemeral ``cache_control`` marker from the environment.

    Read on every call (not memoized) so tests can flip the env var
    via ``monkeypatch.setenv``.

    Returns:
        ``{"type": "ephemeral", "ttl": "1h"}`` when ``ATTUNE_CACHE_TTL``
        (or the deprecated ``ATTUNE_AUTHOR_CACHE_TTL``) is ``1h``;
        otherwise the bare ``{"type": "ephemeral"}`` default.
    """
    raw = os.getenv("ATTUNE_CACHE_TTL") or os.getenv("ATTUNE_AUTHOR_CACHE_TTL") or "5m"
    if raw.strip().lower() == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return {"type": "ephemeral"}


def _sdk_importable() -> bool:
    """Return True when ``claude_agent_sdk`` can be imported."""
    try:
        return importlib.util.find_spec("claude_agent_sdk") is not None
    except (ImportError, ValueError):
        return False


def subscription_available() -> bool:
    """Return True when subscription routing is possible right now.

    Requires both a detectable Claude Code session (the
    ``CLAUDECODE=1`` env var Claude Code sets in every subprocess it
    spawns) and an importable ``claude-agent-sdk``.
    """
    return os.environ.get("CLAUDECODE") == "1" and _sdk_importable()


def api_key_available() -> bool:
    """Return True when a non-empty ``ANTHROPIC_API_KEY`` is set."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _requested_mode(explicit: str | None) -> str:
    """Normalize the requested mode from explicit arg or env vars."""
    mode = (
        (
            explicit
            or os.environ.get(AUTH_MODE_ENV)
            or os.environ.get(LEGACY_AUTH_MODE_ENV)
            or "auto"
        )
        .strip()
        .lower()
    )
    if mode not in VALID_AUTH_MODES:
        raise AnthropicCallError(
            f"Invalid auth mode {mode!r}; expected one of: " + ", ".join(VALID_AUTH_MODES)
        )
    return mode


def resolve_auth_mode(explicit: str | None = None) -> str:
    """Resolve the effective auth route: ``"sub"`` or ``"api"``.

    Args:
        explicit: Explicit mode override (``auto``/``api``/``sub``).
            When ``None``, ``ATTUNE_AUTH_MODE`` (then the deprecated
            ``ATTUNE_AUTHOR_AUTH_MODE``) is consulted; when unset,
            ``auto``.

    Returns:
        ``"sub"`` (subscription via the Agent SDK) or ``"api"``
        (direct Anthropic SDK).

    Raises:
        AnthropicCallError: If the mode string is invalid, or ``sub``
            is forced while no subscription session is detectable.
    """
    mode = _requested_mode(explicit)
    if mode == "sub":
        if not subscription_available():
            raise AnthropicCallError(
                "auth mode 'sub' forced but no subscription session "
                "is detectable (CLAUDECODE is not set, or "
                "claude-agent-sdk is not installed)"
            )
        return "sub"
    if mode == "api":
        return "api"
    return "sub" if subscription_available() else "api"


def auth_status() -> dict[str, object]:
    """Snapshot of the auth environment for diagnostics.

    Never raises: a forced ``sub`` mode that can't be satisfied is
    reported via the ``error`` key instead.

    Returns:
        Dict with the detection signals, the env-var override, the
        resolved route (or ``None`` on error), and ``error`` text.
    """
    try:
        resolved: str | None = resolve_auth_mode()
        error: str | None = None
    except AnthropicCallError as exc:
        resolved, error = None, str(exc)
    return {
        "claudecode": os.environ.get("CLAUDECODE") == "1",
        "sdk_importable": _sdk_importable(),
        "subscription_available": subscription_available(),
        "api_key_available": api_key_available(),
        "env_mode": os.environ.get(AUTH_MODE_ENV) or os.environ.get(LEGACY_AUTH_MODE_ENV),
        "resolved_mode": resolved,
        "error": error,
    }


def auth_telemetry() -> dict[str, float]:
    """Per-process counters of single-turn LLM calls by auth route.

    Stored on the function as an attribute so end-of-run summaries
    can read totals without module-level state. Reset via
    :func:`reset_auth_telemetry`.
    """
    state = getattr(auth_telemetry, "_state", None)
    if state is None:
        state = {"sub_calls": 0.0, "api_calls": 0.0}
        auth_telemetry._state = state  # type: ignore[attr-defined]
    return state


def reset_auth_telemetry() -> None:
    """Reset the per-process auth-route telemetry counters."""
    auth_telemetry._state = {  # type: ignore[attr-defined]
        "sub_calls": 0.0,
        "api_calls": 0.0,
    }


def _log_cache_usage(response: object, model: str) -> tuple[int, int]:
    """Log prompt-cache token usage; return ``(creation, read)`` counts."""
    usage = getattr(response, "usage", None)
    creation = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    if creation or read:
        logger.info(
            "Prompt cache usage for %s: creation=%d read=%d",
            model,
            creation,
            read,
        )
    return creation, read


def call_api(
    client: Anthropic,
    *,
    system: str,
    user_message: str,
    model: str,
    max_tokens: int,
    cache_system: bool = False,
    on_cache_usage: Callable[[int, int, str], None] | None = None,
) -> str:
    """Make a single-turn Messages call with retry/backoff.

    Routes through :func:`attune.llm.fable_call.create_with_fable`
    so premium-tier (fable) models get the beta namespace,
    server-side fallback opt-in, and refusal surfacing. Retries up
    to ``_MAX_RETRIES`` times on transient errors (rate limits and
    overload responses); non-transient SDK errors fail immediately.
    All exceptions are re-raised as :class:`AnthropicCallError` with
    a redacted message and an empty ``__cause__`` chain.

    Args:
        client: Instantiated Anthropic client.
        system: System prompt.
        user_message: User-turn content.
        model: Anthropic model ID.
        max_tokens: Response token budget.
        cache_system: When True, wraps ``system`` as a content-block
            list with an ephemeral ``cache_control`` marker.
        on_cache_usage: Optional callback invoked once per successful
            call with ``(cache_creation_input_tokens,
            cache_read_input_tokens, model)``.

    Returns:
        The first text block of the response, or the empty string if
        the response carried no content.

    Raises:
        ModelRefusalError: When the model (or its whole server-side
            fallback chain) refused the request — a verdict, never
            wrapped as transport noise.
        AnthropicCallError: On any SDK or transport failure after
            retries are exhausted.
    """
    if cache_system:
        system_payload: object = [
            {
                "type": "text",
                "text": system,
                "cache_control": cache_control(),
            }
        ]
    else:
        system_payload = system

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        if attempt:
            delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Anthropic call failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt,
                _MAX_RETRIES,
                delay,
                _redact(str(last_exc)),
            )
            time.sleep(delay)
        try:
            response = create_with_fable(
                client,
                model=model,
                max_tokens=max_tokens,
                system=system_payload,
                messages=[{"role": "user", "content": user_message}],
            )
            creation, read = _log_cache_usage(response, model)
            if on_cache_usage is not None:
                on_cache_usage(creation, read, model)
            # First TEXT block, not content[0]: fable responses can
            # lead with a thinking block that has no ``.text``.
            for block in getattr(response, "content", None) or []:
                text = getattr(block, "text", None)
                if text:
                    return text
            return ""
        except ModelRefusalError:
            # Not transport noise: the model declined. Carries no
            # credential material — no redaction wrap.
            raise
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: every SDK exception type funnels through
            # one redaction pass so credential material can't leak
            # into logs or upstream exception chains. ``from None``
            # strips __cause__ so callers only see the redacted form.
            if _is_retryable(exc):
                last_exc = exc
                continue
            raise AnthropicCallError(_redact(str(exc))) from None

    raise AnthropicCallError(_redact(str(last_exc))) from None


def call_llm(
    *,
    system: str,
    user_message: str,
    model: str | None = None,
    tier: str = "premium",
    max_tokens: int = 8192,
    cache_system: bool = False,
    on_cache_usage: Callable[[int, int, str], None] | None = None,
    auth_mode: str | None = None,
) -> str:
    """Route a single-turn LLM call through subscription or API auth.

    In ``auto`` mode a failed subscription call falls back to the
    API path when ``ANTHROPIC_API_KEY`` is available (subscription
    expiry mid-run shouldn't kill a regen). A *forced* ``sub`` mode
    never falls back — the explicit override wins, including its
    failures.

    Args:
        system: System prompt.
        user_message: User-turn content.
        model: Anthropic model ID. When ``None``, resolved from
            ``tier`` via :func:`attune.model_tiers.resolve_model`.
        tier: Model tier (``premium``/``capable``/``cheap``) used
            when ``model`` is not given.
        max_tokens: Response token budget. API route only — the
            Agent SDK manages its own output budget.
        cache_system: Enable prompt caching of the system prompt.
            API route only; the subscription route's ``claude`` CLI
            applies prompt caching automatically.
        on_cache_usage: Cache-telemetry callback. API route only.
        auth_mode: Explicit mode override; see
            :func:`resolve_auth_mode`.

    Returns:
        The model's text response (may be empty).

    Raises:
        AnthropicCallError: On invalid mode, forced-mode credential
            mismatch, missing credentials, or call failure after the
            routing rules above are exhausted.
    """
    resolved_model = model or resolve_model(tier)
    mode = resolve_auth_mode(auth_mode)
    if mode == "sub":
        forced_sub = _requested_mode(auth_mode) == "sub"
        try:
            text = _call_subscription(
                system=system,
                user_message=user_message,
                model=resolved_model,
            )
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: every subscription-path failure funnels
            # through one redaction + fallback decision point.
            if forced_sub or not api_key_available():
                raise AnthropicCallError(_redact(str(exc))) from None
            logger.warning(
                "Subscription LLM call failed; falling back to the API key path: %s",
                _redact(str(exc)),
            )
        else:
            auth_telemetry()["sub_calls"] += 1
            return text

    try:
        client = get_client()
    except AnthropicCallError:
        raise AnthropicCallError(_NO_CREDENTIALS_MESSAGE) from None
    text = call_api(
        client,
        system=system,
        user_message=user_message,
        model=resolved_model,
        max_tokens=max_tokens,
        cache_system=cache_system,
        on_cache_usage=on_cache_usage,
    )
    auth_telemetry()["api_calls"] += 1
    return text


def _call_subscription(*, system: str, user_message: str, model: str) -> str:
    """Synchronous wrapper around the async Agent-SDK call.

    ``claude_agent_sdk.query()`` spawns a fresh ``claude`` CLI
    subprocess per call, so a per-call ``asyncio.run`` is safe here.
    When the calling thread already runs an event loop, the call is
    pushed to a worker thread instead.
    """
    import asyncio  # noqa: PLC0415

    coro = _query_subscription(system=system, user_message=user_message, model=model)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures  # noqa: PLC0415

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def _query_subscription(*, system: str, user_message: str, model: str) -> str:
    """Single-turn completion via ``claude_agent_sdk.query()``.

    Constructs options with the adapter's ``sdk_isolation_kwargs()``
    (user/project settings stay out of the subprocess) and consumes
    the stream through ``iter_agent_messages`` (the #1534 teardown
    guard). Collects ``AssistantMessage`` text blocks and prefers
    ``ResultMessage.result`` when present.
    """
    from claude_agent_sdk import (  # noqa: PLC0415
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    # Lazy: attune.models must not import attune.workflows at module
    # import time (layering) — the adapter is only needed on the
    # subscription route.
    from attune.workflows.agent_sdk_adapter import (  # noqa: PLC0415
        iter_agent_messages,
        sdk_isolation_kwargs,
    )

    options = ClaudeAgentOptions(
        **sdk_isolation_kwargs(),
        system_prompt=system,
        model=model,
        max_turns=1,
        allowed_tools=[],  # pure completion — no tool use
    )
    text_parts: list[str] = []
    result_text: str | None = None
    async for message in iter_agent_messages(query(prompt=user_message, options=options)):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
        elif isinstance(message, ResultMessage):
            if isinstance(message.result, str) and message.result.strip():
                result_text = message.result
    return result_text if result_text is not None else "".join(text_parts)
