"""Multi-Model Workflow Templates for Attune AI

Cost-optimized workflow patterns that leverage 3-tier model routing:
- Haiku (cheap): Summarization, classification, triage
- Sonnet (capable): Analysis, code generation, security review
- Opus (premium): Synthesis, architectural decisions, coordination

Usage:
    from attune.workflows import ResearchSynthesisWorkflow

    workflow = ResearchSynthesisWorkflow()
    result = await workflow.execute(
        sources=["doc1.md", "doc2.md"],
        question="What are the key patterns?"
    )

    print(f"Cost: ${result.cost_report.total_cost:.4f}")
    print(f"Saved: {result.cost_report.savings_percent:.1f}% vs premium-only")

Workflow Discovery:
    Workflows can be discovered via entry points (pyproject.toml):

    [project.entry-points."empathy.workflows"]
    my-workflow = "my_package.workflows:MyWorkflow"

    Then call discover_workflows() to load all registered workflows.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import importlib.metadata
import logging
import warnings
from typing import TYPE_CHECKING

# =============================================================================
# LAZY IMPORTS - Deferred loading for faster startup
# =============================================================================
# Workflow imports are deferred until actually accessed, reducing initial
# import time from ~0.5s to ~0.05s for simple use cases.

if TYPE_CHECKING:
    from .base import BaseWorkflow
    from .bug_predict import BugPredictionWorkflow
    from .code_review import CodeReviewWorkflow
    from .config import DEFAULT_MODELS, ModelConfig, WorkflowConfig
    from .deep_review import DeepReviewAgentSDKWorkflow
    from .dependency_check import DependencyCheckWorkflow
    from .discovery_sweep import DiscoverySweepWorkflow

    # DependencyCheckAgentSDKWorkflow: Merged into DependencyCheckWorkflow (v4.2.0)
    from .doc_audit import DocAuditWorkflow

    # DocAuditAgentSDKWorkflow: Merged into DocAuditWorkflow (v4.2.0)
    # DocGenAgentSDKWorkflow: Merged into DocumentGenerationWorkflow (v4.2.0)
    from .document_gen import DocumentGenerationWorkflow
    from .document_manager import DocumentManagerWorkflow
    from .documentation_orchestrator import DocumentationOrchestrator, OrchestratorResult
    from .escalation import (
        AttemptResult,
        ConfidenceValidator,
        EscalationChain,
        EscalationResult,
        Evaluator,
        FeedbackType,
        SemanticEvaluator,
        StructureValidator,
        ValidationFeedback,
        Validator,
        escalate,
    )

    # HealthCheckAgentSDKWorkflow: Merged into OrchestratedHealthCheckWorkflow (v5.2.0)
    from .orchestrated_health_check import HealthCheckReport, OrchestratedHealthCheckWorkflow
    from .perf_audit import PerformanceAuditWorkflow
    from .rag_code_gen import RagCodeGenWorkflow
    from .refactor_plan import RefactorPlanWorkflow

    # RefactorPlanAgentSDKWorkflow: Merged into RefactorPlanWorkflow (v4.2.0)
    from .release_prep import ReleasePreparationWorkflow

    # ReleasePrepAgentSDKWorkflow: Merged into ReleasePreparationWorkflow (v4.2.0)
    # release_prep_crew removed (deprecated, use agents.release)
    from .research_synthesis import ResearchSynthesisWorkflow

    # ResearchSynthesisAgentSDKWorkflow: Merged into ResearchSynthesisWorkflow (v4.2.0)
    from .secure_release import SecureReleasePipeline, SecureReleaseResult
    from .security_audit import SecurityAuditWorkflow
    from .simplify_code import SimplifyCodeWorkflow

    # SimplifyCodeAgentSDKWorkflow: Merged into SimplifyCodeWorkflow (v4.2.0)
    from .step_config import WorkflowStepConfig

    # test_coverage_boost_crew removed (deprecated, use test-gen-parallel)
    from .test_audit import TestAuditWorkflow

    # TestAuditAgentSDKWorkflow: Merged into TestAuditWorkflow (v4.2.0)
    from .test_gen import TestGenerationWorkflow

    # TestGenAgentSDKWorkflow: Merged into TestGenerationWorkflow (v4.2.0)
    from .test_gen_parallel import ParallelTestGenerationWorkflow

# Only import base module eagerly (small, needed for type checks)
from .base import (
    PROVIDER_MODELS,
    BaseWorkflow,
    CostReport,
    ModelProvider,
    ModelTier,
    NextAction,
    WorkflowResult,
    WorkflowStage,
    get_workflow_stats,
)

# Builder pattern for workflow construction
from .builder import WorkflowBuilder, workflow_builder

# Config is small and frequently needed
from .config import DEFAULT_MODELS, ModelConfig, WorkflowConfig, create_example_config, get_model

# Mixins for workflow composition (extracted for maintainability)
from .cost_mixin import CostTrackingMixin
from .parsing_mixin import ResponseParsingMixin

# Routing strategies (small, frequently needed for builder pattern)
from .routing import (
    BalancedRouting,
    CostOptimizedRouting,
    PerformanceOptimizedRouting,
    RoutingContext,
    TierRoutingStrategy,
)
from .step_config import WorkflowStepConfig, steps_from_tier_map, validate_step_config

logger = logging.getLogger(__name__)

# Lazy import mapping for workflow classes
_LAZY_WORKFLOW_IMPORTS: dict[str, tuple[str, str]] = {
    # Core workflows
    "BugPredictionWorkflow": (".bug_predict", "BugPredictionWorkflow"),
    "DocAuditWorkflow": (".doc_audit", "DocAuditWorkflow"),
    "CodeReviewWorkflow": (".code_review", "CodeReviewWorkflow"),
    "DependencyCheckWorkflow": (".dependency_check", "DependencyCheckWorkflow"),
    "DiscoverySweepWorkflow": (".discovery_sweep", "DiscoverySweepWorkflow"),
    "FixWorkflow": (".fix_workflow", "FixWorkflow"),
    "DocumentGenerationWorkflow": (".document_gen", "DocumentGenerationWorkflow"),
    "DocumentManagerWorkflow": (".document_manager", "DocumentManagerWorkflow"),
    "DocumentationOrchestrator": (".documentation_orchestrator", "DocumentationOrchestrator"),
    "OrchestratorResult": (".documentation_orchestrator", "OrchestratorResult"),
    "OrchestratedHealthCheckWorkflow": (
        ".orchestrated_health_check",
        "OrchestratedHealthCheckWorkflow",
    ),
    "HealthCheckReport": (".orchestrated_health_check", "HealthCheckReport"),
    "PerformanceAuditWorkflow": (".perf_audit", "PerformanceAuditWorkflow"),
    "RefactorPlanWorkflow": (".refactor_plan", "RefactorPlanWorkflow"),
    "ReleasePreparationWorkflow": (".release_prep", "ReleasePreparationWorkflow"),
    # ReleasePreparationCrew removed (deprecated, use ReleasePrepTeamWorkflow)
    "ResearchSynthesisWorkflow": (".research_synthesis", "ResearchSynthesisWorkflow"),
    "SecureReleasePipeline": (".secure_release", "SecureReleasePipeline"),
    "SecureReleaseResult": (".secure_release", "SecureReleaseResult"),
    "RagCodeGenWorkflow": (".rag_code_gen", "RagCodeGenWorkflow"),
    "SecurityAuditWorkflow": (".security_audit", "SecurityAuditWorkflow"),
    "SimplifyCodeWorkflow": (".simplify_code", "SimplifyCodeWorkflow"),
    # TestCoverageBoostCrew removed (deprecated, use ParallelTestGenerationWorkflow)
    "TestAuditWorkflow": (".test_audit", "TestAuditWorkflow"),
    "TestGenerationWorkflow": (".test_gen", "TestGenerationWorkflow"),
    "ParallelTestGenerationWorkflow": (".test_gen_parallel", "ParallelTestGenerationWorkflow"),
    # Additional workflows (restored to registry)
    "TestMaintenanceWorkflow": (".test_maintenance", "TestMaintenanceWorkflow"),
    "BatchProcessingWorkflow": (".batch_processing", "BatchProcessingWorkflow"),
    # ProgressiveTestGenWorkflow removed in v6.3.0 (deprecated since v5.3.0;
    # users are routed to ParallelTestGenerationWorkflow via
    # migration.py's "progressive-test-gen" -> "test-gen" alias).
    # AgentCodeReviewWorkflow: Merged into CodeReviewWorkflow (v4.2.0)
    "DeepReviewAgentSDKWorkflow": (".deep_review", "DeepReviewAgentSDKWorkflow"),
    # Agent SDK adapters (v3.9.3)
    # SecurityAuditAgentSDKWorkflow: Merged into SecurityAuditWorkflow (v4.2.0)
    # PerfAuditAgentSDKWorkflow: Merged into PerformanceAuditWorkflow (v4.2.0)
    # ReleasePrepAgentSDKWorkflow: Merged into ReleasePreparationWorkflow (v4.2.0)
    # TestAuditAgentSDKWorkflow: Merged into TestAuditWorkflow (v4.2.0)
    # BugPredictAgentSDKWorkflow: Merged into BugPredictionWorkflow (v4.2.0)
    # RefactorPlanAgentSDKWorkflow: Merged into RefactorPlanWorkflow (v4.2.0)
    # TestGenAgentSDKWorkflow: Merged into TestGenerationWorkflow (v4.2.0)
    # DocAuditAgentSDKWorkflow: Merged into DocAuditWorkflow (v4.2.0)
    # DocGenAgentSDKWorkflow: Merged into DocumentGenerationWorkflow (v4.2.0)
    # SimplifyCodeAgentSDKWorkflow: Merged into SimplifyCodeWorkflow (v4.2.0)
    # DependencyCheckAgentSDKWorkflow: Merged into DependencyCheckWorkflow (v4.2.0)
    # ResearchSynthesisAgentSDKWorkflow: Merged into ResearchSynthesisWorkflow (v4.2.0)
    # HealthCheckAgentSDKWorkflow: Merged into OrchestratedHealthCheckWorkflow (v5.2.0)
    # Release agent team (v5.2)
    "ReleasePrepTeamWorkflow": (
        "attune.agents.release.release_prep_team",
        "ReleasePrepTeamWorkflow",
    ),
}

# Cache for loaded workflow classes
_loaded_workflow_modules: dict[str, object] = {}


def _lazy_import_workflow(name: str) -> object:
    """Import a workflow class lazily.

    Args:
        name: Class name to import (must be in _LAZY_WORKFLOW_IMPORTS).

    Returns:
        The imported class or object.

    Raises:
        AttributeError: If name is not a known lazy import.
        ImportError: If the module cannot be loaded.

    """
    if name not in _LAZY_WORKFLOW_IMPORTS:
        raise AttributeError(f"module 'attune.workflows' has no attribute '{name}'")

    module_path, attr_name = _LAZY_WORKFLOW_IMPORTS[name]

    # Check cache first
    cache_key = f"{module_path}.{attr_name}"
    if cache_key in _loaded_workflow_modules:
        return _loaded_workflow_modules[cache_key]

    # Import the module and get the attribute
    import importlib

    try:
        module = importlib.import_module(module_path, package="attune.workflows")
        attr = getattr(module, attr_name)
    except (ImportError, AttributeError) as e:
        logger.debug(f"Failed to lazy-import {name} from {module_path}: {e}")
        raise

    # Cache and return
    _loaded_workflow_modules[cache_key] = attr
    return attr


# Legacy one-command family (morning/ship/fix-all/learn) — REMOVED.
# The implementation modules (workflow_ship.py, workflow_morning.py,
# workflow_fixall.py, workflow_learn.py, the workflow_commands.py facade,
# _workflow_helpers.py) had zero live callers: no argparse subcommand
# wired them, and the "ship" NL intent routes to release-prep instead
# (cli_router.py maps "ship" -> ("release", "prep")). Accessing these
# names still works (deprecation path, not a hard AttributeError) but
# raises with a pointer to the successor. See
# docs/reports/d-block-triage-2026-07-14.md and CHANGELOG.md.
#
# Deliberately NOT bound at module level (no ``cmd_ship = None`` etc.):
# a bound module global shadows ``__getattr__`` for ordinary attribute
# access (``attune.workflows.cmd_ship``, ``from attune.workflows import
# cmd_ship``), which is exactly how the prior "loaded lazily via
# __getattr__" placeholders silently returned ``None`` instead of ever
# lazy-loading -- confirmed nothing in ``src/`` outside this module
# triggered the load any other way. Leaving the names unbound routes
# every access path through ``__getattr__`` so the deprecation warning
# is actually observable.
_DEPRECATED_CLI_COMMAND_SUCCESSORS: dict[str, str | None] = {
    "cmd_ship": "attune workflow run release-prep",
    "cmd_morning": None,
    "cmd_fix_all": None,
    "cmd_learn": None,
}


def _deprecated_cli_command_stub(name: str) -> object:
    """Build a stub for a removed one-command workflow CLI handler.

    Emits a DeprecationWarning on access (matching the
    ``attune.StateManager``-style deprecation pattern) and raises
    ``NotImplementedError`` when called, since the implementation has
    been deleted -- there is nothing left to run.
    """
    successor = _DEPRECATED_CLI_COMMAND_SUCCESSORS.get(name)
    message = (
        f"attune.workflows.{name} belonged to the retired legacy "
        "one-command workflow family (morning/ship/fix-all/learn) and "
        "has been removed -- it had no live caller (no CLI wiring; the "
        "'ship' NL intent already routes to release-prep)."
    )
    if successor:
        message += f" Use '{successor}' instead."
    warnings.warn(message, DeprecationWarning, stacklevel=3)

    def _stub(*_args: object, **_kwargs: object) -> int:
        raise NotImplementedError(message)

    return _stub


# Default workflow registry - uses CLASS NAMES (strings) for lazy loading
# Actual classes are loaded on first access via _get_workflow_class()
_DEFAULT_WORKFLOW_NAMES: dict[str, str] = {
    # Core workflows
    "code-review": "CodeReviewWorkflow",
    # Discovery meta-workflow (Phase 1 — pattern source only)
    "discovery-sweep": "DiscoverySweepWorkflow",
    # Documentation workflows
    "doc-audit": "DocAuditWorkflow",
    "doc-gen": "DocumentGenerationWorkflow",
    "doc-orchestrator": "DocumentationOrchestrator",
    # Outcome-first fix (docs/specs/outcome-first-fix/, Phase 2)
    "fix": "FixWorkflow",
    # Analysis workflows
    "bug-predict": "BugPredictionWorkflow",
    "security-audit": "SecurityAuditWorkflow",
    "rag-code-gen": "RagCodeGenWorkflow",
    "perf-audit": "PerformanceAuditWorkflow",
    # Generation workflows
    "test-audit": "TestAuditWorkflow",
    "test-gen": "TestGenerationWorkflow",
    # test-gen-parallel: Consolidated into test-gen (migration.py)
    "refactor-plan": "RefactorPlanWorkflow",
    # Operational workflows
    "dependency-check": "DependencyCheckWorkflow",
    # Simplification workflow (v3.4)
    "simplify-code": "SimplifyCodeWorkflow",
    # Composite security pipeline (v3.0)
    "secure-release": "SecureReleasePipeline",
    # Meta-orchestration workflows (v4.0.0)
    "orchestrated-health-check": "OrchestratedHealthCheckWorkflow",
    # Release preparation. Two distinct workflows:
    #   release-prep  — deterministic gate (real bandit/ruff/pytest + hard
    #                   thresholds), the agent team (canonical). `release-gate`
    #                   is a first-class synonym for the same class.
    #   release-notes — advisory: drafts a changelog + LLM go/no-go (SDK).
    "release-prep": "ReleasePrepTeamWorkflow",
    "release-gate": "ReleasePrepTeamWorkflow",
    "release-notes": "ReleasePreparationWorkflow",
    # Research and synthesis workflows
    "research-synthesis": "ResearchSynthesisWorkflow",
    # code-review-sdk: Merged into code-review (v4.2.0)
    # Multi-pass deep review (v3.9)
    "deep-review": "DeepReviewAgentSDKWorkflow",
    # Agent SDK adapters (v3.9.3)
    # security-audit-sdk: Merged into security-audit (v4.2.0)
    # perf-audit-sdk: Merged into perf-audit (v4.2.0)
    # release-prep-sdk: Merged into release-prep (v4.2.0)
    # test-audit-sdk: Merged into test-audit (v4.2.0)
    # bug-predict-sdk: Merged into bug-predict (v4.2.0)
    # refactor-plan-sdk: Merged into refactor-plan (v4.2.0)
    # test-gen-sdk: Merged into test-gen (v4.2.0)
    # doc-audit-sdk: Merged into doc-audit (v4.2.0)
    # doc-gen-sdk: Merged into doc-gen (v4.2.0)
    # simplify-code-sdk: Merged into simplify-code (v4.2.0)
    # dependency-check-sdk: Merged into dependency-check (v4.2.0)
    # research-synthesis-sdk: Merged into research-synthesis (v4.2.0)
    "health-check": "OrchestratedHealthCheckWorkflow",
    # test-maintenance: Removed — utility class, not a BaseWorkflow.
    # Import directly: from attune.workflows.test_maintenance import TestMaintenanceWorkflow
    # batch-processing: Removed — batch API client with execute_batch().
    # Import directly: from attune.workflows.batch_processing import BatchProcessingWorkflow
    # Consolidated slugs removed from registry -- handled by migration system:
    # "pro-review" -> code-review (migration.py)
    # "pr-review" -> code-review (migration.py)
    # "document-manager" -> doc-gen (migration.py)
    # "orchestrated-release-prep" -> release-prep (migration.py)
    # "test-gen-parallel" -> test-gen (migration.py)
    # "autonomous-test-gen" -> test-gen (migration.py)
    # "progressive-test-gen" -> test-gen (migration.py)
    # "test-coverage-boost" -> test-gen (migration.py)
}

# Opt-in workflows - class names for lazy loading
_OPT_IN_WORKFLOW_NAMES: dict[str, str] = {}

# Workflow registry - populated lazily on first access
WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]] = {}
_registry_initialized = False

# All workflows are SDK-native (v4.2.0+).
# No separate SDK routing maps needed.


def _get_workflow_class(class_name: str) -> type[BaseWorkflow]:
    """Get a workflow class by name (lazy loading)."""
    return _lazy_import_workflow(class_name)


def _ensure_registry_initialized() -> None:
    """Initialize workflow registry on first access."""
    global _registry_initialized
    if not _registry_initialized:
        WORKFLOW_REGISTRY.update(discover_workflows())
        _registry_initialized = True


def discover_workflows(
    include_defaults: bool = True,
    config: "WorkflowConfig | None" = None,
) -> dict[str, type[BaseWorkflow]]:
    """Discover workflows via entry points and config.

    This function loads workflows registered as entry points under the
    'empathy.workflows' group. This allows third-party packages to register
    custom workflows that integrate with the Attune AI.

    Note: Workflows are loaded lazily - classes are only imported when
    the workflow is actually used, reducing initial import time.

    Args:
        include_defaults: Whether to include default built-in workflows
        config: Optional WorkflowConfig for enabled/disabled workflows

    Returns:
        Dictionary mapping workflow names to workflow classes

    Example:
        from attune.workflows import discover_workflows
        workflows = discover_workflows()
        MyWorkflow = workflows.get("code-review")

    """
    discovered: dict[str, type[BaseWorkflow]] = {}

    # Include default workflows if requested (lazy load each)
    if include_defaults:
        for workflow_id, class_name in _DEFAULT_WORKFLOW_NAMES.items():
            try:
                discovered[workflow_id] = _get_workflow_class(class_name)
            except (ImportError, AttributeError) as e:
                logger.warning(
                    "Failed to load workflow '%s' (%s): %s",
                    workflow_id,
                    class_name,
                    e,
                )

    # Add opt-in workflows based on config
    if config is not None:
        # HIPAA mode auto-enables healthcare workflows
        if config.is_hipaa_mode():
            for workflow_id, class_name in _OPT_IN_WORKFLOW_NAMES.items():
                try:
                    discovered[workflow_id] = _get_workflow_class(class_name)
                except (ImportError, AttributeError) as e:
                    logger.warning(
                        "Failed to load HIPAA workflow '%s' (%s): %s",
                        workflow_id,
                        class_name,
                        e,
                    )

        # Explicitly enabled workflows
        for workflow_name in config.enabled_workflows:
            if workflow_name in _OPT_IN_WORKFLOW_NAMES:
                try:
                    discovered[workflow_name] = _get_workflow_class(
                        _OPT_IN_WORKFLOW_NAMES[workflow_name],
                    )
                except (ImportError, AttributeError) as e:
                    logger.warning(
                        "Failed to load enabled workflow '%s': %s",
                        workflow_name,
                        e,
                    )

        # Explicitly disabled workflows
        for workflow_name in config.disabled_workflows:
            discovered.pop(workflow_name, None)

    # Discover via entry points
    try:
        eps = importlib.metadata.entry_points(group="empathy.workflows")
        for ep in eps:
            try:
                workflow_cls = ep.load()
                if isinstance(workflow_cls, type) and hasattr(workflow_cls, "execute"):
                    if config is None or ep.name not in config.disabled_workflows:
                        discovered[ep.name] = workflow_cls
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: entry point plugins may fail; log but don't break
                logger.warning(
                    "Failed to load workflow entry point '%s': %s",
                    ep.name,
                    e,
                )
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: entry_points() may not be available; log but don't break
        logger.debug("Entry point discovery unavailable: %s", e)

    return discovered


def refresh_workflow_registry(config: "WorkflowConfig | None" = None) -> None:
    """Refresh the global WORKFLOW_REGISTRY by re-discovering all workflows.

    Call this after installing new packages that register workflows,
    or after changing the WorkflowConfig (e.g., enabling HIPAA mode).

    Args:
        config: Optional WorkflowConfig for enabled/disabled workflows

    """
    global WORKFLOW_REGISTRY
    WORKFLOW_REGISTRY.clear()
    WORKFLOW_REGISTRY.update(discover_workflows(config=config))


def get_opt_in_workflows() -> dict[str, type]:
    """Get the list of opt-in workflows that require explicit enabling.

    Returns:
        Dictionary of workflow name to class for opt-in workflows

    """
    result = {}
    for name, class_name in _OPT_IN_WORKFLOW_NAMES.items():
        try:
            result[name] = _get_workflow_class(class_name)
        except (ImportError, AttributeError) as e:
            logger.warning(
                "Failed to load opt-in workflow '%s' (%s): %s",
                name,
                class_name,
                e,
            )
    return result


# Note: Registry is initialized lazily on first access via _ensure_registry_initialized()
# Do NOT call discover_workflows() here - it defeats lazy loading


def get_workflow(name: str) -> type[BaseWorkflow]:
    """Get a workflow class by name, routing to SDK variant automatically.

    When the user requests a base workflow (e.g. ``"security-audit"``),
    this function automatically routes to the SDK variant
    (``"security-audit-sdk"``). If the user explicitly requests an
    ``-sdk`` suffix, it is used directly without re-mapping.

    Args:
        name: Workflow name (e.g., "research", "code-review", "doc-gen")

    Returns:
        Workflow class (SDK variant for mapped workflows)

    Raises:
        KeyError: If workflow not found

    """
    _ensure_registry_initialized()

    if name not in WORKFLOW_REGISTRY:
        available = ", ".join(sorted(WORKFLOW_REGISTRY.keys()))
        raise KeyError(f"Unknown workflow: {name}. Available: {available}")
    return WORKFLOW_REGISTRY[name]


def list_workflows() -> list[dict]:
    """List available workflows with descriptions.

    Returns:
        List of workflow info dicts

    """
    _ensure_registry_initialized()

    workflows = []
    for name, cls in WORKFLOW_REGISTRY.items():
        stages = getattr(cls, "stages", [])
        tier_map = getattr(cls, "tier_map", {})
        description = getattr(cls, "description", "No description")

        # All workflows are SDK-native (v4.2.0+)
        engine = "sdk"

        workflows.append(
            {
                "name": name,
                "class": cls.__name__,
                "description": description,
                "stages": stages,
                "tier_map": {k: v.value for k, v in tier_map.items()} if tier_map else {},
                "engine": engine,
            },
        )
    return workflows


def __getattr__(name: str) -> object:
    """Lazy import handler for workflow classes."""
    if name in _LAZY_WORKFLOW_IMPORTS:
        return _lazy_import_workflow(name)

    # Handle deprecated CLI commands (legacy one-command family, removed)
    if name in _DEPRECATED_CLI_COMMAND_SUCCESSORS:
        return _deprecated_cli_command_stub(name)

    # Handle migration module exports
    _MIGRATION_EXPORTS = {
        "resolve_workflow_migration",
        "MigrationConfig",
        "WORKFLOW_ALIASES",
        "show_migration_tip",
        "list_migrations",
    }
    if name in _MIGRATION_EXPORTS:
        from attune.workflows import migration

        return getattr(migration, name)

    raise AttributeError(f"module 'attune.workflows' has no attribute '{name}'")


__all__ = [
    "DEFAULT_MODELS",
    "PROVIDER_MODELS",
    # Registry and discovery
    "WORKFLOW_REGISTRY",
    # Base classes and mixins
    "BaseWorkflow",
    "CostTrackingMixin",
    "ResponseParsingMixin",
    # Routing strategies
    "TierRoutingStrategy",
    "RoutingContext",
    "CostOptimizedRouting",
    "PerformanceOptimizedRouting",
    "BalancedRouting",
    # Builder pattern
    "WorkflowBuilder",
    "workflow_builder",
    # New high-value workflows
    "BugPredictionWorkflow",
    "CodeReviewWorkflow",
    "CostReport",
    "DependencyCheckWorkflow",
    "DiscoverySweepWorkflow",
    "DocAuditWorkflow",
    "DocumentGenerationWorkflow",
    "DocumentManagerWorkflow",
    # Documentation management (v3.5)
    "DocumentationOrchestrator",
    # Health check crew integration (v3.1)
    # Removed deprecated: "HealthCheckWorkflow" (use OrchestratedHealthCheckWorkflow)
    "HealthCheckReport",
    "ModelConfig",
    "ModelProvider",
    "ModelTier",
    "NextAction",
    "OrchestratorResult",
    "PerformanceAuditWorkflow",
    "RagCodeGenWorkflow",
    "RefactorPlanWorkflow",
    "ReleasePreparationWorkflow",
    # Workflow implementations
    "ResearchSynthesisWorkflow",
    # Security crew integration (v3.0)
    "SecureReleasePipeline",
    "SecureReleaseResult",
    "SecurityAuditWorkflow",
    "SimplifyCodeWorkflow",
    "TestAuditWorkflow",
    "TestGenerationWorkflow",
    "ParallelTestGenerationWorkflow",
    # Configuration
    "WorkflowConfig",
    "WorkflowResult",
    "WorkflowStage",
    # Step configuration (new)
    "WorkflowStepConfig",
    "cmd_fix_all",
    "cmd_learn",
    # CLI commands (re-exported from workflow_commands.py)
    "cmd_morning",
    "cmd_ship",
    "create_example_config",
    "discover_workflows",
    "get_model",
    "get_workflow",
    "get_workflow_stats",
    "list_workflows",
    "refresh_workflow_registry",
    "steps_from_tier_map",
    "validate_step_config",
    # CrewAI-based multi-agent workflows (v4.0.0)
    # Removed deprecated: "HealthCheckCrew" (use OrchestratedHealthCheckWorkflow)
    # Removed deprecated: "HealthCheckCrewResult"
    # Removed deprecated: "ReleasePreparationCrew" (use ReleasePrepTeamWorkflow)
    # Removed deprecated: "ReleasePreparationCrewResult"
    # Removed deprecated: "TestCoverageBoostCrew" (use ParallelTestGenerationWorkflow)
    # Removed deprecated: "TestCoverageBoostCrewResult"
    # Removed deprecated: "TestCoverageBoostWorkflow"
    # Removed deprecated: "CoverageBoostResult"
    # Experimental: Meta-orchestration
    "OrchestratedHealthCheckWorkflow",
    # Removed in v7.0.0: "OrchestratedReleasePrepWorkflow" / "ReleaseReadinessReport"
    # (deprecated v5.2.0; use ReleasePrepTeamWorkflow from attune.agents.release)
    "HealthCheckReport",
    # Additional workflows (added for completeness)
    # Test5Workflow removed - test artifact
    "TestMaintenanceWorkflow",
    "BatchProcessingWorkflow",
    # ProgressiveTestGenWorkflow removed in v6.3.0 — see _LAZY_WORKFLOW_IMPORTS above
    # Multi-pass deep review (Agent SDK)
    "DeepReviewAgentSDKWorkflow",
    # Agent SDK adapters (v3.9.3)
    # SecurityAuditAgentSDKWorkflow: Merged (v4.2.0)
    # PerfAuditAgentSDKWorkflow: Merged (v4.2.0)
    # ReleasePrepAgentSDKWorkflow: Merged (v4.2.0)
    # TestAuditAgentSDKWorkflow: Merged (v4.2.0)
    # BugPredictAgentSDKWorkflow: Merged (v4.2.0)
    # RefactorPlanAgentSDKWorkflow: Merged (v4.2.0)
    # TestGenAgentSDKWorkflow: Merged (v4.2.0)
    # DocAuditAgentSDKWorkflow: Merged (v4.2.0)
    # DocGenAgentSDKWorkflow: Merged (v4.2.0)
    # SimplifyCodeAgentSDKWorkflow: Merged (v4.2.0)
    # DependencyCheckAgentSDKWorkflow: Merged (v4.2.0)
    # ResearchSynthesisAgentSDKWorkflow: Merged (v4.2.0)
    # HealthCheckAgentSDKWorkflow: Merged into OrchestratedHealthCheckWorkflow (v5.2.0)
    # XML-enhanced prompting removed (v5.1.0)
    # Workflow migration system
    "resolve_workflow_migration",
    "MigrationConfig",
    "WORKFLOW_ALIASES",
    "show_migration_tip",
    "list_migrations",
]
