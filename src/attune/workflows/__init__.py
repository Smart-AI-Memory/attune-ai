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
import importlib.util
import logging
import os
from typing import TYPE_CHECKING

# =============================================================================
# LAZY IMPORTS - Deferred loading for faster startup
# =============================================================================
# Workflow imports are deferred until actually accessed, reducing initial
# import time from ~0.5s to ~0.05s for simple use cases.

if TYPE_CHECKING:
    from .base import BaseWorkflow
    from .bug_predict import BugPredictionWorkflow
    from .bug_predict_agent_sdk import BugPredictAgentSDKWorkflow
    from .code_review import CodeReviewWorkflow
    from .code_review_pipeline import CodeReviewPipeline, CodeReviewPipelineResult
    from .config import DEFAULT_MODELS, ModelConfig, WorkflowConfig
    from .deep_review_agent_sdk import DeepReviewAgentSDKWorkflow
    from .dependency_check import DependencyCheckWorkflow
    from .dependency_check_agent_sdk import DependencyCheckAgentSDKWorkflow
    from .doc_audit import DocAuditWorkflow
    from .doc_audit_agent_sdk import DocAuditAgentSDKWorkflow
    from .doc_gen_agent_sdk import DocGenAgentSDKWorkflow
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
    from .health_check_agent_sdk import HealthCheckAgentSDKWorkflow
    from .manage_documentation import ManageDocumentationCrew, ManageDocumentationCrewResult
    from .orchestrated_health_check import HealthCheckReport, OrchestratedHealthCheckWorkflow
    from .orchestrated_release_prep import OrchestratedReleasePrepWorkflow, ReleaseReadinessReport
    from .perf_audit import PerformanceAuditWorkflow
    from .perf_audit_agent_sdk import PerfAuditAgentSDKWorkflow
    from .pr_review import PRReviewResult, PRReviewWorkflow
    from .refactor_plan import RefactorPlanWorkflow
    from .refactor_plan_agent_sdk import RefactorPlanAgentSDKWorkflow
    from .release_prep import ReleasePreparationWorkflow
    from .release_prep_agent_sdk import ReleasePrepAgentSDKWorkflow

    # release_prep_crew removed (deprecated, use agents.release)
    from .research_synthesis import ResearchSynthesisWorkflow
    from .research_synthesis_agent_sdk import ResearchSynthesisAgentSDKWorkflow
    from .secure_release import SecureReleasePipeline, SecureReleaseResult
    from .security_audit import SecurityAuditWorkflow
    from .security_audit_agent_sdk import SecurityAuditAgentSDKWorkflow
    from .simplify_code import SimplifyCodeWorkflow
    from .simplify_code_agent_sdk import SimplifyCodeAgentSDKWorkflow
    from .step_config import WorkflowStepConfig

    # test_coverage_boost_crew removed (deprecated, use test-gen-parallel)
    from .test_audit import TestAuditWorkflow
    from .test_audit_agent_sdk import TestAuditAgentSDKWorkflow
    from .test_gen import TestGenerationWorkflow
    from .test_gen_agent_sdk import TestGenAgentSDKWorkflow
    from .test_gen_parallel import ParallelTestGenerationWorkflow
    from .xml_enhanced_crew import XMLAgent, XMLTask

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
    "CodeReviewPipeline": (".code_review_pipeline", "CodeReviewPipeline"),
    "CodeReviewPipelineResult": (".code_review_pipeline", "CodeReviewPipelineResult"),
    "DependencyCheckWorkflow": (".dependency_check", "DependencyCheckWorkflow"),
    "DocumentGenerationWorkflow": (".document_gen", "DocumentGenerationWorkflow"),
    "DocumentManagerWorkflow": (".document_manager", "DocumentManagerWorkflow"),
    "DocumentationOrchestrator": (".documentation_orchestrator", "DocumentationOrchestrator"),
    "OrchestratorResult": (".documentation_orchestrator", "OrchestratorResult"),
    "ManageDocumentationCrew": (".manage_documentation", "ManageDocumentationCrew"),
    "ManageDocumentationCrewResult": (".manage_documentation", "ManageDocumentationCrewResult"),
    "OrchestratedHealthCheckWorkflow": (
        ".orchestrated_health_check",
        "OrchestratedHealthCheckWorkflow",
    ),
    "HealthCheckReport": (".orchestrated_health_check", "HealthCheckReport"),
    "OrchestratedReleasePrepWorkflow": (
        ".orchestrated_release_prep",
        "OrchestratedReleasePrepWorkflow",
    ),
    "ReleaseReadinessReport": (".orchestrated_release_prep", "ReleaseReadinessReport"),
    "PerformanceAuditWorkflow": (".perf_audit", "PerformanceAuditWorkflow"),
    "PRReviewWorkflow": (".pr_review", "PRReviewWorkflow"),
    "PRReviewResult": (".pr_review", "PRReviewResult"),
    "RefactorPlanWorkflow": (".refactor_plan", "RefactorPlanWorkflow"),
    "ReleasePreparationWorkflow": (".release_prep", "ReleasePreparationWorkflow"),
    # ReleasePreparationCrew removed (deprecated, use ReleasePrepTeamWorkflow)
    "ResearchSynthesisWorkflow": (".research_synthesis", "ResearchSynthesisWorkflow"),
    "SecureReleasePipeline": (".secure_release", "SecureReleasePipeline"),
    "SecureReleaseResult": (".secure_release", "SecureReleaseResult"),
    "SecurityAuditWorkflow": (".security_audit", "SecurityAuditWorkflow"),
    "SimplifyCodeWorkflow": (".simplify_code", "SimplifyCodeWorkflow"),
    # TestCoverageBoostCrew removed (deprecated, use ParallelTestGenerationWorkflow)
    "TestAuditWorkflow": (".test_audit", "TestAuditWorkflow"),
    "TestGenerationWorkflow": (".test_gen", "TestGenerationWorkflow"),
    "ParallelTestGenerationWorkflow": (".test_gen_parallel", "ParallelTestGenerationWorkflow"),
    # Additional workflows (restored to registry)
    "TestMaintenanceWorkflow": (".test_maintenance", "TestMaintenanceWorkflow"),
    "BatchProcessingWorkflow": (".batch_processing", "BatchProcessingWorkflow"),
    "ProgressiveTestGenWorkflow": (".progressive.test_gen", "ProgressiveTestGenWorkflow"),
    "AutonomousTestGenerator": (".autonomous_test_gen", "AutonomousTestGenerator"),
    "AgentCodeReviewWorkflow": (".code_review_agent_sdk", "AgentCodeReviewWorkflow"),
    "DeepReviewAgentSDKWorkflow": (".deep_review_agent_sdk", "DeepReviewAgentSDKWorkflow"),
    # Agent SDK adapters (v3.9.3)
    "SecurityAuditAgentSDKWorkflow": (".security_audit_agent_sdk", "SecurityAuditAgentSDKWorkflow"),
    "PerfAuditAgentSDKWorkflow": (".perf_audit_agent_sdk", "PerfAuditAgentSDKWorkflow"),
    "ReleasePrepAgentSDKWorkflow": (".release_prep_agent_sdk", "ReleasePrepAgentSDKWorkflow"),
    "TestAuditAgentSDKWorkflow": (".test_audit_agent_sdk", "TestAuditAgentSDKWorkflow"),
    "BugPredictAgentSDKWorkflow": (".bug_predict_agent_sdk", "BugPredictAgentSDKWorkflow"),
    "RefactorPlanAgentSDKWorkflow": (".refactor_plan_agent_sdk", "RefactorPlanAgentSDKWorkflow"),
    "TestGenAgentSDKWorkflow": (".test_gen_agent_sdk", "TestGenAgentSDKWorkflow"),
    "DocAuditAgentSDKWorkflow": (".doc_audit_agent_sdk", "DocAuditAgentSDKWorkflow"),
    "DocGenAgentSDKWorkflow": (".doc_gen_agent_sdk", "DocGenAgentSDKWorkflow"),
    "SimplifyCodeAgentSDKWorkflow": (".simplify_code_agent_sdk", "SimplifyCodeAgentSDKWorkflow"),
    "DependencyCheckAgentSDKWorkflow": (
        ".dependency_check_agent_sdk",
        "DependencyCheckAgentSDKWorkflow",
    ),
    "ResearchSynthesisAgentSDKWorkflow": (
        ".research_synthesis_agent_sdk",
        "ResearchSynthesisAgentSDKWorkflow",
    ),
    "HealthCheckAgentSDKWorkflow": (".health_check_agent_sdk", "HealthCheckAgentSDKWorkflow"),
    "XMLAgent": (".xml_enhanced_crew", "XMLAgent"),
    "XMLTask": (".xml_enhanced_crew", "XMLTask"),
    "parse_xml_response": (".xml_enhanced_crew", "parse_xml_response"),
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


