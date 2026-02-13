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
    from .code_review import CodeReviewWorkflow
    from .code_review_pipeline import CodeReviewPipeline, CodeReviewPipelineResult
    from .config import DEFAULT_MODELS, ModelConfig, WorkflowConfig
    from .dependency_check import DependencyCheckWorkflow
    from .document_gen import DocumentGenerationWorkflow
    from .document_manager import DocumentManagerWorkflow
    from .documentation_orchestrator import DocumentationOrchestrator, OrchestratorResult
    from .keyboard_shortcuts import KeyboardShortcutWorkflow
    from .manage_documentation import ManageDocumentationCrew, ManageDocumentationCrewResult
    from .orchestrated_health_check import HealthCheckReport, OrchestratedHealthCheckWorkflow
    from .orchestrated_release_prep import OrchestratedReleasePrepWorkflow, ReleaseReadinessReport
    from .perf_audit import PerformanceAuditWorkflow
    from .pr_review import PRReviewResult, PRReviewWorkflow
    from .refactor_plan import RefactorPlanWorkflow
    from .release_prep import ReleasePreparationWorkflow
    from .release_prep_crew import ReleasePreparationCrew, ReleasePreparationCrewResult
    from .research_synthesis import ResearchSynthesisWorkflow
    from .secure_release import SecureReleasePipeline, SecureReleaseResult
    from .security_audit import SecurityAuditWorkflow
    from .seo_optimization import SEOOptimizationWorkflow
    from .step_config import WorkflowStepConfig
    from .test_coverage_boost_crew import TestCoverageBoostCrew, TestCoverageBoostCrewResult
    from .test_gen import TestGenerationWorkflow
    from .test_gen_parallel import ParallelTestGenerationWorkflow
    from .xml_enhanced_crew import XMLAgent, XMLTask

# Only import base module eagerly (small, needed for type checks)
from .base import (
    PROVIDER_MODELS,
    BaseWorkflow,
    CostReport,
    ModelProvider,
    ModelTier,
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

# Lazy import mapping for workflow classes
_LAZY_WORKFLOW_IMPORTS: dict[str, tuple[str, str]] = {
    # Core workflows
    "BugPredictionWorkflow": (".bug_predict", "BugPredictionWorkflow"),
    "CodeReviewWorkflow": (".code_review", "CodeReviewWorkflow"),
    "CodeReviewPipeline": (".code_review_pipeline", "CodeReviewPipeline"),
    "CodeReviewPipelineResult": (".code_review_pipeline", "CodeReviewPipelineResult"),
    "DependencyCheckWorkflow": (".dependency_check", "DependencyCheckWorkflow"),
    "DocumentGenerationWorkflow": (".document_gen", "DocumentGenerationWorkflow"),
    "DocumentManagerWorkflow": (".document_manager", "DocumentManagerWorkflow"),
    "DocumentationOrchestrator": (".documentation_orchestrator", "DocumentationOrchestrator"),
    "OrchestratorResult": (".documentation_orchestrator", "OrchestratorResult"),
    "KeyboardShortcutWorkflow": (".keyboard_shortcuts", "KeyboardShortcutWorkflow"),
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
    "ReleasePreparationCrew": (".release_prep_crew", "ReleasePreparationCrew"),
    "ReleasePreparationCrewResult": (".release_prep_crew", "ReleasePreparationCrewResult"),
    "ResearchSynthesisWorkflow": (".research_synthesis", "ResearchSynthesisWorkflow"),
    "SecureReleasePipeline": (".secure_release", "SecureReleasePipeline"),
    "SecureReleaseResult": (".secure_release", "SecureReleaseResult"),
    "SecurityAuditWorkflow": (".security_audit", "SecurityAuditWorkflow"),
    "SEOOptimizationWorkflow": (".seo_optimization", "SEOOptimizationWorkflow"),
    "TestCoverageBoostCrew": (".test_coverage_boost_crew", "TestCoverageBoostCrew"),
    "TestCoverageBoostCrewResult": (".test_coverage_boost_crew", "TestCoverageBoostCrewResult"),
    "TestGenerationWorkflow": (".test_gen", "TestGenerationWorkflow"),
    "ParallelTestGenerationWorkflow": (".test_gen_parallel", "ParallelTestGenerationWorkflow"),
    # Additional workflows (restored to registry)
    "TestMaintenanceWorkflow": (".test_maintenance", "TestMaintenanceWorkflow"),
    "BatchProcessingWorkflow": (".batch_processing", "BatchProcessingWorkflow"),
    "ProgressiveTestGenWorkflow": (".progressive.test_gen", "ProgressiveTestGenWorkflow"),
    "AutonomousTestGenerator": (".autonomous_test_gen", "AutonomousTestGenerator"),
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
    """Import a workflow class lazily."""
    if name not in _LAZY_WORKFLOW_IMPORTS:
        raise AttributeError(f"module 'attune.workflows' has no attribute '{name}'")

    module_path, attr_name = _LAZY_WORKFLOW_IMPORTS[name]

    # Check cache first
    cache_key = f"{module_path}.{attr_name}"
    if cache_key in _loaded_workflow_modules:
        return _loaded_workflow_modules[cache_key]

    # Import the module and get the attribute
    import importlib

    module = importlib.import_module(module_path, package="attune.workflows")
    attr = getattr(module, attr_name)

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
    "doc-gen": "DocumentGenerationWorkflow",
    "seo-optimization": "SEOOptimizationWorkflow",
    # Analysis workflows
    "bug-predict": "BugPredictionWorkflow",
    "security-audit": "SecurityAuditWorkflow",
    "perf-audit": "PerformanceAuditWorkflow",
    # Generation workflows
    "test-gen": "TestGenerationWorkflow",
    "test-gen-parallel": "ParallelTestGenerationWorkflow",
    "refactor-plan": "RefactorPlanWorkflow",
    # Operational workflows
    "dependency-check": "DependencyCheckWorkflow",
    # release-prep-legacy removed - handled by migration system (use release-prep instead)
    # Composite security pipeline (v3.0)
    "secure-release": "SecureReleasePipeline",
    # Code review crew integration (v3.1)
    "pro-review": "CodeReviewPipeline",
    "pr-review": "PRReviewWorkflow",
    # Documentation management (v3.5)
    "doc-orchestrator": "DocumentationOrchestrator",
    # manage-docs removed - handled by migration system (was deprecated)
    # Keyboard Conductor (v3.6)
    "keyboard-shortcuts": "KeyboardShortcutWorkflow",
    # User-generated workflows (document-manager kept for backward compat, handled by migration)
    "document-manager": "DocumentManagerWorkflow",
    # Meta-orchestration workflows (v4.0.0 - CANONICAL)
    "orchestrated-health-check": "OrchestratedHealthCheckWorkflow",
    "orchestrated-release-prep": "OrchestratedReleasePrepWorkflow",
    # Release preparation (v5.2 — agent team replaces orchestrated version)
    "release-prep": "ReleasePrepTeamWorkflow",
    # Experimental aliases removed (use production versions instead)
    # Research and synthesis workflows
    "research-synthesis": "ResearchSynthesisWorkflow",
    # Test management workflows
    "test-coverage-boost": "TestCoverageBoostCrew",
    "test-maintenance": "TestMaintenanceWorkflow",
    "autonomous-test-gen": "AutonomousTestGenerator",
    # Batch and progressive workflows
    "batch-processing": "BatchProcessingWorkflow",
    "progressive-test-gen": "ProgressiveTestGenWorkflow",
}

# Opt-in workflows - class names for lazy loading
_OPT_IN_WORKFLOW_NAMES: dict[str, str] = {}

# Workflow registry - populated lazily on first access
WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]] = {}
_registry_initialized = False


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
                        _OPT_IN_WORKFLOW_NAMES[workflow_name]
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
            except Exception:
                pass
    except Exception:
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


