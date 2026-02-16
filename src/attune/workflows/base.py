"""Base Workflow Class for Multi-Model Pipelines

Provides a framework for creating cost-optimized workflows that
route tasks to the appropriate model tier.

Integration with attune.models:
- Uses unified ModelTier/ModelProvider from attune.models
- Supports LLMExecutor for abstracted LLM calls
- Supports TelemetryBackend for telemetry storage
- WorkflowStepConfig for declarative step definitions

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_classes import WorkflowStage
    from .progress import RichProgressReporter
    from .routing import TierRoutingStrategy
    from .tier_tracking import WorkflowTierTracker

# Load .env file for API keys if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables

# Import caching infrastructure
from attune.cache import BaseCache
from attune.cost_tracker import CostTracker

# Import unified types from attune.models
from attune.models import (
    LLMExecutor,
    TelemetryBackend,
)

# Re-export CachedResponse for backward compatibility (moved to caching.py in Phase 1)
# Import mixins (extracted for maintainability)
from .caching import (
    CachedResponse,  # noqa: F401 - re-exported
    CachingMixin,
)

# Import deprecated enums from compat module (extracted for maintainability)
# These are re-exported for backward compatibility
from .compat import (
    PROVIDER_MODELS,  # noqa: F401 - re-exported
    ModelProvider,
    ModelTier,
    _build_provider_models,  # noqa: F401 - re-exported
)
from .coordination_mixin import CoordinationMixin

# Import cost tracking mixin (extracted for maintainability)
from .cost_mixin import CostTrackingMixin

# Import data classes (extracted for maintainability)
from .data_classes import (
    CostReport,  # noqa: F401 - re-exported
    StageQualityMetrics,  # noqa: F401 - re-exported
    WorkflowResult,  # noqa: F401 - re-exported
    WorkflowStage,  # noqa: F401 - re-exported
)
from .execution_mixin import ExecutionMixin
from .executor_mixin import ExecutorMixin

# History utility functions (extracted to history_utils.py for maintainability)
from .history_utils import (
    WORKFLOW_HISTORY_FILE,  # noqa: F401 - re-exported
    _get_history_store,  # noqa: F401 - re-exported
    _load_workflow_history,  # noqa: F401 - re-exported
    _save_workflow_run,  # noqa: F401 - re-exported
    get_workflow_stats,  # noqa: F401 - re-exported
)
from .llm_mixin import LLMMixin
from .multi_agent_mixin import MultiAgentStageMixin

# Import parsing mixin (extracted for maintainability)
from .parsing_mixin import ResponseParsingMixin

# Import progress tracking
from .progress import (
    ProgressCallback,
    ProgressTracker,  # noqa: F401 - re-exported for backward compat
)
from .prompt_mixin import PromptMixin
from .state_mixin import StatePersistenceMixin
from .telemetry_mixin import TelemetryMixin
from .tier_routing_mixin import TierRoutingMixin

if TYPE_CHECKING:
    from attune.agents.state.store import AgentStateStore

    from .config import WorkflowConfig
    from .context import WorkflowContext

logger = logging.getLogger(__name__)


class BaseWorkflow(
    ExecutionMixin,
    LLMMixin,
    CoordinationMixin,
    StatePersistenceMixin,
    MultiAgentStageMixin,
    PromptMixin,
    ExecutorMixin,
    TierRoutingMixin,
    CachingMixin,
    TelemetryMixin,
    ResponseParsingMixin,
    CostTrackingMixin,
    ABC,
):
    """Base class for multi-model workflows.

    Inherits from PromptMixin, ExecutorMixin, CachingMixin, TelemetryMixin, ResponseParsingMixin, and
    CostTrackingMixin (extracted for maintainability).

    Subclasses define stages and tier mappings:

        class MyWorkflow(BaseWorkflow):
            name = "my-workflow"
            description = "Does something useful"
            stages = ["stage1", "stage2", "stage3"]
            tier_map = {
                "stage1": ModelTier.CHEAP,
                "stage2": ModelTier.CAPABLE,
                "stage3": ModelTier.PREMIUM,
            }

            async def run_stage(self, stage_name, tier, input_data):
                # Implement stage logic
                return output_data
    """

    name: str = "base-workflow"
    description: str = "Base workflow template"
    stages: list[str] = []
    tier_map: dict[str, ModelTier] = {}

    def __init__(
        self,
        cost_tracker: CostTracker | None = None,
        provider: ModelProvider | str | None = None,
        config: WorkflowConfig | None = None,
        executor: LLMExecutor | None = None,
        telemetry_backend: TelemetryBackend | None = None,
        progress_callback: ProgressCallback | None = None,
        cache: BaseCache | None = None,
        enable_cache: bool = True,
        enable_tier_tracking: bool = True,
        enable_tier_fallback: bool = True,
        routing_strategy: TierRoutingStrategy | None = None,
        enable_rich_progress: bool = False,
        enable_adaptive_routing: bool = False,
        enable_heartbeat_tracking: bool = False,
        enable_coordination: bool = False,
        agent_id: str | None = None,
        state_store: AgentStateStore | None = None,
        multi_agent_configs: dict[str, dict[str, Any]] | None = None,
        ctx: WorkflowContext | None = None,
    ):
        """Initialize workflow with optional cost tracker, provider, and config.

        Args:
            cost_tracker: CostTracker instance for logging costs
            provider: Model provider (anthropic, openai, ollama) or ModelProvider enum.
                     If None, uses config or defaults to anthropic.
            config: WorkflowConfig for model customization. If None, loads from
                   .attune/workflows.yaml or uses defaults.
            executor: LLMExecutor for abstracted LLM calls (optional).
                     If provided, enables unified execution with telemetry.
            telemetry_backend: TelemetryBackend for storing telemetry records.
                     Defaults to TelemetryStore (JSONL file backend).
            progress_callback: Callback for real-time progress updates.
                     If provided, enables live progress tracking during execution.
            cache: Optional cache instance. If None and enable_cache=True,
                   auto-creates cache with one-time setup prompt.
            enable_cache: Whether to enable caching (default True).
            enable_tier_tracking: Whether to enable automatic tier tracking (default True).
            enable_tier_fallback: Whether to enable intelligent tier fallback
                     (CHEAP → CAPABLE → PREMIUM). Enabled by default. Set to False to disable.
            routing_strategy: Optional TierRoutingStrategy for dynamic tier selection.
                     When provided, overrides static tier_map for stage tier decisions.
                     Strategies: CostOptimizedRouting, PerformanceOptimizedRouting,
                     BalancedRouting, HybridRouting.
            enable_rich_progress: Whether to enable Rich-based live progress display
                     (default False). When enabled and output is a TTY, shows live
                     progress bars with spinners. Default is False because most users
                     run workflows from IDEs (VSCode, etc.) where TTY is not available.
                     The console reporter works reliably in all environments.
            enable_adaptive_routing: Whether to enable adaptive model routing based
                     on telemetry history (default False). When enabled, uses historical
                     performance data to select the optimal Anthropic model for each stage,
                     automatically upgrading tiers when failure rates exceed 20%.
                     Opt-in feature for cost optimization and automatic quality improvement.
            enable_heartbeat_tracking: Whether to enable agent heartbeat tracking
                     (default False). When enabled, publishes TTL-based heartbeat updates
                     to Redis for agent liveness monitoring. Requires Redis backend.
                     Pattern 1 from Agent Coordination Architecture.
            enable_coordination: Whether to enable inter-agent coordination signals
                     (default False). When enabled, workflow can send and receive TTL-based
                     ephemeral signals for agent-to-agent communication. Requires Redis backend.
                     Pattern 2 from Agent Coordination Architecture.
            agent_id: Optional agent ID for heartbeat tracking and coordination.
                     If None, auto-generates ID from workflow name and run ID.
                     Used as identifier in Redis keys (heartbeat:{agent_id}, signal:{agent_id}:...).
            state_store: Optional AgentStateStore for persistent state tracking.
                     When provided, records workflow start/completion/failure and saves
                     stage-level checkpoints for observability and recovery.
                     Default None = no persistence (backwards-compatible).
            multi_agent_configs: Optional per-stage DynamicTeam configurations.
                     Dict mapping stage names to team config dicts. Workflow stages
                     can then call ``self._run_multi_agent_stage()`` to delegate to
                     a multi-agent team instead of a single LLM call.
                     Default None = no multi-agent stages.
            ctx: Optional WorkflowContext for composition-based capabilities.
                     When provided, proxy methods delegate to ctx services instead
                     of mixin implementations. When None (default), all behavior
                     comes from mixins as before. See ``workflows/context.py``.

        """
        from .config import WorkflowConfig

        # Composition context (Phase 2C) -- when provided, proxy methods
        # delegate to ctx services instead of mixin implementations.
        self._ctx = ctx

        self.cost_tracker = cost_tracker or CostTracker()
        self._stages_run: list[WorkflowStage] = []

        # Progress tracking
        self._progress_callback = progress_callback
        self._progress_tracker: ProgressTracker | None = None
        self._enable_rich_progress = enable_rich_progress
        self._rich_reporter: RichProgressReporter | None = None

        # New: LLMExecutor support
        self._executor = executor
        self._api_key: str | None = None  # For default executor creation

        # Cache support
        self._cache: BaseCache | None = cache
        self._enable_cache = enable_cache
        self._cache_setup_attempted = False

        # Tier tracking support
        self._enable_tier_tracking = enable_tier_tracking
        self._tier_tracker: WorkflowTierTracker | None = None

        # Tier fallback support
        self._enable_tier_fallback = enable_tier_fallback
        self._tier_progression: list[tuple[str, str, bool]] = []  # (stage, tier, success)

        # Routing strategy support
        self._routing_strategy: TierRoutingStrategy | None = routing_strategy

        # Adaptive routing support (Pattern 3 from AGENT_COORDINATION_ARCHITECTURE)
        self._enable_adaptive_routing = enable_adaptive_routing
        self._adaptive_router = None  # Lazy initialization on first use

        # Agent tracking and coordination (Pattern 1 & 2 from AGENT_COORDINATION_ARCHITECTURE)
        self._enable_heartbeat_tracking = enable_heartbeat_tracking
        self._enable_coordination = enable_coordination
        self._agent_id = agent_id  # Will be set during execute() if None
        self._heartbeat_coordinator = None  # Lazy initialization on first use
        self._coordination_signals = None  # Lazy initialization on first use

        # State persistence (Phase 4 - AgentStateStore integration)
        self._state_store = state_store
        self._state_exec_id: str | None = None
        self._state_completed_stages: list[str] = []
        self._state_stage_costs: dict[str, float] = {}
        self._state_last_output: Any = None

        # Multi-agent stage configs (Phase 4 - DynamicTeam integration)
        self._multi_agent_configs = multi_agent_configs

        # Telemetry tracking (uses TelemetryMixin)
        self._init_telemetry(telemetry_backend)

        # Load config if not provided
        self._config = config or WorkflowConfig.load()

        # Determine provider (priority: arg > config > default)
        if provider is None:
            provider = self._config.get_provider_for_workflow(self.name)

        # Handle string provider input
        if isinstance(provider, str):
            provider_str = provider.lower()
            try:
                provider = ModelProvider(provider_str)
                self._provider_str = provider_str
            except ValueError:
                # Custom provider, keep as string
                self._provider_str = provider_str
                provider = ModelProvider.CUSTOM
        else:
            self._provider_str = provider.value

        self.provider = provider

    def get_tier_for_stage(self, stage_name: str) -> ModelTier:
        """Get the model tier for a stage from static tier_map."""
        return self.tier_map.get(stage_name, ModelTier.CAPABLE)

    # Coordination methods (_get_adaptive_router, _get_heartbeat_coordinator,
    # _get_coordination_signals, _check_adaptive_tier_upgrade, send_signal,
    # wait_for_signal, check_signal) are inherited from CoordinationMixin

    # Tier routing methods (_get_tier_with_routing, _estimate_input_tokens)
    # are inherited from TierRoutingMixin

    # LLM methods (get_model_for_tier, _call_llm, should_skip_stage,
    # validate_output, _assess_complexity) are inherited from LLMMixin

    # Note: _maybe_setup_cache is inherited from CachingMixin
    # Note: _track_telemetry is inherited from TelemetryMixin
    # Note: _calculate_cost, _calculate_baseline_cost, and _generate_cost_report
    #       are inherited from CostTrackingMixin

    @abstractmethod
    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Execute a single workflow stage.

        Args:
            stage_name: Name of the stage to run
            tier: Model tier to use
            input_data: Input for this stage

        Returns:
            Tuple of (output_data, input_tokens, output_tokens)

        """

    # Execution methods (execute, _execute_tier_fallback, _execute_standard,
    # _finalize_execution) are inherited from ExecutionMixin

    # Prompt methods (describe, _build_cached_system_prompt, XML rendering)
    # are inherited from PromptMixin

    # Executor methods (_create_execution_context, _create_default_executor,
    # _get_executor, run_step_with_executor) are inherited from ExecutorMixin

    # ------------------------------------------------------------------
    # Proxy methods for WorkflowContext composition (Phase 2C)
    #
    # When self._ctx is set and the relevant service exists, these methods
    # delegate to the service. Otherwise they fall back to the mixin via
    # super(), preserving 100% backward compatibility.
    # ------------------------------------------------------------------

    # --- Cache proxies (CachingMixin -> CacheService) ---

    def _maybe_setup_cache(self) -> None:
        """Set up cache -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            self._ctx.cache.setup()
            return
        super()._maybe_setup_cache()

    def _try_cache_lookup(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
    ) -> CachedResponse | None:
        """Try cache lookup -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.lookup(stage, system, user_message, model)
        return super()._try_cache_lookup(stage, system, user_message, model)

    def _store_in_cache(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
        response: CachedResponse,
    ) -> bool:
        """Store in cache -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.store(stage, system, user_message, model, response)
        return super()._store_in_cache(stage, system, user_message, model, response)

    def _get_cache_type(self) -> str:
        """Get cache type -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.get_cache_type()
        return super()._get_cache_type()

    def _get_cache_stats(self) -> dict[str, Any]:
        """Get cache stats -- delegates to CacheService when ctx is provided."""
        if self._ctx and self._ctx.cache:
            return self._ctx.cache.get_stats()
        return super()._get_cache_stats()

    # --- Cost proxies (CostTrackingMixin -> CostService) ---

    def _calculate_cost(self, tier: Any, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost -- delegates to CostService when ctx is provided."""
        if self._ctx and self._ctx.cost:
            return self._ctx.cost.calculate_cost(tier, input_tokens, output_tokens)
        return super()._calculate_cost(tier, input_tokens, output_tokens)

    def _calculate_baseline_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate baseline cost -- delegates to CostService when ctx is provided."""
        if self._ctx and self._ctx.cost:
            return self._ctx.cost.calculate_baseline_cost(input_tokens, output_tokens)
        return super()._calculate_baseline_cost(input_tokens, output_tokens)

    def _generate_cost_report(self) -> CostReport:
        """Generate cost report -- delegates to CostService when ctx is provided."""
        if self._ctx and self._ctx.cost:
            return self._ctx.cost.generate_report(self._stages_run)
        return super()._generate_cost_report()

    # --- Telemetry proxies (TelemetryMixin -> TelemetryService) ---

    def _track_telemetry(
        self,
        stage: str,
        tier: Any,
        model: str,
        cost: float,
        tokens: dict[str, int],
        cache_hit: bool,
        cache_type: str | None,
        duration_ms: int,
    ) -> None:
        """Track telemetry -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            self._ctx.telemetry.track_call(
                stage=stage,
                tier=tier,
                model=model,
                cost=cost,
                tokens=tokens,
                cache_hit=cache_hit,
                cache_type=cache_type,
                duration_ms=duration_ms,
            )
            return
        super()._track_telemetry(
            stage,
            tier,
            model,
            cost,
            tokens,
            cache_hit,
            cache_type,
            duration_ms,
        )

    def _emit_call_telemetry(
        self,
        step_name: str,
        task_type: str,
        tier: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        success: bool = True,
        error_message: str | None = None,
        fallback_used: bool = False,
    ) -> None:
        """Emit call record -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            self._ctx.telemetry.emit_call_record(
                step_name=step_name,
                task_type=task_type,
                tier=tier,
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                fallback_used=fallback_used,
            )
            return
        super()._emit_call_telemetry(
            step_name,
            task_type,
            tier,
            model_id,
            input_tokens,
            output_tokens,
            cost,
            latency_ms,
            success,
            error_message,
            fallback_used,
        )

    def _emit_workflow_telemetry(self, result: Any) -> None:
        """Emit workflow record -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            model_fn = self.get_model_for_tier if hasattr(self, "get_model_for_tier") else None
            self._ctx.telemetry.emit_workflow_record(result, model_fn)
            return
        super()._emit_workflow_telemetry(result)

    def _generate_run_id(self) -> str:
        """Generate run ID -- delegates to TelemetryService when ctx is provided."""
        if self._ctx and self._ctx.telemetry:
            run_id = self._ctx.telemetry.generate_run_id()
            self._run_id = run_id
            return run_id
        return super()._generate_run_id()

    # --- Prompt proxies (PromptMixin -> PromptService) ---

    def _is_xml_enabled(self) -> bool:
        """Check if XML prompts are enabled -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.xml_enabled
        return super()._is_xml_enabled()

    def _build_cached_system_prompt(
        self,
        role: str,
        guidelines: list[str] | None = None,
        documentation: str | None = None,
        examples: list[dict[str, str]] | None = None,
    ) -> str:
        """Build cached system prompt -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.build_cached_system_prompt(
                role,
                guidelines,
                documentation,
                examples,
            )
        return super()._build_cached_system_prompt(
            role,
            guidelines,
            documentation,
            examples,
        )

    def _render_xml_prompt(
        self,
        role: str,
        goal: str,
        instructions: list[str],
        constraints: list[str],
        input_type: str,
        input_payload: str,
        examples: list[dict[str, str]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Render XML prompt -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.render_xml(
                role,
                goal,
                instructions,
                constraints,
                input_type,
                input_payload,
                extra,
            )
        return super()._render_xml_prompt(
            role,
            goal,
            instructions,
            constraints,
            input_type,
            input_payload,
            examples,
            extra,
        )

    def _render_plain_prompt(
        self,
        role: str,
        goal: str,
        instructions: list[str],
        constraints: list[str],
        input_type: str,
        input_payload: str,
    ) -> str:
        """Render plain prompt -- delegates to PromptService when ctx is provided."""
        if self._ctx and self._ctx.prompt:
            return self._ctx.prompt.render_plain(
                role,
                goal,
                instructions,
                constraints,
                input_type,
                input_payload,
            )
        return super()._render_plain_prompt(
            role,
            goal,
            instructions,
            constraints,
            input_type,
            input_payload,
        )

    # --- Parsing proxies (ResponseParsingMixin -> ParsingService) ---

    def _parse_xml_response(self, response: str) -> dict[str, Any]:
        """Parse XML response -- delegates to ParsingService when ctx is provided."""
        if self._ctx and self._ctx.parsing:
            return self._ctx.parsing.parse_xml_response(response)
        return super()._parse_xml_response(response)

    def _extract_findings_from_response(
        self,
        response: str,
        files_changed: list[str],
        code_context: str = "",
    ) -> list[dict[str, Any]]:
        """Extract findings -- delegates to ParsingService when ctx is provided."""
        if self._ctx and self._ctx.parsing:
            return self._ctx.parsing.extract_findings(
                response,
                files_changed,
                code_context,
            )
        return super()._extract_findings_from_response(
            response,
            files_changed,
            code_context,
        )

    # --- Tier routing proxies (TierRoutingMixin -> TierService) ---

    def _get_tier_with_routing(
        self,
        stage_name: str,
        input_data: dict[str, Any] | None = None,
        budget_remaining: float = 100.0,
    ) -> ModelTier:
        """Get tier with routing -- delegates to TierService when ctx is provided."""
        if self._ctx and self._ctx.tier:
            return self._ctx.tier.get_tier(stage_name, input_data, budget_remaining)
        return super()._get_tier_with_routing(
            stage_name,
            input_data,
            budget_remaining,
        )

    # --- Coordination proxies (CoordinationMixin -> CoordinationService) ---

    def send_signal(
        self,
        signal_type: str,
        target_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Send signal -- delegates to CoordinationService when ctx is provided."""
        if self._ctx and self._ctx.coordination:
            return self._ctx.coordination.send_signal(
                signal_type,
                target_agent,
                payload,
                ttl_seconds,
            )
        return super().send_signal(
            signal_type,
            target_agent,
            payload,
            ttl_seconds,
        )

    def wait_for_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> Any:
        """Wait for signal -- delegates to CoordinationService when ctx is provided."""
        if self._ctx and self._ctx.coordination:
            return self._ctx.coordination.wait_for_signal(
                signal_type,
                source_agent,
                timeout,
                poll_interval,
            )
        return super().wait_for_signal(
            signal_type,
            source_agent,
            timeout,
            poll_interval,
        )

    def check_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        consume: bool = True,
    ) -> Any:
        """Check signal -- delegates to CoordinationService when ctx is provided."""
        if self._ctx and self._ctx.coordination:
            return self._ctx.coordination.check_signal(
                signal_type,
                source_agent,
                consume,
            )
        return super().check_signal(
            signal_type,
            source_agent,
            consume,
        )
