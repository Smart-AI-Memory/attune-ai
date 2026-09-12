"""PreToolUse hook: refuse a ``git push`` of shipped code with no CHANGELOG entry.

The bug class (retro 2026-09-11, item 6): four ``src/``-touching PRs in
one evening each cost a red round-trip on the CI ``changelog-entry`` gate
(``.github/scripts/changelog_gate.py``) because the CHANGELOG entry was
written AFTER the PR was opened. The gate is right to fail them; this
guard asks the same question at push time, in the agent session, where
the fix is one more commit instead of a CI cycle.

The check is mechanical and mirrors the CI gate. For each local ref the
push ships (``git push origin feat/y`` ships ``feat/y`` whatever HEAD is;
``src:dst`` ships ``src``; a bare push or one with no refspec ships HEAD)
the range is ``git merge-base origin/main <ref>`` .. ``<ref>``; if any
path changed in that range starts with a shipped prefix and
``CHANGELOG.md`` is not among the changed paths, the push is refused.

What is NOT blocked, deliberately:
- Any command that is not a ``git push``.
- A range that touches nothing under the shipped prefixes (docs, tests,
  tooling, CI).
- A range that already changes ``CHANGELOG.md``.
- A deletion (``:dst`` refspec, ``--delete``): nothing is shipped.
- Anything when ``origin/main`` is unknown, a pushed ref does not
  resolve, or git cannot be read (fail open, one stderr line — a hook
  bug must never block work). The range is read from the session's cwd;
  a ``-C <dir>`` on the push is not followed, and ``--all`` / ``--tags``
  with no refspec are judged as HEAD.

Escape hatch: ``ATTUNE_ALLOW_NO_CHANGELOG=1`` for an internal-only
change — as a leading assignment on the push command itself
(``ATTUNE_ALLOW_NO_CHANGELOG=1 git push ...``, read from the command
text, since the hook process never inherits it) or exported in the
session that launched Claude Code. Apply the ``no-changelog`` label
after opening the PR — that label is the declaration the CI gate
accepts.

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (stderr printed to user)

Metrics: one line per fire in ~/.attune/enforcement-metrics.jsonl, the
same ledger the other guards use.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirty_switch_guard import (  # noqa: E402  (sibling hook script, shared tokenizer)
    _git_args,
    _is_git,
    env_prefix,
    git_invocations,  # noqa: F401  (re-exported: the tests classify pushes through it)
    shell_invocations,
)

ENFORCEMENT_NAME = "changelog-entry-guard"
METRICS_LOG = Path.home() / ".attune" / "enforcement-metrics.jsonl"
ALLOW_ENV = "ATTUNE_ALLOW_NO_CHANGELOG"

#: Mirrors ``SHIPPED_PREFIXES`` in ``.github/scripts/changelog_gate.py``,
#: the CI ``changelog-entry`` gate this guard front-runs. A drift test in
#: tests/unit/hooks/test_changelog_entry_guard.py pins the two equal.
SHIPPED_PREFIXES: tuple[str, ...] = ("src/", "attune_redis/")

#: The file an entry must land in, and the label that declares "none needed".
CHANGELOG = "CHANGELOG.md"
OPT_OUT_LABEL = "no-changelog"

#: Git global options that consume the next token as their value.
_GLOBAL_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}

#: ``git push`` options that consume the next token (so it is not a refspec).
_PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


def _log_metric(outcome: str, detail: str | None = None) -> None:
    """Append one best-effort record to the enforcement metrics log."""
    try:
        METRICS_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "enforcement": ENFORCEMENT_NAME,
            "outcome": outcome,
            "detail": detail,
        }
        with METRICS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        # INTENTIONAL: metrics are best-effort; never block on them.
        pass


def _subcommand_index(args: list[str]) -> int:
    """Index of the git subcommand, past ``-C <dir>``, ``-c k=v``, ``--no-pager`` ..."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in _GLOBAL_OPTS_WITH_VALUE else 1
    return i


def is_push(args: list[str]) -> bool:
    """True if the git arg-list is ``[global opts] push ...``.

    Global options are skipped so the subcommand is matched by position —
    ``git commit -m push`` is not a push.
    """
    i = _subcommand_index(args)
    return args[i : i + 1] == ["push"]


def push_sources(args: list[str]) -> list[str]:
    """The local refs a ``push`` arg-list ships, each judged on its own range.

    ``git push origin feat/y`` ships ``feat/y`` whatever HEAD is (the
    2026-09-12 lane finding: judging HEAD let a push of another branch
    through unread); ``src:dst`` ships ``src``; ``+src`` is ``src``. A
    bare push, ``HEAD``, or a push naming only the remote ships HEAD.
    Deletions (``:dst``, ``--delete``) ship nothing and return ``[]``.
    With ``--repo <remote>`` every positional is a refspec.
    """
    rest = args[_subcommand_index(args) + 1 :]
    positionals: list[str] = []
    delete = False
    remote_named = False
    skip_value = False
    for idx, token in enumerate(rest):
        if skip_value:
            skip_value = False
            continue
        if token == "--":
            positionals.extend(rest[idx + 1 :])
            break
        if token in ("-d", "--delete"):
            delete = True
            continue
        if token == "--repo" or token.startswith("--repo="):
            remote_named = True
        if token in _PUSH_OPTS_WITH_VALUE:
            skip_value = True
            continue
        if token.startswith("-"):
            continue
        positionals.append(token)
    if delete:
        return []
    refspecs = positionals if remote_named else positionals[1:]  # first positional = remote
    if not refspecs:
        return ["HEAD"]
    # A bare ":" is "all matching branches" — ref-expanding, judged as HEAD
    # like --all (third-lane finding, 2026-09-12); not a deletion.
    sources = ["HEAD" if spec == ":" else spec.lstrip("+").partition(":")[0] for spec in refspecs]
    return list(dict.fromkeys(src for src in sources if src))