def get_workflow(name: str) -> type[BaseWorkflow]:
    """Get a workflow class by name.

    Args:
        name: Workflow name (e.g., "research", "code-review", "doc-gen")

    Returns:
        Workflow class

    Raises:
        KeyError: If workflow not found

    """
    _ensure_registry_initialized()
    if name not in WORKFLOW_REGISTRY:
        available = ", ".join(WORKFLOW_REGISTRY.keys())
        raise KeyError(f"Unknown workflow: {name}. Available: {available}")
    return WORKFLOW_REGISTRY[name]


def list_workflows() -> list[dict]:
    """List all available workflows with descriptions.

    Returns:
        List of workflow info dicts

    """
    _ensure_registry_initialized()
    workflows = []
    for name, cls in WORKFLOW_REGISTRY.items():
        # Handle both BaseWorkflow subclasses and composite pipelines
        stages = getattr(cls, "stages", [])
        tier_map = getattr(cls, "tier_map", {})
        description = getattr(cls, "description", "No description")

        workflows.append(
            {
                "name": name,
                "class": cls.__name__,
                "description": description,
                "stages": stages,
                "tier_map": {k: v.value for k, v in tier_map.items()} if tier_map else {},
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
    "DocumentGenerationWorkflow",
    "DocumentManagerWorkflow",
    # Documentation management (v3.5)
    "DocumentationOrchestrator",
    # Health check crew integration (v3.1)
    # Removed deprecated: "HealthCheckWorkflow" (use OrchestratedHealthCheckWorkflow)
    "HealthCheckReport",
    # Keyboard Conductor (v3.6)
    "KeyboardShortcutWorkflow",
    "ManageDocumentationCrew",
    "ManageDocumentationCrewResult",
    "ModelConfig",
    "ModelProvider",
    "ModelTier",
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
    "SEOOptimizationWorkflow",
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
    # Stats for dashboard
    "get_workflow_stats",
    "list_workflows",
    "refresh_workflow_registry",
    "steps_from_tier_map",
    "validate_step_config",
    # CrewAI-based multi-agent workflows (v4.0.0)
    # Removed deprecated: "HealthCheckCrew" (use OrchestratedHealthCheckWorkflow)
    # Removed deprecated: "HealthCheckCrewResult"
    "ReleasePreparationCrew",
    "ReleasePreparationCrewResult",
    "TestCoverageBoostCrew",
    "TestCoverageBoostCrewResult",
    # Removed deprecated: "TestCoverageBoostWorkflow" (use TestCoverageBoostCrew)
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
