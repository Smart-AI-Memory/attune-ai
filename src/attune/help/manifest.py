"""Feature manifest parser and query engine.

Loads .help/features.yaml, validates structure, and matches
changed files against feature glob patterns. The manifest is
the bridge between code changes and help updates.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MANIFEST_VERSION = 1
_MANIFEST_FILENAME = "features.yaml"


@dataclass
class Feature:
    """A project feature mapped to source files.

    Attributes:
        name: Feature identifier (e.g., "authentication").
        description: One-line summary for topic resolution.
        files: Glob patterns matching source files.
        tags: Keywords for cross-referencing and discovery.
        status: ``"generated"`` (default) means the LLM generator
            owns this feature's templates and staleness/maintenance
            may regenerate them. ``"manual"`` means the templates are
            single-sourced (authored or projected) and must NOT be
            regenerated — the entry stays in the manifest purely so
            ``resolve_topic`` can still route queries to it via
            name/description/tags. See
            ``docs/specs/help-docs-single-source/``.
    """

    name: str
    description: str
    files: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    status: str = "generated"

    @property
    def is_manual(self) -> bool:
        """True when this feature is single-sourced (never regenerated)."""
        return self.status == "manual"


@dataclass
class FeatureManifest:
    """Parsed features.yaml manifest.

    Attributes:
        version: Schema version (currently 1).
        features: Map of feature name to Feature object.
        path: Filesystem path the manifest was loaded from.
    """

    version: int
    features: dict[str, Feature]
    path: Path | None = None


def load_manifest(help_dir: str | Path) -> FeatureManifest:
    """Load and validate features.yaml from a .help/ directory.

    Args:
        help_dir: Path to the .help/ directory.

    Returns:
        Parsed FeatureManifest.

    Raises:
        FileNotFoundError: If features.yaml doesn't exist.
        ValueError: If the manifest is malformed.
    """
    import yaml  # lazy — yaml is optional

    manifest_path = Path(help_dir) / _MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"No {_MANIFEST_FILENAME} in {help_dir}")

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        # The docstring promises ValueError for a malformed manifest,
        # and callers degrade on ValueError (preamble.py). yaml raises
        # its own class, which defeated them (library-review F2).
        raise ValueError(f"Invalid manifest YAML in {manifest_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid manifest: expected mapping, got {type(raw).__name__}")

    version = raw.get("version", 1)
    if version != _MANIFEST_VERSION:
        logger.warning(
            "Manifest version %s differs from expected %s",
            version,
            _MANIFEST_VERSION,
        )

    raw_features = raw.get("features", {})
    if not isinstance(raw_features, dict):
        raise ValueError("'features' must be a mapping")

    features: dict[str, Feature] = {}
    for name, spec in raw_features.items():
        if not isinstance(spec, dict):
            raise ValueError(f"Feature '{name}' must be a mapping")
        features[name] = Feature(
            name=name,
            description=spec.get("description", ""),
            files=spec.get("files", []),
            tags=spec.get("tags", []),
            status=spec.get("status", "generated"),
        )

    return FeatureManifest(
        version=version,
        features=features,
        path=manifest_path,
    )


def save_manifest(manifest: FeatureManifest, help_dir: str | Path) -> Path:
    """Write a FeatureManifest to features.yaml.

    Args:
        manifest: The manifest to save.
        help_dir: Path to the .help/ directory.

    Returns:
        Path to the written file.
    """
    import yaml

    help_path = Path(help_dir)
    help_path.mkdir(parents=True, exist_ok=True)
    out = help_path / _MANIFEST_FILENAME

    data: dict[str, Any] = {
        "version": manifest.version,
        "features": {},
    }
    for name, feat in sorted(manifest.features.items()):
        entry: dict[str, Any] = {"description": feat.description}
        if feat.files:
            entry["files"] = feat.files
        if feat.tags:
            entry["tags"] = feat.tags
        if feat.status != "generated":
            entry["status"] = feat.status
        data["features"][name] = entry

    out.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return out


def _glob_match(filepath: str, pattern: str) -> bool:
    """Match a filepath against a glob pattern.

    Converts glob syntax to regex:
    - ``**`` matches any path segments (including ``/``)
    - ``*``  matches anything except ``/``
    - ``?``  matches a single non-``/`` character

    Args:
        filepath: Relative file path (forward slashes).
        pattern: Glob pattern (e.g. ``src/auth/**/*.py``).

    Returns:
        True if the filepath matches the pattern.
    """
    parts = pattern.split("**")
    regex_parts: list[str] = []
    for part in parts:
        escaped = ""
        for ch in part:
            if ch == "*":
                escaped += "[^/]*"
            elif ch == "?":
                escaped += "[^/]"
            else:
                escaped += re.escape(ch)
        regex_parts.append(escaped)
    regex = ".*".join(regex_parts)
    return re.fullmatch(regex, filepath) is not None


def match_files_to_features(
    changed_files: list[str],
    manifest: FeatureManifest,
) -> dict[str, list[str]]:
    """Match changed files against feature glob patterns.

    Args:
        changed_files: Relative paths of changed files.
        manifest: The feature manifest.

    Returns:
        Dict mapping feature name to the changed files that
        matched its globs.
    """
    matches: dict[str, list[str]] = {}
    for name, feat in manifest.features.items():
        matched = []
        for filepath in changed_files:
            for pattern in feat.files:
                if _glob_match(filepath, pattern):
                    matched.append(filepath)
                    break
        if matched:
            matches[name] = matched
    return matches


def resolve_topic(
    query: str,
    manifest: FeatureManifest,
) -> str | None:
    """Resolve a user query to a feature name.

    Tries exact match first, then fuzzy match against
    descriptions and tags. Returns None if ambiguous or
    no match.

    Step 4 (tag match) normalizes spaces and underscores to
    hyphens on BOTH sides so a query like ``"race condition"``
    can match a slug-style tag ``"race-condition"``. The other
    steps compare literal substrings.

    Args:
        query: User's topic query string.
        manifest: The feature manifest.

    Returns:
        Feature name or None.
    """
    q = query.lower().strip()

    # 1. Exact match on feature name
    if q in manifest.features:
        return q

    # 2. Substring match on feature name
    name_hits = [n for n in manifest.features if q in n]
    if len(name_hits) == 1:
        return name_hits[0]

    # 3. Match against descriptions
    desc_hits = [n for n, f in manifest.features.items() if q in f.description.lower()]
    if len(desc_hits) == 1:
        return desc_hits[0]

    # 4. Match against tags (slug-normalized: space/underscore -> hyphen)
    q_slug = q.replace(" ", "-").replace("_", "-")
    tag_hits = [
        n
        for n, f in manifest.features.items()
        if q_slug in [t.lower().replace(" ", "-").replace("_", "-") for t in f.tags]
    ]
    if len(tag_hits) == 1:
        return tag_hits[0]

    return None