# Re-export CLI commands from workflow_commands.py (lazy loaded)
_parent_dir = os.path.dirname(os.path.dirname(__file__))
_workflows_module_path = os.path.join(_parent_dir, "workflow_commands.py")

# Initialize to None for type checking - loaded lazily via __getattr__
cmd_morning = None
cmd_ship = None
cmd_fix_all = None
cmd_learn = None
_cli_loaded = False


def _load_cli_commands() -> None:
    """Load CLI commands lazily."""
    global cmd_morning, cmd_ship, cmd_fix_all, cmd_learn, _cli_loaded
    if _cli_loaded:
        return

    if os.path.exists(_workflows_module_path):
        _spec = importlib.util.spec_from_file_location("_workflows_cli", _workflows_module_path)
        if _spec is not None and _spec.loader is not None:
            _workflows_cli = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_workflows_cli)

            # Re-export CLI commands
            cmd_morning = _workflows_cli.cmd_morning
            cmd_ship = _workflows_cli.cmd_ship
            cmd_fix_all = _workflows_cli.cmd_fix_all
            cmd_learn = _workflows_cli.cmd_learn

    _cli_loaded = True


# Default workflow registry - uses CLASS NAMES (strings) for lazy loading
# Actual classes are loaded on first access via _get_workflow_class()
_DEFAULT_WORKFLOW_NAMES: dict[str, str] = {
    # Core workflows
    "code-review": "CodeReviewWorkflow",
    # Documentation workflows
    "doc-audit": "DocAuditWorkflow",
    "doc-gen": "DocumentGenerationWorkflow",
    "doc-orchestrator": "DocumentationOrchestrator",
    # Analysis workflows
    "bug-predict": "BugPredictionWorkflow",
    "security-audit": "SecurityAuditWorkflow",
    "perf-audit": "PerformanceAuditWorkflow",
    # Generation workflows
    "test-audit": "TestAuditWorkflow",
    "test-gen": "TestGenerationWorkflow",
    "test-gen-parallel": "ParallelTestGenerationWorkflow",
    "refactor-plan": "RefactorPlanWorkflow",
    # Operational workflows
    "dependency-check": "DependencyCheckWorkflow",
    # Simplification workflow (v3.4)
    "simplify-code": "SimplifyCodeWorkflow",
    # Composite security pipeline (v3.0)
    "secure-release": "SecureReleasePipeline",
    # Meta-orchestration workflows (v4.0.0)
    "orchestrated-health-check": "OrchestratedHealthCheckWorkflow",
    # Release preparation (v5.2 — agent team is canonical)
    "release-prep": "ReleasePrepTeamWorkflow",
    # Research and synthesis workflows
    "research-synthesis": "ResearchSynthesisWorkflow",
    # Agent SDK code review (v3.9)
    "code-review-sdk": "AgentCodeReviewWorkflow",
    # Multi-pass deep review (v3.9)
    "deep-review-sdk": "DeepReviewAgentSDKWorkflow",
    # Agent SDK adapters (v3.9.3)
    "security-audit-sdk": "SecurityAuditAgentSDKWorkflow",
    "perf-audit-sdk": "PerfAuditAgentSDKWorkflow",
    "release-prep-sdk": "ReleasePrepAgentSDKWorkflow",
    "test-audit-sdk": "TestAuditAgentSDKWorkflow",
    "bug-predict-sdk": "BugPredictAgentSDKWorkflow",
    "refactor-plan-sdk": "RefactorPlanAgentSDKWorkflow",
    "test-gen-sdk": "TestGenAgentSDKWorkflow",
    "doc-audit-sdk": "DocAuditAgentSDKWorkflow",
    "doc-gen-sdk": "DocGenAgentSDKWorkflow",
    "simplify-code-sdk": "SimplifyCodeAgentSDKWorkflow",
    "dependency-check-sdk": "DependencyCheckAgentSDKWorkflow",
    "research-synthesis-sdk": "ResearchSynthesisAgentSDKWorkflow",
    "health-check-sdk": "HealthCheckAgentSDKWorkflow",
    # test-maintenance: Removed — utility class, not a BaseWorkflow.
    # Import directly: from attune.workflows.test_maintenance import TestMaintenanceWorkflow
    # batch-processing: Removed — batch API client with execute_batch().
    # Import directly: from attune.workflows.batch_processing import BatchProcessingWorkflow
    # Consolidated slugs removed from registry -- handled by migration system:
    # "pro-review" -> code-review (migration.py)
    # "pr-review" -> code-review (migration.py)
    # "document-manager" -> doc-gen (migration.py)
    # "orchestrated-release-prep" -> release-prep (migration.py)
    # "autonomous-test-gen" -> test-gen-parallel (migration.py)
    # "progressive-test-gen" -> test-gen-parallel (migration.py)
    # "test-coverage-boost" -> test-gen (migration.py)
}

