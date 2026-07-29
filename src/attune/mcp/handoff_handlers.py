"""MCP handlers for the cross-provider session handoff tools.

Thin async wrappers over :mod:`attune.handoff` — all behavior
(git-derived truth, caps, drift matrix) lives in the core module.
The wrappers own the ``voice_summary`` phrasing: the core functions
are voice-free, and without a handler-supplied summary the shared
voice layer stamps the generic recall greeting over every response
(same class as the session_memory_* fix, #1684).
Spec: docs/specs/cross-provider-session-handoff/ (T2).
"""

from __future__ import annotations

from typing import Any

from attune.handoff import handoff_create, handoff_resume


def _plural(count: int) -> str:
    """Return "s" for non-singular counts (voice_summary phrasing)."""
    return "" if count == 1 else "s"


class HandoffHandlersMixin:
    """Dispatch-table handlers for ``handoff_create``/``handoff_resume``."""

    _workspace_root: str

    async def _handle_handoff_create(self, args: dict[str, Any]) -> dict[str, Any]:
        result = handoff_create(
            self._workspace_root,
            goal=str(args.get("goal", "")),
            acceptance_criteria=str(args.get("acceptance_criteria", "")),
            scope_assumptions=str(args.get("scope_assumptions", "")),
            current_state=str(args.get("current_state", "")),
            next_action=str(args.get("next_action", "")),
            verification=args.get("verification"),
            provider=str(args.get("provider", "unspecified")),
        )
        if result.get("ok"):
            result["voice_summary"] = f"Wrote the handoff packet for {result['slug']}."
        else:
            reason = result.get("reason", "unknown")
            result["voice_summary"] = f"Couldn't write the handoff packet ({reason})."
        return result

    async def _handle_handoff_resume(self, args: dict[str, Any]) -> dict[str, Any]:
        slug = args.get("slug")
        result = handoff_resume(
            self._workspace_root,
            slug=str(slug) if slug is not None else None,
        )
        if result.get("ok"):
            count = len(result.get("warnings", []))
            memory = result.get("memory", {})
            memory_status = (
                memory.get("status", "skipped") if isinstance(memory, dict) else "skipped"
            )
            result["voice_summary"] = (
                f"Verified the {result['slug']} handoff packet — "
                f"{count} warning{_plural(count)}, memory {memory_status}."
            )
        else:
            reason = result.get("reason", "unknown")
            result["voice_summary"] = f"Couldn't resume the handoff ({reason})."
        return result
