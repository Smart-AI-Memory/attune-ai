"""PreToolUse hook: validate target file path is in the same worktree as the session.

Catches the bare-repo-absolute-path bug class — when an agent
working in a git worktree (e.g. `.claude/worktrees/<slug>/`)
writes to a file via an absolute path that resolves to the
PARENT main checkout (`/Users/.../attune-ai/`), the file
lands in the wrong tree. The session's branch never sees the
change; meanwhile main's working tree silently accumulates
uncommitted edits.

This is the first concrete enforcement under the framework in
[`docs/specs/enforcement-vs-documentation/`](../../../../docs/specs/enforcement-vs-documentation/).
Hit twice in the 2026-05-31 morning session — once writing
spec content, once writing the very CLAUDE.md lesson warning
against it. Meets all three promotion criteria (recurrence ≥2
distinct sessions, cost ≥10 min recovery, mechanical check
available).

Some non-project trees are deliberate Write/Edit targets (e.g. the
curated-memory repo at ``~/.attune/memory`` — a second git tree that
is the R1 deliverable home for
docs/specs/curated-memory-productionization/). Those roots are
allowlisted via ``DEFAULT_ALLOWED_EXTERNAL_ROOTS`` and can be
extended per-machine with the ``ATTUNE_WORKTREE_GUARD_ALLOW`` env
var (``os.pathsep``-separated roots). Everything else stays
default-deny.

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (stderr printed to user)

Metrics: appends one line to ~/.attune/enforcement-metrics.jsonl
per fire so the periodic retirement review can compute hit
rate, false-alarm rate, days-since-last-hit.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENFORCEMENT_NAME = "worktree_path_guard"
METRICS_LOG = Path.home() / ".attune" / "enforcement-metrics.jsonl"

# Roots OUTSIDE any session worktree that are legitimate Write/Edit
# targets. ~/.attune/memory is the curated-memory repo — a deliberate
# second git tree (docs/specs/curated-memory-productionization/, D4).
DEFAULT_ALLOWED_EXTERNAL_ROOTS: tuple[str, ...] = (
    "~/.attune/memory",
    # Sibling project repos (retro 2026-08-12: the attune-forms
    # extraction had to script around the guard for every write into
    # the new repo; attune-verify hit the same wall 2026-06-02).
    # Writes into a DIFFERENT project repo from an attune-ai session
    # are near-always deliberate cross-repo work. ~/attune-ai itself
    # stays deliberately ABSENT: worktree-vs-main-checkout confusion
    # is the accident class this guard exists to catch.
    "~/attune-author",
    "~/attune-docs",
    "~/attune-forms",
    "~/attune-help",
    "~/attune-lite",
    "~/attune-marketing",
    "~/attune-rag",
    "~/attune-verify",
)

# Extend the allowlist without editing code: an os.pathsep-separated
# list of additional allowed root directories.
ALLOWLIST_ENV_VAR = "ATTUNE_WORKTREE_GUARD_ALLOW"


def _allowed_external_roots() -> list[Path]:
    """Return the allowlisted external roots, ``~``-expanded.

    Combines ``DEFAULT_ALLOWED_EXTERNAL_ROOTS`` with any roots in the
    ``ATTUNE_WORKTREE_GUARD_ALLOW`` env var (``os.pathsep``-separated).
    """
    raw = list(DEFAULT_ALLOWED_EXTERNAL_ROOTS)
    raw.extend(os.environ.get(ALLOWLIST_ENV_VAR, "").split(os.pathsep))
    return [Path(entry.strip()).expanduser() for entry in raw if entry.strip()]


def _matched_allowlist_root(target: Path) -> Path | None:
    """Return the allowlisted root containing ``target``, or ``None``.

    Containment is checked on resolved paths so symlinks and ``..``
    segments can't dodge (or spoof) a match, and a sibling like
    ``~/.attune/memory-evil`` never matches ``~/.attune/memory``.
    """
    try:
        resolved = target.resolve()
    except (OSError, RuntimeError):
        return None
    for root in _allowed_external_roots():
        try:
            resolved.relative_to(root.resolve())
        except (ValueError, OSError):
            continue
        return root
    return None


def _git_toplevel(start: Path) -> Path | None:
    """Return the toplevel of the git worktree containing ``start``.

    Returns the worktree's own toplevel (not the main checkout's),
    which is what git reports for any path inside a worktree.
    Returns ``None`` if the path isn't inside any git tree or git
    isn't on PATH.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    line = (result.stdout or "").strip()
    if not line:
        return None
    return Path(line)


