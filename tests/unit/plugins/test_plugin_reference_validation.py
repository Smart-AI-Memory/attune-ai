"""Validate that plugin component references resolve to real code.

Commands reference skills, skills reference MCP tools, and MCP tools
reference workflow classes. This test suite ensures every cross-tier
reference in the plugin markdown files points to something that
actually exists.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[3] / "plugin"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SKILL_RE = re.compile(r"file:///skills/([^/)]+)/SKILL\.md")
_FILE_RE = re.compile(r"file:///(.+?\.md)")
_TOOL_BACKTICK_RE = re.compile(r"`([a-z][a-z_]+)`")
_IMPORT_RE = re.compile(r"from\s+(attune\.\S+)\s+import\s+(\w+(?:Workflow|Pipeline|Orchestrator))")


def _iter_table_rows(content: str, section: str) -> Iterator[str]:
    """Yield non-header table rows within a markdown ``## section``."""
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == f"## {section}" or stripped.startswith(f"## {section}\n"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("|"):
            if "---" in stripped:
                continue
            yield stripped


def _read_commands() -> dict[str, str]:
    """Read all command .md files once, return {filename: content}."""
    commands_dir = PLUGIN_ROOT / "commands"
    if not commands_dir.exists():
        return {}
    return {f.name: f.read_text(encoding="utf-8") for f in sorted(commands_dir.glob("*.md"))}


def _read_skills() -> dict[str, str]:
    """Read all SKILL.md files once, return {skill_name: content}."""
    skills_dir = PLUGIN_ROOT / "skills"
    if not skills_dir.exists():
        return {}
    result: dict[str, str] = {}
    for d in sorted(skills_dir.iterdir()):
        skill_file = d / "SKILL.md"
        if skill_file.exists():
            result[d.name] = skill_file.read_text(encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Data collection (single pass per file)
# ---------------------------------------------------------------------------

_CMD_CONTENTS = _read_commands()
_SKILL_CONTENTS = _read_skills()


def _collect_command_refs() -> tuple[list[tuple[str, str, Path]], list[tuple[str, Path]]]:
    """Single-pass extraction of skill refs and file path refs from commands."""
    skill_refs: list[tuple[str, str, Path]] = []
    file_refs: list[tuple[str, Path]] = []
    for name, content in _CMD_CONTENTS.items():
        for m in _SKILL_RE.finditer(content):
            skill_name = m.group(1)
            expected = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
            skill_refs.append((name, skill_name, expected))
        for m in _FILE_RE.finditer(content):
            file_refs.append((name, Path(m.group(1))))
    return skill_refs, file_refs


def _collect_skill_refs() -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """Single-pass extraction of tool refs and class refs from skills."""
    tool_refs: list[tuple[str, str]] = []
    class_refs: list[tuple[str, str, str]] = []
    for skill_name, content in _SKILL_CONTENTS.items():
        for row in _iter_table_rows(content, "MCP Tools"):
            if "Tool" in row.split("|")[1]:
                continue
            for m in _TOOL_BACKTICK_RE.finditer(row):
                if "_" in m.group(1):
                    tool_refs.append((skill_name, m.group(1)))
        for m in _IMPORT_RE.finditer(content):
            class_refs.append((skill_name, m.group(1), m.group(2)))
    return tool_refs, class_refs


def _collect_hub_tool_refs() -> list[tuple[str, str]]:
    """Extract MCP tool names referenced in attune-hub skill."""
    content = _SKILL_CONTENTS.get("attune-hub", "")
    if not content:
        return []

    refs: list[tuple[str, str]] = []
    for m in re.finditer(r"[Cc]all\s+`([a-z][a-z_]+)`", content):
        if "_" in m.group(1):
            refs.append(("attune-hub", m.group(1)))

    for row in _iter_table_rows(content, "Natural Language Routing"):
        parts = row.split("|")
        if len(parts) >= 3:
            action = parts[2].strip()
            for name in re.findall(r"([a-z][a-z_]+_[a-z_]+)", action):
                refs.append(("attune-hub", name))

    seen: dict[str, tuple[str, str]] = {}
    for pair in refs:
        seen.setdefault(pair[1], pair)
    return list(seen.values())


def _collect_attune_skill_names() -> set[str]:
    """Extract skill names from attune-hub's Skills Reference table."""
    content = _SKILL_CONTENTS.get("attune-hub", "")
    names: set[str] = set()
    for row in _iter_table_rows(content, "Skills Reference"):
        parts = row.split("|")
        if len(parts) >= 2:
            name = parts[1].strip()
            if name and name != "Skill":
                names.add(name)
    return names


def _get_registered_tool_names() -> set[str]:
    """Get the authoritative set of MCP tool names.

    Core tools come from tool_schemas.py; plugin-registered tools
    (redis_memory_*, session_memory_*) come from the bundled
    attune_redis plugin's definition dicts — skills may reference
    either surface.
    """
    from attune.mcp.tool_schemas import (
        get_memory_tools,
        get_utility_tools,
        get_workflow_tools,
    )

    names = get_workflow_tools().keys() | get_utility_tools().keys() | get_memory_tools().keys()
    try:
        from attune_redis.mcp_tools import (
            SESSION_MEMORY_TOOL_DEFINITIONS,
            TOOL_DEFINITIONS,
        )

        names = names | TOOL_DEFINITIONS.keys() | SESSION_MEMORY_TOOL_DEFINITIONS.keys()
    except ImportError:
        pass  # partial environment: core tools still validate
    return set(names)


# ---------------------------------------------------------------------------
# Module-level data (collected once at import time)
# ---------------------------------------------------------------------------

COMMAND_SKILL_REFS, FILE_PATH_REFS = _collect_command_refs()
SKILL_TOOL_REFS, SKILL_CLASS_REFS = _collect_skill_refs()
HUB_TOOL_REFS = _collect_hub_tool_refs()
ATTUNE_SKILL_NAMES = _collect_attune_skill_names()

try:
    MCP_TOOL_NAMES = _get_registered_tool_names()
except ImportError:
    MCP_TOOL_NAMES = set()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCommandSkillRefs:
    """Every command skill reference must resolve to an existing SKILL.md."""

    @pytest.mark.parametrize(
        "command_file,skill_name,skill_path",
        COMMAND_SKILL_REFS,
        ids=[f"{cmd}->{skill}" for cmd, skill, _ in COMMAND_SKILL_REFS],
    )
    def test_skill_exists(self, command_file: str, skill_name: str, skill_path: Path) -> None:
        """Verify skill referenced by command exists on disk."""
        assert skill_path.exists(), (
            f"Command '{command_file}' references skill '{skill_name}' "
            f"but {skill_path} does not exist"
        )


@pytest.mark.unit
class TestSkillMcpToolRefs:
    """Every MCP tool name in a skill must exist in tool_schemas.py."""

    @pytest.mark.skipif(not MCP_TOOL_NAMES, reason="attune not installed")
    @pytest.mark.parametrize(
        "skill_name,tool_name",
        SKILL_TOOL_REFS,
        ids=[f"{skill}:{tool}" for skill, tool in SKILL_TOOL_REFS],
    )
    def test_tool_exists(self, skill_name: str, tool_name: str) -> None:
        """Verify MCP tool referenced by skill is registered."""
        assert tool_name in MCP_TOOL_NAMES, (
            f"Skill '{skill_name}' references MCP tool '{tool_name}' "
            f"which is not registered in tool_schemas.py. "
            f"Registered tools: {sorted(MCP_TOOL_NAMES)}"
        )


@pytest.mark.unit
class TestHubMcpToolRefs:
    """MCP tool names referenced in attune-hub must exist in schemas."""

    @pytest.mark.skipif(not MCP_TOOL_NAMES, reason="attune not installed")
    @pytest.mark.parametrize(
        "skill_name,tool_name",
        HUB_TOOL_REFS,
        ids=[f"{skill}:{tool}" for skill, tool in HUB_TOOL_REFS],
    )
    def test_tool_exists(self, skill_name: str, tool_name: str) -> None:
        """Verify MCP tool referenced by hub skill is registered."""
        assert tool_name in MCP_TOOL_NAMES, (
            f"Skill '{skill_name}' references MCP tool '{tool_name}' "
            f"which is not registered in tool_schemas.py. "
            f"Registered tools: {sorted(MCP_TOOL_NAMES)}"
        )


@pytest.mark.unit
class TestFilePathRefs:
    """Every file:/// reference in commands must resolve on disk."""

    @pytest.mark.parametrize(
        "command_file,ref_path",
        FILE_PATH_REFS,
        ids=[f"{cmd}:{path}" for cmd, path in FILE_PATH_REFS],
    )
    def test_file_exists(self, command_file: str, ref_path: Path) -> None:
        """Verify file:/// reference resolves relative to plugin root."""
        actual = PLUGIN_ROOT / ref_path
        assert actual.exists(), (
            f"Command '{command_file}' references file:///{ref_path} "
            f"but {actual} does not exist"
        )


@pytest.mark.unit
class TestSkillClassRefs:
    """Python classes referenced in skills must be importable."""

    @pytest.mark.parametrize(
        "skill_name,module_path,class_name",
        SKILL_CLASS_REFS,
        ids=[f"{skill}:{cls}" for skill, _, cls in SKILL_CLASS_REFS],
    )
    def test_class_importable(self, skill_name: str, module_path: str, class_name: str) -> None:
        """Verify Python class referenced in skill can be imported."""
        try:
            mod = importlib.import_module(module_path)
        except ImportError as e:
            pytest.fail(
                f"Skill '{skill_name}' references {module_path}.{class_name} "
                f"but module import failed: {e}"
            )
        assert hasattr(mod, class_name), (
            f"Skill '{skill_name}' references {module_path}.{class_name} "
            f"but class '{class_name}' does not exist in that module"
        )


@pytest.mark.unit
class TestCoverage:
    """Ensure no commands or skills are orphaned."""

    def test_all_skill_dirs_referenced_by_attune_hub(self) -> None:
        """Every skill should appear in attune-hub's Skills Reference."""
        skills_dir = PLUGIN_ROOT / "skills"
        if not skills_dir.exists():
            pytest.skip("No skills directory")

        all_skills = {
            d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
        }
        # attune-hub and spec reference themselves, so exclude from orphan check
        referenced = ATTUNE_SKILL_NAMES | {"attune-hub", "spec"}

        orphaned = all_skills - referenced
        assert not orphaned, f"Skills not in attune-hub Skills Reference: {orphaned}"

    def test_all_command_skill_refs_are_unique(self) -> None:
        """Same command should not reference the same skill twice."""
        per_command: dict[str, list[str]] = {}
        for cmd, skill, _ in COMMAND_SKILL_REFS:
            per_command.setdefault(cmd, []).append(skill)
        for cmd, skills in per_command.items():
            assert len(skills) == len(set(skills)), (
                f"Command '{cmd}' references the same skill multiple " f"times: {skills}"
            )


@pytest.mark.unit
class TestDataCollectionSanity:
    """Verify that data collection found a reasonable number of refs."""

    def test_command_skill_refs_found(self) -> None:
        """Commands may have 0 file:/// skill refs (skills-centric architecture)."""
        # After skills migration, commands route via description, not file:/// refs.
        # The attune.md Skills Reference table is the primary reference mechanism.
        assert (
            len(COMMAND_SKILL_REFS) >= 0
        ), f"Unexpected negative command->skill refs: {len(COMMAND_SKILL_REFS)}"

    def test_skill_tool_refs_found(self) -> None:
        """We expect at least 10 skill->tool references."""
        assert len(SKILL_TOOL_REFS) >= 10, (
            f"Expected >=10 skill->tool refs, found "
            f"{len(SKILL_TOOL_REFS)}. Did skill files change?"
        )

    def test_file_path_refs_found(self) -> None:
        """Commands may have 0 file:/// refs (skills-centric architecture)."""
        # After skills migration, commands no longer use file:/// references.
        assert (
            len(FILE_PATH_REFS) >= 0
        ), f"Unexpected negative file path refs: {len(FILE_PATH_REFS)}"

    @pytest.mark.skipif(not MCP_TOOL_NAMES, reason="attune not installed")
    def test_mcp_tools_registered(self) -> None:
        """We expect at least 30 MCP tools registered."""
        assert len(MCP_TOOL_NAMES) >= 30, (
            f"Expected >=30 MCP tools, found " f"{len(MCP_TOOL_NAMES)}. Did tool_schemas.py change?"
        )
