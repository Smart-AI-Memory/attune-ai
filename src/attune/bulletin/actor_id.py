"""Actor identity derivation.

The bulletin needs a stable ``actor_id`` per process so multi-actor
visibility makes sense ("dashboard-patrick-mbp is running X" not just
"some-uuid is running X"). The shape varies by actor kind:

| Actor kind            | ID format                                      |
|-----------------------|------------------------------------------------|
| ``claude-code-session`` | ``cc-<session-id-12>`` (from env)            |
| ``cli``               | ``cli-<hostname>-<pid>``                       |
| ``dashboard``         | ``dashboard-<hostname>``                       |
| ``scheduled``         | ``sched-<task-id>``                            |
| ``mcp``               | inherits CC session if env present, else      |
|                       | ``mcp-<hostname>-<pid>``                       |
| ``attune-rec``        | inherits from triggering actor (dashboard)    |

Detection order in :func:`resolve_actor` checks the most specific
signal first (an explicit ``actor_kind`` argument), then env vars,
then falls back to a generic CLI shape.
"""

from __future__ import annotations

import os
import socket

from .protocol import ActorKind

# Env var Claude Code exposes in live sessions. See CLAUDE.md lesson —
# the name is ``CLAUDE_CODE_SESSION_ID`` (with ``CODE_`` infix), not
# ``CLAUDE_SESSION_ID``.
_CC_SESSION_ENV = "CLAUDE_CODE_SESSION_ID"


def resolve_actor(
    *,
    actor_kind: ActorKind | None = None,
    scheduled_task_id: str | None = None,
) -> tuple[str, ActorKind]:
    """Return ``(actor_id, actor_kind)`` for the current process.

    Args:
        actor_kind: Explicit override. Use when the caller knows its
            role (e.g. dashboard server sets ``"dashboard"`` at
            startup; scheduled tasks set ``"scheduled"``). When
            omitted, the resolver inspects env vars and falls back to
            ``"cli"``.
        scheduled_task_id: Required when ``actor_kind="scheduled"``;
            otherwise ignored.

    Returns:
        ``(actor_id, actor_kind)`` tuple suitable for stamping into
        :class:`BulletinEntry`.
    """
    if actor_kind == "scheduled":
        task = scheduled_task_id or "unknown"
        return (f"sched-{task}", "scheduled")

    if actor_kind == "dashboard":
        return (f"dashboard-{_hostname()}", "dashboard")

    # Claude Code session env wins over the CLI default for both
    # ``claude-code-session`` and ``mcp`` callers — an MCP handler
    # invoked from a Claude Code session should report the session
    # id, not its own pid.
    cc_session = os.environ.get(_CC_SESSION_ENV)
    if cc_session:
        short = cc_session[:12]
        if actor_kind == "mcp":
            return (f"cc-{short}", "mcp")
        return (f"cc-{short}", "claude-code-session")

    if actor_kind == "mcp":
        return (f"mcp-{_hostname()}-{os.getpid()}", "mcp")

    if actor_kind == "attune-rec":
        # Inherits from the dashboard process that triggered it.
        return (f"dashboard-{_hostname()}", "attune-rec")

    # Default: CLI invocation.
    return (f"cli-{_hostname()}-{os.getpid()}", "cli")


def _hostname() -> str:
    """Short hostname, stripped of domain and unsafe chars."""
    try:
        host = socket.gethostname()
    except OSError:
        host = "unknown"
    # Strip ``.local`` / domain suffixes and any path-unsafe chars.
    host = host.split(".")[0]
    return "".join(c if c.isalnum() or c == "-" else "-" for c in host) or "unknown"
