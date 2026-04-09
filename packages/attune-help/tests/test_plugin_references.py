"""Plugin reference validation.

Parses all plugin markdown files, extracts references to MCP
tools and file paths, and asserts that each one resolves to
real code. This catches drift when tools are renamed or
handlers move without updating skills.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugin"
SRC_ROOT = REPO_ROOT / "src" / "attune_help"


def _all_skill_bodies() -> list[tuple[Path, str]]:
    """Return (path, body) for every SKILL.md in the plugin."""
    out: list[tuple[Path, str]] = []
    for skill in sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        out.append((skill, text))
    return out


def _mcp_tool_names() -> set[str]:
    """Read the real tool registry from tool_schemas.py."""
    from attune_help.mcp.tool_schemas import get_tools

    return set(get_tools().keys())


# -- MCP tool references ---------------------------------------------


class TestMcpToolReferences:
    """Every MCP tool named in a skill must exist in tool_schemas."""

    def test_lookup_tool_prefix_enforced(self) -> None:
        """All MCP tools must start with `lookup_` to avoid collision."""
        tools = _mcp_tool_names()
        assert tools, "No tools registered in tool_schemas.py"
        for name in tools:
            assert name.startswith("lookup_"), (
                f"Tool '{name}' missing required `lookup_` prefix "
                f"(collides with attune-ai's help_* tools otherwise)"
            )

    def test_expected_tool_count(self) -> None:
        tools = _mcp_tool_names()
        assert len(tools) == 6, f"Expected 6 lookup_* tools, got {len(tools)}: {sorted(tools)}"

    def test_expected_tool_names(self) -> None:
        expected = {
            "lookup_topic",
            "lookup_list",
            "lookup_warn",
            "lookup_preamble",
            "lookup_reset",
            "lookup_status",
        }
        assert _mcp_tool_names() == expected

    @pytest.mark.parametrize(
        "skill_path,body",
        _all_skill_bodies(),
        ids=lambda x: x.parent.name if isinstance(x, Path) else "",
    )
    def test_skill_mcp_references_resolve(
        self,
        skill_path: Path,
        body: str,
    ) -> None:
        """Every backtick-quoted lookup_* name must exist in tool_schemas."""
        registered = _mcp_tool_names()
        # Match backtick-delimited tool names like `lookup_topic`
        referenced = set(re.findall(r"`(lookup_[a-z_]+)`", body))

        for name in referenced:
            assert name in registered, (
                f"{skill_path.parent.name}/SKILL.md references "
                f"`{name}` which is not in tool_schemas.py"
            )


# -- Handler existence -----------------------------------------------


class TestHandlerExistence:
    """Every registered tool must have a dispatch entry and a handler."""

    def test_all_tools_have_handlers(self) -> None:
        from attune_help.mcp.handlers import AttuneHelpHandlers
        from attune_help.mcp.server import AttuneHelpMCPServer

        server = AttuneHelpMCPServer()
        tools = _mcp_tool_names()

        for tool_name in tools:
            assert tool_name in server._dispatch, f"Tool '{tool_name}' has no dispatch entry"
            handler = server._dispatch[tool_name]
            assert callable(handler), f"Handler for '{tool_name}' is not callable"

        # Every handler must be a method on AttuneHelpHandlers
        handler_methods = {name for name in dir(AttuneHelpHandlers) if name.startswith("lookup_")}
        assert handler_methods == tools, (
            f"AttuneHelpHandlers methods != registered tools: " f"{handler_methods ^ tools}"
        )


# -- File path references --------------------------------------------


class TestFilePathReferences:
    """Every relative path mentioned in a skill must exist."""

    def test_no_stale_src_references(self) -> None:
        """Skills referencing src/attune_help/... must resolve."""
        for skill, body in _all_skill_bodies():
            # Relative imports like `from attune_help.mcp.handlers import X`
            for match in re.finditer(
                r"attune_help\.([a-z_.]+)",
                body,
            ):
                path = match.group(1)
                # Skip dotted attrs (Handlers, etc.)
                parts = path.split(".")
                if parts[-1][0].isupper():
                    parts = parts[:-1]
                if not parts:
                    continue
                target_py = SRC_ROOT / ("/".join(parts) + ".py")
                target_pkg = SRC_ROOT / "/".join(parts) / "__init__.py"
                assert target_py.exists() or target_pkg.exists(), (
                    f"{skill.parent.name}/SKILL.md references "
                    f"attune_help.{path} which doesn't resolve"
                )


# -- No orphaned skills ----------------------------------------------


class TestNoOrphanedSkills:
    """Every work skill must be reachable from the hub skill's routing."""

    def test_hub_references_all_work_skills(self) -> None:
        hub = PLUGIN_ROOT / "skills" / "lookup" / "SKILL.md"
        assert hub.exists()
        body = hub.read_text(encoding="utf-8")

        work_skills = [
            p.parent.name
            for p in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")
            if p.parent.name != "lookup"
        ]
        for name in work_skills:
            assert name in body, (
                f"Hub skill does not reference '{name}' — " f"users can't discover it from /lookup"
            )
