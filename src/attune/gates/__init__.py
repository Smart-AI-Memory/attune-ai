"""Collaboration gates — productized human↔agent guardrails.

The spend gate enforces a budget-envelope confirm before the first
billable workflow call of a session. See
``docs/specs/collaboration-gates/`` for the design.

Submodules are imported directly (``from attune.gates.envelope
import Envelope``) to keep the package import dependency-light —
the envelope module is pure stdlib; the meter module pulls only
``attune.models.auth_strategy``.
"""

from __future__ import annotations

from attune.gates.envelope import (
    DEFAULT_TTL_SECONDS,
    Envelope,
    load_envelope,
    load_or_new,
    save_envelope,
)
from attune.gates.meter import (
    METER_API,
    METER_SUBSCRIPTION,
    Meter,
    resolve,
)
from attune.gates.session_ledger import (
    SessionSpendCapError,
)

# Note: ``spend_gate`` is intentionally NOT eagerly imported here — it
# pulls ``attune.workflows.agent_sdk_adapter`` (the Agent SDK), which
# would weigh down ``import attune.gates``. Consumers import it
# directly: ``from attune.gates.spend_gate import evaluate_spend_gate``.

__all__ = [
    "DEFAULT_TTL_SECONDS",
    "METER_API",
    "METER_SUBSCRIPTION",
    "Envelope",
    "Meter",
    "SessionSpendCapError",
    "load_envelope",
    "load_or_new",
    "resolve",
    "save_envelope",
]
