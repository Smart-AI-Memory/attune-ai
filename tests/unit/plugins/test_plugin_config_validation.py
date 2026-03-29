"""Validation tests for plugin/ directory configuration files.

Validates JSON schemas, YAML frontmatter, and cross-file
version consistency for the Claude Code plugin distribution.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

PLUGIN_ROOT = Path(__file__).parents[3] / "plugin"


@pytest.mark.unit
class TestPluginJson:
    """Validate plugin/.claude-plugin/plugin.json."""

    def test_valid_json(self) -> None:
        """Test that plugin.json parses as valid JSON."""
        path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_required_fields(self) -> None:
        """Test that all required fields are present."""
        path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        required = ["name", "version", "description", "author", "license"]
        for field in required:
            assert field in data, f"Missing required field: {field}"

    def test_version_is_semver(self) -> None:
        """Test that version follows semver format."""
        path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        parts = data["version"].split(".")
        assert len(parts) == 3, f"Version {data['version']} is not semver"
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' is not numeric"

    def test_author_has_name(self) -> None:
        """Test that author object includes a name."""
        path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "name" in data["author"]


@pytest.mark.unit
class TestMarketplaceJson:
    """Validate plugin/.claude-plugin/marketplace.json."""

    def test_valid_json(self) -> None:
        """Test that marketplace.json parses as valid JSON."""
        path = PLUGIN_ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_has_plugins_array(self) -> None:
        """Test that plugins array exists and is non-empty."""
        path = PLUGIN_ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "plugins" in data
        assert len(data["plugins"]) > 0


@pytest.mark.unit
class TestHooksJson:
    """Validate plugin/hooks/hooks.json."""

    def test_valid_json(self) -> None:
        """Test that hooks.json parses as valid JSON."""
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_has_hooks_key(self) -> None:
        """Test that top-level 'hooks' key exists."""
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "hooks" in data

    def test_hook_events_are_valid(self) -> None:
        """Test that hook event names are valid Claude Code events."""
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        valid_events = {
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SubagentStart",
            "SubagentStop",
            "SessionStart",
            "SessionEnd",
            "UserPromptSubmit",
            "PreCompact",
            "Notification",
            "ConfigChange",
            "PermissionRequest",
        }
        for event in data["hooks"]:
            assert event in valid_events, f"Unknown hook event: {event}"

    def test_hook_entries_have_matcher(self) -> None:
        """Test that tool-use hook entries have a matcher field.

        SessionStart/SessionEnd hooks do not use matchers.
        """
        # Events that match on tool names
        tool_events = {"PreToolUse", "PostToolUse"}
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for event, entries in data["hooks"].items():
            if event not in tool_events:
                continue
            for entry in entries:
                assert "matcher" in entry, f"Hook entry in {event} missing 'matcher'"

    def test_hook_entries_have_hooks_array(self) -> None:
        """Test that each hook entry has a hooks array."""
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for event, entries in data["hooks"].items():
            for entry in entries:
                assert "hooks" in entry, f"Hook entry in {event} missing 'hooks'"
                assert isinstance(entry["hooks"], list)

    def test_hook_commands_use_plugin_root(self) -> None:
        """Test that commands use ${CLAUDE_PLUGIN_ROOT} for portability."""
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for _event, entries in data["hooks"].items():
            for entry in entries:
                for hook in entry["hooks"]:
                    if hook.get("type") == "command":
                        assert "${CLAUDE_PLUGIN_ROOT}" in hook["command"], (
                            f"Hook command should use ${{CLAUDE_PLUGIN_ROOT}}: "
                            f"{hook['command']}"
                        )

    def test_timeouts_are_reasonable(self) -> None:
        """Test that hook timeouts are between 1s and 60s."""
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for _event, entries in data["hooks"].items():
            for entry in entries:
                for hook in entry["hooks"]:
                    if "timeout" in hook:
                        assert 1000 <= hook["timeout"] <= 60000, (
                            f"Timeout {hook['timeout']}ms outside " f"reasonable range (1-60s)"
                        )


@pytest.mark.unit
class TestMcpJson:
    """Validate plugin/.mcp.json."""

    def test_valid_json(self) -> None:
        """Test that .mcp.json parses as valid JSON."""
        path = PLUGIN_ROOT / ".mcp.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_has_mcp_servers(self) -> None:
        """Test that mcpServers key exists."""
        path = PLUGIN_ROOT / ".mcp.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "mcpServers" in data

    def test_no_hardcoded_secrets(self) -> None:
        """Test that no hardcoded API keys exist in config."""
        path = PLUGIN_ROOT / ".mcp.json"
        content = path.read_text(encoding="utf-8")
        # Should use ${ANTHROPIC_API_KEY} not a real key
        assert "sk-ant-" not in content
        assert "sk_live" not in content
        assert "AKIAIOSFODNN" not in content


@pytest.mark.unit
class TestSkillFrontmatter:
    """Validate YAML frontmatter in all SKILL.md files."""

    # Official Claude Code skill frontmatter fields (March 2026)
    VALID_FIELDS = {
        "name",
        "description",
        "argument-hint",
        "disable-model-invocation",
        "user-invocable",
        "allowed-tools",
        "model",
        "effort",
        "context",
        "agent",
        "hooks",
        "paths",
        "shell",
    }

    def _get_skill_dirs(self) -> list[Path]:
        """Return all skill directories."""
        skills_dir = PLUGIN_ROOT / "skills"
        return sorted(d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists())

    def _parse_frontmatter(self, path: Path) -> dict:
        """Parse YAML frontmatter from a markdown file."""
        content = path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"No YAML frontmatter in {path}"
        return yaml.safe_load(parts[1])

    def test_all_skills_have_frontmatter(self) -> None:
        """Test that all SKILL.md files have valid YAML frontmatter."""
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            assert isinstance(data, dict), f"{path} frontmatter is not a dict"

    def test_all_skills_have_name(self) -> None:
        """Test that all skills have a name field."""
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            assert "name" in data, f"{path} missing 'name'"

    def test_all_skills_have_description(self) -> None:
        """Test that all skills have a description field."""
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            assert "description" in data, f"{path} missing 'description'"

    def test_skill_names_match_directories(self) -> None:
        """Test that skill name matches its directory name."""
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            assert data["name"] == skill_dir.name, (
                f"Skill name '{data['name']}' doesn't match " f"directory '{skill_dir.name}'"
            )

    def test_skill_names_are_unique(self) -> None:
        """Test that all skill names are unique."""
        names: list[str] = []
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            names.append(data["name"])
        assert len(names) == len(set(names)), f"Duplicate skill names: {names}"

    def test_only_valid_frontmatter_fields(self) -> None:
        """Test that skills use only SDK-supported frontmatter fields."""
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            invalid = set(data.keys()) - self.VALID_FIELDS
            assert not invalid, (
                f"{path} has unsupported fields: {invalid}. " f"Valid: {self.VALID_FIELDS}"
            )

    def test_descriptions_have_trigger_keywords(self) -> None:
        """Test that descriptions include trigger keywords."""
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            desc = data["description"]
            assert len(desc) > 50, (
                f"{path} description too short ({len(desc)} chars) "
                f"for effective auto-invocation"
            )

    def test_descriptions_under_250_chars(self) -> None:
        """Test that descriptions are under 250 chars.

        Anthropic truncates skill descriptions longer than 250
        characters, which breaks auto-triggering from natural language.
        """
        for skill_dir in self._get_skill_dirs():
            path = skill_dir / "SKILL.md"
            data = self._parse_frontmatter(path)
            desc = data["description"]
            assert len(desc) <= 250, (
                f"{skill_dir.name} description is {len(desc)} chars "
                f"(max 250). Truncation will break auto-triggering."
            )


@pytest.mark.unit
class TestPluginStructure:
    """Validate plugin directory counts and layout."""

    def test_skill_count(self) -> None:
        """Test that the expected number of skills exist."""
        skills_dir = PLUGIN_ROOT / "skills"
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
        assert len(skill_dirs) == 11, (
            f"Expected 11 skills, found {len(skill_dirs)}: " f"{sorted(d.name for d in skill_dirs)}"
        )

    def test_command_count(self) -> None:
        """Test that exactly 2 commands exist (attune + spec)."""
        commands_dir = PLUGIN_ROOT / "commands"
        cmd_files = sorted(f.name for f in commands_dir.glob("*.md"))
        assert cmd_files == [
            "attune.md",
            "spec.md",
        ], f"Expected ['attune.md', 'spec.md'], found {cmd_files}"

    def test_hook_scripts_exist(self) -> None:
        """Test that hook commands reference existing scripts."""
        hooks_path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
        for _event, entries in data["hooks"].items():
            for entry in entries:
                for hook in entry["hooks"]:
                    if hook.get("type") == "command":
                        cmd = hook["command"]
                        # Extract script path after ${CLAUDE_PLUGIN_ROOT}/
                        if "${CLAUDE_PLUGIN_ROOT}/" in cmd:
                            rel = cmd.split("${CLAUDE_PLUGIN_ROOT}/")[1]
                            # Strip any trailing arguments
                            script = rel.split()[0]
                            actual = PLUGIN_ROOT / script
                            assert actual.exists(), (
                                f"Hook references {script} " f"but {actual} does not exist"
                            )


@pytest.mark.unit
class TestVersionConsistency:
    """Test that version numbers are consistent across plugin files."""

    def _get_versions(self) -> dict[str, str]:
        """Collect version strings from all plugin files."""
        versions: dict[str, str] = {}

        # plugin.json
        pj = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(pj.read_text(encoding="utf-8"))
        versions["plugin.json"] = data["version"]

        # marketplace.json (metadata + plugins[0])
        mj = PLUGIN_ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(mj.read_text(encoding="utf-8"))
        versions["marketplace.json:metadata"] = data["metadata"]["version"]
        versions["marketplace.json:plugin"] = data["plugins"][0]["version"]

        # core/__init__.py
        init = PLUGIN_ROOT / "core" / "__init__.py"
        content = init.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("__version__"):
                versions["core/__init__.py"] = line.split("=")[1].strip().strip('"').strip("'")

        return versions

    def test_all_versions_match(self) -> None:
        """Test that all version strings are identical."""
        versions = self._get_versions()
        unique = set(versions.values())
        assert len(unique) == 1, f"Version mismatch across files: {versions}"

    def test_version_is_semver(self) -> None:
        """Test that the version follows semver format."""
        versions = self._get_versions()
        for source, version in versions.items():
            parts = version.split(".")
            assert len(parts) == 3, f"{source}: version '{version}' is not semver"
