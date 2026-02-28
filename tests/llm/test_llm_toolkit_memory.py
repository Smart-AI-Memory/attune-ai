"""Tests for empathy_llm_toolkit claude_memory module.

Comprehensive test coverage for ClaudeMemoryConfig, MemoryFile,
ClaudeMemoryLoader, and create_default_project_memory.

Created: 2026-01-20
Coverage target: 80%+
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.memory.claude_memory import (
    ClaudeMemoryConfig,
    ClaudeMemoryLoader,
    MemoryFile,
    create_default_project_memory,
)

# =============================================================================
# ClaudeMemoryConfig Tests
# =============================================================================


class TestClaudeMemoryConfig:
    """Tests for ClaudeMemoryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ClaudeMemoryConfig()

        assert config.enabled is False
        assert config.load_enterprise is True
        assert config.load_user is True
        assert config.load_project is True
        assert config.enterprise_memory_path is None
        assert config.project_root is None
        assert config.max_import_depth == 5
        assert config.max_file_size_bytes == 1_000_000
        assert config.validate_files is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ClaudeMemoryConfig(
            enabled=True,
            load_enterprise=False,
            load_user=False,
            load_project=True,
            enterprise_memory_path="/custom/path",
            project_root="/project",
            max_import_depth=10,
            max_file_size_bytes=2_000_000,
            validate_files=False,
        )

        assert config.enabled is True
        assert config.load_enterprise is False
        assert config.load_user is False
        assert config.load_project is True
        assert config.enterprise_memory_path == "/custom/path"
        assert config.project_root == "/project"
        assert config.max_import_depth == 10
        assert config.max_file_size_bytes == 2_000_000
        assert config.validate_files is False


# =============================================================================
# MemoryFile Tests
# =============================================================================


class TestMemoryFile:
    """Tests for MemoryFile dataclass."""

    def test_creation(self):
        """Test creating a MemoryFile."""
        memory = MemoryFile(
            level="project",
            path="/path/to/CLAUDE.md",
            content="# Project Memory",
        )

        assert memory.level == "project"
        assert memory.path == "/path/to/CLAUDE.md"
        assert memory.content == "# Project Memory"
        assert memory.imports == []
        assert memory.load_order == 0

    def test_with_imports(self):
        """Test MemoryFile with imports."""
        memory = MemoryFile(
            level="project",
            path="/path/to/CLAUDE.md",
            content="# Memory with imports",
            imports=["/path/to/import1.md", "/path/to/import2.md"],
            load_order=3,
        )

        assert len(memory.imports) == 2
        assert "/path/to/import1.md" in memory.imports
        assert memory.load_order == 3


# =============================================================================
# ClaudeMemoryLoader Tests
# =============================================================================


