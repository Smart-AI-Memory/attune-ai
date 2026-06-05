"""Spend-gate core — compose the envelope and the meter into a decision.

``evaluate_spend_gate`` is the pure decision the spend gate rests on:
it reads the persisted session envelope (T1) and the active billing
meter (T2) and returns a :class:`GateDecision` of ``proceed`` |
``confirm`` | ``block``. It performs **no TTY I/O and makes no
billable call** — the surface (CLI in v1) owns the confirm prompt and
passes interactivity in (D9, D10). This keeps the core testable
without a terminal and lets the dashboard / MCP layers reuse it later.

Off switch (R6, heuristic-free): ``ATTUNE_SPEND_GATE=off`` or
``ATTUNE_MAX_BUDGET_USD=0`` (the latter makes ``get_max_budget_usd``
return ``None``) short-circuits to ``proceed``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from attune.gates.envelope import Envelope, load_or_new
from attune.gates.meter import Meter, resolve
from attune.models.auth_strategy import AuthStrategy
from attune.workflows.agent_sdk_adapter import get_max_budget_usd

# Decision actions.
ACTION_PROCEED = "proceed"
ACTION_CONFIRM = "confirm"
ACTION_BLOCK = "block"

_OFF_VALUES = {"off", "0", "false", "no"}
_ON_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GateDecision:
    """The spend gate's verdict for one run.

    The surface presents ``framing`` + the estimate and, on
    ``confirm``, owns the yes/no prompt; on ``block`` it prints the
    env-override hint; on ``proceed`` it runs the workflow. ``envelope``
    is the (possibly fresh) state the surface persists once authorized.
    """

    action: str  # "proceed" | "confirm" | "block"
    estimate_usd: float
    framing: str
    envelope: Envelope
    reason: str
    breach_usd: float = 0.0


def _spend_gate_off() -> bool:
    """True when ``ATTUNE_SPEND_GATE`` explicitly disables the gate."""
    raw = os.environ.get("ATTUNE_SPEND_GATE")
    return raw is not None and raw.strip().lower() in _OFF_VALUES


def _pre_authorized() -> bool:
    """True when ``ATTUNE_SPEND_GATE_AUTHORIZED`` opts a context in (D10)."""
    raw = os.environ.get("ATTUNE_SPEND_GATE_AUTHORIZED")
    return raw is not None and raw.strip().lower() in _ON_VALUES


def evaluate_spend_gate(
    workflow_name: str,
    depth: str = "standard",
    *,
    interactive: bool = True,
    now: float | None = None,
    strategy: AuthStrategy | None = None,
    envelope_path: Path | None = None,
) -> GateDecision:
    """Decide whether a billable run may proceed, needs a confirm, or is blocked.

    Pure logic: reads the persisted envelope and the active meter,
    returns a :class:`GateDecision`. The surface owns all I/O.

    Args:
        workflow_name: The workflow about to run (for the reason text).
        depth: Analysis depth — drives the estimate band via
            ``get_max_budget_usd`` (D7).
        interactive: Whether the surface can prompt. ``False`` (no TTY)
            blocks a first paid call absent pre-authorization (D10).
        now: Injectable epoch clock for window logic; ``time.time()``
            when None.
        strategy: Auth strategy for meter resolution; loaded when None.
        envelope_path: Override the envelope file (tests pass tmp_path).

    Returns:
        The :class:`GateDecision`.
    """
    now = time.time() if now is None else now
    meter: Meter = resolve(strategy)

    # Off switch (R6) — heuristic-free. get_max_budget_usd returns None
    # exactly when ATTUNE_MAX_BUDGET_USD=0, the existing cap-disable.
    cap = get_max_budget_usd(depth)
    if _spend_gate_off() or cap is None:
        env = load_or_new(now, envelope_path, cap_usd=0.0, meter=meter.mode)
        return GateDecision(
            action=ACTION_PROCEED,
            estimate_usd=0.0,
            framing=meter.framing(0.0),
            envelope=env,
            reason="spend gate disabled",
        )

    estimate = cap
    env = load_or_new(now, envelope_path, cap_usd=estimate, meter=meter.mode)
    framing = meter.framing(estimate)
    authorized = env.authorized or _pre_authorized()

    if not authorized:
        if interactive:
            return GateDecision(
                action=ACTION_CONFIRM,
                estimate_usd=estimate,
                framing=framing,
                envelope=env,
                reason=f"first paid run of this window for '{workflow_name}'",
            )
        return GateDecision(
            action=ACTION_BLOCK,
            estimate_usd=estimate,
            framing=framing,
            envelope=env,
            reason=(
                "non-interactive run with no prior authorization — set "
                "ATTUNE_SPEND_GATE_AUTHORIZED=1 to allow"
            ),
        )

    # Authorized — re-gate only once the window's budget is actually
    # used up (cumulative spend >= cap), not pre-emptively on the next
    # run's worst-case estimate. Pre-emptive checking would re-prompt
    # after the very first run when the cap equals one run's budget
    # band, breaking the "later runs won't re-prompt" promise; per-run
    # spend is bounded separately by the ATTUNE_MAX_BUDGET_USD SDK cap.
    if env.is_exhausted:
        breach = env.spent_usd - env.cap_usd
        if interactive:
            return GateDecision(
                action=ACTION_CONFIRM,
                estimate_usd=estimate,
                framing=framing,
                envelope=env,
                reason="this session's spend window is used up",
                breach_usd=breach,
            )
        return GateDecision(
            action=ACTION_BLOCK,
            estimate_usd=estimate,
            framing=framing,
            envelope=env,
            reason="non-interactive run: session spend window is used up",
            breach_usd=breach,
        )

    return GateDecision(
        action=ACTION_PROCEED,
        estimate_usd=estimate,
        framing=framing,
        envelope=env,
        reason="within the authorized session envelope",
    )
