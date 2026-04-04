"""Template engine for the documentation help system.

Facade module — re-exports all public APIs from the
split modules so existing imports continue to work:

    from attune.help.engine import populate, TemplateContext
    from attune.help.engine import populate_progressive
    from attune.help.engine import get_workflow_help
"""

from __future__ import annotations

# Re-export from bootstrap.py (project scanning)
from attune.help.bootstrap import (
    ProposedFeature,
    proposals_to_manifest,
    scan_project,
)

# Re-export from feedback.py (ratings, search, workflows)
from attune.help.feedback import (
    get_precursor_warnings,
    get_template_confidence,
    get_usage_weights,
    get_workflow_help,
    list_tags,
    record_template_feedback,
    search_by_tag,
)

# Re-export from generator.py (template generation)
from attune.help.generator import (
    GeneratedTemplate,
    GenerationResult,
    generate_feature_templates,
)

# Re-export from maintenance.py (hook logic)
from attune.help.maintenance import (
    MaintenanceResult,
    format_status_report,
    get_changed_files,
    run_hook,
    run_maintenance,
)

# Re-export from manifest.py (feature manifest)
from attune.help.manifest import (
    Feature,
    FeatureManifest,
    load_manifest,
    match_files_to_features,
    resolve_topic,
    save_manifest,
)

# Re-export from progression.py (type-driven depth)
from attune.help.progression import (
    populate_progressive,
    reset_session,
)

# Re-export from staleness.py (hash comparison)
from attune.help.staleness import (
    FeatureStaleness,
    StalenessReport,
    check_staleness,
    compute_source_hash,
)

# Re-export from templates.py (core loading/population)
from attune.help.templates import (
    AudienceProfile,
    PopulatedTemplate,
    TemplateContext,
    populate,
)

__all__ = [
    # Dataclasses
    "AudienceProfile",
    "PopulatedTemplate",
    "TemplateContext",
    # Core
    "populate",
    "populate_progressive",
    "reset_session",
    # Queries
    "get_workflow_help",
    "get_precursor_warnings",
    "search_by_tag",
    "list_tags",
    # Feedback
    "record_template_feedback",
    "get_template_confidence",
    "get_usage_weights",
    # Manifest
    "Feature",
    "FeatureManifest",
    "load_manifest",
    "save_manifest",
    "match_files_to_features",
    "resolve_topic",
    # Staleness
    "FeatureStaleness",
    "StalenessReport",
    "check_staleness",
    "compute_source_hash",
    # Bootstrap
    "ProposedFeature",
    "scan_project",
    "proposals_to_manifest",
    # Generator
    "GeneratedTemplate",
    "GenerationResult",
    "generate_feature_templates",
    # Maintenance
    "MaintenanceResult",
    "run_maintenance",
    "run_hook",
    "get_changed_files",
    "format_status_report",
]
