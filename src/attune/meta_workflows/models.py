"""Core data models for meta-workflow system.

This module defines the data structures for:
- Form schemas and responses (Socratic questioning)
- Agent composition rules and specs (dynamic agent generation)
- Meta-workflow templates and results (orchestration)

Created: 2026-01-17
Purpose: Enable dynamic workflow creation via forms + agent teams
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

# =============================================================================
# Enums
# =============================================================================
# Form components — extracted to the standalone ``attune-forms``
# package (2026-08-12). Re-imported here so the 17+ in-repo consumers
# and any external ``attune.meta_workflows.models`` importer keep the
# same import path AND the same class objects (isinstance-safe).
from attune_forms.models import (  # noqa: F401
    FormQuestion,
    FormResponse,
    FormSchema,
    QuestionType,
)


class TierStrategy(str, Enum):
    """Model tier escalation strategies for agents."""

    CHEAP_ONLY = "cheap_only"  # Use only cheap tier
    PROGRESSIVE = "progressive"  # Escalate cheap → capable → premium
    CAPABLE_FIRST = "capable_first"  # Start at capable, escalate to premium if needed
    PREMIUM_ONLY = "premium_only"  # Use only premium tier


# =============================================================================
# Agent Components
# =============================================================================


@dataclass
class AgentCompositionRule:
    """Rule defining when and how to create an agent.

    Attributes:
        role: Agent's role/purpose
        base_template: Base agent template to use
        tier_strategy: Model tier escalation strategy
        tools: List of tools agent can use
        required_responses: Conditions that must be met (question_id → required value)
        config_mapping: Map form responses to agent config (form_key → config_key)
        success_criteria: List of success criteria for this agent

    """

    role: str
    base_template: str
    tier_strategy: TierStrategy
    tools: list[str] = field(default_factory=list)
    required_responses: dict[str, str | list[str]] = field(default_factory=dict)
    config_mapping: dict[str, str] = field(default_factory=dict)
    success_criteria: list[str] = field(default_factory=list)

    def should_create(self, response: FormResponse) -> bool:
        """Check if agent should be created based on form responses.

        Args:
            response: User's form responses

        Returns:
            True if all required conditions are met

        """
        for key, required_value in self.required_responses.items():
            user_response = response.get(key)

            # Multi-select: check if required value in list
            if isinstance(user_response, list):
                # If required_value is a list, check if ANY match
                if isinstance(required_value, list):
                    if not any(rv in user_response for rv in required_value):
                        return False
                # Single required value must be in user's selections
                elif required_value not in user_response:
                    return False

            # Single value: exact match required
            elif isinstance(required_value, list):
                # User must have picked one of the allowed values
                if user_response not in required_value:
                    return False
            # Exact match
            elif user_response != required_value:
                return False

        return True

    def create_agent_config(self, response: FormResponse) -> dict[str, Any]:
        """Create agent configuration from form responses.

        Args:
            response: User's form responses

        Returns:
            Agent configuration dictionary

        """
        config = {}
        for form_key, config_key in self.config_mapping.items():
            value = response.get(form_key)
            if value is not None:
                config[config_key] = value
        return config


@dataclass
class AgentSpec:
    """Specification for a dynamically created agent instance.

    Attributes:
        role: Agent's role/purpose
        base_template: Base agent template used
        tier_strategy: Model tier escalation strategy
        tools: List of tools agent can use
        config: Agent-specific configuration
        success_criteria: List of success criteria
        agent_id: Unique identifier for this agent instance

    """

    role: str
    base_template: str
    tier_strategy: TierStrategy
    tools: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    success_criteria: list[str] = field(default_factory=list)
    agent_id: str = field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:12]}")


# =============================================================================
# Meta-Workflow Components
# =============================================================================


@dataclass
class MetaWorkflowTemplate:
    """Template defining a complete meta-workflow.

    Attributes:
        template_id: Unique identifier for this template
        name: Human-readable name
        description: Description of what this workflow does
        version: Template version
        tags: Tags for categorization
        author: Template author
        form_schema: Form questions to ask user
        agent_composition_rules: Rules for creating agents
        estimated_cost_range: Estimated cost range (min, max)
        estimated_duration_minutes: Estimated duration in minutes

    """

    template_id: str
    name: str
    description: str
    form_schema: FormSchema
    agent_composition_rules: list[AgentCompositionRule] = field(default_factory=list)
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    author: str = "system"
    estimated_cost_range: tuple[float, float] = (0.05, 0.50)
    estimated_duration_minutes: int = 5

    def to_json(self) -> str:
        """Serialize template to JSON string.

        Returns:
            JSON string representation

        """
        data = {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "author": self.author,
            "estimated_cost_range": list(self.estimated_cost_range),
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "form_schema": {
                "title": self.form_schema.title,
                "description": self.form_schema.description,
                "questions": [
                    {
                        "id": q.id,
                        "text": q.text,
                        "type": q.type.value,
                        "options": q.options,
                        "default": q.default,
                        "help_text": q.help_text,
                        "required": q.required,
                    }
                    for q in self.form_schema.questions
                ],
            },
            "agent_composition_rules": [
                {
                    "role": rule.role,
                    "base_template": rule.base_template,
                    "tier_strategy": rule.tier_strategy.value,
                    "tools": rule.tools,
                    "required_responses": rule.required_responses,
                    "config_mapping": rule.config_mapping,
                    "success_criteria": rule.success_criteria,
                }
                for rule in self.agent_composition_rules
            ],
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def from_json(json_str: str) -> "MetaWorkflowTemplate":
        """Deserialize template from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            MetaWorkflowTemplate instance

        Raises:
            ValueError: If JSON is invalid or missing required fields

        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        # Parse form schema
        form_schema = FormSchema(
            title=data["form_schema"]["title"],
            description=data["form_schema"]["description"],
            questions=[
                FormQuestion(
                    id=q["id"],
                    text=q["text"],
                    type=QuestionType(q["type"]),
                    options=q.get("options", []),
                    default=q.get("default"),
                    help_text=q.get("help_text"),
                    required=q.get("required", True),
                )
                for q in data["form_schema"]["questions"]
            ],
        )

        # Parse agent composition rules
        rules = [
            AgentCompositionRule(
                role=rule["role"],
                base_template=rule["base_template"],
                tier_strategy=TierStrategy(rule["tier_strategy"]),
                tools=rule.get("tools", []),
                required_responses=rule.get("required_responses", {}),
                config_mapping=rule.get("config_mapping", {}),
                success_criteria=rule.get("success_criteria", []),
            )
            for rule in data.get("agent_composition_rules", [])
        ]

        return MetaWorkflowTemplate(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            author=data.get("author", "system"),
            form_schema=form_schema,
            agent_composition_rules=rules,
            estimated_cost_range=tuple(data.get("estimated_cost_range", [0.05, 0.50])),
            estimated_duration_minutes=data.get("estimated_duration_minutes", 5),
        )


