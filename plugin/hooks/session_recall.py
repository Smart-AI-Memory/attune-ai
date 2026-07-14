#!/usr/bin/env python
"""SessionStart hook — surface recent cross-session findings at startup.

SessionStart has no query, so recall is recency-driven: the newest
stashed findings for the current project (cwd), via
``attune.memory.session_stash.recent_entries``. Emits a compact
``## Recalled memories`` block to stdout, which Claude Code splices into
the model's initial context.

Quiet by design: no backend, no findings, or the ``compact`` source all
produce no output. Bounded to a small char budget so it never crowds the
opening context. Never raises — a crash must not break the session.

Tunables (env): ``ATTUNE_MEMORY_RECALL`` (set ``0`` to disable),
``ATTUNE_MEMORY_RECALL_TOPK`` (default 5).

Each emission is logged to ``~/.attune/telemetry/memory_events.jsonl``
(size, entry count, surfaced finding ids, a ``surfacing_id`` join key;
see ``_memory_telemetry``) so the layer's token cost is measured, not
modeled, and a later verdict pass can label each surfacing acted-on /
ignored / wrong (memory-recall-eval spec).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import traceback
import uuid
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

try:
    from _memory_telemetry import log_memory_event
except Exception:  # noqa: BLE001 — telemetry is optional, never load-bearing

    def log_memory_event(event: str, session_id: str | None = None, **fields: object) -> None:
        return


_DEFAULT_TOPK = 5
_CONTENT_BUDGET = 1_400  # ~350 tokens of finding text

# --- Task-note reconciliation (stale "PR #N" findings) -------------------
# A stashed note like "CI is re-running on PR #1282" goes stale the moment
# the PR merges — often within hours, far inside any TTL. Reconcile at
# recall time: check each referenced PR's live state (bounded, best-effort)
# and drop+forget notes whose every referent is MERGED/CLOSED.
_PR_REF_RE = re.compile(r"\bPR\s*#(\d+)", re.IGNORECASE)
_MAX_PR_CHECKS = 3  # bound the gh calls per session start
_GH_TIMEOUT_SECONDS = 4.0
_RESOLVED_STATES = {"MERGED", "CLOSED"}


def _enabled() -> bool:
    return os.environ.get("ATTUNE_MEMORY_RECALL", "1").strip() not in {"0", "false", "no"}


def _reconcile_enabled() -> bool:
    return os.environ.get("ATTUNE_MEMORY_RECALL_RECONCILE", "1").strip() not in {
        "0",
        "false",
        "no",
    }


def _pr_refs(content: str) -> list[str]:
    """Extract 'PR #N' referents from a finding's text."""
    return _PR_REF_RE.findall(content or "")


