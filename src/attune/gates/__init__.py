"""Collaboration gates — productized human↔agent guardrails.

The spend gate enforces a budget-envelope confirm before the first
billable workflow call of a session. See
``docs/specs/collaboration-gates/`` for the design.

Submodules are imported directly (``from attune.gates.envelope
import Envelope``) to keep the package import dependency-light —
the envelope module is pure stdlib.
"""

from __future__ import annotations

from attune.gates.envelope import (
    DEFAULT_TTL_SECONDS,
    Envelope,
    load_envelope,
    load_or_new,
    save_envelope,
)

__all__ = [
    "DEFAULT_TTL_SECONDS",
    "Envelope",
    "load_envelope",
    "load_or_new",
    "save_envelope",
]