def push_invocations(command: str) -> list[tuple[dict[str, str], list[str]]]:
    """Every ``git push`` in ``command`` as (leading env assignments, git args)."""
    found: list[tuple[dict[str, str], list[str]]] = []
    for inv in shell_invocations(command):
        if not _is_git(inv):
            continue
        args = _git_args(inv)
        if is_push(args):
            found.append((env_prefix(inv), args))
    return found


def _git(args: list[str], cwd: Path | None = None) -> str | None:
    """Stdout of a git command, or None when it fails for any reason."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def pushed_paths(cwd: Path | None = None, ref: str = "HEAD") -> list[str] | None:
    """Paths changed from the ``origin/main`` merge base to ``ref``, or None if unknown."""
    base = _git(["merge-base", "origin/main", ref], cwd)
    if base is None:
        return None
    diff = _git(["diff", "--name-only", base.strip(), ref], cwd)
    if diff is None:
        return None
    return [line for line in diff.splitlines() if line]


def block_message(shipped: list[str]) -> str:
    """The refusal text: the shipped paths, and the two ways forward."""
    shown = shipped[:8]
    listing = "\n".join(f"    {p}" for p in shown)
    if len(shipped) > len(shown):
        listing += f"\n    ... and {len(shipped) - len(shown)} more"
    return (
        f"[{ENFORCEMENT_NAME}] refusing: this push ships code with no "
        f"{CHANGELOG} change in the pushed range, so the CI `changelog-entry` "
        "gate would fail the PR.\n"
        f"  Shipped paths:\n{listing}\n\n"
        "  Two exits:\n"
        f"    1. Add an entry under `## [Unreleased]` in {CHANGELOG}, inside the "
        "EXISTING `### Added` / `### Changed` / `### Fixed` section for its "
        "kind (never a second one), commit, and push again.\n"
        f"    2. Internal-only change: {ALLOW_ENV}=1 <push command> (a leading "
        "assignment on the push command itself) for this push, then apply the "
        f"`{OPT_OUT_LABEL}` label after opening the PR."
    )


def _unexcused_pushes(pushes: list[tuple[dict[str, str], list[str]]]) -> list[list[str]]:
    """The pushes the escape hatch does not cover (exported, or on that push's own prefix)."""
    exported = os.environ.get(ALLOW_ENV) == "1"
    return [args for prefix, args in pushes if not (exported or prefix.get(ALLOW_ENV) == "1")]


def judge_refs(refs: list[str]) -> tuple[list[str], list[str]]:
    """Offending shipped paths and unreadable refs, each ref judged on its own range.

    An unreadable ref is reported, not decisive: the refs that could be read
    still decide (second-lane finding, 2026-09-12 — returning early on the
    unknown ref let an already-found offender through).
    """
    offending: list[str] = []
    unreadable: list[str] = []
    for ref in refs:
        paths = pushed_paths(ref=ref)
        if paths is None:
            unreadable.append(ref)
            continue
        shipped = [p for p in paths if p.startswith(SHIPPED_PREFIXES)]
        if shipped and CHANGELOG not in paths:
            offending.extend(shipped if ref == "HEAD" else [f"{p}  (ref {ref})" for p in shipped])
    return offending, unreadable


def main(context: dict[str, Any]) -> int:
    """Block a push of shipped code with no CHANGELOG entry; 0 allow, 2 block."""
    if context.get("tool_name") != "Bash":
        return 0
    command = (context.get("tool_input") or {}).get("command", "")
    pushes = push_invocations(command) if command else []
    if not pushes:
        return 0
    judged = _unexcused_pushes(pushes)
    if not judged:
        _log_metric("allowed", "escape hatch set")
        return 0
    refs = list(dict.fromkeys(ref for args in judged for ref in push_sources(args)))
    if not refs:
        _log_metric("allowed", "deletion only")
        return 0

    offending, unreadable = judge_refs(refs)
    if unreadable:
        print(
            f"[{ENFORCEMENT_NAME}] cannot read the push range for {', '.join(unreadable)} "
            "(no origin/main, unknown ref, or not a git tree) — skipping that ref",
            file=sys.stderr,
        )
        _log_metric("unknown", f"push range unreadable for {', '.join(unreadable)}")
    if not offending:
        if len(unreadable) < len(refs):
            _log_metric("allowed", f"{len(refs) - len(unreadable)} ref(s) judged")
        return 0

    print(block_message(offending), file=sys.stderr)
    _log_metric("fired", f"{len(offending)} shipped path(s), no {CHANGELOG}")
    return 2


def _read_stdin_context() -> dict[str, Any]:
    """Parse the hook context from stdin; empty dict when unavailable."""
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    ctx = _read_stdin_context()
    if not ctx:
        sys.exit(0)
    try:
        sys.exit(main(ctx))
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a hook bug must never block real work.
        print(
            f"[{ENFORCEMENT_NAME}] hook error (allowing): {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(0)
