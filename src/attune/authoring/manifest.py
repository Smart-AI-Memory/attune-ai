"""Feature manifest parser with project-doc field support.

Loads .help/features.yaml, validates structure, and exposes the
Feature model extended with doc_kinds/doc_paths/arch_path fields
for project-level documentation tracking. Also parses the
top-level ``_docs:`` bucket for hand-written narrative docs that
don't belong to any single feature (FAQ, glossary, installation,
etc.).

Backward compatibility: legacy ``doc_path`` (scalar) is accepted
on load and migrated into ``doc_paths`` (list). Saved manifests
always emit ``doc_paths``.

Extracted verbatim from attune-author's ``manifest.py`` during the
attune-author consolidation (``docs/specs/attune-author-consolidation/``).
Self-contained: stdlib (``fnmatch``/``re``) plus a lazy ``yaml`` import.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MANIFEST_VERSION = 1
_MANIFEST_FILENAME = "features.yaml"

#: Substrings that turn a feature name into a path-traversal vector
#: when the name is used as a directory component.
_UNSAFE_NAME_TOKENS = ("/", "\\", "..", "\x00")


def is_safe_feature_name(name: object) -> bool:
    """Check whether a feature name is safe to use as a path component.

    Feature names appear as directory components under
    ``.help/templates/<name>/``. A name containing path separators,
    parent-directory tokens, or null bytes can escape that directory.

    Args:
        name: Candidate feature name. Non-string values are rejected.

    Returns:
        True if ``name`` is a non-empty string with no traversal
        characters.
    """
    if not isinstance(name, str) or not name:
        return False
    return not any(token in name for token in _UNSAFE_NAME_TOKENS)


@dataclass
class Feature:
    """A project feature mapped to source files and optional doc outputs.

    Attributes:
        name: Feature identifier (e.g., "authentication").
        description: One-line summary for topic resolution.
        files: Glob patterns matching source files.
        tags: Keywords for cross-referencing and discovery.
        doc_kinds: Doc kinds to generate (e.g., ["how-to", "architecture"]).
        doc_paths: Output paths under docs/ for non-architecture kinds.
            A feature may have multiple docs (e.g., memory has 4 how-to
            files); the first entry is the primary doc. Prefer this over
            the scalar ``doc_path`` going forward.
        doc_path: Deprecated scalar form of ``doc_paths``. On load, a
            legacy ``doc_path`` scalar is migrated into ``doc_paths``;
            this attribute remains populated as ``doc_paths[0]`` for
            readers that have not yet moved to the list form.
        arch_path: Output path for the architecture doc under docs/.
        doc_nav_section: mkdocs.yml nav section to insert under.
        cli_command: Consumer-CLI subcommand that exposes this
            feature (e.g., ``"ops"`` for ``attune ops``). Optional;
            absence skips the CLI-help block during ground-truth
            context injection. See polish-fact-check Phase 2.
        status: Maintenance mode for the feature's help content.
            ``"auto"`` (default) means the generator owns the
            templates: staleness tracking and LLM regeneration
            apply. ``"manual"`` means the content is owned
            elsewhere (hand-written or projected from a
            single-source master); staleness checks skip the
            feature and ``generate`` refuses to run for it
            without ``overwrite=True``. The entry stays in the
            manifest so topic resolution still routes to it.
    """

    name: str
    description: str
    files: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    doc_kinds: list[str] = field(default_factory=list)
    doc_paths: list[str] = field(default_factory=list)
    doc_path: str | None = None
    arch_path: str | None = None
    doc_nav_section: str | None = None
    cli_command: str | None = None
    status: str = "auto"

    def __post_init__(self) -> None:
        """Keep ``doc_paths`` and ``doc_path`` in sync.

        Callers may set either form; whichever is populated drives the
        other so downstream code can read either without a surprise
        None/empty mismatch.
        """
        if self.doc_paths and not self.doc_path:
            self.doc_path = self.doc_paths[0]
        elif self.doc_path and not self.doc_paths:
            self.doc_paths = [self.doc_path]


@dataclass
class FeatureManifest:
    """Parsed features.yaml manifest.

    Attributes:
        version: Schema version (currently 1).
        features: Map of feature name to Feature object.
        docs: Top-level narrative docs not owned by any single feature
            (FAQ, glossary, installation, etc.). These are tracked for
            discovery and mkdocs nav but are hand-written and never
            regenerated from source.
        path: Filesystem path the manifest was loaded from.
    """

    version: int
    features: dict[str, Feature]
    docs: list[str] = field(default_factory=list)
    path: Path | None = None


#: Public alias kept for backward compatibility.
Manifest = FeatureManifest


def load_manifest(help_dir: str | Path) -> FeatureManifest:
    """Load and validate features.yaml from a .help/ directory.

    Parses all standard fields (name, description, files, tags) plus
    the new project-doc fields (doc_kinds, doc_path, arch_path,
    doc_nav_section). Unknown fields are silently ignored so older
    manifests remain loadable.

    Args:
        help_dir: Path to the .help/ directory.

    Returns:
        Parsed FeatureManifest.

    Raises:
        FileNotFoundError: If features.yaml doesn't exist.
        ValueError: If the manifest is malformed.
    """
    import yaml  # optional dep; must be available (python-frontmatter installs it)

    manifest_path = Path(help_dir) / _MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"No {_MANIFEST_FILENAME} in {help_dir}")

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        # The docstring promises ValueError for a malformed manifest, and
        # ops/help_data.py degrades on (OSError, ValueError). yaml raises
        # its own class, which is not a ValueError subclass and defeated
        # that caller (library-review F2 twin).
        raise ValueError(f"Invalid manifest YAML in {manifest_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(
            f"Invalid manifest at {manifest_path}: expected mapping, " f"got {type(raw).__name__}"
        )

    version = raw.get("version", 1)
    if version != _MANIFEST_VERSION:
        logger.warning(
            "Manifest version %s differs from expected %s",
            version,
            _MANIFEST_VERSION,
        )

    raw_features = raw.get("features", {})
    if not isinstance(raw_features, dict):
        raise ValueError(f"Invalid manifest at {manifest_path}: 'features' must be a mapping")

    features: dict[str, Feature] = {}
    for name, spec in raw_features.items():
        if not is_safe_feature_name(name):
            raise ValueError(f"Invalid feature name: {name!r}")
        if not isinstance(spec, dict):
            raise ValueError(
                f"Invalid manifest at {manifest_path}: " f"feature '{name}' must be a mapping"
            )

        # Coalesce doc_path (legacy scalar) and doc_paths (list).
        # doc_paths wins when both are present.
        doc_paths_raw = spec.get("doc_paths")
        doc_path_raw = spec.get("doc_path")
        if isinstance(doc_paths_raw, list):
            doc_paths = [str(p) for p in doc_paths_raw]
        elif doc_path_raw:
            doc_paths = [str(doc_path_raw)]
        else:
            doc_paths = []

        features[name] = Feature(
            name=name,
            description=spec.get("description", ""),
            files=spec.get("files", []),
            tags=spec.get("tags", []),
            doc_kinds=spec.get("doc_kinds", []),
            doc_paths=doc_paths,
            doc_path=doc_paths[0] if doc_paths else None,
            arch_path=spec.get("arch_path"),
            doc_nav_section=spec.get("doc_nav_section"),
            cli_command=spec.get("cli_command"),
            status=str(spec.get("status", "auto")),
        )

    # Top-level _docs bucket (hand-written narrative docs).
    raw_docs = raw.get("_docs", [])
    if not isinstance(raw_docs, list):
        raise ValueError(f"Invalid manifest at {manifest_path}: '_docs' must be a list")
    docs = [str(p) for p in raw_docs]

    return FeatureManifest(
        version=version,
        features=features,
        docs=docs,
        path=manifest_path,
    )


def save_manifest(manifest: FeatureManifest, help_dir: str | Path) -> Path:
    """Write a FeatureManifest to features.yaml.

    Omits optional fields that are empty/None to keep YAML clean.

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
    }
    if manifest.docs:
        data["_docs"] = manifest.docs
    data["features"] = {}
    for name, feat in sorted(manifest.features.items()):
        entry: dict[str, Any] = {"description": feat.description}
        if feat.files:
            entry["files"] = feat.files
        if feat.tags:
            entry["tags"] = feat.tags
        if feat.doc_kinds:
            entry["doc_kinds"] = feat.doc_kinds
        if feat.doc_paths:
            entry["doc_paths"] = feat.doc_paths
        if feat.arch_path:
            entry["arch_path"] = feat.arch_path
        if feat.doc_nav_section:
            entry["doc_nav_section"] = feat.doc_nav_section
        if feat.cli_command:
            entry["cli_command"] = feat.cli_command
        if feat.status != "auto":
            entry["status"] = feat.status
        data["features"][name] = entry

    out.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return out


