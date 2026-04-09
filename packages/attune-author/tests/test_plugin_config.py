"""Plugin configuration validation.

Validates JSON manifests, hooks.json, .mcp.json, SKILL.md
frontmatter, and version consistency across all plugin files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugin"
PACKAGE_INIT = Path(__file__).resolve().parent.parent / "src" / "attune_author" / "__init__.py"

VALID_SKILL_FIELDS = {
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

VALID_HOOK_EVENTS = {
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
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML frontmatter parser (no PyYAML needed)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]

    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            fields[key] = value
    return fields, body


def _all_skills() -> list[Path]:
    return sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))


# -- plugin.json -----------------------------------------------------


class TestPluginJson:
    """Validate plugin/.claude-plugin/plugin.json."""

    @pytest.fixture
    def manifest(self) -> dict:
        return _read_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")

    def test_valid_json(self, manifest: dict) -> None:
        assert isinstance(manifest, dict)

    def test_required_fields(self, manifest: dict) -> None:
        for field in ("name", "version", "description", "author", "license"):
            assert field in manifest, f"Missing required field: {field}"

    def test_name_is_attune_author(self, manifest: dict) -> None:
        assert manifest["name"] == "attune-author"

    def test_version_is_semver(self, manifest: dict) -> None:
        assert re.match(r"^\d+\.\d+\.\d+$", manifest["version"])

    def test_author_has_name(self, manifest: dict) -> None:
        assert "name" in manifest["author"]


# -- marketplace.json ------------------------------------------------


class TestMarketplaceJson:
    """Validate plugin/.claude-plugin/marketplace.json."""

    @pytest.fixture
    def market(self) -> dict:
        return _read_json(PLUGIN_ROOT / ".claude-plugin" / "marketplace.json")

    def test_valid_json(self, market: dict) -> None:
        assert isinstance(market, dict)

    def test_has_plugins_array(self, market: dict) -> None:
        assert isinstance(market.get("plugins"), list)
        assert len(market["plugins"]) >= 1

    def test_first_plugin_is_attune_author(self, market: dict) -> None:
        assert market["plugins"][0]["name"] == "attune-author"


# -- .mcp.json -------------------------------------------------------


class TestMcpJson:
    """Validate plugin/.mcp.json."""

    @pytest.fixture
    def mcp(self) -> dict:
        return _read_json(PLUGIN_ROOT / ".mcp.json")

    def test_valid_json(self, mcp: dict) -> None:
        assert "mcpServers" in mcp

    def test_has_attune_author_server(self, mcp: dict) -> None:
        assert "attune-author" in mcp["mcpServers"]

    def test_no_hardcoded_secrets(self, mcp: dict) -> None:
        text = json.dumps(mcp)
        forbidden = ("sk-ant-", "sk_live", "AKIA")
        for pattern in forbidden:
            assert pattern not in text, f"Found hardcoded secret: {pattern}"

    def test_uses_env_var_for_api_key(self, mcp: dict) -> None:
        env = mcp["mcpServers"]["attune-author"].get("env", {})
        assert env.get("ANTHROPIC_API_KEY") == "${ANTHROPIC_API_KEY}"


# -- hooks.json ------------------------------------------------------


class TestHooksJson:
    """Validate plugin/hooks/hooks.json."""

    @pytest.fixture
    def hooks(self) -> dict:
        return _read_json(PLUGIN_ROOT / "hooks" / "hooks.json")

    def test_valid_json(self, hooks: dict) -> None:
        assert "hooks" in hooks

    def test_event_names_valid(self, hooks: dict) -> None:
        for event_name in hooks["hooks"]:
            assert event_name in VALID_HOOK_EVENTS, f"Invalid event: {event_name}"

    def test_tool_use_hooks_have_matcher(self, hooks: dict) -> None:
        for event_name, entries in hooks["hooks"].items():
            if event_name not in ("PreToolUse", "PostToolUse"):
                continue
            for entry in entries:
                assert "matcher" in entry, f"{event_name} entry missing matcher"

    def test_commands_use_plugin_root(self, hooks: dict) -> None:
        for entries in hooks["hooks"].values():
            for entry in entries:
                for h in entry.get("hooks", []):
                    cmd = h.get("command", "")
                    if "/hooks/" in cmd or "hooks\\" in cmd:
                        assert (
                            "${CLAUDE_PLUGIN_ROOT}" in cmd
                        ), f"Hook command missing $CLAUDE_PLUGIN_ROOT: {cmd}"

    def test_timeouts_in_range(self, hooks: dict) -> None:
        for entries in hooks["hooks"].values():
            for entry in entries:
                for h in entry.get("hooks", []):
                    timeout = h.get("timeout")
                    if timeout is None:
                        continue
                    assert 1000 <= timeout <= 60000, f"Hook timeout out of range: {timeout}"

    def test_referenced_hook_scripts_exist(self, hooks: dict) -> None:
        for entries in hooks["hooks"].values():
            for entry in entries:
                for h in entry.get("hooks", []):
                    cmd = h.get("command", "")
                    # Extract path after ${CLAUDE_PLUGIN_ROOT}/
                    marker = "${CLAUDE_PLUGIN_ROOT}/"
                    if marker in cmd:
                        rel = cmd.split(marker, 1)[1].split()[0]
                        target = PLUGIN_ROOT / rel
                        assert target.exists(), f"Referenced script missing: {target}"


# -- SKILL.md frontmatter --------------------------------------------


class TestSkillFrontmatter:
    """Validate every SKILL.md frontmatter."""

    @pytest.mark.parametrize("skill_path", _all_skills(), ids=lambda p: p.parent.name)
    def test_skill_has_valid_frontmatter(self, skill_path: Path) -> None:
        text = skill_path.read_text(encoding="utf-8")
        fields, body = _parse_frontmatter(text)

        assert fields, f"No frontmatter found in {skill_path}"
        assert "name" in fields, f"{skill_path}: missing 'name'"
        assert "description" in fields, f"{skill_path}: missing 'description'"

        # Name matches directory
        assert (
            fields["name"] == skill_path.parent.name
        ), f"{skill_path}: name '{fields['name']}' != dir '{skill_path.parent.name}'"

        # Description length
        desc_len = len(fields["description"])
        assert (
            50 <= desc_len <= 250
        ), f"{skill_path}: description is {desc_len} chars (must be 50-250)"

        # Only allowed fields
        for field in fields:
            assert field in VALID_SKILL_FIELDS, f"{skill_path}: invalid frontmatter field '{field}'"

        # Body must exist
        assert body.strip(), f"{skill_path}: empty body"


class TestSkillUniqueness:
    """Validate skill names are unique."""

    def test_skill_names_unique(self) -> None:
        names = []
        for skill in _all_skills():
            text = skill.read_text(encoding="utf-8")
            fields, _ = _parse_frontmatter(text)
            names.append(fields.get("name"))

        assert len(names) == len(set(names)), "Duplicate skill names detected"


# -- Plugin structure ------------------------------------------------


class TestPluginStructure:
    """Validate plugin directory structure."""

    def test_six_skills_exist(self) -> None:
        skills = _all_skills()
        assert len(skills) == 6, f"Expected 6 skills, found {len(skills)}"

    def test_expected_skill_names(self) -> None:
        names = {p.parent.name for p in _all_skills()}
        expected = {
            "author",
            "author-init",
            "author-status",
            "author-generate",
            "author-maintain",
            "author-docs",
        }
        assert names == expected, f"Skill names mismatch: {names ^ expected}"

    def test_doc_writer_agent_exists(self) -> None:
        assert (PLUGIN_ROOT / "agents" / "doc-writer.md").exists()

    def test_post_commit_hook_exists(self) -> None:
        assert (PLUGIN_ROOT / "hooks" / "help_post_commit.py").exists()

    def test_readme_exists(self) -> None:
        assert (PLUGIN_ROOT / "README.md").exists()


# -- Version consistency ---------------------------------------------


class TestVersionConsistency:
    """Validate version matches across all plugin files."""

    def test_versions_match(self) -> None:
        plugin_json = _read_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
        market = _read_json(PLUGIN_ROOT / ".claude-plugin" / "marketplace.json")
        core_init = (PLUGIN_ROOT / "core" / "__init__.py").read_text(encoding="utf-8")
        package_init = PACKAGE_INIT.read_text(encoding="utf-8")

        # Extract __version__ from each Python file
        core_match = re.search(r'__version__\s*=\s*"([^"]+)"', core_init)
        package_match = re.search(r'__version__\s*=\s*"([^"]+)"', package_init)

        assert core_match, "core/__init__.py missing __version__"
        assert package_match, "src/attune_author/__init__.py missing __version__"

        versions = {
            "plugin.json": plugin_json["version"],
            "marketplace.json metadata": market["metadata"]["version"],
            "marketplace.json plugins[0]": market["plugins"][0]["version"],
            "plugin/core/__init__.py": core_match.group(1),
            "src/attune_author/__init__.py": package_match.group(1),
        }

        unique = set(versions.values())
        assert len(unique) == 1, f"Version mismatch: {versions}"
