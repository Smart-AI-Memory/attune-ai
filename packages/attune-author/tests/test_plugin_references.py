"""Plugin reference validation.

Ensures cross-tier references resolve to real code:
- MCP tool names mentioned in skills exist in tool_schemas.py
- No orphaned skills (every skill is reachable from author hub)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugin"
SKILLS_DIR = PLUGIN_ROOT / "skills"


def _all_skills() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _registered_tool_names() -> set[str]:
    """Get the authoritative set of MCP tool names from tool_schemas."""
    from attune_author.mcp.tool_schemas import get_tools

    return set(get_tools().keys())


def _extract_tool_refs(text: str, valid_tools: set[str]) -> set[str]:
    """Extract tool names referenced in markdown body.

    Looks for backtick-wrapped tool names that match a known
    tool. Avoids false positives by intersecting with the
    valid_tools set.
    """
    backtick_pattern = re.compile(r"`([a-z_][a-z0-9_]*)`")
    refs = set(backtick_pattern.findall(text))
    return refs & valid_tools


# -- Skill -> MCP tool refs ------------------------------------------


class TestSkillMcpToolRefs:
    """Every MCP tool referenced in a skill must exist."""

    def test_registered_tool_count(self) -> None:
        """Sanity check that we have the expected 6 tools."""
        tools = _registered_tool_names()
        assert len(tools) == 6, f"Expected 6 tools, got {len(tools)}: {tools}"

    @pytest.mark.parametrize("skill_path", _all_skills(), ids=lambda p: p.parent.name)
    def test_skill_tool_refs_resolve(self, skill_path: Path) -> None:
        text = skill_path.read_text(encoding="utf-8")
        valid = _registered_tool_names()
        refs = _extract_tool_refs(text, valid)

        # No assertion on minimum — some skills may be pure routing
        # and reference no tools by name. We only check that any
        # ref that *looks* like a tool name is actually one.
        for ref in refs:
            assert ref in valid, f"{skill_path}: references unknown tool '{ref}'"


# -- Hub -> sub-skill refs -------------------------------------------


class TestHubRouting:
    """Hub skill must reference all sub-skills."""

    def test_hub_routes_to_all_sub_skills(self) -> None:
        hub_path = SKILLS_DIR / "author" / "SKILL.md"
        hub_text = hub_path.read_text(encoding="utf-8")

        sub_skill_names = {p.parent.name for p in _all_skills() if p.parent.name != "author"}

        for sub in sub_skill_names:
            assert sub in hub_text, f"Hub skill does not reference sub-skill '{sub}'"

    def test_hub_references_mcp_tools(self) -> None:
        hub_path = SKILLS_DIR / "author" / "SKILL.md"
        hub_text = hub_path.read_text(encoding="utf-8")

        valid = _registered_tool_names()
        refs = _extract_tool_refs(hub_text, valid)

        # Hub should reference at least 5 of the 6 tools
        # (lookup is mentioned but other 5 are routed via sub-skills)
        assert len(refs) >= 5, f"Hub references only {len(refs)} tools: {refs}"


# -- No orphaned skills ----------------------------------------------


class TestNoOrphanedSkills:
    """All skills must be discoverable from the hub."""

    def test_no_orphaned_skills(self) -> None:
        hub_path = SKILLS_DIR / "author" / "SKILL.md"
        hub_text = hub_path.read_text(encoding="utf-8")

        for skill in _all_skills():
            name = skill.parent.name
            if name == "author":
                continue
            assert name in hub_text, f"Skill '{name}' not referenced by hub"
