"""Help system — template engine and audience transformers.

Provides runtime access to generated documentation templates
with context-aware population and audience-adaptive rendering.

Re-exports core authoring types from attune-author for
backward compatibility.
"""

from attune_author.generator import (  # noqa: F401
    GeneratedTemplate,
    GenerationResult,
    generate_feature_templates,
)
from attune_author.manifest import (  # noqa: F401
    Feature,
    FeatureManifest,
    load_manifest,
    match_files_to_features,
    resolve_topic,
    save_manifest,
)
from attune_author.staleness import (  # noqa: F401
    StalenessReport,
    check_staleness,
    compute_source_hash,
)
