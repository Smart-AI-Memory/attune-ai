"""Collaboration inbox data — read-only, action-required first.

Roundtable-ruled (q-ops-memory-multi-llm-pages-001, issue #1613):
ONE page at minimum scope. Three sources, each degrading
independently — the page must render whatever subset is reachable:

- board threads pending promotion (Redis, TTL countdown);
- handoff packets whose branch is gone or merged (files + read-only
  git);
- cross-review ledger rows still ``not-triaged`` (spec receipts
  file).

The inbox never mutates anything and owns no state: promotion is
in-session by design (R4) — this surface displays, deep-links, and
names the command.
"""

from __future__ import annotations

import json
import logging
import subprocess  # nosec B404 — fixed argv, read-only git, never shell=True
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

THREAD_PREFIX = "attune:roundtable:thread:"
_META_SUFFIX = ":meta"
_SCAN_COUNT = 500
_GIT_TIMEOUT_SECONDS = 10.0

#: Ledger row marker in docs/specs/cross-review/receipts.md.
_NOT_TRIAGED = "| not-triaged |"

_LEDGER_PATH = Path("docs") / "specs" / "cross-review" / "receipts.md"
_HANDOFFS_DIR = Path("docs") / "handoffs"


@dataclass
class ThreadRow:
    """One pending deliberation thread."""

    thread: str
    messages: int
    ttl_hours: float | None
    status: str


@dataclass
class HandoffRow:
    """One handoff packet needing attention."""

    slug: str
    branch: str
    reason: str


@dataclass
class CollabInbox:
    """Everything the inbox renders; sources degrade independently."""

    board_reachable: bool = False
    threads: list[ThreadRow] = field(default_factory=list)
    stale_handoffs: list[HandoffRow] = field(default_factory=list)
    untriaged_reviews: int = 0

    @property
    def action_count(self) -> int:
        return len(self.threads) + len(self.stale_handoffs) + (1 if self.untriaged_reviews else 0)


def _connect(url: str | None = None) -> Any | None:
    try:
        import redis

        client = redis.Redis.from_url(url or "redis://127.0.0.1:6379/0", decode_responses=True)
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        # INTENTIONAL: board absence degrades, never errors.
        return None


def _pending_threads(client: Any) -> list[ThreadRow]:
    rows: list[ThreadRow] = []
    for key in client.scan_iter(match=THREAD_PREFIX + "*", count=_SCAN_COUNT):
        name = str(key)
        if name.endswith(_META_SUFFIX):
            continue
        meta = client.hgetall(name + _META_SUFFIX) or {}
        if meta.get("status") == "promoted":
            continue
        try:
            messages = int(client.llen(name))
        except Exception:  # noqa: BLE001
            # INTENTIONAL: non-list keys in the namespace are skipped.
            continue
        ttl = client.ttl(name)
        rows.append(
            ThreadRow(
                thread=name[len(THREAD_PREFIX) :],
                messages=messages,
                ttl_hours=round(ttl / 3600.0, 1) if ttl and ttl > 0 else None,
                status=meta.get("status", "open"),
            )
        )
    rows.sort(key=lambda r: (r.ttl_hours is None, r.ttl_hours))
    return rows


def _git(repo_root: Path, *args: str) -> str | None:
    """Allowlisted read-only git; None on any failure."""
    if not args or args[0] not in ("rev-parse", "merge-base", "branch"):
        return None
    try:
        proc = subprocess.run(  # nosec B603 — fixed binary, allowlisted args
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def _packet_branch(path: Path) -> str:
    """Branch from packet frontmatter (``branch: "<json>"`` line)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in lines[1:40]:
        if line == "---":
            break
        if line.startswith("branch: "):
            try:
                return str(json.loads(line[len("branch: ") :]))
            except json.JSONDecodeError:
                return ""
    return ""


def _stale_handoffs(project_root: Path) -> list[HandoffRow]:
    rows: list[HandoffRow] = []
    handoffs = project_root / _HANDOFFS_DIR
    if not handoffs.is_dir():
        return rows
    for packet in sorted(handoffs.glob("*.md")):
        branch = _packet_branch(packet)
        if not branch:
            continue
        if _git(project_root, "rev-parse", "--verify", f"refs/heads/{branch}") is None:
            rows.append(HandoffRow(slug=packet.stem, branch=branch, reason="branch missing"))
        elif _git(project_root, "merge-base", "--is-ancestor", branch, "origin/main") is not None:
            rows.append(
                HandoffRow(
                    slug=packet.stem,
                    branch=branch,
                    reason="branch merged — packet should be deleted",
                )
            )
    return rows


def _untriaged_reviews(project_root: Path) -> int:
    ledger = project_root / _LEDGER_PATH
    try:
        text = ledger.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return text.count(_NOT_TRIAGED)


def read_inbox(project_root: Any, url: str | None = None) -> CollabInbox:
    """The whole inbox; each source degrades independently."""
    root = Path(project_root)
    inbox = CollabInbox()
    client = _connect(url)
    if client is not None:
        inbox.board_reachable = True
        try:
            inbox.threads = _pending_threads(client)
        except Exception:  # noqa: BLE001
            logger.warning("collab inbox: thread scan failed", exc_info=True)
            inbox.board_reachable = False
    inbox.stale_handoffs = _stale_handoffs(root)
    inbox.untriaged_reviews = _untriaged_reviews(root)
    return inbox


def read_thread(thread: str, url: str | None = None) -> list[dict[str, Any]] | None:
    """Messages of one thread (read-only), or None when unreadable.

    Guard: the thread id must be a bare id — no whitespace, no key
    separators beyond the id itself (the inbox must never become a
    generic Redis browser).
    """
    if not thread or any(c.isspace() for c in thread) or ":" in thread:
        return None
    client = _connect(url)
    if client is None:
        return None
    try:
        raw = client.lrange(THREAD_PREFIX + thread, 0, 199)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: degradation contract.
        return None
    messages: list[dict[str, Any]] = []
    for item in raw:
        try:
            parsed = json.loads(item)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            messages.append(parsed)
    return messages
