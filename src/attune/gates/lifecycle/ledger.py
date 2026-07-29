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
    """CHAIR_REQUIRED receipts not yet cited by any ruling.

    Rows are superseded per ``receipt_id`` (later rows win — the
    same discipline :func:`latest_for` applies per gate), so a
    receipt discharged via :func:`discharge` no longer reports as
    unresolved even though its original row remains in the
    append-only history.
    """
    latest: dict[str, GateReceipt] = {}
    for receipt in _rows(path):
        latest[receipt.receipt_id] = receipt  # later rows supersede
    return [r for r in latest.values() if r.state == "CHAIR_REQUIRED" and r.decisions_ref is None]


def discharge(
    receipt_id: str, decisions_ref: str, *, path: Path | None = None
) -> GateReceipt | None:
    """Cite a chair ruling on an existing receipt — append-only.

    Appends a superseding copy of the receipt's latest row with
    ``decisions_ref`` set; the original row is never touched (G1:
    the ledger never deletes). Returns the appended receipt, or
    ``None`` when no row carries ``receipt_id`` (nothing is
    written — an invented discharge must fail loudly at the
    caller, never fabricate history).
    """
    if not decisions_ref.strip():
        raise ValueError("decisions_ref must name the ruling that discharges the receipt")
    target: GateReceipt | None = None
    for receipt in _rows(path):
        if receipt.receipt_id == receipt_id:
            target = receipt  # later rows supersede
    if target is None:
        return None
    cited = GateReceipt(
        gate_id=target.gate_id,
        phase=target.phase,
        target=target.target,
        state=target.state,
        findings=list(target.findings),
        evidence_refs=list(target.evidence_refs),
        proposed_disposition=target.proposed_disposition,
        waived=target.waived,
        receipt_id=target.receipt_id,
        timestamp=target.timestamp,
        decisions_ref=decisions_ref,
    )
    append(cited, path=path)
    return cited


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m attune.gates.lifecycle.ledger discharge <receipt_id> <decisions_ref>``."""
    import argparse

    parser = argparse.ArgumentParser(description="G1 verdict-ledger maintenance (append-only).")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("discharge", help="cite a chair ruling on an existing receipt")
    d.add_argument("receipt_id")
    d.add_argument("decisions_ref", help="e.g. docs/specs/<slug>/decisions.md#<entry>")
    args = parser.parse_args(argv)

    cited = discharge(args.receipt_id, args.decisions_ref)
    if cited is None:
        print(f"no ledger row carries receipt_id {args.receipt_id!r}; nothing written")
        return 1
    print(
        f"discharged {cited.receipt_id} ({cited.target} :: {cited.gate_id}) "
        f"citing {cited.decisions_ref}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