def _pr_state(number: str, cwd: str | None) -> str | None:
    """Live PR state via gh (MERGED/OPEN/CLOSED), or None on any failure."""

    try:
        proc = subprocess.run(  # noqa: S603, S607 — fixed argv, no shell
            ["gh", "pr", "view", number, "--json", "state"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GH_TIMEOUT_SECONDS,
            cwd=cwd or None,
        )
        if proc.returncode != 0:
            return None
        state = json.loads(proc.stdout).get("state")
        return state if isinstance(state, str) else None
    except Exception:  # noqa: BLE001 — gh missing/slow/offline -> keep the note
        return None


def _reconcile(entries: list[dict], cwd: str | None) -> tuple[list[dict], list[str]]:
    """Partition entries into (fresh, stale-ids); best-effort, conservative.

    An entry is stale only when it references at least one PR and EVERY
    referenced PR is definitively MERGED/CLOSED — an unknown state (gh
    missing, timeout, cross-repo number) keeps the note. Checks are
    bounded to :data:`_MAX_PR_CHECKS` unique PR numbers per session start.
    """
    if not _reconcile_enabled():
        return entries, []
    checked: dict[str, str | None] = {}
    fresh: list[dict] = []
    stale_ids: list[str] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        refs = _pr_refs(str(e.get("text") or e.get("content") or ""))
        resolved = bool(refs)
        for n in dict.fromkeys(refs):
            if n not in checked:
                if len(checked) >= _MAX_PR_CHECKS:
                    resolved = False
                    break
                checked[n] = _pr_state(n, cwd)
            if checked[n] not in _RESOLVED_STATES:
                resolved = False
                break
        if resolved:
            # Stale: drop from render either way; forget only when the
            # record carries an id to delete by.
            if e.get("id"):
                stale_ids.append(str(e["id"]))
            continue
        fresh.append(e)
    return fresh, stale_ids


def _forget(ids: list[str]) -> int:
    """Best-effort backend deletion of reconciled-stale findings."""
    if not ids:
        return 0
    try:
        from attune.memory.session_stash import forget_entries

        return forget_entries(ids)
    except Exception:  # noqa: BLE001 — older attune without forget_entries
        return 0


def _type_of(topics: object) -> str:
    """Pull the ``type:X`` marker out of a record's topics (default note)."""
    if isinstance(topics, list):
        for t in topics:
            if isinstance(t, str) and t.startswith("type:"):
                return t[len("type:") :] or "note"
    return "note"


def _format(entries: list[dict]) -> tuple[str, list[str]]:
    """Render the recalled findings as a compact markdown block.

    Returns the block plus one id per rendered finding ("" when the
    record carries none), so the telemetry event can say WHICH findings
    were surfaced, not just how many.
    """
    lines = [
        "## Recalled memories",
        "",
        "Recent findings from this project (most recent first):",
        "",
    ]
    rendered_ids: list[str] = []
    used = 0
    for e in entries:
        if not isinstance(e, dict):
            continue
        content = e.get("text") or e.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        content = content.strip()
        used += len(content)
        if used > _CONTENT_BUDGET:
            break
        lines.append(f"- [{_type_of(e.get('topics'))}] {content}")
        rendered_ids.append(str(e.get("id") or ""))
    lines.append("")
    lines.append("_Pull more with `/recall <topic>`._")
    return "\n".join(lines), rendered_ids


def main() -> int:
    try:
        if not _enabled():
            return 0
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        source = (payload.get("source") or "startup").lower()
        if source == "compact":
            return 0  # post-compact context is handled elsewhere; don't pile on
        cwd = str(payload.get("cwd") or Path.cwd())

        try:
            from attune.memory.session_stash import recent_entries
        except Exception:  # noqa: BLE001 — attune not importable -> silent
            return 0

        try:
            topk = int(os.environ.get("ATTUNE_MEMORY_RECALL_TOPK", _DEFAULT_TOPK))
        except ValueError:
            topk = _DEFAULT_TOPK

        # Health line: a registered upgrade backend (e.g. Redis AMS) that is
        # unreachable means recall is silently degraded and findings stored
        # in that tier are dark. Surfacing this at session start is the fix
        # for the 2026-06-11 incident where AMS was down for a week unnoticed.
        health = ""
        try:
            from attune.memory.session_stash import backend_status

            status = backend_status()
            dark = status.get("unreachable_upgrade")
            if dark:
                health = (
                    f"⚠ cross-session recall degraded: memory backend '{dark}' is "
                    "unreachable — findings stored there are dark until it's back "
                    "(e.g. restart the Agent Memory Server)."
                )
        except Exception:  # noqa: BLE001 — health line is best-effort
            pass

        entries = recent_entries(top_k=topk, cwd=cwd)
        # Drop task notes whose PR referents have since merged/closed —
        # and forget them so they never resurface (task-note expiry).
        entries, stale_ids = _reconcile(entries, cwd)
        forgotten = _forget(stale_ids)
        if not entries:
            if stale_ids:
                # Everything recalled was stale — still record the reconcile.
                log_memory_event(
                    "session_recall",
                    session_id=payload.get("session_id"),
                    entries=0,
                    injected_chars=0,
                    reconciled_stale=len(stale_ids),
                    forgotten=forgotten,
                )
            if health:
                print(health)
            return 0
        block, rendered_ids = _format(entries)
        # Only print if we actually rendered at least one finding line.
        if rendered_ids:
            print(block)
            # finding_ids says WHICH findings were surfaced (id-less
            # records are counted in `entries` but not listed); the
            # surfacing_id is the join key a later verdict pass
            # (acted-on / ignored / wrong) references
            # (memory-recall-eval spec, 2026-07-14).
            log_memory_event(
                "session_recall",
                session_id=payload.get("session_id"),
                surfacing_id=uuid.uuid4().hex[:12],
                entries=len(rendered_ids),
                finding_ids=[i for i in rendered_ids if i],
                injected_chars=len(block),
                reconciled_stale=len(stale_ids),
                forgotten=forgotten,
            )
        if health:
            print(health)
        return 0
    except Exception:  # noqa: BLE001 — SessionStart hook must never crash a session
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
