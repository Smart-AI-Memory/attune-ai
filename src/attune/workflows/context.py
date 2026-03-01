"""WorkflowContext - Composition-based capability container.

Replaces mixin inheritance with explicit service composition. Workflows can
declare only the capabilities they need by populating the relevant service
slots on WorkflowContext.

Phase 2B of the modular architecture evolution plan.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .services import (
    CacheService,
    CoordinationService,
    CostService,
    ParsingService,
    PromptService,
    TelemetryService,
    TierService,
)


@dataclass
class WorkflowContext:
    """Container for workflow capability services.

    Each slot is optional -- workflows only populate the services they need.
    When attached to a BaseWorkflow via the ``ctx`` parameter, proxy methods
    delegate to the service when available and fall back to mixin behavior
    when the service is ``None``.

    Args:
        cache: Response caching service
        cost: Cost calculation and reporting service
        telemetry: Telemetry tracking service
        prompt: Prompt building and rendering service
        parsing: Response parsing and finding extraction service
        tier: Model tier routing service
        coordination: Inter-agent coordination service

    Example:
        >>> from attune.workflows.context import WorkflowContext
        >>> from attune.workflows.services import CacheService, CostService
        >>>
        >>> ctx = WorkflowContext(
        ...     cache=CacheService("my-workflow"),
        ...     cost=CostService(),
        ... )
        >>>
        >>> # Attach to workflow
        >>> workflow = MyWorkflow(ctx=ctx)

    Example with builder:
        >>> from attune.workflows.builder import WorkflowBuilder
        >>>
        >>> workflow = (
        ...     WorkflowBuilder(MyWorkflow)
        ...     .with_context(ctx)
        ...     .build()
        ... )

    """

    cache: CacheService | None = None
    cost: CostService | None = None
    telemetry: TelemetryService | None = None
    prompt: PromptService | None = None
    parsing: ParsingService | None = None
    tier: TierService | None = None
    coordination: CoordinationService | None = None

    # Extensible metadata for future services or custom data
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def services(self) -> dict[str, Any]:
        """Return a dict of all non-None services.

        Useful for introspection and debugging.

        Returns:
            Dictionary mapping service name to service instance.

        """
        result: dict[str, Any] = {}
        for name in (
            "cache",
            "cost",
            "telemetry",
            "prompt",
            "parsing",
            "tier",
            "coordination",
        ):
            svc = getattr(self, name)
            if svc is not None:
                result[name] = svc
        return result

    @classmethod
    def minimal(cls, workflow_name: str = "workflow") -> WorkflowContext:
        """Create a minimal context with only cost tracking.

        Useful for lightweight workflows that only need cost reporting.

        Args:
            workflow_name: Name of the workflow

        Returns:
            WorkflowContext with CostService only

        """
        return cls(cost=CostService())

    @classmethod
    def standard(
        cls,
        workflow_name: str,
        provider: str = "anthropic",
        enable_cache: bool = True,
    ) -> WorkflowContext:
        """Create a standard context with cache, cost, and telemetry.

        Covers the most common workflow needs without coordination or
        advanced routing.

        Args:
            workflow_name: Name of the workflow
            provider: Provider identifier for telemetry
            enable_cache: Whether to enable caching

        Returns:
            WorkflowContext with cache, cost, and telemetry services

        """
        return cls(
            cache=CacheService(workflow_name, enable=enable_cache),
            cost=CostService(),
            telemetry=TelemetryService(workflow_name, provider=provider),
            prompt=PromptService(workflow_name),
            parsing=ParsingService(),
        )
