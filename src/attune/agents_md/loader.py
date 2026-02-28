"""Agent Loader

Loads agents from directory structures.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from collections.abc import Iterator
from pathlib import Path

from attune.agents_md.parser import MarkdownAgentParser
from attune.config.agent_config import UnifiedAgentConfig

logger = logging.getLogger(__name__)


class AgentLoader:
    """Loader for discovering and loading markdown agent files.

    Scans directories for .md files with agent definitions and loads them
    into UnifiedAgentConfig instances.

    Example:
        loader = AgentLoader()

        # Load a single agent
        config = loader.load("agents/architect.md")

        # Load all agents from a directory
        agents = loader.load_directory("agents/")

        # Discover and iterate agents lazily
        for config in loader.discover("agents/"):
            print(config.name)

    """

    def __init__(self, parser: MarkdownAgentParser | None = None):
        """Initialize the loader.

        Args:
            parser: Optional custom parser instance

        """
        self.parser = parser or MarkdownAgentParser()

    def load(self, file_path: str | Path) -> UnifiedAgentConfig:
        """Load a single agent file.

        Args:
            file_path: Path to the agent markdown file

        Returns:
            UnifiedAgentConfig instance

        """
        return self.parser.parse_file(file_path)

    def load_directory(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> dict[str, UnifiedAgentConfig]:
        """Load all agents from a directory.

        Args:
            directory: Directory to scan for .md files
            recursive: If True, scan subdirectories

        Returns:
            Dictionary mapping agent names to configs

        """
        agents = {}

        for config in self.discover(directory, recursive=recursive):
            if config.name in agents:
                logger.warning(
                    "Duplicate agent name '%s' - keeping first occurrence",
                    config.name,
                )
                continue
            agents[config.name] = config

        logger.info("Loaded %d agent(s) from %s", len(agents), directory)
        return agents

    def discover(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> Iterator[UnifiedAgentConfig]:
        """Discover and yield agents from a directory.

        Args:
            directory: Directory to scan
            recursive: If True, scan subdirectories

        Yields:
            UnifiedAgentConfig instances

        """
        directory = Path(directory)

        if not directory.exists():
            logger.warning("Agent directory not found: %s", directory)
            return

        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Get pattern for globbing
        pattern = "**/*.md" if recursive else "*.md"

        for file_path in sorted(directory.glob(pattern)):
            if not file_path.is_file():
                continue

            # Skip files that don't look like agent definitions
            if file_path.name.startswith("_"):
                continue
            if file_path.name.upper() in ("README.MD", "CHANGELOG.MD"):
                continue

            try:
                config = self.parser.parse_file(file_path)
                yield config
            except ValueError as e:
                logger.warning("Skipping invalid agent file %s: %s", file_path, e)
            except Exception as e:
                logger.error("Error loading agent file %s: %s", file_path, e)

    def validate_directory(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> dict[str, list[str]]:
        """Validate all agent files in a directory.

        Args:
            directory: Directory to validate
            recursive: If True, scan subdirectories

        Returns:
            Dictionary mapping file paths to lists of errors

        """
        directory = Path(directory)
        results = {}

        pattern = "**/*.md" if recursive else "*.md"

        for file_path in sorted(directory.glob(pattern)):
            if not file_path.is_file():
                continue
            if file_path.name.startswith("_"):
                continue
            if file_path.name.upper() in ("README.MD", "CHANGELOG.MD"):
                continue

            errors = self.parser.validate_file(file_path)
            if errors:
                results[str(file_path)] = errors

        return results

    def get_agent_names(
        self,
        directory: str | Path,
        recursive: bool = False,
    ) -> list[str]:
        """Get list of agent names in a directory without fully loading.

        Args:
            directory: Directory to scan
            recursive: If True, scan subdirectories

        Returns:
            List of agent names

        """
        names = []
        for config in self.discover(directory, recursive=recursive):
            names.append(config.name)
        return names


def load_agents_from_paths(
    paths: list[str | Path],
    parser: MarkdownAgentParser | None = None,
) -> dict[str, UnifiedAgentConfig]:
    """Load agents from multiple paths (files or directories).

    Args:
        paths: List of file or directory paths
        parser: Optional custom parser

    Returns:
        Dictionary mapping agent names to configs

    """
    loader = AgentLoader(parser=parser)
    agents = {}

    for path in paths:
        path = Path(path)

        if path.is_file():
            config = loader.load(path)
            agents[config.name] = config
        elif path.is_dir():
            dir_agents = loader.load_directory(path)
            agents.update(dir_agents)
        else:
            logger.warning("Path not found: %s", path)

    return agents
