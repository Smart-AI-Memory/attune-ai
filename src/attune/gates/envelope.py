"""Persisted, TTL'd session spend envelope for the spend gate.

The envelope is the durable state behind the budget-envelope spend
gate (``docs/specs/collaboration-gates/``). Each ``attune workflow
run`` is a fresh process, so the envelope persists on disk under
``~/.attune/spend_gate/`` keyed by a TTL window aligned to
Anthropic's rolling usage window — so the gate's notion of "this
session" resets on the same clock as the meter it gates against.

Modeled on the ``Budget`` dataclass
(``src/attune/ops/session_summarizer.py``) and its ``cap_usd <= 0``
off-switch latch.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Anthropic's rolling usage window is ~5h; the envelope TTL defaults
# to match so the gate's "session" resets on the same clock as the
# meter it gates against (decisions.md D6).
DEFAULT_TTL_SECONDS: float = 5 * 60 * 60  # 18000


def _default_envelope_path() -> Path:
    """Return the on-disk location of the persisted envelope.

    Mirrors the ``~/.attune/session_stash`` state-file pattern
    (``src/attune/memory/file_stash.py``).
    """
    return Path.home() / ".attune" / "spend_gate" / "envelope.json"


@dataclass
class Envelope:
    """One session's spend envelope.

    The envelope is established (``authorized=True``) by an explicit
    first-run confirm and is then session-durable within its TTL
    window. Runs proceed silently until cumulative ``spent_usd``
    reaches the window budget ``cap_usd``, at which point the window
    is exhausted and the next run re-gates (see :attr:`is_exhausted`).
    """

    window_start: float
    ttl_seconds: float = DEFAULT_TTL_SECONDS
    authorized: bool = False
    cap_usd: float = 0.0
    spent_usd: float = 0.0
    meter: str = "api"

    @classmethod
    def new(
        cls,
        now: float,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        cap_usd: float = 0.0,
        meter: str = "api",
    ) -> Envelope:
        """Create a fresh, unauthorized envelope opening a new window."""
        return cls(
            window_start=now,
            ttl_seconds=ttl_seconds,
            authorized=False,
            cap_usd=cap_usd,
            spent_usd=0.0,
            meter=meter,
        )

    @property
    def disabled(self) -> bool:
        """True when ``cap_usd <= 0`` marks the gate off.

        Mirrors the ``Budget`` ``cap_usd <= 0`` latch — the gate core
        reads a disabled envelope as "proceed" (R6 off switch). A
        disabled envelope is never exhausted.
        """
        return self.cap_usd <= 0

    def is_expired(self, now: float) -> bool:
        """True once the TTL window has elapsed (``now`` is epoch s)."""
        return (now - self.window_start) >= self.ttl_seconds

    @property
    def is_exhausted(self) -> bool:
        """True once cumulative spend has used up the window budget.

        Post-hoc, not pre-emptive: runs proceed silently until actual
        ``spent_usd`` reaches ``cap_usd``, then the window re-gates.
        This is what lets the confirm's "later runs won't re-prompt"
        promise hold — a per-run worst-case check would re-gate after
        the very first run when ``cap_usd`` equals a single run's
        budget band. Per-run spend is still bounded separately by the
        ``ATTUNE_MAX_BUDGET_USD`` SDK cap. A disabled envelope is never
        exhausted; subscription runs report ``$0`` so never exhaust.
        """
        if self.disabled:
            return False
        return self.spent_usd >= self.cap_usd

    def record(self, cost_usd: float) -> None:
        """Add a completed run's actual cost to the ledger."""
        if cost_usd < 0:
            raise ValueError("cost_usd must be non-negative")
        self.spent_usd += cost_usd


def load_envelope(path: Path | None = None) -> Envelope | None:
    """Load the persisted envelope, or ``None`` if missing/corrupt.

    Fail-safe: a missing or unreadable file returns ``None`` so the
    caller opens a fresh window rather than crashing (R7).
    """
    path = path or _default_envelope_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
        return Envelope(
            window_start=float(data["window_start"]),
            ttl_seconds=float(data.get("ttl_seconds", DEFAULT_TTL_SECONDS)),
            authorized=bool(data.get("authorized", False)),
            cap_usd=float(data.get("cap_usd", 0.0)),
            spent_usd=float(data.get("spent_usd", 0.0)),
            meter=str(data.get("meter", "api")),
        )
    except (ValueError, KeyError, TypeError) as e:
        logger.warning(
            "spend-gate envelope unreadable (fail-safe to fresh): %s",
            e,
        )
        return None


def save_envelope(env: Envelope, path: Path | None = None) -> None:
    """Persist the envelope atomically.

    The path is internal (constructed by this module or supplied by
    tests), never user-controlled, so it isn't run through
    ``_validate_file_path`` — doing so would resolve the macOS
    ``/var`` -> ``/private/var`` symlink and desync from the
    caller's load path. Uses ``Path.replace`` for a cross-platform
    atomic rename (Windows ``Path.rename`` fails when the target
    exists).

    The temp file is named by :func:`tempfile.mkstemp` rather than
    derived from the target: two processes saving the same envelope
    would otherwise pick the same ``<name>.tmp`` and one would
    truncate the other's partial write before the rename published
    it (class G1).
    """
    path = path or _default_envelope_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(env), indent=2) + "\n")
        tmp.replace(path)
    finally:
        # A successful replace consumes the temp file, so this only
        # fires on the failure paths — no leftover .tmp either way.
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()


def load_or_new(
    now: float,
    path: Path | None = None,
    *,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    cap_usd: float = 0.0,
    meter: str = "api",
) -> Envelope:
    """Load the live envelope, or a fresh one if missing/corrupt/expired.

    The single entry point the gate core uses: it never has to think
    about expiry or absence — a stale or absent envelope yields a
    fresh, unauthorized window (fail-safe, R7).
    """
    env = load_envelope(path)
    if env is None or env.is_expired(now):
        return Envelope.new(
            now,
            ttl_seconds=ttl_seconds,
            cap_usd=cap_usd,
            meter=meter,
        )
    return env
