"""Staleness detection for feature help templates.

Computes SHA-256 hashes of a feature's source files and
compares against the hash stored in template frontmatter.
Used by the maintenance hook and manual refresh commands.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from attune.help.manifest import Feature, FeatureManifest

logger = logging.getLogger(__name__)


@dataclass
class FeatureStaleness:
    """Staleness status for one feature.

    Attributes:
        feature: The feature name.
        is_stale: True if source hash differs from stored.
        current_hash: SHA-256 of current source files.
        stored_hash: Hash from template frontmatter (or None).
        matched_files: Source files that matched the globs.
    """

    feature: str
    is_stale: bool
    current_hash: str
    stored_hash: str | None
    matched_files: list[str] = field(default_factory=list)


@dataclass
class StalenessReport:
    """Staleness report across all features.

    Attributes:
        entries: Per-feature staleness results.
        stale_count: Number of stale features.
        current_count: Number of up-to-date features.
    """

    entries: list[FeatureStaleness]

    @property
    def stale_count(self) -> int:
        """Count of stale features."""
        return sum(1 for e in self.entries if e.is_stale)

    @property
    def current_count(self) -> int:
        """Count of up-to-date features."""
        return sum(1 for e in self.entries if not e.is_stale)

    @property
    def stale_features(self) -> list[str]:
        """Names of stale features."""
        return [e.feature for e in self.entries if e.is_stale]


def compute_source_hash(
    feature: Feature,
    project_root: str | Path,
) -> tuple[str, list[str]]:
    """Compute SHA-256 hash of a feature's source files.

    Reads all files matching the feature's glob patterns,
    concatenates their contents in sorted order, and returns
    the SHA-256 hex digest.

    Args:
        feature: The feature to hash.
        project_root: Project root for resolving globs.

    Returns:
        Tuple of (hex digest, list of matched file paths).
    """
    root = Path(project_root)
    matched: list[str] = []

    for pattern in feature.files:
        # Ensure ** patterns match files, not just directories
        glob_pattern = pattern
        if glob_pattern.endswith("**"):
            glob_pattern += "/*"
        for path in sorted(root.glob(glob_pattern)):
            if path.is_file():
                rel = str(path.relative_to(root))
                if rel not in matched:
                    matched.append(rel)

    hasher = hashlib.sha256()
    for rel_path in matched:
        try:
            content = (root / rel_path).read_bytes()
            hasher.update(content)
        except OSError as e:
            logger.warning("Cannot read %s: %s", rel_path, e)

    return hasher.hexdigest(), matched


def _read_stored_hash(
    feature_name: str,
    help_dir: Path,
) -> str | None:
    """Read source_hash from a feature's concept.md frontmatter.

    Args:
        feature_name: Feature name (directory name in .help/).
        help_dir: Path to the .help/ directory.

    Returns:
        The stored source_hash or None if not found.
    """
    concept = help_dir / "templates" / feature_name / "concept.md"
    if not concept.exists():
        return None

    try:
        text = concept.read_text(encoding="utf-8")
    except OSError:
        return None

    # Parse YAML frontmatter between --- delimiters
    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    frontmatter = text[3:end]
    for line in frontmatter.splitlines():
        line = line.strip()
        if line.startswith("source_hash:"):
            return line.split(":", 1)[1].strip()

    return None


def check_staleness(
    manifest: FeatureManifest,
    help_dir: str | Path,
    project_root: str | Path,
    features: list[str] | None = None,
) -> StalenessReport:
    """Check which features have stale help templates.

    Args:
        manifest: The feature manifest.
        help_dir: Path to the .help/ directory.
        project_root: Project root for resolving globs.
        features: Optional list of feature names to check.
            If None, checks all features.

    Returns:
        StalenessReport with per-feature results.
    """
    help_path = Path(help_dir)
    entries: list[FeatureStaleness] = []

    names = features if features else list(manifest.features.keys())

    for name in names:
        feat = manifest.features.get(name)
        if not feat:
            logger.warning("Feature '%s' not in manifest", name)
            continue

        current_hash, matched = compute_source_hash(feat, project_root)
        stored_hash = _read_stored_hash(name, help_path)

        entries.append(
            FeatureStaleness(
                feature=name,
                is_stale=stored_hash != current_hash,
                current_hash=current_hash,
                stored_hash=stored_hash,
                matched_files=matched,
            )
        )

    return StalenessReport(entries=entries)
