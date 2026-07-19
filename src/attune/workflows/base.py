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

import functools
import inspect
import logging
from abc import ABC
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

from attune.cost_tracker import CostTracker

# Import unified types from attune.models
from attune.models import (
    LLMExecutor,
    TelemetryBackend,
)

# Import verification mixin for post-execution verification loops
from attune.verification.mixin import VerificationMixin

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
from .context_proxy_mixin import ContextProxyMixin
from .coordination_mixin import CoordinationMixin

# Import cost tracking mixin (extracted for maintainability)
from .cost_mixin import CostTrackingMixin

# Import data classes (extracted for maintainability)
from .data_classes import (
    CostReport,  # noqa: F401 - re-exported
    NextAction,  # noqa: F401 - re-exported
    StageQualityMetrics,  # noqa: F401 - re-exported
    WorkflowResult,  # noqa: F401 - re-exported
    WorkflowStage,
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

# Import parsing mixin (extracted for maintainability)
from .parsing_mixin import ResponseParsingMixin
from .post_simplification_mixin import PostSimplificationMixin

# Import progress tracking
from .progress import (
    ProgressCallback,
    ProgressTracker,
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


def estimate_tokens(obj: Any, max_chars: int = 1_000_000) -> int:
    """Rough token estimate: ~4 characters per token.

    Args:
        obj: Object to estimate tokens for.
        max_chars: Upper bound on characters to inspect (default 1M).

    Returns:
        Estimated token count (capped at max_chars // 4).

    """
    if isinstance(obj, str):
        return min(len(obj), max_chars) // 4
    # Fallback: cap str() conversion to avoid unbounded allocation
    s = str(obj)[:max_chars]
    return len(s) // 4


def _wrap_execute_with_run_record(execute):
    """Wrap a subclass ``execute`` override so it emits a run record.

    SDK-native workflows override ``execute`` wholesale and never reach
    ``ExecutionMixin.execute``'s telemetry epilogue — historically that
    meant NO ``WorkflowRunRecord`` for exactly the workflows with real
    usage (run-record-corpus RC-2). The wrapper closes the gap at one
    seam instead of editing every override. Emission is best-effort and
    idempotent (see ``TelemetryMixin._emit_workflow_telemetry``); an
    override that raises emits nothing — a run that never produced a
    result is not a run.
    """

    @functools.wraps(execute)
    async def _execute(self, *args: Any, **kwargs: Any):
        result = await execute(self, *args, **kwargs)
        try:
            self._emit_workflow_telemetry(result)
        except Exception:  # noqa: BLE001
            # INTENTIONAL: telemetry is optional diagnostics — never
            # fail a workflow over a record write.
            logger.debug("run-record emission failed", exc_info=True)
        return result

    _execute._emits_run_record = True
    return _execute


class BaseWorkflow(
    ContextProxyMixin,
    ExecutionMixin,
    LLMMixin,
    CoordinationMixin,
    StatePersistenceMixin,
    PromptMixin,
    ExecutorMixin,
    TierRoutingMixin,
    CachingMixin,
    TelemetryMixin,
    ResponseParsingMixin,
    CostTrackingMixin,
    PostSimplificationMixin,
    VerificationMixin,
    ABC,
):
    """Base class for multi-model workflows.

    Inherits from ContextProxyMixin (for WorkflowContext delegation),
    plus PromptMixin, ExecutorMixin, CachingMixin, TelemetryMixin,
    ResponseParsingMixin, and CostTrackingMixin.

    Subclasses define stages, tier mappings, and handler methods.
    The default ``run_stage`` dispatches by convention: stage
    ``"scan"`` calls ``self._scan(input_data, tier)``.

        class MyWorkflow(BaseWorkflow):
            name = "my-workflow"
            description = "Does something useful"
            stages = ["scan", "analyze", "report"]
            tier_map = {
                "scan": ModelTier.CHEAP,
                "analyze": ModelTier.CAPABLE,
                "report": ModelTier.PREMIUM,
            }

            async def _scan(self, input_data, tier):
                ...
            async def _analyze(self, input_data, tier):
                ...
            async def _report(self, input_data, tier):
                ...
    """

    name: str = "base-workflow"
    description: str = "Base workflow template"
    stages: list[str] = []
    tier_map: dict[str, ModelTier] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Ensure every ``execute`` override emits a run record (RC-2)."""
        super().__init_subclass__(**kwargs)
        execute = cls.__dict__.get("execute")
        if (
            execute is not None
            and inspect.iscoroutinefunction(execute)
            and not getattr(execute, "_emits_run_record", False)
        ):
            cls.execute = _wrap_execute_with_run_record(execute)

    # ``_stage_index`` cached_property lives on TierRoutingMixin so test
    # stubs that mix in TierRoutingMixin directly (without BaseWorkflow)
    # inherit it via the descriptor. ExecutionMixin reads it via MRO.

    def __init__(
        self,
        cost_tracker: CostTracker | None = None,
        provider: ModelProvider | str | None = None,
        config: WorkflowConfig | None = None,
        executor: LLMExecutor | None = None,
        telemetry_backend: TelemetryBackend | None = None,
        progress_callback: ProgressCallback | None = None,
        cache: Any | None = None,
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
        ctx: WorkflowContext | None = None,
        enable_post_simplification: bool = False,
        simplification_min_complexity: int = 5,
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
                     (CHEAP -> CAPABLE -> PREMIUM). Enabled by default. Set to False to disable.
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
            ctx: Optional WorkflowContext for composition-based capabilities.
                     When provided, proxy methods delegate to ctx services instead
                     of mixin implementations. When None (default), all behavior
                     comes from mixins as before. See ``workflows/context.py``.
            enable_post_simplification: Whether to run the code simplifier
                     after stage execution but before verification (default False).
                     When enabled, scans output for complexity hotspots and
                     attaches simplification metadata. Implements Boris Cherny's
                     recommendation: simplify Claude-generated code before verifying.
            simplification_min_complexity: Minimum cyclomatic complexity threshold
                     for functions to be flagged by the post-simplification scan
                     (default 5).

        """
        from .config import WorkflowConfig

        # Instance-level logger so subclasses can use self.logger
        self.logger = logging.getLogger(type(self).__module__)

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

        # Cache support (no-op — Anthropic handles caching server-side)
        self._cache = None
        self._enable_cache = False
        self._cache_setup_attempted = True

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
        self._agent_id: str | None = agent_id  # Will be set during execute() if None
        self._heartbeat_coordinator = None  # Lazy initialization on first use
        self._coordination_signals = None  # Lazy initialization on first use

        # State persistence (Phase 4 - AgentStateStore integration)
        self._state_store = state_store
        self._state_exec_id: str | None = None
        self._state_completed_stages: list[str] = []
        self._state_stage_costs: dict[str, float] = {}
        self._state_last_output: Any = None

        # Telemetry tracking (uses TelemetryMixin)
        self._init_telemetry(telemetry_backend)

        # Load config if not provided
        self._config = config or WorkflowConfig.load()

        # Initialize verification loop (uses VerificationMixin)
        self._init_verification()

        # Initialize post-simplification (uses PostSimplificationMixin)
        self._init_post_simplification(
            enable_post_simplification=enable_post_simplification,
            simplification_min_complexity=simplification_min_complexity,
        )

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

    def _error_result(
        self,
        message: str,
        *,
        sdk_stderr: str | None = None,
        sdk_error_kind: str | None = None,
    ) -> WorkflowResult:
        """Build a failed WorkflowResult with the given error message.

        Provides a standard error result so subclasses don't need
        to duplicate the boilerplate. Uses the workflow's own name
        and description for the stage metadata.

        Args:
            message: Human-readable error description.
            sdk_stderr: Optional raw stderr captured from the
                ``claude`` CLI subprocess (already redacted). When
                provided, threaded into ``metadata["sdk_stderr"]``
                so Phase 3's persistence + render layer surfaces it
                on the run-view page. Part of the
                ``docs/specs/sdk-error-message-fidelity/`` flow.
            sdk_error_kind: Optional classifier kind (see
                ``SdkErrorKind`` Literal in ``agent_sdk_adapter``).
                Threaded into ``metadata["sdk_error_kind"]`` so
                downstream consumers (run-view chip classifier,
                periodic reporting) can branch on a typed value
                instead of regex-scanning the error string.

        Returns:
            WorkflowResult with success=False. When either SDK kwarg
            is set, the corresponding ``metadata[...]`` key is
            populated; absent kwargs leave ``metadata`` empty.
        """
        from datetime import datetime

        now = datetime.now()
        metadata: dict[str, Any] = {}
        if sdk_stderr is not None:
            metadata["sdk_stderr"] = sdk_stderr
        if sdk_error_kind is not None:
            metadata["sdk_error_kind"] = sdk_error_kind

        return WorkflowResult(
            success=False,
            stages=[
                WorkflowStage(
                    name=self.name,
                    tier=ModelTier.CAPABLE,
                    description=self.description,
                ),
            ],
            final_output=None,
            cost_report=CostReport(
                total_cost=0.0,
                baseline_cost=0.0,
                savings=0.0,
                savings_percent=0.0,
            ),
            started_at=now,
            completed_at=now,
            total_duration_ms=0,
            provider="anthropic",
            error=message,
            metadata=metadata,
        )

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

    # Context proxy methods (cache, cost, telemetry, prompt, parsing,
    # tier routing, and coordination proxies) are inherited from
    # ContextProxyMixin -- see context_proxy_mixin.py

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Execute a single workflow stage.

        Default implementation dispatches by convention: stage ``"X"``
        calls ``self._X(input_data, tier)``.  Subclasses may override
        for non-standard dispatch.

        Args:
            stage_name: Name of the stage to run
            tier: Model tier to use
            input_data: Input for this stage

        Returns:
            Tuple of (output_data, input_tokens, output_tokens)

        Raises:
            ValueError: If no handler method exists for stage_name

        """
        handler = getattr(self, f"_{stage_name}", None)
        if handler is None:
            raise ValueError(f"Unknown stage: {stage_name}")
        return await handler(input_data, tier)

    # Execution methods (execute, _execute_tier_fallback, _execute_standard,
    # _finalize_execution) are inherited from ExecutionMixin

    # Prompt methods (describe, _build_cached_system_prompt, XML rendering)
    # are inherited from PromptMixin

    # Executor methods (_create_execution_context, _create_default_executor,
    # _get_executor, run_step_with_executor) are inherited from ExecutorMixin