class TestClaudeMemoryLoader:
    """Tests for ClaudeMemoryLoader class."""

    def test_init_default(self):
        """Test initialization with default config."""
        loader = ClaudeMemoryLoader()

        assert loader.config.enabled is False
        assert loader._memory_cache == {}
        assert loader._import_stack == []

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = ClaudeMemoryConfig(enabled=True, max_import_depth=10)
        loader = ClaudeMemoryLoader(config)

        assert loader.config.enabled is True
        assert loader.config.max_import_depth == 10

    def test_load_all_memory_disabled(self):
        """Test that disabled config returns empty string."""
        config = ClaudeMemoryConfig(enabled=False)
        loader = ClaudeMemoryLoader(config)

        result = loader.load_all_memory()

        assert result == ""

    def test_load_all_memory_enabled(self, tmp_path):
        """Test loading memory when enabled."""
        # Create project memory file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        memory_file = claude_dir / "CLAUDE.md"
        memory_file.write_text("# Project Memory\nTest content")

        config = ClaudeMemoryConfig(
            enabled=True,
            load_enterprise=False,
            load_user=False,
            load_project=True,
            project_root=str(tmp_path),
        )
        loader = ClaudeMemoryLoader(config)

        result = loader.load_all_memory(str(tmp_path))

        assert "Project Memory" in result
        assert "Test content" in result
        assert "PROJECT Level" in result

    def test_load_all_memory_no_files(self, tmp_path):
        """Test loading memory when no files exist."""
        config = ClaudeMemoryConfig(
            enabled=True,
            load_enterprise=False,
            load_user=False,
            load_project=True,
            project_root=str(tmp_path),
        )
        loader = ClaudeMemoryLoader(config)

        result = loader.load_all_memory(str(tmp_path))

        assert result == ""

    def test_load_project_memory_from_claude_dir(self, tmp_path):
        """Test loading project memory from .claude directory."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        memory_file = claude_dir / "CLAUDE.md"
        memory_file.write_text("# Claude Dir Memory")

        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        result = loader._load_project_memory(str(tmp_path))

        assert result is not None
        assert result.level == "project"
        assert "Claude Dir Memory" in result.content

    def test_load_project_memory_from_root(self, tmp_path):
        """Test loading project memory from project root fallback."""
        memory_file = tmp_path / "CLAUDE.md"
        memory_file.write_text("# Root Memory")

        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        result = loader._load_project_memory(str(tmp_path))

        assert result is not None
        assert "Root Memory" in result.content

    def test_load_project_memory_not_found(self, tmp_path):
        """Test that missing project memory returns None."""
        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        result = loader._load_project_memory(str(tmp_path))

        assert result is None

    def test_load_user_memory_not_found(self):
        """Test that missing user memory returns None."""
        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        # Mock Path.home() to a non-existent directory
        with patch.object(Path, "home", return_value=Path("/nonexistent/home")):
            result = loader._load_user_memory()

        assert result is None

    def test_load_enterprise_memory_from_env(self, tmp_path):
        """Test loading enterprise memory from environment variable."""
        memory_file = tmp_path / "enterprise.md"
        memory_file.write_text("# Enterprise Memory")

        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        with patch.dict(os.environ, {"CLAUDE_ENTERPRISE_MEMORY": str(memory_file)}):
            result = loader._load_enterprise_memory()

        assert result is not None
        assert result.level == "enterprise"
        assert "Enterprise Memory" in result.content

    def test_load_enterprise_memory_from_config(self, tmp_path):
        """Test loading enterprise memory from config path."""
        memory_file = tmp_path / "enterprise.md"
        memory_file.write_text("# Enterprise Config Memory")

        config = ClaudeMemoryConfig(
            enabled=True,
            enterprise_memory_path=str(memory_file),
        )
        loader = ClaudeMemoryLoader(config)

        # Clear any environment variable
        with patch.dict(os.environ, {}, clear=True):
            result = loader._load_enterprise_memory()

        assert result is not None
        assert "Enterprise Config Memory" in result.content

    def test_load_enterprise_memory_not_found(self):
        """Test that missing enterprise memory returns None."""
        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        with patch.dict(os.environ, {}, clear=True):
            result = loader._load_enterprise_memory()

        assert result is None


class TestClaudeMemoryLoaderImports:
    """Tests for import processing in ClaudeMemoryLoader."""

    def test_process_imports_basic(self, tmp_path):
        """Test processing basic @import directive."""
        # Create imported file
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir()
        imported_file = imports_dir / "shared.md"
        imported_file.write_text("# Shared Content\nImported text")

        # Create main file with import
        main_file = tmp_path / "CLAUDE.md"
        main_file.write_text("# Main\n@imports/shared.md\nAfter import")

        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        result = loader._load_memory_file(str(main_file), "project")

        assert result is not None
        assert "Shared Content" in result.content
        assert "Imported text" in result.content
        assert "Main" in result.content
        assert str(imported_file.resolve()) in result.imports

    def test_process_imports_not_found(self, tmp_path):
        """Test handling import that doesn't exist."""
        main_file = tmp_path / "CLAUDE.md"
        main_file.write_text("# Main\n@nonexistent.md\nAfter")

        config = ClaudeMemoryConfig(enabled=True, validate_files=False)
        loader = ClaudeMemoryLoader(config)

        result = loader._load_memory_file(str(main_file), "project")

        assert result is not None
        assert "Import not found" in result.content

    def test_circular_import_detection(self, tmp_path):
        """Test that circular imports are detected."""
        file_a = tmp_path / "a.md"
        file_b = tmp_path / "b.md"

        file_a.write_text("# File A\n@b.md")
        file_b.write_text("# File B\n@a.md")

        config = ClaudeMemoryConfig(enabled=True, validate_files=False)
        loader = ClaudeMemoryLoader(config)

        # Load file a which imports b which imports a
        result = loader._load_memory_file(str(file_a), "project")

        # Should not cause infinite loop
        assert result is not None
        # File B should be imported
        assert "File B" in result.content
        # But circular import of A from B should be handled
        assert "Import failed" in result.content or result.content.count("File A") == 1

    def test_import_depth_exceeded(self, tmp_path):
        """Test that import depth limit is enforced."""
        config = ClaudeMemoryConfig(
            enabled=True,
            max_import_depth=2,
            validate_files=False,
        )
        loader = ClaudeMemoryLoader(config)

        # Create chain of imports deeper than limit
        files = []
        for i in range(5):
            file = tmp_path / f"level{i}.md"
            if i < 4:
                file.write_text(f"# Level {i}\n@level{i + 1}.md")
            else:
                file.write_text(f"# Level {i}")
            files.append(file)

        result = loader._load_memory_file(str(files[0]), "project")

        # Should load but stop at depth limit
        assert result is not None
        assert "Level 0" in result.content


