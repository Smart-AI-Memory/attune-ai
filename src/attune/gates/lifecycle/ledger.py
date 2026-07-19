"""The G1 machine verdict ledger (spec-lifecycle-gates).

Gate receipts persist to an append-only JSONL under the attune home —
NEVER to decisions.md, which stays the human-judgment record (G1).
Resolution mirrors the run-record corpus (``ATTUNE_HOME`` env →
``~/.attune``), so the suite's isolation fixture redirects writes
automatically.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .protocol import GateReceipt

logger = logging.getLogger(__name__)


def ledger_path() -> Path:
    """`<ATTUNE_HOME|~/.attune>/ops/gates/verdicts.jsonl` (G1)."""
    home = os.environ.get("ATTUNE_HOME")
    attune_dir = Path(home).expanduser() if home else Path.home() / ".attune"
    return attune_dir / "ops" / "gates" / "verdicts.jsonl"


def append(receipt: GateReceipt, *, path: Path | None = None) -> Path:
    """Append one receipt to the ledger (append-only; never deletes)."""
    dest = path or ledger_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt.to_dict()) + "\n")
    return dest


def _rows(path: Path | None) -> list[GateReceipt]:
    src = path or ledger_path()
    if not src.is_file():
        return []
    out: list[GateReceipt] = []
    try:
        lines = src.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("gates: unreadable ledger %s: %s", src, exc)
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(GateReceipt.from_dict(json.loads(line)))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning("gates: skipping malformed ledger line")
    return out


def latest_for(target: str, *, path: Path | None = None) -> list[GateReceipt]:
    """The most recent receipt per gate_id for one target."""
    latest: dict[str, GateReceipt] = {}
    for receipt in _rows(path):
        if receipt.target == target:
            latest[receipt.gate_id] = receipt  # later rows supersede
    return list(latest.values())


def unresolved_chair_required(*, path: Path | None = None) -> list[GateReceipt]:
    """CHAIR_REQUIRED receipts not yet cited by any ruling."""
    return [r for r in _rows(path) if r.state == "CHAIR_REQUIRED" and r.decisions_ref is None]