# Opt-in workflows - class names for lazy loading
_OPT_IN_WORKFLOW_NAMES: dict[str, str] = {}

# Workflow registry - populated lazily on first access
WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]] = {}
_registry_initialized = False

# Maps base workflow names to their SDK equivalents.
# When a user requests a base name (e.g. "security-audit"), the resolver
# checks whether the SDK variant is available and routes to it automatically.
_SDK_WORKFLOW_MAP: dict[str, str] = {
    "code-review": "code-review-sdk",
    "security-audit": "security-audit-sdk",
    "perf-audit": "perf-audit-sdk",
    "release-prep": "release-prep-sdk",
    "test-audit": "test-audit-sdk",
    "bug-predict": "bug-predict-sdk",
    "refactor-plan": "refactor-plan-sdk",
    "test-gen": "test-gen-sdk",
    "doc-audit": "doc-audit-sdk",
    "doc-gen": "doc-gen-sdk",
    "simplify-code": "simplify-code-sdk",
    "dependency-check": "dependency-check-sdk",
    "research-synthesis": "research-synthesis-sdk",
}

# Reverse map: SDK name -> base name (for display purposes)
_SDK_REVERSE_MAP: dict[str, str] = {v: k for k, v in _SDK_WORKFLOW_MAP.items()}


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
            except (ImportError, AttributeError):
                # Skip workflows that fail to load
                pass

    # Add opt-in workflows based on config
    if config is not None:
        # HIPAA mode auto-enables healthcare workflows
        if config.is_hipaa_mode():
            for workflow_id, class_name in _OPT_IN_WORKFLOW_NAMES.items():
                try:
                    discovered[workflow_id] = _get_workflow_class(class_name)
                except (ImportError, AttributeError):
                    pass

        # Explicitly enabled workflows
        for workflow_name in config.enabled_workflows:
            if workflow_name in _OPT_IN_WORKFLOW_NAMES:
                try:
                    discovered[workflow_name] = _get_workflow_class(
                        _OPT_IN_WORKFLOW_NAMES[workflow_name],
                    )
                except (ImportError, AttributeError):
                    pass

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
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass

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
        except (ImportError, AttributeError):
            pass
    return result


