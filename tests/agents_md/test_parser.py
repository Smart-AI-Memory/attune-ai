"""Tests for markdown agent parser."""

import tempfile
from pathlib import Path

import pytest

from attune.agents_md.parser import MarkdownAgentParser
from attune.config.agent_config import ModelTier, Provider


class TestMarkdownAgentParser:
    """Tests for MarkdownAgentParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return MarkdownAgentParser()

    def test_parse_minimal_agent(self, parser):
        """Test parsing a minimal agent definition."""
        content = """---
name: test-agent
---

This is the system prompt.
"""
        config = parser.parse_content(content)

        assert config.name == "test-agent"
        assert config.role == "test-agent"  # Defaults to name
        assert config.model_tier == ModelTier.CAPABLE  # Default
        assert "This is the system prompt" in config.system_prompt

    def test_parse_full_agent(self, parser):
        """Test parsing an agent with all fields."""
        content = """---
name: architect
description: Software architecture specialist
role: architect
model: opus
provider: anthropic
tools: Read, Grep, Glob
empathy_level: 5
memory_enabled: true
pattern_learning: true
temperature: 0.5
max_tokens: 8192
timeout: 180
---

You are an expert software architect.

## Your Role
Design systems.
"""
        config = parser.parse_content(content)

        assert config.name == "architect"
        assert config.description == "Software architecture specialist"
        assert config.role == "architect"
        assert config.model_tier == ModelTier.PREMIUM  # opus -> PREMIUM
        assert config.provider == Provider.ANTHROPIC
        assert "Read" in config.tools
        assert "Grep" in config.tools
        assert "Glob" in config.tools
        assert config.memory_enabled is True
        assert config.pattern_learning is True
        assert config.temperature == 0.5
        assert config.max_tokens == 8192
        assert config.timeout == 180
        assert "expert software architect" in config.system_prompt
        assert "Your Role" in config.system_prompt

    def test_parse_model_tiers(self, parser):
        """Test parsing different model tier names."""
        test_cases = [
            ("cheap", ModelTier.CHEAP),
            ("haiku", ModelTier.CHEAP),
            ("capable", ModelTier.CAPABLE),
            ("sonnet", ModelTier.CAPABLE),
            ("premium", ModelTier.PREMIUM),
            ("opus", ModelTier.PREMIUM),
        ]

        for model_name, expected_tier in test_cases:
            content = f"""---
name: test
model: {model_name}
---
Test.
"""
            config = parser.parse_content(content)
            assert config.model_tier == expected_tier, f"Failed for {model_name}"

    def test_parse_providers(self, parser):
        """Test parsing Anthropic provider."""
        content = """---
name: test
provider: anthropic
---
Test.
"""
        config = parser.parse_content(content)
        assert config.provider == Provider.ANTHROPIC

    def test_parse_tools_as_list(self, parser):
        """Test parsing tools as YAML list."""
        content = """---
name: test
tools:
  - Read
  - Write
  - Edit
---
Test.
"""
        config = parser.parse_content(content)
        assert config.tools == ["Read", "Write", "Edit"]

    def test_parse_tools_as_string(self, parser):
        """Test parsing tools as comma-separated string."""
        content = """---
name: test
tools: Read, Write, Edit
---
Test.
"""
        config = parser.parse_content(content)
        assert "Read" in config.tools
        assert "Write" in config.tools
        assert "Edit" in config.tools

    def test_parse_empty_body(self, parser):
        """Test parsing with empty body."""
        content = """---
name: test
---
"""
        config = parser.parse_content(content)

        assert config.name == "test"
        assert config.system_prompt is None or config.system_prompt == ""

    def test_parse_missing_name_raises(self, parser):
        """Test that missing name raises ValueError."""
        content = """---
description: No name here
---
Test.
"""
        with pytest.raises(ValueError, match="missing required 'name'"):
            parser.parse_content(content)

    def test_parse_no_frontmatter_raises(self, parser):
        """Test that missing frontmatter raises ValueError."""
        content = "Just markdown, no frontmatter."

        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            parser.parse_content(content)

    def test_parse_invalid_yaml_raises(self, parser):
        """Test that invalid YAML raises ValueError."""
        content = """---
name: test
invalid: yaml: syntax:
---
Test.
"""
        with pytest.raises(ValueError, match="Invalid YAML"):
            parser.parse_content(content)

    def test_parse_file(self, parser):
        """Test parsing from a file."""
        content = """---
name: file-agent
description: Loaded from file
---

