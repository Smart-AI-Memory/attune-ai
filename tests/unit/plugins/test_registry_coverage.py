"""Registry-coverage guard: every registered capability has a user surface.

The existing reference-validation tests check the *forward* direction —
that every reference written in a skill/command resolves to real code.
This suite checks the *reverse* direction: that every capability the
code registers (workflow, MCP tool) is actually reachable by a user
through some surface (an MCP tool, or a skill that names it).

This is the gate that would have caught the discovery-sweep gap: a
runnable workflow shipped with no MCP tool and no skill, invisible to
users despite working perfectly.

Intentionally-unsurfaced capabilities are listed in the allowlists
below WITH A REASON. The allowlists double as a living TODO of the
additive-access backlog. A hygiene check fails if an allowlisted item
later gains a surface — forcing the list to shrink as the backlog is
built, rather than rotting into a permanent waiver.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[3] / "plugin"


# ---------------------------------------------------------------------------
# Data collection (once at import time)
# ---------------------------------------------------------------------------


def _skill_bodies() -> dict[str, str]:
    """Return {skill_name: full SKILL.md text} for every plugin skill."""
    skills_dir = PLUGIN_ROOT / "skills"
    if not skills_dir.exists():
        return {}
    bodies: dict[str, str] = {}
    for d in sorted(skills_dir.iterdir()):
        skill_file = d / "SKILL.md"
        if skill_file.exists():
            bodies[d.name] = skill_file.read_text(encoding="utf-8")
    return bodies


def _all_mcp_tool_names() -> set[str]:
    """Authoritative set of every registered MCP tool name (all categories)."""
    from attune.mcp.tool_schemas import (
        get_help_tools,
        get_memory_tools,
        get_personal_memory_tools,
        get_utility_tools,
        get_workflow_tools,
    )

    return (
        get_workflow_tools().keys()
        | get_utility_tools().keys()
        | get_memory_tools().keys()
        | get_help_tools().keys()
        | get_personal_memory_tools().keys()
    )


def _workflow_slugs() -> set[str]:
    """Every registered, runnable workflow slug."""
    from attune.workflows import _DEFAULT_WORKFLOW_NAMES

    return set(_DEFAULT_WORKFLOW_NAMES)


SKILL_BODIES = _skill_bodies()

try:
    MCP_TOOL_NAMES = _all_mcp_tool_names()
except ImportError:  # pragma: no cover - import-time guard
    MCP_TOOL_NAMES = set()

try:
    WORKFLOW_SLUGS = _workflow_slugs()
except ImportError:  # pragma: no cover - import-time guard
    WORKFLOW_SLUGS = set()


# ---------------------------------------------------------------------------
# Workflow -> MCP-tool surface
# ---------------------------------------------------------------------------

# Workflow slug -> MCP tool name(s), where the tool name is NOT just the
# slug with dashes turned into underscores (renames the guard can't infer).
WORKFLOW_TOOL_ALIASES: dict[str, set[str]] = {
    "perf-audit": {"performance_audit"},
    "rag-code-gen": {"rag_knowledge_query"},
    "test-gen": {"test_generation", "test_gen_parallel"},
}

# Workflows that intentionally expose no MCP tool, with the reason. Each
# is reachable another way (skill, wizard, CLI/CI) — never a silent gap.
WORKFLOWS_WITHOUT_MCP_SURFACE: dict[str, str] = {
    "fix": (
        "outcome-first-fix Phase 2: deliberately CLI-only "
        "(`attune fix --run`) while the surface is proving out; "
        "MCP/docs surfaces are that spec's Phase 3 scope."
    ),
    "release-prep": (
        "Surfaced via the release-prep skill AND the release-prep "
        "builtin wizard; deliberately not a one-shot MCP tool."
    ),
    "release-gate": (
        "Internal CI release gate (CLI/CI-only). Covered contextually "
        "inside the release-prep skill; no standalone MCP tool."
    ),
    "orchestrated-health-check": (
        "Internal composed variant of health-check. User surface is the "
        "health_check MCP tool + health-check workflow."
    ),
}


def _tool_candidates(slug: str) -> set[str]:
    """MCP tool names that would surface ``slug`` (norm + explicit aliases)."""
    return {slug.replace("-", "_")} | WORKFLOW_TOOL_ALIASES.get(slug, set())


class TestWorkflowSurfaceCoverage:
    """Every runnable workflow is reachable as an MCP tool (or allowlisted)."""

    def test_every_workflow_has_mcp_tool_or_is_allowlisted(self) -> None:
        unsurfaced = {
            slug
            for slug in WORKFLOW_SLUGS
            if not (_tool_candidates(slug) & MCP_TOOL_NAMES)
            and slug not in WORKFLOWS_WITHOUT_MCP_SURFACE
        }
        assert not unsurfaced, (
            "Workflow(s) registered with no MCP-tool surface and not "
            f"allowlisted: {sorted(unsurfaced)}. Either add an MCP tool in "
            "src/attune/mcp/tool_schemas.py (see discovery-sweep-access for "
            "the pattern), or add the slug to WORKFLOWS_WITHOUT_MCP_SURFACE "
            "with a reason explaining how users reach it."
        )

    def test_workflow_allowlist_has_no_stale_entries(self) -> None:
        """Allowlisted workflows must still genuinely lack a tool surface."""
        now_surfaced = {
            slug
            for slug in WORKFLOWS_WITHOUT_MCP_SURFACE
            if _tool_candidates(slug) & MCP_TOOL_NAMES
        }
        assert not now_surfaced, (
            "These workflows now HAVE an MCP tool — remove them from "
            f"WORKFLOWS_WITHOUT_MCP_SURFACE: {sorted(now_surfaced)}"
        )

    def test_workflow_aliases_point_at_real_tools(self) -> None:
        """Alias map must not reference tools that no longer exist."""
        dangling = {
            tool
            for tools in WORKFLOW_TOOL_ALIASES.values()
            for tool in tools
            if tool not in MCP_TOOL_NAMES
        }
        assert (
            not dangling
        ), f"WORKFLOW_TOOL_ALIASES references unknown MCP tools: {sorted(dangling)}"


# ---------------------------------------------------------------------------
# MCP tool -> skill surface
# ---------------------------------------------------------------------------

# MCP tools that intentionally have no skill naming them, with the reason.
# Tool names are distinctive snake_case, so "named by a skill" is a plain
# substring check across skill bodies (robust to `tool(args)` forms).
TOOLS_WITHOUT_SKILL_SURFACE: dict[str, str] = {
    # Utility/infra tools — surfaced via the CLI (/utilities), not a skill.
    "auth_status": "Utility/infra; surfaced via CLI auth commands, not a skill.",
    "auth_recommend": "Utility/infra; surfaced via CLI auth commands, not a skill.",
    "telemetry_stats": "Utility/infra; surfaced via CLI telemetry commands.",
    # The additive-access backlog is now empty: analyze_batch -> bulk skill,
    # analyze_image -> image-analysis skill, personal_memory_* -> the
    # personal-memory skill. Only the CLI-surfaced infra tools remain.
}


def _tool_is_named_by_a_skill(tool: str) -> bool:
    return any(tool in body for body in SKILL_BODIES.values())


class TestToolSurfaceCoverage:
    """Every MCP tool is named by some skill (or allowlisted with a reason)."""

    def test_every_tool_is_named_by_a_skill_or_allowlisted(self) -> None:
        orphans = {
            tool
            for tool in MCP_TOOL_NAMES
            if not _tool_is_named_by_a_skill(tool) and tool not in TOOLS_WITHOUT_SKILL_SURFACE
        }
        assert not orphans, (
            "MCP tool(s) registered but named by no skill and not "
            f"allowlisted: {sorted(orphans)}. Either add/extend a skill in "
            "plugin/skills/ that calls the tool, or add it to "
            "TOOLS_WITHOUT_SKILL_SURFACE with a reason."
        )

    def test_tool_allowlist_has_no_stale_entries(self) -> None:
        """Allowlisted tools must still genuinely lack a skill surface."""
        now_surfaced = {
            tool for tool in TOOLS_WITHOUT_SKILL_SURFACE if _tool_is_named_by_a_skill(tool)
        }
        assert not now_surfaced, (
            "These tools are now named by a skill — remove them from "
            f"TOOLS_WITHOUT_SKILL_SURFACE: {sorted(now_surfaced)}"
        )

    def test_tool_allowlist_references_real_tools(self) -> None:
        """Allowlist must not reference tools that no longer exist."""
        unknown = set(TOOLS_WITHOUT_SKILL_SURFACE) - MCP_TOOL_NAMES
        assert not unknown, (
            "TOOLS_WITHOUT_SKILL_SURFACE references unknown MCP tools "
            f"(rename/removed?): {sorted(unknown)}"
        )


def test_guard_has_data_to_check() -> None:
    """Sanity: the guard actually loaded registries (not silently empty)."""
    assert len(MCP_TOOL_NAMES) >= 40, f"Expected >=40 MCP tools, got {len(MCP_TOOL_NAMES)}"
    assert len(WORKFLOW_SLUGS) >= 20, f"Expected >=20 workflows, got {len(WORKFLOW_SLUGS)}"
    assert len(SKILL_BODIES) >= 17, f"Expected >=17 skills, got {len(SKILL_BODIES)}"


# ---------------------------------------------------------------------------
# Catalog completeness: every capability REGISTRY has a browse-all surface
# ---------------------------------------------------------------------------
#
# The two suites above check per-item surfaces (workflow -> tool,
# tool -> skill). This one checks the registry level: the catalog skill's
# `list_capabilities` tool is the universal "what can attune do?" surface,
# so a registry that exists, IS surfaced, but is not wired into it would be
# hidden. These tests fail if a surfaced registry drops out of the catalog or
# its count drifts from the live registry.
#
# IMPORTANT: surfacing is a privilege, not an obligation. Only registries
# with a working, dogfooded run path belong in the catalog. The agent-template
# registry was surfaced here (#1088) then REMOVED once dogfooding showed its
# only run path (the DynamicTeam -> StubAgent engine) was a fake-success stub —
# see .claude/rules-tail/attune/removing-dead-code.md. That dead engine has since
# been deleted (spec-gate-real-review). "Registered" never implies
# "should be surfaced"; verify the capability actually works first.


def _catalog_payload() -> dict:
    """Run the real list_capabilities handler and return its payload."""
    import asyncio

    from attune.mcp.server import EmpathyMCPServer

    return asyncio.run(EmpathyMCPServer()._handle_list_capabilities())


# Registry name in the catalog payload -> a callable returning the live
# registry's items. Adding a new capability registry to the product means
# adding it here AND wiring it into list_capabilities, or this fails.
def _live_registry_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    from attune.workflows import list_workflows

    counts["workflows"] = len(list_workflows())
    try:
        from attune.wizards.registry import list_wizards

        counts["wizards"] = len(list_wizards())
    except Exception:  # noqa: BLE001 - wizards optional; handler degrades too
        pass
    return counts


class TestCatalogCompleteness:
    """list_capabilities must enumerate EVERY capability registry."""

    def test_catalog_exposes_every_registry_group(self) -> None:
        try:
            cat = _catalog_payload()
        except ImportError:  # pragma: no cover - minimal env
            pytest.skip("MCP server not importable in this environment")
        for group in ("workflows", "wizards", "tools"):
            assert group in cat, f"list_capabilities dropped the '{group}' group"
            assert group in cat.get("counts", {}), f"counts missing '{group}'"

    def test_catalog_counts_match_live_registries(self) -> None:
        try:
            cat = _catalog_payload()
        except ImportError:  # pragma: no cover - minimal env
            pytest.skip("MCP server not importable in this environment")
        counts = cat["counts"]
        for name, live in _live_registry_counts().items():
            assert counts.get(name) == live, (
                f"catalog '{name}' count {counts.get(name)} != live registry "
                f"{live} — list_capabilities is out of sync with the registry."
            )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
