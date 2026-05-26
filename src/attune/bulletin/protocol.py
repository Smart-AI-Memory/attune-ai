"""Bulletin protocol — data model and backend interface.

See docs/specs/multi-actor-bulletin/requirements.md for the spec.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal, Protocol

ActorKind = Literal[
    "claude-code-session",
    "cli",
    "dashboard",
    "scheduled",
    "attune-rec",
    "mcp",
]

Status = Literal["running", "completed", "failed", "cancelled"]


def _utcnow_iso() -> str:
    """ISO 8601 UTC timestamp, timezone-aware."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BulletinEntry:
    """One actor's report of one in-flight or terminal workflow run.

    The bulletin is keyed by ``run_id``. Multiple entries with the same
    ``run_id`` represent the same run at different points in time — the
    newest (by ``last_heartbeat``) wins on read.
    """

    actor_id: str
    actor_kind: ActorKind
    workflow: str
    run_id: str
    started_at: str = field(default_factory=_utcnow_iso)
    last_heartbeat: str = field(default_factory=_utcnow_iso)
    current_status: Status = "running"
    scope: str | None = None
    hostname: str | None = None

    def to_dict(self) -> dict:
        """Serialize for JSON line append."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> BulletinEntry:
        """Deserialize from a parsed JSON line.

        Unknown keys are dropped silently to keep forward-compatibility
        with newer-format entries written by a different actor.
        """
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def is_terminal(self) -> bool:
        """True if this entry represents a finished run."""
        return self.current_status in ("completed", "failed", "cancelled")


class BulletinBackend(Protocol):
    """Backend interface — file, Redis Streams, or future AMS-backed."""

    def append(self, entry: BulletinEntry) -> None:
        """Record an entry (start, heartbeat, or finish)."""
        ...

    def read_active(self, *, stale_after_seconds: float = 90.0) -> list[BulletinEntry]:
        """Return current non-stale, non-terminal entries.

        Dedupe by ``run_id``, keeping the newest by ``last_heartbeat``.
        Drop entries whose latest heartbeat is older than
        ``stale_after_seconds`` — they represent actors that have
        crashed or gone away without writing a terminal entry.
        """
        ...
