"""Workflow catalog visibility — the hidden-from-users sets.

Chair-directed 2026-08-24: workflows that demonstrably do not work
(probe registry: docs/specs/workflow-behavioral-validation/registry.md)
are HIDDEN from user-facing catalogs until they work; workflows that
only fail on surfaces unable to supply their required arguments are
hidden from THOSE surfaces alone. Remove an entry when its probe
passes.

Two tiers:

- :data:`HIDDEN_WORKFLOWS` — broken everywhere (deterministic failure
  or no usable output on any surface). Hidden from every catalog: the
  ops dashboard, ``attune workflow list``, the MCP
  ``list_capabilities`` catalog.
- :data:`DASHBOARD_HIDDEN_WORKFLOWS` — work when a caller supplies
  their required arguments (CLI ``--input`` JSON, MCP tool params) but
  are guaranteed error cards from the dashboard's argument-less Run
  button. Hidden from the dashboard only.

Hiding is a PRESENTATION concern only. The registry itself is
untouched: ``get_workflow()`` resolves every name (probes, API
launches, and the ops runner keep working), telemetry keeps counting
historical runs, and the claim-drift count gates read the registry,
not these catalogs.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

#: Broken on every surface — name -> one-line reason (with tracking ref).
HIDDEN_WORKFLOWS: dict[str, str] = {
    "test-gen": "emits no runnable test files (no Write tool wired) — #2213",
    "doc-gen": "deterministic SDK failure (fleet roundtable Sev3) — fix pending",
    "research-synthesis": ("deterministic SDK failure (fleet roundtable Sev6) — fix pending"),
}

#: Unrunnable only from the dashboard's argument-less Run button.
DASHBOARD_HIDDEN_WORKFLOWS: dict[str, str] = {
    "fix": "requires a goal argument the dashboard Run button cannot supply",
    "rag-code-gen": ("requires a query argument the dashboard Run button cannot supply"),
}


def is_hidden(name: str, *, surface: str = "catalog") -> bool:
    """True when ``name`` is hidden on the given surface.

    Args:
        name: Registry workflow name.
        surface: ``"catalog"`` (CLI/MCP — broken-everywhere set only)
            or ``"dashboard"`` (also hides the argument-requiring set).
    """
    if name in HIDDEN_WORKFLOWS:
        return True
    return surface == "dashboard" and name in DASHBOARD_HIDDEN_WORKFLOWS


def visible_entries(
    entries: Iterable[dict[str, Any]], *, surface: str = "catalog"
) -> list[dict[str, Any]]:
    """Filter registry-shaped entry dicts (``{"name": ...}``) to visible ones."""
    return [e for e in entries if not is_hidden(str(e.get("name", "")), surface=surface)]
