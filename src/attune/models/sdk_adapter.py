"""Adapter to convert Agent SDK output into WorkflowResult.

Bridges the Agent SDK world (ResultMessage text) with attune's
workflow system (WorkflowResult, WorkflowStage, CostReport).

Lives in the models layer (#2239 slice 1): ``attune.models`` must
never import ``attune.workflows``, and ``models.single_turn`` needs
the adapter. ``attune.workflows.agent_sdk_adapter`` remains as a
back-compat facade re-exporting this module's surface.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import claude_agent_sdk

# Only what this module actually uses. The historical re-export
# surface (full sdk_errors + AgentSDKResultAdapter) lives on the
# workflows.agent_sdk_adapter facade, not here.
from .sdk_errors import (
    _DEFAULT_BUDGET_USD,
    SdkSubprocessError,
    classify_subprocess_failure,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    """Data extracted from Agent SDK execution.

    Carries cost, usage, and timing data from ResultMessage
    alongside the text output. Passed to
    ``AgentSDKResultAdapter.from_agent_output()`` so it can
    populate CostReport and WorkflowStage fields.
    """

    result_text: str
    structured_output: Any = None
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None
    duration_ms: int = 0
    duration_api_ms: int = 0
    num_turns: int = 0
    session_id: str | None = None
    is_error: bool = False
    stop_reason: str | None = None
    subtype: str | None = None
    errors: list[str] | None = None


def _maybe_dump_message(message: Any) -> None:
    """Append one JSON line describing an SDK message when
    ``ATTUNE_SDK_STREAM_DUMP=<dir>`` is set.

    Phase-0 instrumentation for the opus-4-8-platform-fit spec: every
    measured axis (narration volume, subagent/tool counts, ask-rate,
    effort fit, cost) derives from this dump. Content-free by design —
    TextBlocks record only ``chars`` and an ``interrogative`` flag,
    never the text itself, so dump dirs carry no code or prose.

    Off by default; best-effort — never raises into the stream loop.
    """
    dump_dir = os.environ.get("ATTUNE_SDK_STREAM_DUMP")
    if not dump_dir:
        return
    try:
        record: dict[str, Any] = {"ts": time.time(), "type": type(message).__name__}
        parent_id = getattr(message, "parent_tool_use_id", None)
        if parent_id is not None:
            record["parent_tool_use_id"] = parent_id
        content = getattr(message, "content", None)
        if isinstance(content, list):
            blocks: list[dict[str, Any]] = []
            for block in content:
                entry: dict[str, Any] = {"kind": type(block).__name__}
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    entry["chars"] = len(text)
                    entry["interrogative"] = text.rstrip().endswith("?")
                tool_name = getattr(block, "name", None)
                if isinstance(tool_name, str):
                    entry["tool_name"] = tool_name
                blocks.append(entry)
            record["blocks"] = blocks
        if isinstance(message, claude_agent_sdk.ResultMessage):
            record["result"] = {
                "total_cost_usd": message.total_cost_usd,
                "usage": message.usage,
                "num_turns": message.num_turns,
                "duration_ms": message.duration_ms,
                "duration_api_ms": message.duration_api_ms,
                "is_error": message.is_error,
                "session_id": message.session_id,
            }
        path = Path(dump_dir) / f"stream-{os.getpid()}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: instrumentation must never break the stream loop.
        logger.debug("ATTUNE_SDK_STREAM_DUMP write failed", exc_info=True)


def collect_agent_output(
    message: Any,
    assistant_parts: list[str],
    result_parts: list[str],
) -> AgentRunResult | None:
    """Extract text and metadata from a single SDK message.

    Call this inside ``async for message in claude_agent_sdk.query()``.
    It collects text from both ``AssistantMessage`` (the actual agent
    analysis) and ``ResultMessage`` (final metadata + optional summary).

    Args:
        message: A message yielded by ``claude_agent_sdk.query()``.
        assistant_parts: Mutable list accumulating AssistantMessage text.
        result_parts: Mutable list accumulating ResultMessage text.

    Returns:
        An AgentRunResult with metadata when a ResultMessage is received,
        or None for other message types. The caller should set
        ``run_result.result_text`` after the loop completes using
        ``build_result_text(assistant_parts, result_parts)``.
    """
    _maybe_dump_message(message)

    if isinstance(message, claude_agent_sdk.AssistantMessage):
        for block in message.content:
            if isinstance(block, claude_agent_sdk.types.TextBlock):
                assistant_parts.append(block.text)
        return None

    if isinstance(message, claude_agent_sdk.ResultMessage):
        if message.result:
            result_parts.append(message.result)
        return AgentRunResult(
            result_text="",
            structured_output=message.structured_output,
            total_cost_usd=message.total_cost_usd,
            usage=message.usage,
            duration_ms=message.duration_ms,
            duration_api_ms=message.duration_api_ms,
            num_turns=message.num_turns,
            session_id=message.session_id,
            is_error=message.is_error,
            stop_reason=getattr(message, "stop_reason", None),
            subtype=getattr(message, "subtype", None),
            errors=getattr(message, "errors", None),
        )

    return None


def _is_benign_teardown_exit(exc: Exception) -> bool:
    """True for the SDK's bare post-result 'Command failed' teardown exit.

    ``claude_agent_sdk`` raises a bare
    ``Exception("Command failed with exit code N")`` when the underlying
    ``claude`` subprocess exits non-zero — including on teardown, AFTER a
    successful run has already streamed its ``ResultMessage``. This matches
    that shape conservatively; it is only ever consulted once a successful
    result has already been observed (see :func:`iter_agent_messages`).
    """
    return "command failed" in str(exc).lower()


async def iter_agent_messages(query: AsyncIterator[Any]) -> AsyncIterator[Any]:
    """Yield SDK messages, recovering from a teardown exit after success.

    Wraps ``claude_agent_sdk.query(...)``. Every message is passed through
    unchanged so :func:`collect_agent_output` works exactly as before. If
    the underlying stream raises a benign teardown "Command failed"
    exception AFTER a ``ResultMessage(subtype="success")`` was already
    yielded, the iteration stops cleanly so the caller returns its
    already-captured result instead of discarding it.

    When the stream raises AFTER an ``is_error`` ``ResultMessage`` was
    seen, the raise is upgraded to a classified
    :class:`SdkSubprocessError` built from that result's own error text.
    The SDK's replacement exception names only the result *subtype*
    (``"Claude Code returned an error result: success"``) and drops the
    ``result`` body — which is where the CLI put the actual cause (e.g.
    ``API Error: 400 ... specified API usage limits ...``). Re-probing
    from the parent instead runs in a DIFFERENT env than the SDK child
    and can report an unrelated auth condition (#2227), so the captured
    in-stream text is the highest-fidelity source available.

    Any other exception — or one raised before a successful result — is
    re-raised unchanged, preserving fail-closed semantics: a genuine
    auth/quota/startup/runtime failure never becomes a false pass. The
    success signal is ``subtype == "success"`` (not ``not is_error``),
    which is the marker that stayed correct across the SDK 0.2.102 /
    bundled CLI 2.1.178 window where ``is_error`` was wrongly ``True`` on
    success. ``BaseException`` (KeyboardInterrupt / SystemExit /
    CancelledError) is never caught.

    Args:
        query: The async iterable returned by ``claude_agent_sdk.query()``.

    Yields:
        Each message from the underlying stream, unchanged.
    """
    saw_success = False
    last_error_result_text: str | None = None
    iterator = query.__aiter__()
    while True:
        try:
            message = await iterator.__anext__()
        except StopAsyncIteration:
            return
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: a non-zero teardown exit AFTER a successful
            # ResultMessage is benign — the work completed and its result
            # was already yielded; recover it. Anything else (including a
            # failure before success) re-raises so a genuine error never
            # fake-passes.
            if saw_success and _is_benign_teardown_exit(exc):
                logger.warning(
                    "SDK exited non-zero after a successful ResultMessage; "
                    "surfacing the captured result (%s)",
                    exc,
                )
                return
            if last_error_result_text is not None:
                kind, summary = classify_subprocess_failure(last_error_result_text)
                raise SdkSubprocessError(
                    message=summary,
                    stderr=last_error_result_text,
                    kind=kind,
                    original_exc=exc,
                ) from exc
            raise
        if isinstance(message, claude_agent_sdk.ResultMessage):
            if getattr(message, "subtype", None) == "success":
                saw_success = True
            if getattr(message, "is_error", False):
                error_bits = [str(e) for e in (getattr(message, "errors", None) or [])]
                result_text = getattr(message, "result", None)
                if result_text:
                    error_bits.append(str(result_text))
                last_error_result_text = "\n".join(error_bits) or None
        yield message


async def collect_subagent_transcripts(
    session_id: str | None,
) -> dict[str, list[str]]:
    """Return per-subagent text transcripts for a completed run.

    Multi-subagent workflows (``security_audit``, ``code_review``)
    spawn parallel subagents via the SDK's ``Agent`` tool. The
    orchestrator's top-level ``AssistantMessage`` stream only
    surfaces what it chose to synthesize — per-subagent
    exploration is lost if the orchestrator summarizes tersely
    or hits the budget/turn cap. This helper reads each
    subagent's JSONL transcript from the session's directory
    and returns the raw assistant-text chunks so consumers can
    attach them to the ``WorkflowResult``.

    Args:
        session_id: ``AgentRunResult.session_id`` from a completed
            SDK run. Pass ``None`` when unknown — the helper
            returns an empty dict rather than raising.

    Returns:
        Dict keyed by subagent ID (NOT name — the SDK stores
        transcripts under their generated IDs; human-readable
        subagent names live inside each message). Values are
        lists of assistant-text chunks in original order.
        Empty dict when ``session_id`` is None, the SDK version
        doesn't expose ``list_subagents`` / ``get_subagent_messages``,
        or the transcript directory is missing.
    """
    if not session_id:
        return {}

    list_fn = getattr(claude_agent_sdk, "list_subagents", None)
    get_fn = getattr(claude_agent_sdk, "get_subagent_messages", None)
    if list_fn is None or get_fn is None:
        logger.debug(
            "collect_subagent_transcripts: SDK %s lacks list_subagents / "
            "get_subagent_messages — skipping enrichment",
            getattr(claude_agent_sdk, "__version__", "unknown"),
        )
        return {}

    try:
        subagent_ids = list_fn(session_id)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: transcript enrichment is best-effort.
        # Any failure reading session storage (missing directory,
        # permission error, disk I/O hiccup, schema drift) should
        # return an empty dict so callers emit the normal result
        # without the enrichment block.
        logger.debug(
            "collect_subagent_transcripts: list_subagents(%s) failed",
            session_id,
            exc_info=True,
        )
        return {}

    transcripts: dict[str, list[str]] = {}
    for agent_id in subagent_ids:
        try:
            messages = get_fn(session_id, agent_id)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: one broken subagent transcript must
            # not prevent the others from being recovered.
            logger.debug(
                "collect_subagent_transcripts: get_subagent_messages(%s, %s) failed",
                session_id,
                agent_id,
                exc_info=True,
            )
            continue
        texts = _extract_assistant_texts(messages)
        if texts:
            transcripts[agent_id] = texts
    return transcripts


def format_subagent_transcripts_markdown(
    transcripts: dict[str, list[str]],
    max_chars_per_agent: int = 2000,
) -> str:
    """Render recovered subagent transcripts as a markdown block.

    Produces one ``### <agent_id>`` subsection per subagent.
    Each subsection concatenates the agent's text chunks and
    truncates to ``max_chars_per_agent`` with a ``[truncated,
    full transcript in metadata]`` footer — the full content
    stays available under ``metadata["subagent_transcripts"]``
    for programmatic consumers.

    Returns an empty string when ``transcripts`` is empty so
    callers can safely concatenate.
    """
    if not transcripts:
        return ""
    parts: list[str] = []
    for agent_id, texts in transcripts.items():
        joined = "\n\n".join(t.strip() for t in texts if t and t.strip())
        if not joined:
            continue
        truncated_note = ""
        if len(joined) > max_chars_per_agent:
            joined = joined[:max_chars_per_agent]
            truncated_note = (
                "\n\n_[truncated; full transcript in " '`metadata["subagent_transcripts"]`]_'
            )
        parts.append(f"### {agent_id}\n\n{joined}{truncated_note}")
    return "\n\n".join(parts)


def _extract_assistant_texts(messages: Any) -> list[str]:
    """Pull assistant text blocks out of a subagent's transcript.

    Each ``SessionMessage`` carries a ``message`` field whose
    shape follows the Anthropic API. We only care about
    ``assistant``-typed messages' text content, in the order
    they were emitted.
    """
    out: list[str] = []
    if not messages:
        return out
    for msg in messages:
        if getattr(msg, "type", None) != "assistant":
            continue
        payload = getattr(msg, "message", None)
        if not payload:
            continue
        content = payload.get("content") if isinstance(payload, dict) else None
        if content is None:
            continue
        # content can be a string OR a list of typed blocks.
        if isinstance(content, str):
            if content.strip():
                out.append(content)
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            text = block.get("text", "")
            if text:
                out.append(text)
    return out


def build_result_text(
    assistant_parts: list[str],
    result_parts: list[str],
) -> str:
    """Combine collected text into the final result string.

    Prefers ``ResultMessage.result`` when available (explicit summary).
    Falls back to ``AssistantMessage`` text blocks (the full analysis).

    Args:
        assistant_parts: Text from AssistantMessage TextBlocks.
        result_parts: Text from ResultMessage.result fields.

    Returns:
        Combined result text, or a default message if both are empty.
    """
    result_text = "\n".join(result_parts).strip()
    assistant_text = "\n\n".join(assistant_parts).strip()

    # Prefer whichever source has more content — assistant_parts
    # typically contain the full subagent analysis while
    # result_parts may only have brief orchestrator commentary
    if assistant_text and len(assistant_text) >= len(result_text):
        return assistant_text

    if result_text:
        return result_text

    return "No results returned."


# Budget defaults by depth level.
#
# These caps target multi-subagent workflows like security-audit
# and code-review, which spawn 4-5 parallel Opus subagents that
# each make 15-25 tool calls before synthesis. A trace of
# security-audit with the prior $2 "standard" cap showed the SDK
# cutting the stream mid-exploration after ~100s with
# ``ResultMessage(result=None, is_error=False)`` — silent early
# termination before any subagent produced final findings.
#
# Set ``ATTUNE_MAX_BUDGET_USD=0`` to disable caps entirely, or
# any positive float to override the depth default.


_DEFAULT_TASK_BUDGET_TOKENS: dict[str, int] = {
    "quick": 20_000,
    "standard": 80_000,
    "deep": 200_000,
}


# Cache for the CLI's --task-budget support probe. None = not yet
# probed; True/False = result. Probe is lazy + once-per-process.
_CLI_SUPPORTS_TASK_BUDGET: bool | None = None


def _cli_supports_task_budget() -> bool:
    """Return True iff the resolved ``claude`` CLI accepts ``--task-budget``.

    The SDK appends ``--task-budget <N>`` to the CLI command when
    ``ClaudeAgentOptions.task_budget`` is set. Older CLI binaries
    (including the bundled one in ``claude-agent-sdk`` 0.1.63 and
    the system ``claude`` 2.1.x) don't recognize the flag and exit
    with code 1 at startup — surfaced to the workflow as an
    opaque ``Command failed with exit code 1`` with ``$0 cost /
    1-2s elapsed``. This probe gates the feature off until both
    sides catch up.

    Probes by running ``<cli> --help`` once and grepping for
    ``--task-budget``. Result is cached in
    ``_CLI_SUPPORTS_TASK_BUDGET`` so the subprocess fires at most
    once per Python process.

    The CLI is resolved using the same precedence as the SDK
    transport: prefer the SDK's bundled CLI when present,
    fall back to ``shutil.which("claude")``.
    """
    global _CLI_SUPPORTS_TASK_BUDGET
    if _CLI_SUPPORTS_TASK_BUDGET is not None:
        return _CLI_SUPPORTS_TASK_BUDGET

    # SDK's bundled CLI takes precedence over PATH.
    sdk_dir = Path(claude_agent_sdk.__file__).resolve().parent
    bundled = sdk_dir / "_bundled" / "claude"
    cli_path = str(bundled) if bundled.is_file() else shutil.which("claude")

    if not cli_path:
        _CLI_SUPPORTS_TASK_BUDGET = False
        return False

    try:
        result = subprocess.run(
            [cli_path, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        _CLI_SUPPORTS_TASK_BUDGET = "--task-budget" in (result.stdout + result.stderr)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning(
            "task-budget CLI probe failed (%s); disabling task_budget",
            type(exc).__name__,
        )
        _CLI_SUPPORTS_TASK_BUDGET = False
    return _CLI_SUPPORTS_TASK_BUDGET


def get_task_budget(depth: str = "standard") -> Any:
    """Build a token-aware ``TaskBudget`` for a workflow depth.

    Pairs with :func:`get_max_budget_usd` — the USD cap is the
    hard safety net; the ``TaskBudget`` is the primitive the
    model actually sees, so it can pace itself and wrap up
    cleanly instead of getting cut mid-exploration. Available
    since ``claude-agent-sdk`` 0.1.51.

    Override the per-depth default via the
    ``ATTUNE_TASK_BUDGET_TOKENS`` env var (positive integer;
    unset or 0 falls back to the depth default).

    Returns ``None`` when (a) the installed SDK doesn't expose
    ``TaskBudget``, or (b) the resolved ``claude`` CLI doesn't
    accept the ``--task-budget`` flag (SDK transport appends it
    unconditionally; older CLIs reject the unknown arg and
    exit 1 at subprocess startup). Callers can treat None as a
    no-op field.
    """
    budget_cls = getattr(claude_agent_sdk, "TaskBudget", None)
    if budget_cls is None:
        return None
    if not _cli_supports_task_budget():
        return None
    override = os.environ.get("ATTUNE_TASK_BUDGET_TOKENS")
    if override:
        try:
            val = int(override)
            if val > 0:
                return budget_cls(total=val)
        except ValueError:
            logger.warning(
                "ATTUNE_TASK_BUDGET_TOKENS=%r not an int; falling back to depth default",
                override,
            )
    total = _DEFAULT_TASK_BUDGET_TOKENS.get(depth, 80_000)
    return budget_cls(total=total)


def get_thinking_config(depth: str = "standard") -> Any:
    """Return an ``ThinkingConfigAdaptive`` for deep runs, else None.

    Deep-depth workflows spend 40+ turns of budget and benefit
    materially from extended thinking on architecture /
    remediation-planner subagents. Shallow runs don't need it
    and paying for it is waste. Available since
    ``claude-agent-sdk`` 0.1.36; replaces the deprecated
    ``max_thinking_tokens`` knob.

    Callers should do ``if cfg := get_thinking_config(depth):``
    and only include ``thinking=cfg`` + ``effort="high"`` in
    the options when non-None.
    """
    if depth != "deep":
        return None
    cfg_cls = getattr(claude_agent_sdk, "ThinkingConfigAdaptive", None)
    if cfg_cls is None:
        return None
    return cfg_cls()


def get_max_budget_usd(
    depth: str = "standard",
    explicit: float | None = None,
) -> float | None:
    """Get budget cap for a workflow depth.

    Acts as a cost cap for API-key users and a complexity
    bound for subscription users. Priority:

    1. ``explicit`` caller-supplied cap (e.g. a discovery-sweep
       source's per-call allocation). When not ``None`` it wins
       outright — the caller has already decided the ceiling.
    2. ``ATTUNE_MAX_BUDGET_USD`` env var (set to 0 to disable)
    3. Depth-based default from ``_DEFAULT_BUDGET_USD``

    Args:
        depth: Analysis depth — "quick", "standard", or "deep".
        explicit: Caller-supplied USD cap that overrides both the
            env var and the depth default. Used by discovery-sweep
            to plumb each source's budget allocation down into the
            wrapped workflow (budget-enforcement spec, FR-1). A
            non-sweep caller passes ``None`` and gets today's
            env/depth-derived behavior unchanged.

    Returns:
        Budget cap in USD, or None if caps are disabled.

    Notes:
        For pre-release audits where the default caps feel too
        restrictive, export ``ATTUNE_MAX_BUDGET_USD=0`` to let
        multi-subagent workflows run to completion. Subscription
        users pay no per-request cost for these runs. The env
        var is NOT a hard ceiling over ``explicit`` — a sweep
        passing a per-source allocation overrides it (the sweep's
        ``budget_usd`` is the user's ceiling for that sweep). See
        the budget-enforcement spec ``decisions.md`` for the
        precedence rationale.
    """
    if explicit is not None:
        return explicit
    override = os.environ.get("ATTUNE_MAX_BUDGET_USD")
    if override is not None:
        val = float(override)
        return val if val > 0 else None
    return _DEFAULT_BUDGET_USD.get(depth, 10.00)


#: Env marker every SDK-spawned ``claude`` subprocess carries so attune
#: hooks can self-gate (sdk-subprocess-isolation spec, D3/D4).
SDK_SUBPROCESS_ENV_VAR = "ATTUNE_SDK_SUBPROCESS"


async def _guard_bash_tool(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """In-process PreToolUse guard for SDK subprocess sessions (Phase 4).

    Isolation (``setting_sources=[]``) strips ALL filesystem hooks from
    workflow subprocesses — including the protective ``security_guard``.
    This callback re-injects that one control programmatically: the
    protection travels with the adapter instead of depending on the
    environment. Reuses the hook script's own ``validate_bash_command``
    (single source of truth for the banned patterns) and denies with a
    reason so the workflow agent can adapt rather than crash.

    Args:
        input_data: PreToolUse hook payload (``tool_name``/``tool_input``).
        tool_use_id: SDK-provided tool use id (unused).
        context: SDK hook context (unused).

    Returns:
        Empty dict to allow; a deny decision with reason to block.

    """
    from attune.hooks.scripts.security_guard import validate_bash_command

    command = str((input_data.get("tool_input") or {}).get("command", ""))
    ok, reason = validate_bash_command(command)
    if ok:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def make_edit_scope_guard(scope_paths: list[Path]):
    """Build a PreToolUse hook denying Edit/Write outside ``scope_paths``.

    Prevention layer for the scope contract (codex D11 lane finding):
    the deny happens at tool-call time, not just in the post-run
    receipt diff.
    """
    resolved_scope = [p.resolve() for p in scope_paths]

    async def _guard_edit_tool(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: Any,
    ) -> dict[str, Any]:
        raw = str((input_data.get("tool_input") or {}).get("file_path", ""))
        if not raw:
            return {}
        try:
            target = Path(raw).resolve()
        except (OSError, RuntimeError):
            target = None
        if target is not None and any(
            target == allowed or allowed in target.parents for allowed in resolved_scope
        ):
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"path {raw!r} is outside the allowed write scope; "
                    "allowed: " + ", ".join(str(p) for p in resolved_scope)
                ),
            }
        }

    return _guard_edit_tool


def sdk_isolation_kwargs() -> dict[str, Any]:
    """``ClaudeAgentOptions`` kwargs isolating the SDK subprocess session.

    sdk-subprocess-isolation spec (D2–D5): ``setting_sources=[]`` keeps
    user/project/local settings — and with them SessionStart hooks and
    CLAUDE.md injection — out of workflow subprocesses, which is what
    makes SDK workflows usable for subscription users (hook stdout
    otherwise poisons the stream-json channel). The env marker lets
    attune hooks self-gate on older SDKs and non-adapter spawn paths.
    The programmatic Bash guard (Phase 4, D8) re-injects the eval/exec
    protection that settings exclusion would otherwise remove.

    Splat into every ``ClaudeAgentOptions`` construction::

        claude_agent_sdk.ClaudeAgentOptions(
            **sdk_isolation_kwargs(),
            system_prompt=...,
        )

    A drift-guard test asserts every construction site uses it. NOTE:
    never pass ``options.skills`` without an explicit
    ``setting_sources`` — the SDK silently forces ``["user","project"]``
    back on (spec findings F4).

    Returns:
        Kwargs dict with ``setting_sources``, ``env``, and ``hooks``.

    """
    return {
        "setting_sources": [],
        "env": {SDK_SUBPROCESS_ENV_VAR: "1"},
        "hooks": {
            "PreToolUse": [
                claude_agent_sdk.HookMatcher(matcher="Bash", hooks=[_guard_bash_tool]),
            ],
        },
    }


def resolve_cwd_for_path(path: str | Path) -> Path:
    """Return a directory path suitable for the Agent SDK ``cwd=`` arg.

    The Claude Agent SDK's ``cwd`` must be an existing directory.
    Passing a file raises ``CLIConnectionError: Not a directory``
    at subprocess startup, which the SDK surfaces opaquely as
    ``Command failed with exit code 1``. When the caller's path
    targets a single file (e.g. a per-module workflow run), the
    file's parent directory is the correct ``cwd``.

    Args:
        path: File or directory path the workflow is targeting.

    Returns:
        ``Path(path).parent`` when ``path`` is an existing file;
        otherwise ``Path(path)`` unchanged.
    """
    p = Path(path)
    return p.parent if p.is_file() else p


# Role-keyword to model mapping for subagents.
#
# Each entry registers a keyword that hooks two things:
#
# 1. The default model for subagents whose name contains the keyword.
# 2. An env-var override path: ``ATTUNE_AGENT_MODEL_<KEYWORD>=sonnet``
#    lets users opt subagents matching that keyword to a different
#    tier without code changes.
#
# Map value ``"inherit"`` means "preserve current behavior — fall
# through to the orchestrator's model unless overridden by env var."
# Useful for agent roles where we want the override knob exposed
# but don't want to commit to a specific tier as the default.
#
# Subscription-tier (Pro/Max) users hitting rate limits on
# subagent-heavy workflows (security-audit, deep-review,
# code-review) can lighten the load with e.g.
# ``ATTUNE_AGENT_MODEL_VULN=sonnet ATTUNE_AGENT_MODEL_DETECTOR=sonnet
# ATTUNE_AGENT_MODEL_REVIEWER=sonnet attune workflow run security-audit``.
_SUBAGENT_MODEL_MAP: dict[str, str] = {
    # Deep reasoning agents → opus
    # ORDERING NOTE: these must come BEFORE scanner/finder/detector
    # so that security-scanner and vuln-scanner stay on opus rather
    # than dropping to haiku via the broader scanner keyword.
    "security": "opus",
    "vuln": "opus",
    "architect": "opus",
    # Synthesis/planning agents → sonnet (balanced)
    "quality": "sonnet",
    "plan": "sonnet",
    "research": "sonnet",
    # Scanning/detection agents → haiku (fast, cheap)
    "complexity": "haiku",
    "lint": "haiku",
    "coverage": "haiku",
    "dep": "haiku",
    # Role-shape keywords for pattern-matching / structured-parse
    # work. Catches subagents like ``pattern-scanner``,
    # ``debt-scanner``, ``bottleneck-finder``, ``gap-finder``,
    # ``secret-detector``. Vuln-scanner / security-scanner stay
    # on opus because their (security, vuln) keywords match first.
    "scanner": "haiku",
    "finder": "haiku",
    "detector": "haiku",
    # Role-shape keyword with no committed default; exposed
    # primarily as override hook. ``inherit`` preserves the
    # parent's model unless the corresponding env var is set.
    # Covers auth-reviewer (security-audit), perf-reviewer
    # (code-review), safety-reviewer (simplify-code),
    # test-gap-reviewer (deep-review), accuracy-reviewer
    # (doc-audit), polish-reviewer (document-gen).
    "reviewer": "inherit",
}


def get_subagent_model(agent_name: str) -> str | None:
    """Get model for a subagent based on role keywords.

    Priority:

    1. ``ATTUNE_AGENT_MODEL_<KEYWORD>`` env var (exact keyword match)
    2. ``ATTUNE_AGENT_MODEL_DEFAULT`` env var (global override)
    3. ``_SUBAGENT_MODEL_MAP`` dict (built-in defaults)
    4. ``None`` (inherit parent model)

    Valid model values: ``"opus"``, ``"sonnet"``, ``"haiku"``,
    ``"inherit"``. The literal ``"inherit"`` is normalized to
    ``None`` so callers can pass the return value directly to the
    SDK ``AgentDefinition.model`` field.

    Args:
        agent_name: Name of the subagent (e.g. ``"security-reviewer"``).

    Returns:
        Model name string, or None to inherit the parent model.
    """
    name_lower = agent_name.lower()

    # Check keyword-specific env var override
    for keyword in _SUBAGENT_MODEL_MAP:
        if keyword in name_lower:
            env_key = f"ATTUNE_AGENT_MODEL_{keyword.upper()}"
            env_val = os.environ.get(env_key)
            if env_val:
                return env_val if env_val != "inherit" else None
            configured = _SUBAGENT_MODEL_MAP[keyword]
            if configured != "inherit":
                return configured
            # Map value is ``inherit`` — this keyword exists solely
            # to expose an override hook. Without that override, fall
            # through to the global DEFAULT or ultimately None
            # (parent-inherit) below. Match the FIRST keyword only.
            break

    # Check global default override
    default = os.environ.get("ATTUNE_AGENT_MODEL_DEFAULT")
    if default:
        return default if default != "inherit" else None

    return None
