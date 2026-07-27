"""MCP handlers for the cross-provider session handoff tools.

Thin async wrappers over :mod:`attune.handoff` — all behavior
(git-derived truth, caps, drift matrix) lives in the core module.
Spec: docs/specs/cross-provider-session-handoff/ (T2).
"""

from __future__ import annotations

from typing import Any

from attune.handoff import handoff_create, handoff_resume


class HandoffHandlersMixin:
    """Dispatch-table handlers for ``handoff_create``/``handoff_resume``."""

    _workspace_root: str

    async def _handle_handoff_create(self, args: dict[str, Any]) -> dict[str, Any]:
        return handoff_create(
            self._workspace_root,
            goal=str(args.get("goal", "")),
            acceptance_criteria=str(args.get("acceptance_criteria", "")),
            scope_assumptions=str(args.get("scope_assumptions", "")),
            current_state=str(args.get("current_state", "")),
            next_action=str(args.get("next_action", "")),
            verification=args.get("verification"),
            provider=str(args.get("provider", "unspecified")),
        )

    async def _handle_handoff_resume(self, args: dict[str, Any]) -> dict[str, Any]:
        slug = args.get("slug")
        return handoff_resume(
            self._workspace_root,
            slug=str(slug) if slug is not None else None,
        )