# Note: Registry is initialized lazily on first access via _ensure_registry_initialized()
# Do NOT call discover_workflows() here - it defeats lazy loading


def _is_sdk_available() -> bool:
    """Check if claude_agent_sdk is installed and importable."""
    try:
        import claude_agent_sdk  # noqa: F401

        return True
    except ImportError:
        return False


def get_workflow(name: str) -> type[BaseWorkflow]:
    """Get a workflow class by name, preferring SDK variant when available.

    When the user requests a base workflow (e.g. ``"security-audit"``),
    this function automatically routes to the SDK variant
    (``"security-audit-sdk"``) if ``claude_agent_sdk`` is installed.
    If the user explicitly requests an ``-sdk`` suffix, it is used
    directly without re-mapping.

    Args:
        name: Workflow name (e.g., "research", "code-review", "doc-gen")

    Returns:
        Workflow class (SDK variant when available, API otherwise)

    Raises:
        KeyError: If workflow not found

    """
    _ensure_registry_initialized()

    # Auto-resolve to SDK variant when available
    sdk_variant = _SDK_WORKFLOW_MAP.get(name)
    if sdk_variant and sdk_variant in WORKFLOW_REGISTRY and _is_sdk_available():
        logger.debug("Routing %s → %s (Agent SDK available)", name, sdk_variant)
        return WORKFLOW_REGISTRY[sdk_variant]

    if name not in WORKFLOW_REGISTRY:
        available = ", ".join(sorted(WORKFLOW_REGISTRY.keys()))
        raise KeyError(f"Unknown workflow: {name}. Available: {available}")
    return WORKFLOW_REGISTRY[name]


