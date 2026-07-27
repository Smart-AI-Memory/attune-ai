"""Cross-provider session handoff — public API.

``handoff_create`` assembles a packet from real git state (R1);
``handoff_resume`` verifies a packet against the current tree and
returns a report, not a go signal (R2). Pure functions returning
dicts; no MCP imports. Spec:
docs/specs/cross-provider-session-handoff/.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import structlog

from attune.handoff import packet as _packet
from attune.handoff import verify as _verify

logger = structlog.get_logger(__name__)

__all__ = ["handoff_create", "handoff_resume"]

#: R3 memory linkage lands in T3; until then the report says so
#: explicitly rather than omitting the key (stable report shape).
_MEMORY_NOT_WIRED = {"status": "skipped", "reason": "not_implemented"}


def handoff_create(
    repo_root: str | Path = ".",
    *,
    goal: str = "",
    acceptance_criteria: str = "",
    scope_assumptions: str = "",
    current_state: str = "",
    next_action: str = "",
    verification: list[dict[str, str]] | None = None,
    provider: str = "unspecified",
    base_ref: str = "origin/main",
) -> dict[str, Any]:
    """Assemble and write the current branch's handoff packet.

    Git-derived frontmatter comes from git at call time; caller
    prose is recorded verbatim in the body (ASSERTED). Returns
    ``{ok, path, packet}`` or a truthful ``{ok: False, reason}``.
    """
    started = time.monotonic()
    root = Path(repo_root)
    fields = {
        "goal": goal,
        "acceptance_criteria": acceptance_criteria,
        "scope_assumptions": scope_assumptions,
        "current_state": current_state,
        "next_action": next_action,
        "verification": verification,
    }
    rejection = _packet.check_caps(fields)
    if rejection:
        return rejection

    try:
        meta = _verify.snapshot(root, base_ref=base_ref)
    except _verify.GitReadError as exc:
        return {"ok": False, "reason": "git_read_failed", "detail": str(exc)}
    meta["provider"] = provider

    slug = _verify.slugify_branch(meta["branch"] or "detached")
    sections = _packet.assemble_sections(fields)
    result = _packet.write_packet(root, slug, meta, sections)
    logger.info(
        "handoff_create",
        slug=slug,
        ok=result.get("ok"),
        reason=result.get("reason"),
        duration_ms=round((time.monotonic() - started) * 1000),
        memory=_MEMORY_NOT_WIRED["status"],
    )
    if not result.get("ok"):
        return result
    return {
        "ok": True,
        "path": result["path"],
        "slug": slug,
        "packet": {"verified": meta, "asserted": sections},
        "memory": dict(_MEMORY_NOT_WIRED),
    }


def handoff_resume(
    repo_root: str | Path = ".",
    *,
    slug: str | None = None,
) -> dict[str, Any]:
    """Read a packet and verify it against the current tree (R2).

    Report keys in authority order: ``verified`` (git-rechecked),
    ``warnings`` (D3 drift codes, report-only), ``asserted``
    (caller prose, authority-free), ``memory``. Performs no side
    effects: no checkout, no writes, no test runs.
    """
    started = time.monotonic()
    root = Path(repo_root)
    if slug is None:
        try:
            branch = _verify.snapshot(root)["branch"]
        except _verify.GitReadError as exc:
            return {"ok": False, "reason": "git_read_failed", "detail": str(exc)}
        slug = _verify.slugify_branch(branch or "detached")

    try:
        path = _packet.packet_path(root, slug)
    except _packet.PacketError as exc:
        return {"ok": False, "reason": "invalid_slug", "detail": str(exc)}
    if not path.exists():
        return {"ok": False, "reason": "packet_not_found", "path": str(path)}

    try:
        meta, sections = _packet.parse(path.read_text(encoding="utf-8"))
    except (OSError, _packet.PacketError) as exc:
        return {"ok": False, "reason": "packet_unreadable", "detail": str(exc)}

    packet_rel = f"docs/handoffs/{slug}.md"
    warnings = _verify.drift(meta, root, ignore_paths=(packet_rel,))
    logger.info(
        "handoff_resume",
        slug=slug,
        warning_codes=[w["code"] for w in warnings],
        duration_ms=round((time.monotonic() - started) * 1000),
        memory=_MEMORY_NOT_WIRED["status"],
    )
    return {
        "ok": True,
        "slug": slug,
        "path": str(path),
        "verified": meta,
        "warnings": warnings,
        "asserted": sections,
        "memory": dict(_MEMORY_NOT_WIRED),
    }
