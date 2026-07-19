"""Durable accept/decline decision state (pipeline-learner RR-6).

The learner proposes; the chair disposes. Decisions persist to a named
ledger — an authorized, NON-artifact write, distinct from the
pipeline-artifact write (RR-7) and explicitly permitted. Re-runs are
idempotent: accepted or declined fingerprints are not re-proposed; a
declined candidate reopens only when its support has grown by at least
``REOPEN_DELTA`` since the decline (the stated delta).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .mining import Candidate

logger = logging.getLogger(__name__)

#: A declined candidate reopens only when support has grown by ≥ this
#: many co-occurrences since the decline (RR-6 "stated delta").
REOPEN_DELTA = 3

_VALID_DECISIONS = ("accepted", "declined")


def ledger_path() -> Path:
    """`<ATTUNE_HOME|~/.attune>/ops/pipeline_learner/decisions.jsonl`."""
    home = os.environ.get("ATTUNE_HOME")
    attune_dir = Path(home).expanduser() if home else Path.home() / ".attune"
    return attune_dir / "ops" / "pipeline_learner" / "decisions.jsonl"


@dataclass(frozen=True)
class Decision:
    """One chair ruling on a candidate fingerprint."""

    fingerprint: str
    decision: str  # "accepted" | "declined"
    support_at_decision: int
    decided_at: str  # ISO timestamp


def record_decision(
    fingerprint: str,
    decision: str,
    *,
    support: int,
    path: Path | None = None,
) -> Decision:
    """Append one decision to the ledger (the permitted non-artifact write)."""
    if decision not in _VALID_DECISIONS:
        raise ValueError(f"decision must be one of {_VALID_DECISIONS}, got {decision!r}")
    entry = Decision(
        fingerprint=fingerprint,
        decision=decision,
        support_at_decision=support,
        decided_at=datetime.now(timezone.utc).isoformat(),
    )
    dest = path or ledger_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry.__dict__) + "\n")
    return entry


def load_decisions(path: Path | None = None) -> dict[str, Decision]:
    """Latest decision per fingerprint (later lines supersede earlier)."""
    src = path or ledger_path()
    out: dict[str, Decision] = {}
    if not src.is_file():
        return out
    try:
        lines = src.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("pipeline_learner: unreadable ledger %s: %s", src, exc)
        return out
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            entry = Decision(
                fingerprint=str(data["fingerprint"]),
                decision=str(data["decision"]),
                support_at_decision=int(data["support_at_decision"]),
                decided_at=str(data["decided_at"]),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning("pipeline_learner: skipping malformed ledger line")
            continue
        out[entry.fingerprint] = entry
    return out


def filter_proposable(
    candidates: list[Candidate],
    decisions: dict[str, Decision],
    *,
    reopen_delta: int = REOPEN_DELTA,
) -> list[Candidate]:
    """Drop already-ruled candidates (RR-6 idempotent re-runs).

    Accepted: never re-proposed. Declined: re-proposed only when
    support ≥ support-at-decline + ``reopen_delta``.
    """
    out: list[Candidate] = []
    for cand in candidates:
        ruling = decisions.get(cand.fingerprint())
        if ruling is None:
            out.append(cand)
        elif (
            ruling.decision == "declined"
            and cand.support >= ruling.support_at_decision + reopen_delta
        ):
            out.append(cand)
    return out
