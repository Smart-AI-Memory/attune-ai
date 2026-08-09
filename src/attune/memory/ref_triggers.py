"""Ref-triggered queue-jump for project-type memories (P2 task 7, ruling D7).

Project memories rot on EVENTS (merges, closed issues, moved paths), not
on the clock — the motivating incident age-ranked LAST on its most
dangerous day. This module is the ratified low-risk cut: a cheap
existence/state check over EXPLICIT typed refs that can only PROMOTE a
memory into the review queue, layered on the age × volatility baseline.

The typed-ref convention (author-declared live dependencies):

- ``file:relative/path.py``  — triggers when the path is missing.
- ``sha:abc1234``            — triggers when local git doesn't know it.
- ``pr:123``                 — triggers when the PR is no longer OPEN.
- ``issue:456``              — triggers when the issue is no longer OPEN.

Bare ``#123`` mentions are deliberately NOT treated: half the corpus
cites already-merged PRs as provenance ("shipped #1979"), and without
state-at-write those would all false-fire. Writing ``pr:123`` is the
author saying "this claim depends on that PR's LIVE state".

Boundaries, per the D7 ruling:

- **Promote-only.** A trigger floats a memory into review; nothing here
  demotes, hides, or auto-certifies (D1 here, D6 of the sibling spec).
- **Fail-open.** ``gh``/``git`` missing, erroring, or timing out means
  NO flag — never a blocked triage.
- **Existence checks only.** If this module ever grows content diffing,
  CUT IT — that engine belongs to ``memory-claim-verification``.
- **Bounded.** At most :data:`MAX_REFS_PER_MEMORY` refs checked per
  memory and :data:`MAX_CHECKED_MEMORIES` memories per triage.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import re
import subprocess  # noqa: S404 — fixed-argv git/gh existence probes, shell=False
from pathlib import Path

logger = logging.getLogger(__name__)

#: Refs checked per memory — a memory listing dozens of refs still costs
#: at most this many subprocess probes.
MAX_REFS_PER_MEMORY = 5

#: Memories ref-checked per triage (the D6 attention budget, applied to
#: probe cost too).
MAX_CHECKED_MEMORIES = 10

#: Seconds per external probe. A hung gh call must not stall the loop.
PROBE_TIMEOUT = 5

_REF_RES: dict[str, re.Pattern[str]] = {
    "file": re.compile(r"\bfile:([\w~][\w./-]*)"),
    "sha": re.compile(r"\bsha:([0-9a-fA-F]{7,40})\b"),
    "pr": re.compile(r"\bpr:#?(\d{1,6})\b"),
    "issue": re.compile(r"\bissue:#?(\d{1,6})\b"),
}


def extract_refs(text: str) -> list[tuple[str, str]]:
    """Pull explicit typed refs from memory text, capped and deduped.

    Args:
        text: The memory's description + body.

    Returns:
        Up to :data:`MAX_REFS_PER_MEMORY` ``(kind, value)`` pairs in
        first-appearance order.
    """
    seen: list[tuple[str, str]] = []
    for kind, pattern in _REF_RES.items():
        for match in pattern.finditer(text):
            ref = (kind, match.group(1))
            if ref not in seen:
                seen.append(ref)
    return seen[:MAX_REFS_PER_MEMORY]


def _run(argv: list[str], runner=subprocess.run) -> subprocess.CompletedProcess | None:
    """Run a probe; None on ANY launch/timeout failure (fail-open)."""
    try:
        return runner(  # noqa: S603 — fixed argv from _REF_RES matches
            argv, capture_output=True, text=True, timeout=PROBE_TIMEOUT
        )
    except (OSError, subprocess.SubprocessError):
        return None


def check_ref(
    kind: str, value: str, repo_root: Path | None = None, runner=subprocess.run
) -> str | None:
    """Existence/state-check one typed ref. Reason string when triggered.

    Args:
        kind: One of ``file`` / ``sha`` / ``pr`` / ``issue``.
        value: The ref value (path, sha, or number).
        repo_root: Repo the refs are relative to; defaults to the cwd.
        runner: Injectable subprocess runner (tests).

    Returns:
        A human-readable trigger reason, or None (ref holds / unverifiable).
    """
    root = repo_root or Path.cwd()
    if kind == "file":
        candidate = (root / value).resolve()
        # A ref escaping the repo root is unverifiable, not a trigger.
        if not str(candidate).startswith(str(root.resolve())):
            return None
        return None if candidate.exists() else f"file:{value} no longer exists"
    if kind == "sha":
        result = _run(["git", "-C", str(root), "cat-file", "-e", f"{value}^{{commit}}"], runner)
        if result is None:
            return None
        return None if result.returncode == 0 else f"sha:{value} not in local git"
    if kind in {"pr", "issue"}:
        result = _run(["gh", kind, "view", value, "--json", "state"], runner)
        if result is None or result.returncode != 0:
            return None  # gh absent, unauthenticated, or wrong repo — fail open
        try:
            state = str(json.loads(result.stdout).get("state", "")).upper()
        except (json.JSONDecodeError, ValueError):
            return None
        return None if state in {"OPEN", ""} else f"{kind}:{value} is {state}"
    return None


def queue_jump_reasons(mem, repo_root: Path | None = None, runner=subprocess.run) -> list[str]:
    """All trigger reasons for one memory. Empty for non-project types.

    Args:
        mem: A ``CuratedMemory``.
        repo_root: Repo the refs are relative to; defaults to the cwd.
        runner: Injectable subprocess runner (tests).

    Returns:
        Trigger reasons; an empty list means no queue-jump.
    """
    if mem.mem_type != "project":
        return []
    text = f"{mem.description or ''}\n"
    try:
        text += mem.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        pass  # description alone still carries explicit refs when present
    reasons = []
    for kind, value in extract_refs(text):
        reason = check_ref(kind, value, repo_root=repo_root, runner=runner)
        if reason:
            reasons.append(reason)
    return reasons