def _log_metric(outcome: str, session_root: Path | None, target_root: Path | None) -> None:
    """Append one record to the enforcement metrics log.

    ``outcome`` is one of:

    - ``"fired"``: the hook blocked a wrong-tree write
    - ``"allowed"``: the hook ran and the paths matched (no block)
    - ``"allowlisted"``: the target is under an allowlisted external
      root (deliberate non-project tree; no block)
    - ``"unknown"``: couldn't determine session or target worktree
      (degraded mode; do not block in this case)
    """
    try:
        METRICS_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "enforcement": ENFORCEMENT_NAME,
            "outcome": outcome,
            "session_root": str(session_root) if session_root else None,
            "target_root": str(target_root) if target_root else None,
        }
        with METRICS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        # Metrics are best-effort; never let logging failure block work.
        pass


def main(context: dict[str, Any]) -> int:
    """Validate target path matches the session's worktree.

    Returns the exit code: ``0`` for allow, ``2`` for block.
    """
    tool_name = context.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        return 0

    tool_input = context.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    # Only check absolute paths — relative paths resolve against the
    # session's cwd and don't carry the wrong-tree risk.
    target_path = Path(file_path)
    if not target_path.is_absolute():
        return 0

    # Allowlisted external trees (e.g. the curated-memory repo) are
    # deliberate non-project targets — allow before any git comparison.
    allowed_root = _matched_allowlist_root(target_path)
    if allowed_root is not None:
        _log_metric("allowlisted", None, allowed_root)
        return 0

    # Determine the session's worktree (from cwd at hook invocation).
    session_root = _git_toplevel(Path.cwd())

    # Determine the target file's enclosing worktree. The file may
    # not exist yet (Write creates it); use its parent dir.
    target_parent = target_path.parent if target_path.parent.exists() else None
    if target_parent is None:
        # New file in a non-existent directory — can't validate.
        _log_metric("unknown", session_root, None)
        return 0
    target_root = _git_toplevel(target_parent)

    if session_root is None or target_root is None:
        # Can't determine one side — degrade to allow.
        _log_metric("unknown", session_root, target_root)
        return 0

    if session_root.resolve() == target_root.resolve():
        # Paths match — allow.
        _log_metric("allowed", session_root, target_root)
        return 0

    # Mismatch — block.
    _log_metric("fired", session_root, target_root)
    allow_roots = ", ".join(str(r) for r in _allowed_external_roots())
    msg = (
        f"\n[worktree-path-guard] BLOCKED Write/Edit to {file_path}\n"
        f"  Session worktree:  {session_root}\n"
        f"  Target worktree:   {target_root}\n"
        "  These don't match — the write would land in a different "
        "tree than the one you're working in.\n"
        "  Fix: change the path to use this session's worktree, "
        "or switch your session if you intended the other tree.\n"
        "  Shipping several PRs from one session? Don't create "
        "sibling worktrees — switch branches sequentially in THIS "
        "checkout (branch off origin/main, edit, commit, push, PR, "
        "switch back; the dirty-switch guard permits it while the "
        "tree is clean).\n"
        "  Intentional external tree? Allowlisted roots bypass this "
        f"guard (currently: {allow_roots}).\n"
        f"  Extend via the {ALLOWLIST_ENV_VAR} env var "
        "(os.pathsep-separated roots) or "
        "DEFAULT_ALLOWED_EXTERNAL_ROOTS in worktree_path_guard.py.\n"
        "\n  (See docs/specs/enforcement-vs-documentation/ for "
        "the framework this enforcement runs under.)\n"
    )
    print(msg, file=sys.stderr)
    return 2


def _read_stdin_context() -> dict[str, Any]:
    """Read the Claude Code hook context from stdin."""
    _buf = getattr(sys.stdin, "buffer", None)  # None when tests patch stdin
    raw = _buf.read().decode("utf-8", errors="replace") if _buf else sys.stdin.read()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, RecursionError):
        # RecursionError: deeply-nested JSON overflows the parser; this
        # reader is called BEFORE main()'s crash guard, so it must
        # absorb it here (library-review L4).
        return {}
    return parsed if isinstance(parsed, dict) else {}


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    # The hook MAY be invoked outside Claude Code (smoke tests,
    # local manual runs); in that case stdin is empty and we
    # silently allow.
    ctx = _read_stdin_context()
    if not ctx:
        sys.exit(0)
    try:
        sys.exit(main(ctx))
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a hook bug must never block real work.
        # Surface to stderr but exit 0 so the tool call proceeds.
        print(
            f"[worktree-path-guard] hook error (allowing): " f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(0)
