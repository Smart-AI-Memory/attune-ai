"""Tests for agent loader."""

import tempfile
from pathlib import Path

import pytest

from attune_llm.agents_md.loader import AgentLoader, load_agents_from_paths


class TestAgentLoader:
    """Tests for AgentLoader."""

    @pytest.fixture
    def loader(self):
        """Create a loader instance."""
        return AgentLoader()

    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary directory with agent files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create valid agent files
            (tmpdir / "agent1.md").write_text(
                """---
name: agent1
description: First agent
---
Agent 1 instructions.
"""
            )
            (tmpdir / "agent2.md").write_text(
                """---
name: agent2
description: Second agent
model: opus
---
Agent 2 instructions.
"""
            )

            # Create a subdirectory with an agent
            subdir = tmpdir / "subdir"
            subdir.mkdir()
            (subdir / "agent3.md").write_text(
                """---
name: agent3
description: Nested agent
---
Agent 3 instructions.
"""
            )

            # Create files that should be skipped
            (tmpdir / "README.md").write_text("# README\nNot an agent.")
            (tmpdir / "_private.md").write_text(
                """---
name: private
---
Should be skipped.
"""
            )

            yield tmpdir

    def test_load_single_file(self, loader, temp_agents_dir):
        """Test loading a single agent file."""
        config = loader.load(temp_agents_dir / "agent1.md")

        assert config.name == "agent1"
        assert config.description == "First agent"

    def test_load_directory(self, loader, temp_agents_dir):
        """Test loading all agents from a directory."""
        agents = loader.load_directory(temp_agents_dir)

        assert len(agents) == 2
        assert "agent1" in agents
        assert "agent2" in agents
        # README.md and _private.md should be skipped

    def test_load_directory_recursive(self, loader, temp_agents_dir):
        """Test recursive directory loading."""
        agents = loader.load_directory(temp_agents_dir, recursive=True)

        assert len(agents) == 3
        assert "agent1" in agents
        assert "agent2" in agents
        assert "agent3" in agents

    def test_load_directory_nonexistent(self, loader):
        """Test loading from nonexistent directory."""
        agents = loader.load_directory("/nonexistent/path")

        assert agents == {}

    def test_load_directory_not_a_directory(self, loader, temp_agents_dir):
        """Test error when path is not a directory."""
        with pytest.raises(ValueError, match="Not a directory"):
            loader.load_directory(temp_agents_dir / "agent1.md")

    def test_discover_yields_configs(self, loader, temp_agents_dir):
        """Test discover yields configs lazily."""
        configs = list(loader.discover(temp_agents_dir))

        assert len(configs) == 2
        names = [c.name for c in configs]
        assert "agent1" in names
        assert "agent2" in names

    def test_discover_skips_readme(self, loader, temp_agents_dir):
        """Test that README.md is skipped."""
        configs = list(loader.discover(temp_agents_dir))
        names = [c.name for c in configs]

        assert "README" not in str(names)

    def test_discover_skips_private(self, loader, temp_agents_dir):
        """Test that files starting with _ are skipped."""
        configs = list(loader.discover(temp_agents_dir))
        names = [c.name for c in configs]

        assert "private" not in names

    def test_validate_directory(self, loader, temp_agents_dir):
        """Test validating a directory of agents."""
        # Add an invalid agent
        (temp_agents_dir / "invalid.md").write_text(
            """---
description: No name
---
Invalid.
"""
        )

        errors = loader.validate_directory(temp_agents_dir)

        assert len(errors) == 1
        assert "invalid.md" in list(errors.keys())[0]

    def test_get_agent_names(self, loader, temp_agents_dir):
        """Test getting just agent names."""
        names = loader.get_agent_names(temp_agents_dir)

        assert sorted(names) == ["agent1", "agent2"]

    def test_duplicate_names_warning(self, loader, temp_agents_dir):
        """Test that duplicate agent names are handled."""
        # Create a duplicate
        (temp_agents_dir / "agent1_copy.md").write_text(
            """---
name: agent1
description: Duplicate
---
Duplicate.
"""
        )

        agents = loader.load_directory(temp_agents_dir)

        # Should still have only one agent1 (first one loaded)
        assert len([k for k in agents if k == "agent1"]) == 1


class TestLoadAgentsFromPaths:
    """Tests for load_agents_from_paths helper."""

    def test_load_from_mixed_paths(self):
        """Test loading from files and directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a file
            file_path = tmpdir / "single.md"
            file_path.write_text(
                """---
name: single
---
Single agent.
"""
            )

            # Create a directory with agents
            dir_path = tmpdir / "agents"
            dir_path.mkdir()
            (dir_path / "dir_agent.md").write_text(
                """---
name: dir-agent
---
Directory agent.
"""
            )

            agents = load_agents_from_paths([file_path, dir_path])

            assert len(agents) == 2
            assert "single" in agents
            assert "dir-agent" in agents

    def test_load_from_nonexistent_path(self):
        """Test that nonexistent paths are handled gracefully."""
        agents = load_agents_from_paths(["/nonexistent/path"])

        assert agents == {}