def match_files_to_features(
    changed_files: list[str],
    manifest: FeatureManifest,
) -> dict[str, list[str]]:
    """Match changed files against feature glob patterns.

    Args:
        changed_files: Relative paths of changed files.
        manifest: The feature manifest.

    Returns:
        Dict mapping feature name to the changed files that matched
        its globs.
    """
    matches: dict[str, list[str]] = {}
    for name, feat in manifest.features.items():
        matched = []
        for filepath in changed_files:
            for pattern in feat.files:
                flat = pattern.replace("**", "*")
                if fnmatch.fnmatch(filepath, flat):
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

    Tries exact match first, then fuzzy match against descriptions
    and tags. Returns None if ambiguous or no match.

    Args:
        query: User's topic query string.
        manifest: The feature manifest.

    Returns:
        Feature name or None.
    """
    q = query.lower().strip()

    if q in manifest.features:
        return q

    name_hits = [n for n in manifest.features if q in n]
    if len(name_hits) == 1:
        return name_hits[0]

    desc_hits = [n for n, f in manifest.features.items() if q in f.description.lower()]
    if len(desc_hits) == 1:
        return desc_hits[0]

    tag_hits = [n for n, f in manifest.features.items() if q in [t.lower() for t in f.tags]]
    if len(tag_hits) == 1:
        return tag_hits[0]

    return None


# ---------------------------------------------------------------------------
# Helpers for slugging feature names to tags in the slug-normalized resolver
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Convert text to a lowercase slug for tag comparison.

    Args:
        text: Input string.

    Returns:
        Lowercase hyphenated slug.
    """
    return _SLUG_RE.sub("-", text.lower()).strip("-")