def is_using_api_fallback(name: str) -> bool:
    """Check if a workflow name would use the API fallback (not SDK).

    Args:
        name: Workflow name the user requested.

    Returns:
        True if the name has an SDK variant but will use the API
        version because the SDK is not installed.

    """
    return name in _SDK_WORKFLOW_MAP and not _is_sdk_available()


def list_workflows(*, show_all: bool = False) -> list[dict]:
    """List available workflows with descriptions.

    By default, hides SDK duplicates and shows only the best variant
    per task (SDK when available, API otherwise). Pass ``show_all=True``
    to include every registered workflow.

    Args:
        show_all: If True, return every registered workflow including
            SDK duplicates.

    Returns:
        List of workflow info dicts

    """
    _ensure_registry_initialized()
    sdk_available = _is_sdk_available()

    workflows = []
    for name, cls in WORKFLOW_REGISTRY.items():
        # When hiding duplicates, only skip the explicit -sdk entries.
        # Users see base names (e.g. "security-audit") and the resolver
        # routes to the SDK variant transparently when available.
        if not show_all and name in _SDK_REVERSE_MAP:
            continue

        stages = getattr(cls, "stages", [])
        tier_map = getattr(cls, "tier_map", {})
        description = getattr(cls, "description", "No description")

        # Determine which engine is active for display
        if name in _SDK_WORKFLOW_MAP and sdk_available:
            engine = "sdk"
        elif name in _SDK_WORKFLOW_MAP:
            engine = "api"
        else:
            engine = "native"

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

    # Handle CLI commands
    if name in ("cmd_morning", "cmd_ship", "cmd_fix_all", "cmd_learn"):
        _load_cli_commands()
        return globals().get(name)

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
    # Code review crew integration (v3.1)
    "CodeReviewPipeline",
    "CodeReviewPipelineResult",
    "CodeReviewWorkflow",
    "CostReport",
    "DependencyCheckWorkflow",
    "DocAuditWorkflow",
    "DocumentGenerationWorkflow",
    "DocumentManagerWorkflow",
    # Documentation management (v3.5)
    "DocumentationOrchestrator",
    # Health check crew integration (v3.1)
    # Removed deprecated: "HealthCheckWorkflow" (use OrchestratedHealthCheckWorkflow)
    "HealthCheckReport",
    "ManageDocumentationCrew",
    "ManageDocumentationCrewResult",
    "ModelConfig",
    "ModelProvider",
    "ModelTier",
    "NextAction",
    "OrchestratorResult",
    "PRReviewResult",
    "PRReviewWorkflow",
    "PerformanceAuditWorkflow",
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
    "OrchestratedReleasePrepWorkflow",
    "HealthCheckReport",
    "ReleaseReadinessReport",
    # Additional workflows (added for completeness)
    # Test5Workflow removed - test artifact
    "TestMaintenanceWorkflow",
    "BatchProcessingWorkflow",
    "ProgressiveTestGenWorkflow",
    "AutonomousTestGenerator",
    # Multi-pass deep review (Agent SDK)
    "DeepReviewAgentSDKWorkflow",
    # Agent SDK adapters (v3.9.3)
    "SecurityAuditAgentSDKWorkflow",
    "PerfAuditAgentSDKWorkflow",
    "ReleasePrepAgentSDKWorkflow",
    "TestAuditAgentSDKWorkflow",
    "BugPredictAgentSDKWorkflow",
    "RefactorPlanAgentSDKWorkflow",
    "TestGenAgentSDKWorkflow",
    "DocAuditAgentSDKWorkflow",
    "DocGenAgentSDKWorkflow",
    "SimplifyCodeAgentSDKWorkflow",
    "DependencyCheckAgentSDKWorkflow",
    "ResearchSynthesisAgentSDKWorkflow",
    "HealthCheckAgentSDKWorkflow",
    # XML-enhanced prompting
    "XMLAgent",
    "XMLTask",
    "parse_xml_response",
    # Workflow migration system
    "resolve_workflow_migration",
    "MigrationConfig",
    "WORKFLOW_ALIASES",
    "show_migration_tip",
    "list_migrations",
]
