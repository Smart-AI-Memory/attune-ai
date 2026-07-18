"""Tests for scripts/sync_agents_skills.py.

Validates frontmatter parsing, field filtering, name
validation, and sync output for the agentskills.io
compatibility layer.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Add scripts/ to path so we can import the sync module.
_scripts_dir = Path(__file__).parents[3] / "scripts"
sys.path.insert(0, str(_scripts_dir))

_sync_module = pytest.importorskip(
    "sync_agents_skills",
    reason="scripts/sync_agents_skills.py not found",
)
CLAUDE_CODE_FIELDS = _sync_module.CLAUDE_CODE_FIELDS
build_output = _sync_module.build_output
discover_skills = _sync_module.discover_skills
parse_frontmatter = _sync_module.parse_frontmatter
sync_one = _sync_module.sync_one
validate_name = _sync_module.validate_name

# -----------------------------------------------------------
# parse_frontmatter
# -----------------------------------------------------------


@pytest.mark.unit
class TestParseFrontmatter:
    """Test YAML frontmatter parsing."""

    def test_simple_fields(self) -> None:
        """Test parsing simple key: value fields."""
        text = textwrap.dedent(
            """\
            ---
            name: test-skill
            description: "A test skill"
            license: "Apache-2.0"
            ---

            # Body
        """
        )
        fields, body = parse_frontmatter(text)
        assert "name" in fields
        assert "description" in fields
        assert "license" in fields
        assert "# Body" in body

    def test_nested_metadata(self) -> None:
        """Test parsing nested metadata block."""
        text = textwrap.dedent(
            """\
            ---
            name: test
            metadata:
              author: "Test Author"
              version: "1.0.0"
            ---

            Body content
        """
        )
        fields, body = parse_frontmatter(text)
        assert "metadata" in fields
        assert "author" in fields["metadata"]
        assert "version" in fields["metadata"]

    def test_missing_opening_delimiter(self) -> None:
        """Test error on missing opening ---."""
        text = "name: test\n---\nBody"
        with pytest.raises(ValueError, match="does not start with"):
            parse_frontmatter(text)

    def test_missing_closing_delimiter(self) -> None:
        """Test error on missing closing ---."""
        text = "---\nname: test\nBody without closing"
        with pytest.raises(ValueError, match="No closing"):
            parse_frontmatter(text)

    def test_empty_body(self) -> None:
        """Test file with no body after frontmatter."""
        text = "---\nname: test\n---\n"
        fields, body = parse_frontmatter(text)
        assert "name" in fields
        assert body.strip() == ""

    def test_preserves_field_order(self) -> None:
        """Test that field order is preserved."""
        text = textwrap.dedent(
            """\
            ---
            name: test
            description: "desc"
            license: "MIT"
            ---
        """
        )
        fields, _ = parse_frontmatter(text)
        keys = list(fields.keys())
        assert keys == ["name", "description", "license"]


# -----------------------------------------------------------
# validate_name
# -----------------------------------------------------------


@pytest.mark.unit
class TestValidateName:
    """Test skill name validation against agentskills.io."""

    def test_valid_simple_name(self) -> None:
        """Test valid single-word name."""
        assert validate_name("planning", "planning") == []

    def test_valid_hyphenated_name(self) -> None:
        """Test valid hyphenated name."""
        assert validate_name("code-quality", "code-quality") == []

    def test_valid_name_with_digits(self) -> None:
        """Test valid name with digits."""
        assert validate_name("test2go", "test2go") == []

    def test_name_dir_mismatch(self) -> None:
        """Test name must match directory name."""
        errors = validate_name("code-quality", "other-dir")
        assert any("does not match" in e for e in errors)

    def test_uppercase_rejected(self) -> None:
        """Test uppercase characters are rejected."""
        errors = validate_name("Code-Quality", "Code-Quality")
        assert any("lowercase" in e for e in errors)

    def test_underscore_rejected(self) -> None:
        """Test underscores are rejected."""
        errors = validate_name("code_quality", "code_quality")
        assert any("lowercase" in e for e in errors)

    def test_empty_name(self) -> None:
        """Test empty name is rejected."""
        errors = validate_name("", "empty")
        assert any("empty" in e for e in errors)

    def test_leading_hyphen_rejected(self) -> None:
        """Test leading hyphen is rejected."""
        errors = validate_name("-test", "-test")
        assert len(errors) > 0

    def test_consecutive_hyphens_rejected(self) -> None:
        """Test consecutive hyphens are rejected."""
        errors = validate_name("code--quality", "code--quality")
        assert len(errors) > 0

    def test_max_length_enforced(self) -> None:
        """Test name exceeding 64 chars is rejected."""
        long_name = "a" * 65
        errors = validate_name(long_name, long_name)
        assert any("exceeds" in e for e in errors)

    def test_exact_max_length_allowed(self) -> None:
        """Test name at exactly 64 chars is allowed."""
        name = "a" * 64
        errors = validate_name(name, name)
        assert not any("exceeds" in e for e in errors)


# -----------------------------------------------------------
# build_output
# -----------------------------------------------------------


@pytest.mark.unit
class TestBuildOutput:
    """Test agentskills.io output generation."""

    def test_strips_claude_code_fields(self) -> None:
        """Test that Claude Code-specific fields are removed."""
        fields = {
            "name": "name: test",
            "description": 'description: "Test"',
            "argument-hint": 'argument-hint: "<path>"',
            "disable-model-invocation": ("disable-model-invocation: true"),
            "license": 'license: "Apache-2.0"',
        }
        output = build_output(fields, "\n# Body")
        assert "argument-hint" not in output
        assert "disable-model-invocation" not in output

    def test_keeps_allowed_fields(self) -> None:
        """Test that agentskills.io fields are preserved."""
        fields = {
            "name": "name: test",
            "description": 'description: "Test"',
            "license": 'license: "Apache-2.0"',
            "compatibility": 'compatibility: "Requires X"',
            "metadata": "metadata:\n  author: Test",
        }
        output = build_output(fields, "\n# Body")
        assert "name: test" in output
        assert "license:" in output
        assert "compatibility:" in output
        assert "metadata:" in output

    def test_preserves_body(self) -> None:
        """Test that body content is preserved verbatim."""
        fields = {"name": "name: test"}
        body = "\n# Heading\n\nSome content here."
        output = build_output(fields, body)
        assert "# Heading" in output
        assert "Some content here." in output

    def test_unknown_fields_stripped(self) -> None:
        """Test that unrecognized fields are also stripped."""
        fields = {
            "name": "name: test",
            "custom-field": "custom-field: value",
        }
        output = build_output(fields, "\n# Body")
        assert "custom-field" not in output


# -----------------------------------------------------------
# sync_one
# -----------------------------------------------------------


@pytest.mark.unit
class TestSyncOne:
    """Test single-file sync operation."""

    def test_generates_output(self, tmp_path: Path) -> None:
        """Test that sync generates output file."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            textwrap.dedent(
                """\
            ---
            name: test-skill
            description: "Test"
            argument-hint: "<path>"
            license: "Apache-2.0"
            ---

            # Content
        """
            ),
            encoding="utf-8",
        )

        output_root = tmp_path / "output"
        ok, msg = sync_one(skill_file, output_root)

        assert ok, msg
        assert "generated" in msg
        out_file = output_root / "test-skill" / "SKILL.md"
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "argument-hint" not in content
        assert "license:" in content

    def test_check_mode_missing(self, tmp_path: Path) -> None:
        """Test --check fails when output doesn't exist."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: test-skill\ndescription: T\n---\n",
            encoding="utf-8",
        )

        output_root = tmp_path / "output"
        ok, msg = sync_one(skill_file, output_root, check=True)
        assert not ok
        assert "missing" in msg

    def test_check_mode_in_sync(self, tmp_path: Path) -> None:
        """Test --check passes when output matches."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: test-skill\ndescription: T\n---\n# B",
            encoding="utf-8",
        )

        output_root = tmp_path / "output"
        # Generate first
        sync_one(skill_file, output_root)
        # Then check
        ok, msg = sync_one(skill_file, output_root, check=True)
        assert ok
        assert "in sync" in msg

    def test_invalid_frontmatter(self, tmp_path: Path) -> None:
        """Test error on invalid frontmatter."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("No frontmatter here", encoding="utf-8")

        output_root = tmp_path / "output"
        ok, msg = sync_one(skill_file, output_root)
        assert not ok
        assert "parse error" in msg


# -----------------------------------------------------------
# discover_skills
# -----------------------------------------------------------


@pytest.mark.unit
class TestDiscoverSkills:
    """Test skill discovery from plugin directory."""

    def test_discovers_skills(self, tmp_path: Path) -> None:
        """Test finding SKILL.md files."""
        skills = tmp_path / "skills"
        for name in ("alpha", "beta"):
            d = skills / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\n---\n",
                encoding="utf-8",
            )

        found = discover_skills(tmp_path)
        assert len(found) == 2

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test returns empty for no skills."""
        found = discover_skills(tmp_path)
        assert found == []


