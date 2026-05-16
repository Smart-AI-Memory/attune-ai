"""Adapter to convert Agent SDK output into WorkflowResult.

Bridges the Agent SDK world (ResultMessage text) with attune's
workflow system (WorkflowResult, WorkflowStage, CostReport).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import claude_agent_sdk

from .base import ModelTier
from .data_classes import CostReport, NextAction, WorkflowResult, WorkflowStage

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
        )

    return None


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
_DEFAULT_BUDGET_USD: dict[str, float] = {
    "quick": 2.00,
    "standard": 10.00,
    "deep": 25.00,
}


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


def sdk_error_message(
    exc: BaseException,
    *,
    duration_seconds: float | None = None,
    depth: str | None = None,
) -> str:
    """Translate a ``claude_agent_sdk`` failure into actionable text.

    The SDK surfaces several failure modes as a generic
    ``Exception("Command failed with exit code 1 (exit code: 1)\\n
    Error output: Check stderr output for details")`` — the message
    is opaque, the user doesn't know what to do. This helper
    inspects the exception type, message, and the wall-clock
    duration of the run to classify the failure and produce a
    message that names the most likely cause and a concrete next
    step.

    Args:
        exc: The exception raised by ``claude_agent_sdk.query()``
            (or one of its async iterators).
        duration_seconds: Wall-clock seconds the run was alive
            before the exception. Optional. When provided, used
            to discriminate between startup-time failures
            (auth, CLI availability) and mid-stream failures
            (budget exhaustion, network blip).
        depth: The workflow depth that was running ("quick" /
            "standard" / "deep"). Used to suggest a depth bump
            when the failure smells budget-related.

    Returns:
        A one-paragraph error message suitable for embedding in
        a ``WorkflowResult`` error field. Always includes the
        original exception's raw string at the end so debugging
        information isn't lost.

    Patterns detected:

    * Startup failure (exit 1 + duration < 5s) → auth / CLI /
      version mismatch.
    * Mid-stream exit 1 (duration ≥ 30s) → likely budget cap
      hit during streaming.
    * ConnectionError / TimeoutError → upstream network.
    * Unrecognized → generic header + raw exception message.
    """
    raw_message = str(exc)
    raw_type = type(exc).__name__
    raw_tail = f"  Underlying error: {raw_type}: {raw_message}"

    if isinstance(exc, ConnectionError | TimeoutError):
        return (
            "Network error talking to the Anthropic API.\n"
            "Next steps:\n"
            "  - Check your internet connection.\n"
            "  - Verify api.anthropic.com isn't blocked by a "
            "firewall, VPN, or corporate proxy.\n"
            "  - Retry — transient API hiccups self-heal in seconds.\n"
            f"{raw_tail}"
        )

    is_exit_1 = "Command failed with exit code 1" in raw_message

    if is_exit_1 and duration_seconds is not None and duration_seconds < 5.0:
        return (
            "The `claude` CLI subprocess failed at startup "
            f"(only {duration_seconds:.1f}s elapsed). Most likely:\n"
            "  - `ANTHROPIC_API_KEY` is unset, expired, or invalid. "
            "Test it: `echo $ANTHROPIC_API_KEY` and try `claude` "
            "interactively.\n"
            "  - The `claude` CLI isn't installed or isn't on PATH. "
            "Install: `npm install -g @anthropic-ai/claude-code`.\n"
            "  - `claude-agent-sdk` version is incompatible with "
            "the installed `claude` CLI. Try upgrading both.\n"
            f"{raw_tail}"
        )

    if is_exit_1 and duration_seconds is not None and duration_seconds >= 30.0:
        suggested_depth = "standard" if depth == "quick" else "deep"
        return (
            "The `claude` CLI subprocess died mid-stream after "
            f"{duration_seconds:.1f}s. Most likely cause: budget "
            "cap exhausted during a multi-subagent run "
            "(security-audit, code-review, deep-review fan out "
            "to 3-5 parallel Opus subagents).\n"
            "Next steps:\n"
            f"  - Re-run with a higher cap: `ATTUNE_MAX_BUDGET_USD=0 "
            f"attune workflow run <name> --path <path>` to disable "
            f"the cap entirely.\n"
            f"  - Or bump depth: `--depth {suggested_depth}` (current "
            f"cap is ${_DEFAULT_BUDGET_USD.get(depth or 'standard', 10.0):.0f} "
            f"at `{depth or 'standard'}`).\n"
            "  - Subscription users pay no per-request cost; the cap "
            "is a complexity bound, not a billing limit.\n"
            f"{raw_tail}"
        )

    if is_exit_1:
        return (
            "The `claude` CLI subprocess failed (exit code 1). "
            "Common causes: missing or invalid `ANTHROPIC_API_KEY`, "
            "missing `claude` CLI, budget cap exhaustion, or a "
            "transient API failure.\n"
            "Next steps:\n"
            "  - Verify auth: try `claude` interactively or check "
            "`echo $ANTHROPIC_API_KEY`.\n"
            "  - For multi-subagent workflows, try `ATTUNE_MAX_BUDGET_USD=0` "
            "to rule out budget exhaustion.\n"
            "  - Check the stderr output in your terminal for the "
            "actual subprocess error.\n"
            f"{raw_tail}"
        )

    return (
        f"Agent SDK failure ({raw_type}). "
        "If this recurs, check the stderr output for the underlying "
        f"error and consider opening an issue.\n{raw_tail}"
    )


def get_max_budget_usd(depth: str = "standard") -> float | None:
    """Get budget cap for a workflow depth.

    Acts as a cost cap for API-key users and a complexity
    bound for subscription users. Priority:

    1. ``ATTUNE_MAX_BUDGET_USD`` env var (set to 0 to disable)
    2. Depth-based default from ``_DEFAULT_BUDGET_USD``

    Args:
        depth: Analysis depth — "quick", "standard", or "deep".

    Returns:
        Budget cap in USD, or None if caps are disabled.

    Notes:
        For pre-release audits where the default caps feel too
        restrictive, export ``ATTUNE_MAX_BUDGET_USD=0`` to let
        multi-subagent workflows run to completion. Subscription
        users pay no per-request cost for these runs.
    """
    override = os.environ.get("ATTUNE_MAX_BUDGET_USD")
    if override is not None:
        val = float(override)
        return val if val > 0 else None
    return _DEFAULT_BUDGET_USD.get(depth, 10.00)


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


# Role-keyword to model mapping for subagents
_SUBAGENT_MODEL_MAP: dict[str, str] = {
    # Deep reasoning agents → opus
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
}


def get_subagent_model(agent_name: str) -> str | None:
    """Get model for a subagent based on role keywords.

    Priority:

    1. ``ATTUNE_AGENT_MODEL_<KEYWORD>`` env var (exact keyword match)
    2. ``ATTUNE_AGENT_MODEL_DEFAULT`` env var (global override)
    3. ``_SUBAGENT_MODEL_MAP`` dict (built-in defaults)
    4. ``None`` (inherit parent model)

    Valid model values: ``"opus"``, ``"sonnet"``, ``"haiku"``,
    ``"inherit"``.

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
            return _SUBAGENT_MODEL_MAP[keyword]

    # Check global default override
    default = os.environ.get("ATTUNE_AGENT_MODEL_DEFAULT")
    if default:
        return default if default != "inherit" else None

    return None


# Section headers mapped to finding categories
_CATEGORY_PATTERNS: dict[str, re.Pattern[str]] = {
    "security": re.compile(r"##\s*security", re.IGNORECASE),
    "quality": re.compile(r"##\s*(?:code\s+)?quality", re.IGNORECASE),
    "performance": re.compile(r"##\s*performance", re.IGNORECASE),
    "architecture": re.compile(r"##\s*architecture", re.IGNORECASE),
    "test_gaps": re.compile(r"##\s*test\s*gaps?", re.IGNORECASE),
    "dependencies": re.compile(r"##\s*dependenc(?:y|ies)", re.IGNORECASE),
    "coverage": re.compile(r"##\s*(?:test\s+)?coverage", re.IGNORECASE),
    "refactoring": re.compile(r"##\s*refactor(?:ing)?", re.IGNORECASE),
    "bugs": re.compile(r"##\s*bugs?(?:\s+predict)?", re.IGNORECASE),
    "documentation": re.compile(r"##\s*documentation", re.IGNORECASE),
    "changelog": re.compile(r"##\s*changelog", re.IGNORECASE),
    "health": re.compile(r"##\s*health", re.IGNORECASE),
    "optimization": re.compile(r"##\s*optimiz(?:ation|e)", re.IGNORECASE),
    "complexity": re.compile(r"##\s*complexity", re.IGNORECASE),
    "outline": re.compile(r"##\s*outline", re.IGNORECASE),
    "research": re.compile(r"##\s*research", re.IGNORECASE),
}

# Pattern for suggestion-like bullet points
_SUGGESTION_RE = re.compile(
    r"^[\s]*[-*]\s+(?:(?:consider|suggest|recommend|should|could|try)\w*\s+)?(.+)",
    re.IGNORECASE,
)


class AgentSDKResultAdapter:
    """Converts Agent SDK ResultMessage text into a WorkflowResult.

    This adapter parses unstructured agent output text, extracts
    structured findings and suggestions, and packages everything
    into the standard WorkflowResult dataclass that downstream
    consumers (quality gates, telemetry, CLI) expect.
    """

    @classmethod
    def from_agent_output(
        cls,
        result_text: str,
        subagent_names: list[str],
        started_at: datetime,
        completed_at: datetime,
        metadata: dict[str, Any] | None = None,
        agent_run_result: AgentRunResult | None = None,
    ) -> WorkflowResult:
        """Build a WorkflowResult from raw agent text output.

        Args:
            result_text: The agent's full text response.
            subagent_names: Names of subagents that participated.
            started_at: When the agent execution began.
            completed_at: When the agent execution finished.
            metadata: Optional extra metadata to attach to the result.
            agent_run_result: Optional rich result data from the SDK
                including cost, usage, and timing. When provided,
                populates CostReport and WorkflowStage fields.

        Returns:
            A WorkflowResult populated with parsed findings,
            suggestions, stages, and cost/usage data.
        """
        if not result_text:
            logger.warning("Empty result_text passed to AgentSDKResultAdapter")

        text = result_text or ""
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Extract cost and usage from AgentRunResult if available
        total_cost: float | None = None
        usage: dict[str, Any] | None = None
        if agent_run_result:
            total_cost = agent_run_result.total_cost_usd
            usage = agent_run_result.usage

        stages = cls._build_stages(subagent_names, duration_ms, usage=usage)
        cost_report = cls._build_cost_report(
            subagent_names,
            total_cost_usd=total_cost,
        )

        # Prefer structured output when available; fall back to text parsing
        if (
            agent_run_result
            and agent_run_result.structured_output
            and isinstance(agent_run_result.structured_output, dict)
        ):
            findings, suggestions, summary = cls._from_structured_output(
                agent_run_result.structured_output,
            )
        else:
            findings = cls._parse_findings(text)
            suggestions = cls._extract_suggestions(text)
            summary = cls._extract_summary(text)

        result_metadata: dict[str, Any] = {
            "source": "agent_sdk",
            "subagent_count": len(subagent_names),
            "findings": findings,
        }
        if agent_run_result:
            result_metadata["num_turns"] = agent_run_result.num_turns
            result_metadata["session_id"] = agent_run_result.session_id
            result_metadata["duration_api_ms"] = agent_run_result.duration_api_ms
        if metadata:
            result_metadata.update(metadata)

        # Build final_output: prefer structured findings as markdown,
        # fall back to collected text
        final_output: str | dict[str, Any] = text
        if findings:
            formatted = cls._format_findings_markdown(findings, summary)
            if formatted:
                final_output = formatted

        return WorkflowResult(
            success=True,
            stages=stages,
            final_output=final_output,
            cost_report=cost_report,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=duration_ms,
            provider="anthropic",
            metadata=result_metadata,
            summary=summary,
            suggestions=suggestions,
        )

    @classmethod
    def _build_stages(
        cls,
        subagent_names: list[str],
        total_duration_ms: int,
        usage: dict[str, Any] | None = None,
    ) -> list[WorkflowStage]:
        """Create a WorkflowStage for each subagent.

        Splits total duration and token counts evenly across
        subagents as a rough approximation (actual per-agent
        timing is not available).
        """
        if not subagent_names:
            return []

        count = len(subagent_names)
        per_agent_ms = total_duration_ms // count

        # Distribute tokens evenly if usage data is available
        per_input = 0
        per_output = 0
        if usage:
            per_input = usage.get("input_tokens", 0) // count
            per_output = usage.get("output_tokens", 0) // count

        return [
            WorkflowStage(
                name=name,
                tier=ModelTier.CAPABLE,
                description=f"Agent SDK subagent: {name}",
                duration_ms=per_agent_ms,
                input_tokens=per_input,
                output_tokens=per_output,
            )
            for name in subagent_names
        ]

    @classmethod
    def _build_cost_report(
        cls,
        subagent_names: list[str],
        total_cost_usd: float | None = None,
    ) -> CostReport:
        """Build a cost report from SDK execution data.

        Uses actual cost when available (API-key users).
        Falls back to zero for subscription users (None).
        """
        cost = total_cost_usd if total_cost_usd is not None else 0.0
        by_stage = dict.fromkeys(subagent_names, 0.0)
        return CostReport(
            total_cost=cost,
            baseline_cost=cost,
            savings=0.0,
            savings_percent=0.0,
            by_stage=by_stage,
            by_tier={"capable": cost},
        )

    @classmethod
    def _extract_summary(cls, result_text: str) -> str:
        """Extract a summary from the agent's output.

        Looks for an explicit ``## Summary`` section first. Falls
        back to the first non-empty paragraph of text.
        """
        if not result_text.strip():
            return ""

        # Try explicit summary section
        summary_match = re.search(
            r"##\s*Summary\s*\n(.*?)(?=\n##|\Z)",
            result_text,
            re.DOTALL | re.IGNORECASE,
        )
        if summary_match:
            return summary_match.group(1).strip()

        # Fall back to first paragraph
        for paragraph in result_text.split("\n\n"):
            stripped = paragraph.strip()
            if stripped and not stripped.startswith("#"):
                return stripped

        # Last resort: first non-empty line
        for line in result_text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped

        return ""

    @classmethod
    def _parse_findings(cls, result_text: str) -> dict[str, Any]:
        """Extract structured findings by category from agent output.

        Looks for markdown section headers matching known categories
        (security, quality, performance, architecture) and collects
        the bullet points underneath each one.

        Args:
            result_text: The full agent response text.

        Returns:
            Dict mapping category names to lists of finding strings.
        """
        findings: dict[str, Any] = {}
        if not result_text.strip():
            return findings

        lines = result_text.splitlines()
        current_category: str | None = None

        for line in lines:
            stripped = line.strip()

            # Check if this line is a category header
            matched_category = False
            for category, pattern in _CATEGORY_PATTERNS.items():
                if pattern.search(stripped):
                    current_category = category
                    findings.setdefault(category, [])
                    matched_category = True
                    break

            if matched_category:
                continue

            # Any other h2/h3 header ends the current category
            if stripped.startswith("##"):
                current_category = None
                continue

            # Collect bullet points under the current category
            if current_category and re.match(r"^[-*]\s+", stripped):
                item = re.sub(r"^[-*]\s+", "", stripped)
                if item:
                    findings[current_category].append(item)

        return findings

    @classmethod
    def _extract_suggestions(cls, result_text: str) -> list[NextAction]:
        """Extract actionable suggestions as NextAction items.

        Scans for a ``## Suggestions`` or ``## Recommendations``
        section and converts each bullet into a NextAction. Falls
        back to scanning the entire text for suggestion-phrased
        bullets if no dedicated section exists.

        Args:
            result_text: The full agent response text.

        Returns:
            List of NextAction items parsed from the text.
        """
        if not result_text.strip():
            return []

        suggestions: list[NextAction] = []

        # Try dedicated section first
        section_match = re.search(
            r"##\s*(?:Suggestions?|Recommendations?|Next\s*Steps?)\s*\n(.*?)(?=\n##|\Z)",
            result_text,
            re.DOTALL | re.IGNORECASE,
        )

        if section_match:
            section_text = section_match.group(1)
            for line in section_text.splitlines():
                stripped = line.strip()
                bullet_match = re.match(r"^[-*]\s+(.+)", stripped)
                if bullet_match:
                    desc = bullet_match.group(1).strip()
                    if desc:
                        suggestions.append(
                            NextAction(
                                workflow_name="agent-followup",
                                description=desc,
                                reasoning="Extracted from agent SDK output",
                                priority="medium",
                                confidence=0.7,
                            )
                        )
            return suggestions

        # Fallback: scan entire text for suggestion-phrased bullets
        keywords = ("consider", "suggest", "recommend", "should", "could", "try")
        for line in result_text.splitlines():
            stripped = line.strip()
            bullet_match = re.match(r"^[-*]\s+(.+)", stripped)
            if bullet_match:
                content = bullet_match.group(1)
                lower = content.lower()
                if any(lower.startswith(kw) or f" {kw} " in lower for kw in keywords):
                    suggestions.append(
                        NextAction(
                            workflow_name="agent-followup",
                            description=content.strip(),
                            reasoning="Suggestion-phrased bullet in agent output",
                            priority="low",
                            confidence=0.5,
                        )
                    )

        return suggestions

    @classmethod
    def _format_findings_markdown(
        cls,
        findings: dict[str, Any],
        summary: str = "",
    ) -> str:
        """Render findings dict as readable markdown.

        Args:
            findings: Category-keyed dict of finding lists.
            summary: Optional summary to prepend.

        Returns:
            Markdown string, or empty string if no findings.
        """
        parts: list[str] = []
        if summary:
            parts.append(summary)
            parts.append("")

        for category, items in findings.items():
            if not items:
                continue
            heading = category.replace("_", " ").title()
            parts.append(f"## {heading}")
            parts.append("")
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        desc = item.get("description", str(item))
                        loc = item.get("file", "")
                        if loc:
                            line = item.get("line", "")
                            loc_str = f"{loc}:{line}" if line else loc
                            parts.append(f"- **{loc_str}** — {desc}")
                        else:
                            parts.append(f"- {desc}")
                    else:
                        parts.append(f"- {item}")
            else:
                parts.append(str(items))
            parts.append("")

        return "\n".join(parts).strip()

    @classmethod
    def _from_structured_output(
        cls,
        data: dict[str, Any],
    ) -> tuple[dict[str, Any], list[NextAction], str]:
        """Extract findings, suggestions, and summary from structured JSON.

        Called when the SDK returns ``structured_output`` instead of
        free-form markdown. Produces the same triple that the text-
        parsing path yields so the caller can use either transparently.

        Args:
            data: Parsed JSON dict from ``ResultMessage.structured_output``.

        Returns:
            Tuple of (findings dict, suggestions list, summary string).
        """
        findings: dict[str, Any] = data.get("findings", {})
        summary_data = data.get("summary", {})
        summary = summary_data.get("text", "") if isinstance(summary_data, dict) else ""

        suggestions = [
            NextAction(
                workflow_name="agent-followup",
                description=item.get("description", ""),
                reasoning="Structured agent output",
                priority=item.get("priority", "medium"),
                confidence=0.9,
            )
            for item in data.get("suggestions", [])
            if isinstance(item, dict) and item.get("description")
        ]
        return findings, suggestions, summary
