"""attune-author: Documentation authoring and maintenance.

Generate, maintain, and validate help content for the attune
ecosystem. Works standalone or as the authoring layer between
attune-help (reader) and attune-ai (full dev workflows).
"""

__version__ = "0.1.0"

from attune_author.manifest import Feature, Manifest, load_manifest
from attune_author.staleness import StalenessReport, check_staleness, compute_source_hash

__all__ = [
    # Manifest
    "Feature",
    "Manifest",
    "load_manifest",
    # Staleness
    "StalenessReport",
    "check_staleness",
    "compute_source_hash",
]
