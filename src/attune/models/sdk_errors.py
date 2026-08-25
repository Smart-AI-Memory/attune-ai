"""SDK error taxonomy — classification, capture, and user-facing messages.

Split out of ``agent_sdk_adapter`` (#2240): the god-module mixed SDK
message iteration, this error taxonomy, and a markdown output parser.
Moved to the models layer in #2239 slice 1 alongside the adapter core;
``attune.workflows.agent_sdk_adapter`` re-exports every public name
here, so existing imports keep working. Tests that monkeypatch the
probe/classifier must target THIS module (the defining namespace) —
patching a re-export binding is the #2162 vacuous-test class.

Spec: docs/specs/sdk-error-message-fidelity/.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal

from attune.ops.session_redaction import redact

logger = logging.getLogger(__name__)

_DEFAULT_BUDGET_USD: dict[str, float] = {
    "quick": 2.00,
    "standard": 10.00,
    "deep": 25.00,
}


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


# ----------------------------------------------------------------------
# SDK error fidelity (spec: docs/specs/sdk-error-message-fidelity/)
#
# Typed exception, classifier, capture helper, argv extractor —
# wired into every workflow catch-all via sdk_error_from_exception
# and into iter_agent_messages' in-stream upgrade (#2227/#2229).
# ----------------------------------------------------------------------

SdkErrorKind = Literal[
    "api_quota",
    "auth",
    "rate_limit",
    "not_found",
    "schema_rejected",
    "unknown",
]


@dataclass
class SdkSubprocessError(Exception):
    """Typed wrapper around the SDK's bare 'Command failed' Exception.

    Captures the underlying ``claude`` CLI's stderr (via a second
    direct-subprocess call) and classifies it into one of the known
    failure-kind labels for user-facing messaging.

    Attributes:
        message: User-facing one-line summary (e.g. "Anthropic API
            quota reached for this account.").
        stderr: Redacted stderr captured from the second
            ``subprocess.run`` call.
        kind: Classified failure category (see ``SdkErrorKind``).
        original_exc: The SDK's wrapped exception, preserved so
            callers / tests can ``raise X from err.original_exc``.
    """

    message: str
    stderr: str
    kind: SdkErrorKind
    original_exc: BaseException | None = None

    def __str__(self) -> str:
        return self.message

    def format_user_message(self) -> str:
        """Voice-layer-ready user-facing block.

        When ``kind == "unknown"`` the raw stderr is included inline
        so the user has the truth even when the classifier didn't
        match a known pattern. For classified kinds, the message is
        the summary and the full stderr is available via the run
        view (persisted by Phase 3).
        """
        if self.kind == "unknown":
            if _stderr_carries_no_signal(self.stderr):
                # No stderr was recoverable — the most common real-world
                # cause on a fresh machine is no working auth (no
                # ANTHROPIC_API_KEY and a `claude` CLI that isn't logged
                # in). Say so instead of pointing at stderr that doesn't
                # exist (setup-friction F1).
                key_state = (
                    "ANTHROPIC_API_KEY is not set"
                    if not os.environ.get("ANTHROPIC_API_KEY", "").strip()
                    else "ANTHROPIC_API_KEY is set but may be invalid"
                )
                return (
                    "The claude CLI subprocess failed without producing "
                    "any error output.\n\n"
                    f"On this machine, {key_state} — the most common "
                    "cause is missing or logged-out auth.\n"
                    "Most likely fixes:\n"
                    "  - Log in to Claude Code: run `claude` once "
                    "interactively, or\n"
                    "  - Set an API key: export ANTHROPIC_API_KEY=..., or\n"
                    "  - Run `attune auth setup` for guided configuration.\n\n"
                    "Still stuck? https://github.com/Smart-AI-Memory/"
                    "attune-ai/discussions/1325"
                )
            return (
                f"{self.message}\n\n"
                "Underlying error (raw stderr from the claude CLI):\n"
                f"{self.stderr.strip()}"
            )
        return f"{self.message}\n\nFull stderr is available on /runs/<id>/view."


def _stderr_carries_no_signal(stderr: str) -> bool:
    """True when captured "stderr" has nothing a user could act on.

    ``capture_subprocess_failure()`` returns synthetic single-line
    parenthetical markers — e.g. ``"(the SDK reported a subprocess
    failure but exposed no command or stderr to capture)"`` or
    ``"(claude exited 1 with no stderr/stdout)"`` — when no real
    output was recoverable. Rendering those under an "Underlying
    error" heading points the user at evidence that doesn't exist
    (setup-friction F1). Treat text as no-signal when it is empty or
    every non-empty line is such a parenthetical marker.
    """
    text = stderr.strip()
    if not text:
        return True
    return all(
        line.startswith("(") and line.endswith(")")
        for line in (ln.strip() for ln in text.splitlines())
        if line
    )


# (compiled_re, kind, message) tuples. Ordered most-specific first so
# a more-precise label wins over a generic one (e.g. an "API usage
# limits" message that also mentions "401" still classifies as
# api_quota).
_CLASSIFIERS: list[tuple[re.Pattern[str], SdkErrorKind, str]] = [
    (
        re.compile(r"specified API usage limits", re.I),
        "api_quota",
        "Anthropic API quota reached for this account.",
    ),
    (
        re.compile(r"disabled Claude subscription access", re.I),
        "auth",
        "Claude subscription access is disabled for this organization; "
        "set ANTHROPIC_API_KEY so workflow subprocesses bill the API key.",
    ),
    (
        re.compile(r"\b(401|invalid[_\s-]?api[_\s-]?key|unauthorized)\b", re.I),
        "auth",
        "Anthropic auth invalid or missing.",
    ),
    (
        re.compile(r"\b(429|rate[_\s-]?limit|too many requests)\b", re.I),
        "rate_limit",
        "Rate-limited by Anthropic; retry shortly.",
    ),
    (
        re.compile(r"FileNotFoundError|claude.*not.*(found|on.*PATH)", re.I),
        "not_found",
        "The bundled claude CLI was not found at the expected path.",
    ),
    (
        re.compile(r"json[_\s-]?schema|--?json-?schema", re.I),
        "schema_rejected",
        "The output schema was rejected by the claude CLI.",
    ),
]


def classify_subprocess_failure(stderr: str) -> tuple[SdkErrorKind, str]:
    """Classify a captured stderr blob into ``(kind, user-message)``.

    Args:
        stderr: Captured stderr text from the ``claude`` CLI
            subprocess. Typically the redacted output of
            ``capture_subprocess_failure()``.

    Returns:
        A 2-tuple of ``(SdkErrorKind, str)``. Falls back to
        ``("unknown", "The claude CLI subprocess failed; see raw
        stderr below.")`` when no classifier pattern matches.
    """
    for pattern, kind, message in _CLASSIFIERS:
        if pattern.search(stderr):
            return kind, message
    return "unknown", "The claude CLI subprocess failed; see raw stderr below."


def sdk_error_from_exception(exc: Exception) -> SdkSubprocessError:
    """Return a classified :class:`SdkSubprocessError` for an SDK failure.

    Fast-path: :func:`iter_agent_messages` already raises a fully
    classified ``SdkSubprocessError`` when the CLI's own error-result
    text was captured from the stream — reuse it as-is. A re-probe would
    run outside the SDK child's env and can report a DIFFERENT auth
    condition than the one the child actually hit (#2227).

    Fallback: recover the failing argv from the exception, re-run/probe
    the CLI, and classify the captured stderr (the Phase-2 path).

    Args:
        exc: The exception caught around an SDK ``query()`` call.

    Returns:
        A classified ``SdkSubprocessError`` (never raises).
    """
    if isinstance(exc, SdkSubprocessError):
        return exc
    stderr = capture_subprocess_failure(_last_subprocess_argv(exc))
    kind, summary = classify_subprocess_failure(stderr)
    return SdkSubprocessError(
        message=summary,
        stderr=stderr,
        kind=kind,
        original_exc=exc,
    )


def _sdk_error_probe_enabled() -> bool:
    """Whether to fall back to a live ``claude`` health probe when the
    failing argv can't be recovered from the SDK exception.

    OFF by default so unit tests (which mock the SDK to raise) never spawn
    a real ``claude`` subprocess and stay deterministic. The ops dashboard
    runner sets ``ATTUNE_SDK_ERROR_PROBE=1`` when spawning workflows so a
    real failure surfaces the actual auth/quota error instead of a generic
    "no stderr" note.
    """
    return os.environ.get("ATTUNE_SDK_ERROR_PROBE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _claude_health_probe_argv() -> list[str]:
    """Minimal ``claude`` invocation used as the fallback diagnostic when
    the exact failing argv can't be recovered from the SDK exception.

    The installed ``claude_agent_sdk`` raises a bare
    ``Exception("Command failed ...")`` with the argv stored NOWHERE on it
    (no ``args[0]`` list, no ``__cause__.cmd``, no ``.cmd``), so
    ``_last_subprocess_argv()`` returns ``[]``. Re-running the exact
    command is therefore impossible — but a minimal ``claude -p`` probe
    reproduces the auth / quota / not-found failure modes (the ones this
    capture exists to reveal), all of which fail fast before any real
    generation. Factored out so tests can monkeypatch it deterministically
    instead of invoking the real binary.
    """
    return [shutil.which("claude") or "claude", "-p", "ok"]


def capture_subprocess_failure(
    args: list[str],
    env: dict[str, str] | None = None,
    timeout_s: float = 10.0,
) -> str:
    """Surface the real cause of a swallowed ``claude`` subprocess failure.

    Called from the broad-except branch around a
    ``claude_agent_sdk.query()`` call when the bare 'Command failed'
    exception fires. The SDK swallows stderr; this helper runs a
    ``claude`` invocation directly via ``subprocess.run()`` so the real
    cause (auth 401, quota, not-found) becomes visible.

    Args:
        args: argv to re-run. Normally the exact failing command from
            ``_last_subprocess_argv()`` — but the current SDK doesn't
            expose it, so this is usually ``[]``, in which case we fall
            back to a minimal ``claude`` health probe
            (``_claude_health_probe_argv()``).
        env: Optional env override. Defaults to the inherited
            process environment.
        timeout_s: Subprocess timeout. The failure modes we care
            about (quota / auth / not-found) all exit in sub-second;
            10s is a generous ceiling.

    Returns:
        Redacted stderr/stdout text, or a synthetic
        ``"(capture-call also failed: <reason>)"`` / ``"(capture-call
        timed out after <Ns>)"`` string if the subprocess itself raises.
        When the health-probe fallback was used, the text is prefixed
        with a one-line note so the user knows it's a probe, not the
        exact failing command. The synthetic strings are intentionally
        formatted so the classifier's "unknown" fallback still renders
        them to the user.
    """
    probe_note = ""
    if not args:
        # No recoverable argv (the SDK exception carries none). Only probe
        # `claude` directly when explicitly enabled — default-off keeps
        # unit tests deterministic (no real subprocess); the dashboard
        # runner opts in so the real auth/quota error surfaces.
        if not _sdk_error_probe_enabled():
            return (
                "(the SDK reported a subprocess failure but exposed no "
                "command or stderr to capture)"
            )
        args = _claude_health_probe_argv()
        probe_note = (
            "(could not recover the exact failing command from the SDK; "
            "ran a minimal `claude` health probe instead)\n"
        )
    if env is None:
        # Mirror the SDK's child env (subprocess_cli strips CLAUDECODE and
        # forces the sdk-py entrypoint) so the probe reproduces the
        # condition the SDK child actually hit. Inheriting a desktop
        # session's CLAUDE_CODE_ENTRYPOINT flips the CLI to host/
        # subscription auth and reports an unrelated error (#2227,
        # verified live 2026-08-24: probe said "subscription disabled"
        # while the child's real failure was an API usage-limit 400).
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env["CLAUDE_CODE_ENTRYPOINT"] = "sdk-py"
    try:
        result = subprocess.run(  # noqa: S603
            args,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,  # we want to inspect failure output
            input="",  # don't block on stdin for `-p` probes
        )
        # Some failures put real errors on stdout (e.g. JSON envelope).
        # Concatenate; the classifier scans both anyway.
        combined = (result.stderr or "") + ("\n" + result.stdout if result.stdout else "")
        text = redact(combined).text.strip()
        if not text:
            text = f"(claude exited {result.returncode} with no stderr/stdout)"
        return probe_note + text
    except subprocess.TimeoutExpired:
        return probe_note + f"(capture-call timed out after {timeout_s}s)"
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        # OSError: binary not found. ValueError: malformed argv.
        return probe_note + f"(capture-call also failed: {type(exc).__name__}: {exc})"


def _split_string_cmd(cmd: str) -> list[str]:
    """Split a string-valued exception ``cmd`` into argv.

    Wrapping the whole command line as ``[cmd]`` makes
    ``subprocess.run`` treat it as one executable path and report a
    misleading not-found. POSIX lexing mangles Windows backslash
    paths, so on Windows split in non-POSIX mode and strip the
    quotes the lexer preserves.
    """
    try:
        if os.name == "nt":
            return [tok.strip('"') for tok in shlex.split(cmd, posix=False)]
        return shlex.split(cmd)
    except ValueError:
        # Unbalanced quotes — a whitespace split still beats the
        # single-element argv's misleading not-found diagnostic.
        return cmd.split()


def _last_subprocess_argv(exc: BaseException) -> list[str]:
    """Extract the failing argv from an SDK ``Exception('Command failed ...')``.

    The SDK's ``claude_agent_sdk._internal.query`` raises a bare
    ``Exception`` with a string message but stores the subprocess
    args on the exception's ``__cause__`` or in an attribute the
    classifier walks. This helper centralises that extraction so
    a drift-guard test can fail loudly when the SDK changes shape.

    Walks these candidate attribute paths in order:

    1. ``exc.args[0]`` if it's already a ``list[str]`` (some SDK
       versions stash the argv there).
    2. ``exc.__cause__.cmd`` — ``subprocess.CalledProcessError``-shaped
       wrap. A string-valued ``cmd`` is shlex-split into argv (see
       :func:`_split_string_cmd`) — never wrapped as ``[cmd]``, which
       would make the re-run treat the whole line as an executable
       path.
    3. ``exc.cmd`` — direct attribute on the exception; same
       string-splitting rule.
    4. Fallback: empty list — the installed claude_agent_sdk raises a
       bare ``Exception`` with the argv stored nowhere, so ``[]`` is the
       normal result. The caller's ``capture_subprocess_failure([])``
       then runs a minimal ``claude`` health probe to surface the real
       auth/quota/not-found error.

    Returns:
        The captured argv as ``list[str]``, or ``[]`` if no
        recognized shape was found.
    """
    # Shape 1: argv stashed in exc.args[0]
    args_attr = getattr(exc, "args", None)
    if args_attr and isinstance(args_attr, tuple) and len(args_attr) > 0:
        first = args_attr[0]
        if isinstance(first, list) and all(isinstance(x, str) for x in first):
            return first

    # Shape 2: subprocess.CalledProcessError on __cause__
    cause = getattr(exc, "__cause__", None)
    if cause is not None:
        cmd = getattr(cause, "cmd", None)
        if isinstance(cmd, list) and all(isinstance(x, str) for x in cmd):
            return cmd
        if isinstance(cmd, str):
            return _split_string_cmd(cmd)

    # Shape 3: direct .cmd on the exception
    cmd = getattr(exc, "cmd", None)
    if isinstance(cmd, list) and all(isinstance(x, str) for x in cmd):
        return cmd
    if isinstance(cmd, str):
        return _split_string_cmd(cmd)

    return []