# -----------------------------------------------------------
# Integration: real plugin skills
# -----------------------------------------------------------


REPO_ROOT = Path(__file__).parents[3]
PLUGIN_SKILLS = REPO_ROOT / "plugin" / "skills"
CLAUDE_SKILLS = REPO_ROOT / ".claude" / "skills"
AGENTS_SKILLS = REPO_ROOT / ".agents" / "skills"


def _expected_sources() -> dict[str, Path]:
    """Map mirror name -> source SKILL.md, applying shadowing.

    plugin/skills/ wins a name collision; non-shadowed
    .claude/skills/ entries fill in the rest. Mirrors the sync
    script's source resolution.
    """
    sources: dict[str, Path] = {}
    for root in (PLUGIN_SKILLS, CLAUDE_SKILLS):
        for skill_dir in sorted(root.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.exists():
                continue
            if skill_dir.name not in sources:
                sources[skill_dir.name] = skill_file
    return sources


@pytest.mark.unit
class TestAgentSkillsIntegration:
    """Validate .agents/skills/ matches its two source roots."""

    def test_agents_skills_directory_exists(self) -> None:
        """Test that .agents/skills/ directory exists."""
        assert AGENTS_SKILLS.is_dir(), (
            ".agents/skills/ not found. Run: " "python scripts/sync_agents_skills.py"
        )

    def test_all_plugin_skills_synced(self) -> None:
        """Test the mirror set equals plugin ∪ non-shadowed .claude."""
        expected = set(_expected_sources())
        agents = {
            d.name for d in AGENTS_SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
        }
        assert expected == agents, f"Missing: {expected - agents}. " f"Extra: {agents - expected}"

    def test_skill_body_content_matches(self) -> None:
        """Test .agents/ SKILL.md body matches its source copy.

        Frontmatter differs (Claude Code fields stripped), but
        the body content after the closing --- should match.
        """
        for name, source_file in _expected_sources().items():
            agents_file = AGENTS_SKILLS / name / "SKILL.md"
            if not agents_file.exists():
                continue

            def _body(path: Path) -> str:
                parts = path.read_text(encoding="utf-8").split("---", 2)
                return parts[2].strip() if len(parts) >= 3 else ""

            source_body = _body(source_file)
            agents_body = _body(agents_file)
            assert source_body == agents_body, (
                f"{name}/SKILL.md body differs from {source_file}. "
                f"Run: python scripts/sync_agents_skills.py"
            )

    def test_frontmatter_in_sync(self) -> None:
        """Test .agents/ SKILL.md matches sync output exactly.

        ``sync_one`` in check mode compares the full generated
        file (frontmatter *and* body) byte-for-byte. This guards
        against frontmatter drift -- e.g. a ``description`` edited
        in a source SKILL.md but never re-synced -- which the
        body-only and dir-set checks above do not catch.
        """
        for _name, source_file in _expected_sources().items():
            ok, msg = sync_one(source_file, AGENTS_SKILLS, check=True)
            assert ok, f"{msg}. Run: python scripts/sync_agents_skills.py"

    def test_no_claude_code_fields_in_agents(self) -> None:
        """Test .agents/ skills have no Claude Code fields."""
        for skill_dir in AGENTS_SKILLS.iterdir():
            if not skill_dir.is_dir():
                continue
            path = skill_dir / "SKILL.md"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            for field in CLAUDE_CODE_FIELDS:
                assert f"{field}:" not in content, (
                    f"{path} contains Claude Code field " f"'{field}'"
                )

    def test_agents_skills_have_required_fields(self) -> None:
        """Test .agents/ skills have name and description."""
        for skill_dir in AGENTS_SKILLS.iterdir():
            if not skill_dir.is_dir():
                continue
            path = skill_dir / "SKILL.md"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            assert "name:" in content, f"{path} missing 'name' field"
            assert "description:" in content, f"{path} missing 'description' field"