File-based agent.
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as f:
            f.write(content)
            f.flush()

            config = parser.parse_file(f.name)

            assert config.name == "file-agent"
            assert config.extra["source_file"] == str(Path(f.name).resolve())

    def test_parse_file_not_found(self, parser):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/agent.md")

    def test_validate_file_valid(self, parser):
        """Test validating a valid file."""
        content = """---
name: valid-agent
model: capable
---
Valid agent.
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as f:
            f.write(content)
            f.flush()

            errors = parser.validate_file(f.name)
            assert errors == []

    def test_validate_file_missing_name(self, parser):
        """Test validation catches missing name."""
        content = """---
description: No name
---
Invalid.
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as f:
            f.write(content)
            f.flush()

            errors = parser.validate_file(f.name)
            assert any("name" in e.lower() for e in errors)

    def test_validate_file_invalid_model(self, parser):
        """Test validation catches invalid model."""
        content = """---
name: test
model: invalid_model_tier
---
Test.
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as f:
            f.write(content)
            f.flush()

            errors = parser.validate_file(f.name)
            assert any("model" in e.lower() for e in errors)

    def test_validate_file_ignores_legacy_empathy_level(self, parser):
        """A legacy empathy_level key is ignored, not a validation error."""
        content = """---
name: test
model: capable
empathy_level: 10
---
Test.
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as f:
            f.write(content)
            f.flush()

            errors = parser.validate_file(f.name)
            assert not any("empathy_level" in e for e in errors)

    def test_extra_contains_source_and_raw(self, parser):
        """Test that extra contains source_file and raw_frontmatter."""
        content = """---
name: test
custom_field: custom_value
---
Test.
"""
        config = parser.parse_content(content, source="test.md")

        assert config.extra["source_file"] == "test.md"
        assert "raw_frontmatter" in config.extra
        assert config.extra["raw_frontmatter"]["custom_field"] == "custom_value"

    def test_parse_capabilities_as_string(self, parser):
        """Test parsing capabilities as a comma-separated string (line 169)."""
        content = """---
name: test
capabilities: code_review, testing, docs
---
Test.
"""
        config = parser.parse_content(content)
        assert config.capabilities == ["code_review", "testing", "docs"]

    def test_parse_capabilities_as_list(self, parser):
        """Test parsing capabilities as a YAML list (default codepath)."""
        content = """---
name: test
capabilities:
  - code_review
  - testing
---
Test.
"""
        config = parser.parse_content(content)
        assert config.capabilities == ["code_review", "testing"]

    def test_validate_file_invalid_path(self, parser):
        """Test validation catches an invalid file path (null byte, lines 219-220)."""
        errors = parser.validate_file("bad\x00path.md")

        assert len(errors) == 1
        assert "Invalid file path" in errors[0]

    def test_validate_file_not_found(self, parser, tmp_path):
        """Test validation catches a nonexistent file (line 223)."""
        missing = tmp_path / "does_not_exist.md"

        errors = parser.validate_file(str(missing))

        assert len(errors) == 1
        assert "File not found" in errors[0]

    def test_validate_file_read_error(self, parser, tmp_path):
        """Test validation catches an OSError while reading (lines 228-229).

        A directory that exists but cannot be opened as a file (via
        ``open()``) reaches the file-exists check and then raises
        ``IsADirectoryError``, a subclass of ``OSError``.
        """
        directory = tmp_path / "a_directory.md"
        directory.mkdir()

        errors = parser.validate_file(str(directory))

        assert len(errors) == 1
        assert "Cannot read file" in errors[0]

    def test_validate_file_missing_frontmatter(self, parser, tmp_path):
        """Test validation catches a file with no YAML frontmatter (lines 234-235)."""
        agent_file = tmp_path / "no_frontmatter.md"
        agent_file.write_text("Just markdown, no frontmatter at all.")

        errors = parser.validate_file(str(agent_file))

        assert errors == ["Missing YAML frontmatter (must start with ---)"]

    def test_validate_file_invalid_yaml(self, parser, tmp_path):
        """Test validation catches malformed YAML frontmatter (lines 242-244)."""
        agent_file = tmp_path / "bad_yaml.md"
        agent_file.write_text(
            """---
name: test
invalid: yaml: syntax:
---
Test.
"""
        )

        errors = parser.validate_file(str(agent_file))

        assert len(errors) == 1
        assert "Invalid YAML" in errors[0]

    def test_validate_file_invalid_provider(self, parser, tmp_path):
        """Test validation catches an invalid provider (line 260)."""
        agent_file = tmp_path / "bad_provider.md"
        agent_file.write_text(
            """---
name: test
provider: not_a_real_provider
---
Test.
"""
        )

        errors = parser.validate_file(str(agent_file))

        assert any("provider" in e.lower() for e in errors)

    def test_parse_content_ignores_legacy_empathy_level(self, parser):
        """A legacy empathy_level key does not reach the config model."""
        config = parser.parse_content(
            """---
name: test
model: capable
empathy_level: 4
---
Test.
"""
        )

        assert not hasattr(config, "empathy_level")