@dataclass
class AgentExecutionResult:
    """Result from executing a single agent.

    Attributes:
        agent_id: ID of agent that executed
        role: Agent's role
        success: Whether agent succeeded
        cost: Cost of execution
        duration: Duration in seconds
        tier_used: Model tier used
        output: Agent's output/result
        error: Error message if failed

    """

    agent_id: str
    role: str
    success: bool
    cost: float
    duration: float
    tier_used: str
    output: str | dict[str, Any]
    error: str | None = None


@dataclass
class MetaWorkflowResult:
    """Result from executing a complete meta-workflow.

    Attributes:
        run_id: Unique ID for this execution
        template_id: ID of template used
        timestamp: When execution started
        form_responses: User's form responses
        agents_created: List of agents that were created
        agent_results: Results from agent executions
        total_cost: Total cost of execution
        total_duration: Total duration in seconds
        success: Whether workflow succeeded
        error: Error message if failed

    """

    run_id: str
    template_id: str
    timestamp: str
    form_responses: FormResponse
    agents_created: list[AgentSpec] = field(default_factory=list)
    agent_results: list[AgentExecutionResult] = field(default_factory=list)
    total_cost: float = 0.0
    total_duration: float = 0.0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization.

        Returns:
            Dictionary representation

        """
        return {
            "run_id": self.run_id,
            "template_id": self.template_id,
            "timestamp": self.timestamp,
            "form_responses": asdict(self.form_responses),
            "agents_created": [asdict(agent) for agent in self.agents_created],
            "agent_results": [asdict(result) for result in self.agent_results],
            "total_cost": self.total_cost,
            "total_duration": self.total_duration,
            "success": self.success,
            "error": self.error,
        }

    def to_json(self) -> str:
        """Serialize result to JSON string.

        Returns:
            JSON string representation

        """
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "MetaWorkflowResult":
        """Create result from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            MetaWorkflowResult instance

        """
        form_responses = FormResponse(
            template_id=data["form_responses"]["template_id"],
            responses=data["form_responses"]["responses"],
            timestamp=data["form_responses"]["timestamp"],
            response_id=data["form_responses"]["response_id"],
        )

        agents_created = [
            AgentSpec(
                role=agent["role"],
                base_template=agent["base_template"],
                tier_strategy=TierStrategy(agent["tier_strategy"]),
                tools=agent["tools"],
                config=agent["config"],
                success_criteria=agent["success_criteria"],
                agent_id=agent["agent_id"],
            )
            for agent in data.get("agents_created", [])
        ]

        agent_results = [
            AgentExecutionResult(
                agent_id=result["agent_id"],
                role=result["role"],
                success=result["success"],
                cost=result["cost"],
                duration=result["duration"],
                tier_used=result["tier_used"],
                output=result["output"],
                error=result.get("error"),
            )
            for result in data.get("agent_results", [])
        ]

        return MetaWorkflowResult(
            run_id=data["run_id"],
            template_id=data["template_id"],
            timestamp=data["timestamp"],
            form_responses=form_responses,
            agents_created=agents_created,
            agent_results=agent_results,
            total_cost=data.get("total_cost", 0.0),
            total_duration=data.get("total_duration", 0.0),
            success=data.get("success", True),
            error=data.get("error"),
        )


# =============================================================================
# Insight/Analytics Components
# =============================================================================


@dataclass
class PatternInsight:
    """An insight learned from analyzing workflow patterns.

    Attributes:
        insight_type: Type of insight (cost, tier_performance, agent_count, etc.)
        description: Human-readable description
        confidence: Confidence level (0.0 to 1.0)
        data: Supporting data for this insight
        sample_size: Number of runs this insight is based on

    """

    insight_type: str
    description: str
    confidence: float
    data: dict[str, Any] = field(default_factory=dict)
    sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation

        """
        return asdict(self)
