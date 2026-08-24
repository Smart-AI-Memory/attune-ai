"""Cross-launcher session spend ledger — hard refusal at the cap.

Spec: ``docs/specs/session-spend-ledger/``. Every billed launcher
(the workflow probe runner, roundtable seat invocations, cross-model
review runs) calls :func:`check` before a billable launch and
:func:`record` after it. Once cumulative spend inside the rolling
session window reaches the cap, :func:`check` raises
:class:`SessionSpendCapError` — a hard refusal, not a warning or a
confirm prompt (14.1.0-retro item 4: "enforceable").

Postures that differ from the spend-gate envelope, deliberately
(decisions.md D4): ``ATTUNE_SESSION_SPEND_CAP_USD=0`` means "no
budget → refuse every billable launch" — never a free first call
(the known budget-latch bug class). Disabling is explicit:
``ATTUNE_SESSION_LEDGER=off`` (recording continues so the audit
trail survives an override).

The ledger file is append-only jsonl (one ``{ts, label, cost_usd}``
line per billed launch): no read-modify-write race can lose a spend
record under concurrent launchers, and undercounting is the failure
mode enforcement can least afford (D3). Like the envelope, the path
is internal (module-constructed or an operator env override), never
LLM-supplied, so it is not run through ``_validate_file_path``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from attune.gates.envelope import DEFAULT_TTL_SECONDS

logger = logging.getLogger(__name__)

#: Default session cap: 20% of the standing $50 budget — one runaway
#: session is bounded to a fifth of the budget while the largest
#: known legitimate session (full probe set, ~$6-8) fits (D2).
DEFAULT_CAP_USD: float = 10.0

#: "Session" = the rolling window this many seconds wide — the same
#: 5-hour clock as the spend-gate envelope (D1).
WINDOW_SECONDS: float = DEFAULT_TTL_SECONDS

_OFF_VALUES = {"off", "0", "false", "no"}


class SessionSpendCapError(RuntimeError):
    """The session spend cap refuses this billable launch."""


def _ledger_path(path: Path | None = None) -> Path:
    """Resolve the ledger file: explicit arg > env override > default."""
    if path is not None:
        return path
    raw = os.environ.get("ATTUNE_SESSION_LEDGER_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".attune" / "telemetry" / "session_spend.jsonl"


def ledger_off() -> bool:
    """True when ``ATTUNE_SESSION_LEDGER`` explicitly disables checking."""
    raw = os.environ.get("ATTUNE_SESSION_LEDGER")
    return raw is not None and raw.strip().lower() in _OFF_VALUES


def get_cap_usd() -> float:
    """The session cap in USD.

    A malformed env value falls back to the DEFAULT cap, never to
    "unlimited" (R7 — degrade toward enforcement). ``0`` and negative
    values pass through: they mean "no budget", which :func:`check`
    refuses (D4).
    """
    raw = os.environ.get("ATTUNE_SESSION_SPEND_CAP_USD", "").strip()
    if not raw:
        return DEFAULT_CAP_USD
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "ATTUNE_SESSION_SPEND_CAP_USD=%r is not a number; using default $%.2f",
            raw,
            DEFAULT_CAP_USD,
        )
        return DEFAULT_CAP_USD


def spent_usd(now: float | None = None, path: Path | None = None) -> float:
    """Cumulative recorded spend inside the current session window.

    A missing file is $0; corrupt lines are skipped and logged — a
    torn write may undercount by one entry, but never blocks work or
    zeroes the whole ledger (R7).
    """
    now = time.time() if now is None else now
    ledger = _ledger_path(path)
    try:
        raw_lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0.0
    total = 0.0
    for line in raw_lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            ts = float(entry["ts"])
            cost = float(entry["cost_usd"])
        except (ValueError, KeyError, TypeError):
            logger.warning("session ledger line unreadable (skipped): %r", line[:120])
            continue
        if now - ts < WINDOW_SECONDS and cost > 0:
            total += cost
    return total


def check(label: str, now: float | None = None, path: Path | None = None) -> float:
    """Refuse a billable launch once the session cap is reached.

    Returns the remaining headroom in USD when the launch may
    proceed. Raises :class:`SessionSpendCapError` when the cap is
    ``<= 0`` (no budget — refuses the FIRST call, R3) or when
    cumulative window spend has reached the cap (R2). A disabled
    ledger (``ATTUNE_SESSION_LEDGER=off``) always proceeds.
    """
    if ledger_off():
        return float("inf")
    cap = get_cap_usd()
    if cap <= 0:
        raise SessionSpendCapError(
            f"session spend ledger refuses {label!r}: cap is "
            f"${cap:.2f} (<= 0 means no budget — no free first call). "
            "Raise ATTUNE_SESSION_SPEND_CAP_USD, or set "
            "ATTUNE_SESSION_LEDGER=off to disable checking."
        )
    spent = spent_usd(now=now, path=path)
    if spent >= cap:
        raise SessionSpendCapError(
            f"session spend ledger refuses {label!r}: "
            f"${spent:.2f} already spent this session (cap ${cap:.2f}, "
            f"rolling {WINDOW_SECONDS / 3600:.0f}h window). Raise "
            "ATTUNE_SESSION_SPEND_CAP_USD, or set "
            "ATTUNE_SESSION_LEDGER=off to disable checking."
        )
    return cap - spent


def record(
    label: str,
    cost_usd: float,
    now: float | None = None,
    path: Path | None = None,
) -> None:
    """Append one billed launch to the ledger.

    Recording never raises past validation: an unwritable ledger is
    logged, not fatal — the launch already happened and refusing to
    return would not un-spend it. Recording also ignores the off
    switch, so the audit trail survives an override (D4).
    """
    if cost_usd < 0:
        raise ValueError("cost_usd must be non-negative")
    now = time.time() if now is None else now
    ledger = _ledger_path(path)
    line = json.dumps({"ts": round(now, 3), "label": label, "cost_usd": round(cost_usd, 6)})
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError as exc:
        logger.warning("session ledger unwritable (spend NOT recorded): %s", exc)


def seat_estimate_usd() -> float:
    """Flat conservative estimate for one billed ``claude`` seat call.

    Seat subprocesses report no cost, so the ledger records this per
    invocation — deliberately above the typical single-reply
    ``claude -p`` cost, so it overcounts rather than undercounts
    (D5). Env override: ``ATTUNE_SEAT_SPEND_ESTIMATE_USD``.
    """
    raw = os.environ.get("ATTUNE_SEAT_SPEND_ESTIMATE_USD", "").strip()
    if not raw:
        return 0.25
    try:
        return max(float(raw), 0.0)
    except ValueError:
        logger.warning("ATTUNE_SEAT_SPEND_ESTIMATE_USD=%r is not a number; using $0.25", raw)
        return 0.25
