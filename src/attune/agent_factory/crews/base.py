"""Base class for Attune AI crews.

Provides shared initialization, XML prompt rendering, framework
detection, Memory Graph setup, and common properties used by all
crew implementations.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CrewBase:
    """Base class providing shared infrastructure for all crews.

    Subclasses must:
    - Set ``config_class`` to the crew's config dataclass type.
    - Set ``XML_PROMPT_TEMPLATES`` to a dict of prompt templates.
    - Implement ``_create_agents()`` async method.
    - Implement ``_create_workflow()`` async method.
    - Implement ``run()`` async method.

    Provides:
    - ``__init__`` with config-or-kwargs pattern
    - ``_render_xml_prompt()``
    - ``_get_system_prompt()``
    - ``_initialize()`` with framework detection + Memory Graph
    - ``agents`` property
    - ``is_initialized`` property
    - ``get_agent_stats()`` async method
    """

    config_class: type  # Subclass must set this
    XML_PROMPT_TEMPLATES: dict[str, str] = {}  # Subclass must set this

    def __init__(
        self,
        config: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the crew.

        Args:
            config: Crew-specific config dataclass, or None to
                build from kwargs.
            **kwargs: Individual config parameters forwarded to
                the config dataclass constructor.
        """
        if config:
            self.config = config
        else:
            self.config = self.config_class(**kwargs)

        self._factory: Any = None
        self._agents: dict[str, Any] = {}
        self._workflow: Any = None
        self._graph: Any = None
        self._initialized = False

    # -- XML prompt helpers --------------------------------------------------

    def _render_xml_prompt(self, template_key: str) -> str:
        """Render XML prompt template with config values."""
        template = self.XML_PROMPT_TEMPLATES.get(template_key, "")
        return template.format(
            schema_version=self.config.xml_schema_version,
        )

    def _get_system_prompt(self, agent_key: str, fallback: str) -> str:
        """Get system prompt - XML if enabled, fallback otherwise."""
        if self.config.xml_prompts_enabled:
            return self._render_xml_prompt(agent_key)
        return fallback

    # -- Initialization ------------------------------------------------------

    async def _initialize(self) -> None:
        """Lazy initialization of agents and workflow."""
        if self._initialized:
            return

        from attune.agent_factory import AgentFactory, Framework

        # Check if CrewAI is available
        try:
            from attune.agent_factory.adapters.crewai_adapter import (
                _check_crewai,
            )

            use_crewai = _check_crewai()
        except ImportError:
            use_crewai = False

        # Use CrewAI if available, otherwise fall back to Native
        framework = Framework.CREWAI if use_crewai else Framework.NATIVE

        self._factory = AgentFactory(
            framework=framework,
            provider=self.config.provider,
            api_key=self.config.api_key,
        )

        # Initialize Memory Graph if enabled
        if self.config.memory_graph_enabled:
            try:
                from attune.memory import MemoryGraph

                self._graph = MemoryGraph(
                    path=self.config.memory_graph_path,
                )
            except ImportError:
                logger.warning("Memory Graph not available, continuing without it")

        # Delegate agent and workflow creation to subclass
        await self._create_agents()
        await self._create_workflow()

        self._initialized = True

    async def _create_agents(self) -> None:
        """Create specialized agents. Subclass MUST override."""
        raise NotImplementedError

    async def _create_workflow(self) -> None:
        """Create the crew workflow. Subclass MUST override."""
        raise NotImplementedError

    # -- Properties ----------------------------------------------------------

    @property
    def agents(self) -> dict[str, Any]:
        """Get the crew's agents."""
        return self._agents

    @property
    def is_initialized(self) -> bool:
        """Check if crew is initialized."""
        return self._initialized

    # -- Stats ---------------------------------------------------------------

    async def get_agent_stats(self) -> dict:
        """Get statistics about crew agents."""
        await self._initialize()

        agents_dict: dict = {}
        stats: dict = {
            "agent_count": len(self._agents),
            "agents": agents_dict,
            "framework": (self._factory.framework.value if self._factory else "unknown"),
            "memory_graph_enabled": self.config.memory_graph_enabled,
            "xml_prompts_enabled": self.config.xml_prompts_enabled,
        }

        for name, agent in self._agents.items():
            agents_dict[name] = {
                "role": (agent.config.role if hasattr(agent, "config") else "unknown"),
                "model_tier": getattr(agent.config, "model_tier", "unknown"),
            }

        return stats
