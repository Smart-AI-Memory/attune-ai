"""Plugin configuration validation.

Validates JSON manifests, .mcp.json, SKILL.md frontmatter,
and version consistency across all plugin files and the
package's pyproject.toml.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugin"
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Anthropic's valid skill frontmatter allowlist (March 2026)
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


def _pyproject_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml missing version"
    return match.group(1)


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

    def test_name_is_attune_help(self, manifest: dict) -> None:
        assert manifest["name"] == "attune-help"

    def test_version_is_semver(self, manifest: dict) -> None:
        assert re.match(r"^\d+\.\d+\.\d+$", manifest["version"])

    def test_author_has_name(self, manifest: dict) -> None:
        assert "name" in manifest["author"]

    def test_description_length(self, manifest: dict) -> None:
        # Plugin.json description isn't under the 250 cap, but
        # keep it short enough to stay readable in marketplace UIs.
        assert 20 <= len(manifest["description"]) <= 300


# -- marketplace.json (plugin-local) --------------------------------


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

    def test_first_plugin_is_attune_help(self, market: dict) -> None:
        assert market["plugins"][0]["name"] == "attune-help"

    def test_metadata_present(self, market: dict) -> None:
        assert "metadata" in market
        assert "version" in market["metadata"]


# -- .mcp.json -------------------------------------------------------


class TestMcpJson:
    """Validate plugin/.mcp.json."""

    @pytest.fixture
    def mcp(self) -> dict:
        return _read_json(PLUGIN_ROOT / ".mcp.json")

    def test_valid_json(self, mcp: dict) -> None:
        assert "mcpServers" in mcp

    def test_has_attune_help_server(self, mcp: dict) -> None:
        assert "attune-help" in mcp["mcpServers"]

    def test_no_hardcoded_secrets(self, mcp: dict) -> None:
        text = json.dumps(mcp)
        forbidden = ("sk-ant-", "sk_live", "AKIA")
        for pattern in forbidden:
            assert pattern not in text, f"Found hardcoded secret: {pattern}"

    def test_uses_uv_not_python_shim(self, mcp: dict) -> None:
        """Lesson: bare `python` resolves to the pyenv shim, not the venv."""
        server = mcp["mcpServers"]["attune-help"]
        assert server["command"] == "uv", (
            "attune-help MCP server must launch via `uv run --from`, "
            "not bare `python` (pyenv shim resolution issue)"
        )

    def test_uv_args_include_plugin_extra(self, mcp: dict) -> None:
        """The plugin needs the [plugin] extra to get mcp>=0.9.0."""
        server = mcp["mcpServers"]["attune-help"]
        args = server.get("args", [])
        assert any("attune-help[plugin]" in arg for arg in args), (
            "uv args must use `--from attune-help[plugin]` so the MCP " "dep is pulled in"
        )


# -- SKILL.md frontmatter --------------------------------------------


class TestSkillFrontmatter:
    """Validate every SKILL.md frontmatter."""

    @pytest.mark.parametrize(
        "skill_path",
        _all_skills(),
        ids=lambda p: p.parent.name,
    )
    def test_skill_has_valid_frontmatter(self, skill_path: Path) -> None:
        text = skill_path.read_text(encoding="utf-8")
        fields, body = _parse_frontmatter(text)

        assert fields, f"No frontmatter found in {skill_path}"
        assert "name" in fields, f"{skill_path}: missing 'name'"
        assert "description" in fields, f"{skill_path}: missing 'description'"

        # Name matches directory
        assert fields["name"] == skill_path.parent.name, (
            f"{skill_path}: name '{fields['name']}' != " f"dir '{skill_path.parent.name}'"
        )

        # Description length (Anthropic truncates >250)
        desc_len = len(fields["description"])
        assert (
            50 <= desc_len <= 250
        ), f"{skill_path}: description is {desc_len} chars (must be 50-250)"

        # Only allowlisted fields
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


# -- Collision safety ------------------------------------------------


class TestNoCollisions:
    """Verify /lookup doesn't collide with attune-ai's /coach or built-ins."""

    BUILTIN_COMMANDS = {
        "batch",
        "compact",
        "config",
        "cost",
        "help",
        "init",
        "login",
        "logout",
        "memory",
        "permissions",
        "review",
        "status",
        "vim",
    }

    # Known names from sibling plugins we explicitly don't collide with
    ATTUNE_AI_SKILLS = {
        "coach",
        "attune",
        "security",
        "smart-test",
        "release",
    }
    ATTUNE_AUTHOR_SKILLS = {
        "author",
        "author-init",
        "author-status",
        "author-generate",
        "author-maintain",
        "author-docs",
    }

    def test_no_builtin_collision(self) -> None:
        for skill in _all_skills():
            name = skill.parent.name
            assert (
                name not in self.BUILTIN_COMMANDS
            ), f"Skill '{name}' collides with Claude Code built-in"

    def test_no_attune_ai_collision(self) -> None:
        for skill in _all_skills():
            name = skill.parent.name
            assert name not in self.ATTUNE_AI_SKILLS, (
                f"Skill '{name}' collides with attune-ai — "
                "users installing both plugins will get conflicting triggers"
            )

    def test_no_attune_author_collision(self) -> None:
        for skill in _all_skills():
            name = skill.parent.name
            assert (
                name not in self.ATTUNE_AUTHOR_SKILLS
            ), f"Skill '{name}' collides with attune-author"


# -- Plugin structure ------------------------------------------------


class TestPluginStructure:
    """Validate plugin directory structure."""

    def test_four_skills_exist(self) -> None:
        skills = _all_skills()
        assert len(skills) == 4, f"Expected 4 skills, found {len(skills)}"

    def test_expected_skill_names(self) -> None:
        names = {p.parent.name for p in _all_skills()}
        expected = {
            "lookup",
            "lookup-topic",
            "lookup-warn",
            "lookup-list",
        }
        assert names == expected, f"Skill names mismatch: {names ^ expected}"

    def test_no_hooks_directory(self) -> None:
        """attune-help intentionally ships no hooks."""
        assert not (PLUGIN_ROOT / "hooks").exists(), (
            "attune-help shouldn't have a hooks/ dir — if you add one, "
            "update this test and test_plugin_config.py::TestHooksJson"
        )

    def test_readme_exists(self) -> None:
        assert (PLUGIN_ROOT / "README.md").exists()

    def test_core_init_exists(self) -> None:
        assert (PLUGIN_ROOT / "core" / "__init__.py").exists()


# -- Version consistency ---------------------------------------------


class TestVersionConsistency:
    """Validate version matches across all plugin files and pyproject.toml."""

    def test_versions_match(self) -> None:
        plugin_json = _read_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
        market = _read_json(PLUGIN_ROOT / ".claude-plugin" / "marketplace.json")
        core_init = (PLUGIN_ROOT / "core" / "__init__.py").read_text(encoding="utf-8")

        core_match = re.search(r'__version__\s*=\s*"([^"]+)"', core_init)
        assert core_match, "plugin/core/__init__.py missing __version__"

        versions = {
            "pyproject.toml": _pyproject_version(),
            "plugin.json": plugin_json["version"],
            "marketplace.json metadata": market["metadata"]["version"],
            "marketplace.json plugins[0]": market["plugins"][0]["version"],
            "plugin/core/__init__.py": core_match.group(1),
        }

        unique = set(versions.values())
        assert len(unique) == 1, f"Version mismatch: {versions}"
