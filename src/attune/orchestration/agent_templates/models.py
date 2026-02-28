"""Data models for the agent template system.

Provides reusable dataclasses for defining agent capabilities,
resource requirements, and template specifications.

Security:
    - All fields validated on creation
    - No eval() or exec() usage
    - Input sanitization on field values

Example:
    >>> from attune.orchestration.agent_templates.models import AgentTemplate
    >>> template = AgentTemplate(
    ...     id="my_agent",
    ...     role="My Agent",
    ...     capabilities=["analyze"],
    ...     tier_preference="CAPABLE",
    ...     tools=["reader"],
    ...     default_instructions="Analyze code.",
    ...     quality_gates={"min_score": 7},
    ... )

"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentCapability:
    """Capability that an agent can perform.

    Attributes:
        name: Capability identifier (e.g., "analyze_gaps")
        description: Human-readable description
        required_tools: List of tools needed for this capability

    Example:
        >>> cap = AgentCapability(
        ...     name="analyze_gaps",
        ...     description="Identify test coverage gaps",
        ...     required_tools=["coverage_analyzer"]
        ... )

    """

    name: str
    description: str
    required_tools: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate capability fields."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")
        if not self.description or not isinstance(self.description, str):
            raise ValueError("description must be a non-empty string")
        if not isinstance(self.required_tools, list):
            raise ValueError("required_tools must be a list")


@dataclass(frozen=True)
class ResourceRequirements:
    """Resource requirements for agent execution.

    Attributes:
        min_tokens: Minimum token budget required
        max_tokens: Maximum token budget allowed
        timeout_seconds: Maximum execution time in seconds
        memory_mb: Maximum memory usage in megabytes

    Example:
        >>> req = ResourceRequirements(
        ...     min_tokens=1000,
        ...     max_tokens=10000,
        ...     timeout_seconds=300,
        ...     memory_mb=512
        ... )

    """

    min_tokens: int = 1000
    max_tokens: int = 10000
    timeout_seconds: int = 300
    memory_mb: int = 512

    def __post_init__(self):
        """Validate resource requirements."""
        if self.min_tokens < 0:
            raise ValueError("min_tokens must be non-negative")
        if self.max_tokens < self.min_tokens:
            raise ValueError("max_tokens must be >= min_tokens")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.memory_mb <= 0:
            raise ValueError("memory_mb must be positive")


@dataclass(frozen=True)
class AgentTemplate:
    """Reusable agent archetype.

    Templates define agent capabilities, tools, and quality gates.
    They can be customized for specific tasks during agent spawning.

    Attributes:
        id: Unique template identifier
        role: Agent role description
        capabilities: List of capability names
        tier_preference: Preferred tier ("CHEAP", "CAPABLE", "PREMIUM")
        tools: List of tool identifiers
        default_instructions: Default instructions for the agent
        quality_gates: Quality gate thresholds
        resource_requirements: Resource limits and requirements

    Example:
        >>> template = AgentTemplate(
        ...     id="test_coverage_analyzer",
        ...     role="Test Coverage Expert",
        ...     capabilities=["analyze_gaps", "suggest_tests"],
        ...     tier_preference="CAPABLE",
        ...     tools=["coverage_analyzer"],
        ...     default_instructions="Analyze test coverage...",
        ...     quality_gates={"min_coverage": 80}
        ... )

    Security:
        - All fields validated on creation
        - tier_preference restricted to allowed values
        - No user input used in eval/exec

    """

    id: str
    role: str
    capabilities: list[str]
    tier_preference: str
    tools: list[str]
    default_instructions: str
    quality_gates: dict[str, Any]
    resource_requirements: ResourceRequirements = field(default_factory=ResourceRequirements)

    ALLOWED_TIERS = {"CHEAP", "CAPABLE", "PREMIUM"}

    def __post_init__(self):
        """Validate template fields.

        Raises:
            ValueError: If any field is invalid

        """
        # Validate ID
        if not self.id or not isinstance(self.id, str):
            raise ValueError("id must be a non-empty string")

        # Validate role
        if not self.role or not isinstance(self.role, str):
            raise ValueError("role must be a non-empty string")

        # Validate capabilities
        if not isinstance(self.capabilities, list):
            raise ValueError("capabilities must be a list")
        if not self.capabilities:
            raise ValueError("capabilities must not be empty")
        for cap in self.capabilities:
            if not isinstance(cap, str) or not cap:
                raise ValueError("all capabilities must be non-empty strings")

        # Validate tier preference
        if self.tier_preference not in self.ALLOWED_TIERS:
            raise ValueError(f"tier_preference must be one of {self.ALLOWED_TIERS}")

        # Validate tools
        if not isinstance(self.tools, list):
            raise ValueError("tools must be a list")
        for tool in self.tools:
            if not isinstance(tool, str) or not tool:
                raise ValueError("all tools must be non-empty strings")

        # Validate instructions
        if not self.default_instructions or not isinstance(self.default_instructions, str):
            raise ValueError("default_instructions must be a non-empty string")

        # Validate quality gates
        if not isinstance(self.quality_gates, dict):
            raise ValueError("quality_gates must be a dict")

        # Validate resource requirements
        if not isinstance(self.resource_requirements, ResourceRequirements):
            raise ValueError("resource_requirements must be a ResourceRequirements instance")
