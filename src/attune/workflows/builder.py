"""Builder pattern for BaseWorkflow construction.

Simplifies complex workflow configuration by providing a fluent API
for setting optional parameters.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from attune.cache import BaseCache
    from attune.models import LLMExecutor, TelemetryBackend, UnifiedModelProvider
    from attune.workflows.base import BaseWorkflow
    from attune.workflows.config import WorkflowConfig
    from attune.workflows.context import WorkflowContext
    from attune.workflows.progress import ProgressCallback
    from attune.workflows.routing import TierRoutingStrategy
    from attune.workflows.tier_tracking import WorkflowTierTracker

T = TypeVar("T", bound="BaseWorkflow")


class WorkflowBuilder(Generic[T]):
    """Builder for complex workflow configuration.

    Provides a fluent API for constructing workflows with many optional parameters.
    Eliminates the need to pass 12+ constructor arguments.

    Example:
        >>> from attune.workflows.test_gen import TestGenerationWorkflow
        >>> from attune.workflows.builder import WorkflowBuilder
        >>> from attune.workflows.routing import BalancedRouting
        >>>
        >>> workflow = (
        ...     WorkflowBuilder(TestGenerationWorkflow)
        ...     .with_config(my_config)
        ...     .with_routing(BalancedRouting(budget=10.0))
        ...     .with_cache_enabled(True)
        ...     .with_telemetry_enabled(True)
        ...     .build()
        ... )

    Chaining methods:
        - with_config() - Set workflow configuration
        - with_executor() - Set custom LLM executor
        - with_provider() - Set model provider
        - with_cache() - Set custom cache instance
        - with_cache_enabled() - Enable/disable caching
        - with_telemetry() - Set custom telemetry backend
        - with_telemetry_enabled() - Enable/disable telemetry
        - with_progress_callback() - Set progress callback
        - with_tier_tracker() - Set tier tracker
        - with_routing() - Set routing strategy
        - with_context() - Set WorkflowContext for composition
        - build() - Construct the workflow

    """

    def __init__(self, workflow_class: type[T]):
        """Initialize builder for a specific workflow class.

        Args:
            workflow_class: The workflow class to build (e.g., TestGenerationWorkflow)

        """
        self.workflow_class = workflow_class

        # Optional configuration
        self._config: WorkflowConfig | None = None
        self._executor: LLMExecutor | None = None
        self._provider: UnifiedModelProvider | None = None
        self._cache: BaseCache | None = None
        self._enable_cache: bool = True
        self._telemetry_backend: TelemetryBackend | None = None
        self._enable_telemetry: bool = True
        self._progress_callback: ProgressCallback | None = None
        self._tier_tracker: WorkflowTierTracker | None = None
        self._routing_strategy: TierRoutingStrategy | None = None
        self._ctx: WorkflowContext | None = None

    def with_config(self, config: WorkflowConfig) -> WorkflowBuilder[T]:
        """Set workflow configuration.

        Args:
            config: WorkflowConfig instance with provider, models, etc.

        Returns:
            Self for method chaining

        """
        self._config = config
        return self

    def with_executor(self, executor: LLMExecutor) -> WorkflowBuilder[T]:
        """Set custom LLM executor.

        Args:
            executor: LLMExecutor instance for making LLM calls

        Returns:
            Self for method chaining

        """
        self._executor = executor
        return self

    def with_provider(self, provider: UnifiedModelProvider) -> WorkflowBuilder[T]:
        """Set model provider.

        Args:
            provider: ModelProvider enum (ANTHROPIC, OPENAI, GOOGLE)

        Returns:
            Self for method chaining

        """
        self._provider = provider
        return self

    def with_cache(self, cache: BaseCache) -> WorkflowBuilder[T]:
        """Set custom cache instance.

        Args:
            cache: BaseCache instance for caching LLM responses

        Returns:
            Self for method chaining

        """
        self._cache = cache
        return self

    def with_cache_enabled(self, enabled: bool) -> WorkflowBuilder[T]:
        """Enable or disable caching.

        Args:
            enabled: Whether to enable caching (default: True)

        Returns:
            Self for method chaining

        """
        self._enable_cache = enabled
        return self

    def with_telemetry(self, backend: TelemetryBackend) -> WorkflowBuilder[T]:
        """Set custom telemetry backend.

        Args:
            backend: TelemetryBackend instance for tracking workflow runs

        Returns:
            Self for method chaining

        """
        self._telemetry_backend = backend
        return self

    def with_telemetry_enabled(self, enabled: bool) -> WorkflowBuilder[T]:
        """Enable or disable telemetry.

        Args:
            enabled: Whether to enable telemetry (default: True)

        Returns:
            Self for method chaining

        """
        self._enable_telemetry = enabled
        return self

    def with_progress_callback(
        self,
        callback: ProgressCallback | Callable[[str, int, int], None],
    ) -> WorkflowBuilder[T]:
        """Set progress callback for workflow execution.

        Args:
            callback: ProgressCallback instance or callable(stage, current, total)

        Returns:
            Self for method chaining

        """
        self._progress_callback = callback  # type: ignore
        return self

    def with_tier_tracker(self, tracker: WorkflowTierTracker) -> WorkflowBuilder[T]:
        """Set tier tracker for learning tier progression.

        Args:
            tracker: WorkflowTierTracker instance

        Returns:
            Self for method chaining

        """
        self._tier_tracker = tracker
        return self

    def with_routing(self, strategy: TierRoutingStrategy) -> WorkflowBuilder[T]:
        """Set tier routing strategy.

        Args:
            strategy: TierRoutingStrategy (CostOptimized, PerformanceOptimized, Balanced)

        Returns:
            Self for method chaining

        Example:
            >>> from attune.workflows.routing import BalancedRouting
            >>> builder.with_routing(BalancedRouting(budget=50.0))

        """
        self._routing_strategy = strategy
        return self

    def with_context(self, ctx: WorkflowContext) -> WorkflowBuilder[T]:
        """Set a WorkflowContext for composition-based capabilities.

        When a context is provided, the workflow delegates to its services
        instead of using mixin implementations. This enables selective
        capability composition without changing the mixin inheritance chain.

        Args:
            ctx: WorkflowContext with desired services configured

        Returns:
            Self for method chaining

        Example:
            >>> from attune.workflows.context import WorkflowContext
            >>> from attune.workflows.services import CacheService, CostService
            >>>
            >>> ctx = WorkflowContext(
            ...     cache=CacheService("my-workflow"),
            ...     cost=CostService(),
            ... )
            >>> workflow = (
            ...     WorkflowBuilder(MyWorkflow)
            ...     .with_context(ctx)
            ...     .build()
            ... )

        """
        self._ctx = ctx
        return self

    def build(self) -> T:
        """Build the configured workflow.

        Returns:
            Configured workflow instance ready for execution

        Raises:
            TypeError: If workflow_class constructor doesn't accept the provided parameters

        """
        # Build kwargs for constructor
        kwargs: dict[str, Any] = {}

        if self._config is not None:
            kwargs["config"] = self._config

        if self._executor is not None:
            kwargs["executor"] = self._executor

        if self._provider is not None:
            kwargs["provider"] = self._provider

        if self._cache is not None:
            kwargs["cache"] = self._cache

        kwargs["enable_cache"] = self._enable_cache

        if self._telemetry_backend is not None:
            kwargs["telemetry_backend"] = self._telemetry_backend

        kwargs["enable_telemetry"] = self._enable_telemetry

        if self._progress_callback is not None:
            kwargs["progress_callback"] = self._progress_callback

        if self._tier_tracker is not None:
            kwargs["tier_tracker"] = self._tier_tracker

        if self._routing_strategy is not None:
            kwargs["routing_strategy"] = self._routing_strategy

        if self._ctx is not None:
            kwargs["ctx"] = self._ctx

        # Construct workflow
        return self.workflow_class(**kwargs)


def workflow_builder(workflow_class: type[T]) -> WorkflowBuilder[T]:
    """Factory function for creating workflow builders.

    Convenience function for creating builders with cleaner syntax.

    Args:
        workflow_class: The workflow class to build

    Returns:
        WorkflowBuilder instance

    Example:
        >>> from attune.workflows.builder import workflow_builder
        >>> from attune.workflows.test_gen import TestGenerationWorkflow
        >>>
        >>> workflow = (
        ...     workflow_builder(TestGenerationWorkflow)
        ...     .with_cache_enabled(True)
        ...     .with_telemetry_enabled(False)
        ...     .build()
        ... )

    """
    return WorkflowBuilder(workflow_class)