class TestClaudeMemoryLoaderFileHandling:
    """Tests for file handling in ClaudeMemoryLoader."""

    def test_file_too_large(self, tmp_path):
        """Test that oversized files are rejected."""
        large_file = tmp_path / "large.md"
        large_file.write_text("x" * 100)  # 100 bytes

        config = ClaudeMemoryConfig(
            enabled=True,
            max_file_size_bytes=50,  # Limit to 50 bytes
        )
        loader = ClaudeMemoryLoader(config)

        result = loader._load_memory_file(str(large_file), "project")

        assert result is None

    def test_file_caching(self, tmp_path):
        """Test that files are cached after first load."""
        memory_file = tmp_path / "CLAUDE.md"
        memory_file.write_text("# Cached Content")

        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        # First load
        result1 = loader._load_memory_file(str(memory_file), "project")

        # Modify file (but cache should be used)
        memory_file.write_text("# Modified Content")

        # Second load should return cached version
        result2 = loader._load_memory_file(str(memory_file), "project")

        assert result1 is result2  # Same object from cache
        assert "Cached Content" in result2.content

    def test_clear_cache(self, tmp_path):
        """Test cache clearing."""
        memory_file = tmp_path / "CLAUDE.md"
        memory_file.write_text("# Original")

        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        # Load file
        loader._load_memory_file(str(memory_file), "project")
        assert len(loader._memory_cache) == 1

        # Clear cache
        loader.clear_cache()

        assert len(loader._memory_cache) == 0

    def test_get_loaded_files(self, tmp_path):
        """Test getting list of loaded files."""
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file1.write_text("# File 1")
        file2.write_text("# File 2")

        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        loader._load_memory_file(str(file1), "project")
        loader._load_memory_file(str(file2), "project")

        loaded = loader.get_loaded_files()

        assert len(loaded) == 2
        assert str(file1) in loaded
        assert str(file2) in loaded

    def test_file_not_found(self):
        """Test loading non-existent file."""
        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        result = loader._load_memory_file("/nonexistent/path.md", "project")

        assert result is None


class TestClaudeMemoryLoaderCombine:
    """Tests for memory file combination."""

    def test_combine_empty_list(self):
        """Test combining empty list."""
        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        result = loader._combine_memory_files([])

        assert result == ""

    def test_combine_single_file(self):
        """Test combining single file."""
        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        memory = MemoryFile(
            level="project",
            path="/test/CLAUDE.md",
            content="# Test Content",
            load_order=1,
        )

        result = loader._combine_memory_files([memory])

        assert "PROJECT Level" in result
        assert "/test/CLAUDE.md" in result
        assert "Test Content" in result

    def test_combine_multiple_files(self):
        """Test combining multiple files in order."""
        config = ClaudeMemoryConfig(enabled=True)
        loader = ClaudeMemoryLoader(config)

        enterprise = MemoryFile(
            level="enterprise",
            path="/enterprise.md",
            content="# Enterprise",
            load_order=1,
        )
        user = MemoryFile(
            level="user",
            path="/user.md",
            content="# User",
            load_order=2,
        )
        project = MemoryFile(
            level="project",
            path="/project.md",
            content="# Project",
            load_order=3,
        )

        result = loader._combine_memory_files([enterprise, user, project])

        # All levels should be present
        assert "ENTERPRISE Level" in result
        assert "USER Level" in result
        assert "PROJECT Level" in result

        # Order should be preserved
        enterprise_pos = result.find("ENTERPRISE")
        user_pos = result.find("USER")
        project_pos = result.find("PROJECT")

        assert enterprise_pos < user_pos < project_pos


class TestClaudeMemoryLoaderErrorHandling:
    """Tests for error handling in ClaudeMemoryLoader."""

    def test_load_with_validation_enabled_raises(self, tmp_path):
        """Test that validation errors are raised when enabled."""
        # Create file that will cause an error when reading
        bad_file = tmp_path / "bad.md"
        bad_file.write_bytes(b"\xff\xfe")  # Invalid UTF-8

        config = ClaudeMemoryConfig(enabled=True, validate_files=True)
        loader = ClaudeMemoryLoader(config)

        with pytest.raises(Exception):
            loader._load_memory_file(str(bad_file), "project")

    def test_load_with_validation_disabled_returns_none(self, tmp_path):
        """Test that errors return None when validation disabled."""
        # Create file that will cause an error when reading
        bad_file = tmp_path / "bad.md"
        bad_file.write_bytes(b"\xff\xfe")  # Invalid UTF-8

        config = ClaudeMemoryConfig(enabled=True, validate_files=False)
        loader = ClaudeMemoryLoader(config)

        result = loader._load_memory_file(str(bad_file), "project")

        assert result is None


