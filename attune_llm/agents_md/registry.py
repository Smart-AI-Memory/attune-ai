"""Agent Registry

Central registry for managing available agents.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from attune_llm.agents_md.loader import AgentLoader
from attune_llm.config.unified import UnifiedAgentConfig

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for agent configurations.

    Provides a single point of access for all available agents,
    supporting both programmatic registration and directory loading.

    Example:
        # Create registry and load agents
        registry = AgentRegistry()
        registry.load_from_directory("agents/")

        # Get an agent by name
        architect = registry.get("architect")

        # Register a custom agent
        registry.register(my_custom_config)

        # List all available agents
        for name in registry.list_agents():
            print(name)
    """

    _instance: "AgentRegistry | None" = None

    def __init__(self):
        """Initialize the registry."""
        self._agents: dict[str, UnifiedAgentConfig] = {}
        self._loader = AgentLoader()
        self._load_paths: list[Path] = []

    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """Get the singleton registry instance.

        Returns:
            The global AgentRegistry instance

        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None

    def register(
        self,
        config: UnifiedAgentConfig,
        overwrite: bool = False,
    ) -> None:
        """Register an agent configuration.

        Args:
            config: Agent configuration to register
            overwrite: If True, overwrite existing agent with same name

        Raises:
            ValueError: If agent name already exists and overwrite=False

        """
        if config.name in self._agents and not overwrite:
            raise ValueError(
                f"Agent '{config.name}' already registered. Use overwrite=True to replace."
            )

        self._agents[config.name] = config
        logger.debug("Registered agent: %s", config.name)

    def unregister(self, name: str) -> bool:
        """Unregister an agent by name.

        Args:
            name: Agent name to remove

        Returns:
            True if agent was found and removed

        """
        if name in self._agents:
            del self._agents[name]
            logger.debug("Unregistered agent: %s", name)
            return True
        return False

    def get(self, name: str) -> UnifiedAgentConfig | None:
        """Get an agent configuration by name.

        Args:
            name: Agent name

        Returns:
            Agent config or None if not found

        """
        return self._agents.get(name)

    def get_required(self, name: str) -> UnifiedAgentConfig:
        """Get an agent configuration, raising if not found.

        Args:
            name: Agent name

        Returns:
            Agent configuration

        Raises:
            KeyError: If agent not found

        """
        config = self.get(name)
        if config is None:
            available = ", ".join(sorted(self._agents.keys()))
            raise KeyError(f"Agent '{name}' not found. Available agents: {available}")
        return config

    def has(self, name: str) -> bool:
        """Check if an agent is registered.

        Args:
            name: Agent name

        Returns:
            True if agent exists

        """
        return name in self._agents

    def list_agents(self) -> list[str]:
        """Get list of all registered agent names.

        Returns:
            Sorted list of agent names

        """
        return sorted(self._agents.keys())

    def iter_agents(self) -> Iterator[UnifiedAgentConfig]:
        """Iterate over all registered agents.

        Yields:
            Agent configurations

        """
        for name in sorted(self._agents.keys()):
            yield self._agents[name]

    def load_from_directory(
        self,
        directory: str | Path,
        recursive: bool = False,
        overwrite: bool = False,
    ) -> int:
        """Load agents from a directory.

        Args:
            directory: Directory containing .md agent files
            recursive: If True, scan subdirectories
            overwrite: If True, overwrite existing agents

        Returns:
            Number of agents loaded

        """
        directory = Path(directory)
        self._load_paths.append(directory)

        agents = self._loader.load_directory(directory, recursive=recursive)

        loaded = 0
        for _name, config in agents.items():
            try:
                self.register(config, overwrite=overwrite)
                loaded += 1
            except ValueError as e:
                logger.warning("Skipping agent: %s", e)

        logger.info("Loaded %d agent(s) from %s", loaded, directory)
        return loaded

    def load_from_file(
        self,
        file_path: str | Path,
        overwrite: bool = False,
    ) -> UnifiedAgentConfig:
        """Load a single agent from a file.

        Args:
            file_path: Path to agent markdown file
            overwrite: If True, overwrite existing agent

        Returns:
            Loaded agent configuration

        """
        config = self._loader.load(file_path)
        self.register(config, overwrite=overwrite)
        return config

    def reload(self) -> int:
        """Reload all agents from previously loaded directories.

        Returns:
            Total number of agents after reload

        """
        self._agents.clear()

        # Copy _load_paths and clear it to avoid duplicates when load_from_directory appends
        paths_to_reload = list(self._load_paths)
        self._load_paths.clear()

        for directory in paths_to_reload:
            if directory.exists():
                self.load_from_directory(directory, overwrite=True)

        return len(self._agents)

    def get_by_role(self, role: str) -> list[UnifiedAgentConfig]:
        """Get all agents with a specific role.

        Args:
            role: Role to filter by

        Returns:
            List of matching agent configs

        """
        role = role.lower()
        return [config for config in self._agents.values() if config.role.lower() == role]

    def get_by_empathy_level(
        self,
        min_level: int = 1,
        max_level: int = 5,
    ) -> list[UnifiedAgentConfig]:
        """Get agents within an empathy level range.

        Args:
            min_level: Minimum empathy level (inclusive)
            max_level: Maximum empathy level (inclusive)

        Returns:
            List of matching agent configs

        """
        return [
            config
            for config in self._agents.values()
            if min_level <= config.empathy_level <= max_level
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of registered agents.

        Returns:
            Summary dictionary

        """
        by_role = {}
        by_level = {}
        by_tier = {}

        for config in self._agents.values():
            role = config.role
            by_role[role] = by_role.get(role, 0) + 1

            level = config.empathy_level
            by_level[level] = by_level.get(level, 0) + 1

            tier = (
                config.model_tier.value
                if hasattr(config.model_tier, "value")
                else str(config.model_tier)
            )
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_agents": len(self._agents),
            "agent_names": self.list_agents(),
            "by_role": by_role,
            "by_empathy_level": by_level,
            "by_model_tier": by_tier,
            "load_paths": [str(p) for p in self._load_paths],
        }

    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._load_paths.clear()
        logger.debug("Cleared agent registry")
