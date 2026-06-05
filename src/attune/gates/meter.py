"""Active-meter resolution for the spend gate.

Resolves whether the user is on the dollar meter (Anthropic API,
pay-per-token) or the subscription meter (usage quota / rolling
window), and produces the human framing string the confirm surface
shows. This keeps the gate honest per ``decisions.md`` D3/D8: a
subscription user never sees a misleading ``$0`` dollar figure
(``feedback_workflow_output`` — "cost figures don't apply,
subscription not API").

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass

from attune.models.auth_strategy import AuthMode, AuthStrategy

# Public mode tokens — also stored in the envelope's ``meter`` field.
METER_API = "api"
METER_SUBSCRIPTION = "subscription"


@dataclass(frozen=True)
class Meter:
    """The user's active billing meter and how to frame a spend."""

    mode: str  # "api" | "subscription"

    @property
    def is_dollars(self) -> bool:
        """True when spend is denominated in dollars (API mode)."""
        return self.mode == METER_API

    def framing(self, estimate_usd: float) -> str:
        """Frame a spend estimate in the user's actual meter.

        API mode shows the dollar band; subscription mode shows
        usage-headroom framing with no dollar figure — never a
        misleading ``$0`` (R5 / D8).

        Args:
            estimate_usd: The run's estimated dollar ceiling. Used
                only in API mode; ignored in subscription mode.

        Returns:
            A one-line framing string for the confirm surface.
        """
        if self.is_dollars:
            return (
                f"≈ up to ${estimate_usd:.2f} this session window "
                "— counts against your Anthropic API spend."
            )
        return (
            "uses your subscription quota (no per-call charge) "
            "— counts against your Anthropic usage window."
        )


def resolve(
    strategy: AuthStrategy | None = None,
    *,
    module_lines: int = 0,
) -> Meter:
    """Resolve the active meter from the user's auth strategy.

    Reads ``AuthStrategy`` -> ``AuthMode`` (D8). ``AUTO`` is resolved
    to a concrete mode via ``get_recommended_mode``, which never
    returns ``AUTO``. ``module_lines`` lets a caller that knows the
    target size refine an ``AUTO`` decision; the gate's default (0)
    resolves ``AUTO`` the same way a small run would.

    Args:
        strategy: Auth strategy to read; loaded from disk when None.
        module_lines: Target size hint for ``AUTO`` resolution.

    Returns:
        The active :class:`Meter`.
    """
    strategy = strategy or AuthStrategy.load()
    mode = strategy.get_recommended_mode(module_lines)
    if mode == AuthMode.SUBSCRIPTION:
        return Meter(mode=METER_SUBSCRIPTION)
    return Meter(mode=METER_API)