# =============================================================================
# create_default_project_memory Tests
# =============================================================================


class TestCreateDefaultProjectMemory:
    """Tests for create_default_project_memory function."""

    def test_creates_directory_and_file(self, tmp_path):
        """Test that .claude directory and CLAUDE.md are created."""
        create_default_project_memory(str(tmp_path), framework="empathy")

        claude_dir = tmp_path / ".claude"
        memory_file = claude_dir / "CLAUDE.md"

        assert claude_dir.exists()
        assert memory_file.exists()

    def test_empathy_framework_content(self, tmp_path):
        """Test Attune AI default content."""
        create_default_project_memory(str(tmp_path), framework="empathy")

        memory_file = tmp_path / ".claude" / "CLAUDE.md"
        content = memory_file.read_text()

        assert "Attune AI" in content
        assert "PEP 8" in content
        assert "type hints" in content
        assert "90%+ test coverage" in content
        assert "PII" in content
        assert "async/await" in content

    def test_generic_framework_content(self, tmp_path):
        """Test generic framework default content."""
        create_default_project_memory(str(tmp_path), framework="other")

        memory_file = tmp_path / ".claude" / "CLAUDE.md"
        content = memory_file.read_text()

        assert "Project Memory" in content
        assert "Project Context" in content
        assert "@imports" in content

    def test_does_not_overwrite_existing(self, tmp_path):
        """Test that existing file is not overwritten."""
        # Create existing file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        memory_file = claude_dir / "CLAUDE.md"
        memory_file.write_text("# Existing Content")

        create_default_project_memory(str(tmp_path), framework="empathy")

        # Should still have original content
        content = memory_file.read_text()
        assert content == "# Existing Content"

    def test_creates_in_nested_directory(self, tmp_path):
        """Test creating memory in nested project directory."""
        nested = tmp_path / "projects" / "my-project"
        nested.mkdir(parents=True)

        create_default_project_memory(str(nested), framework="empathy")

        memory_file = nested / ".claude" / "CLAUDE.md"
        assert memory_file.exists()


# =============================================================================
# Integration Tests
# =============================================================================


class TestClaudeMemoryIntegration:
    """Integration tests for Claude memory system."""

    def test_full_hierarchy_loading(self, tmp_path):
        """Test loading full memory hierarchy."""
        # Create enterprise memory
        enterprise_file = tmp_path / "enterprise.md"
        enterprise_file.write_text("# Enterprise Standards")

        # Create user memory (mock home dir)
        user_dir = tmp_path / "home" / ".claude"
        user_dir.mkdir(parents=True)
        user_file = user_dir / "CLAUDE.md"
        user_file.write_text("# User Preferences")

        # Create project memory
        project_dir = tmp_path / "project" / ".claude"
        project_dir.mkdir(parents=True)
        project_file = project_dir / "CLAUDE.md"
        project_file.write_text("# Project Config")

        config = ClaudeMemoryConfig(
            enabled=True,
            enterprise_memory_path=str(enterprise_file),
        )
        loader = ClaudeMemoryLoader(config)

        # Mock user home to our temp directory
        with patch.object(Path, "home", return_value=tmp_path / "home"):
            result = loader.load_all_memory(str(tmp_path / "project"))

        # All three levels should be present
        assert "Enterprise Standards" in result
        assert "User Preferences" in result
        assert "Project Config" in result

    def test_memory_with_nested_imports(self, tmp_path):
        """Test memory with nested import structure."""
        # Create shared standards
        shared_dir = tmp_path / "shared"
        shared_dir.mkdir()

        coding_standards = shared_dir / "coding.md"
        coding_standards.write_text("# Coding Standards\n- Use type hints")

        security_standards = shared_dir / "security.md"
        security_standards.write_text("# Security\n- Never commit secrets")

        # Create main memory that imports both
        main_file = tmp_path / ".claude" / "CLAUDE.md"
        main_file.parent.mkdir()
        main_file.write_text(
            "# Main\n@../shared/coding.md\n@../shared/security.md\n## Project Specific",
        )

        config = ClaudeMemoryConfig(
            enabled=True,
            load_enterprise=False,
            load_user=False,
        )
        loader = ClaudeMemoryLoader(config)

        result = loader.load_all_memory(str(tmp_path))

        assert "Coding Standards" in result
        assert "type hints" in result
        assert "Security" in result
        assert "secrets" in result
        assert "Project Specific" in result
