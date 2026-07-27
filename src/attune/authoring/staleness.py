"""Staleness detection for help templates and project docs.

Two tracking formats are supported:

1. **Help templates** (``.help/templates/<feature>/concept.md``):
   Source hash stored in YAML frontmatter:
   ``source_hash: abc123``

2. **Project docs** (``docs/how-to/foo.md``, etc.):
   Source hash stored in an HTML comment footer (mkdocs-invisible):
   ``<!-- attune-generated: source_hash=abc123 feature=foo kind=how-to generated_at=2026-04-23 -->``

Both formats use the same SHA-256 of the feature's source files so
that staleness comparisons are consistent across tracking locations.

Extracted verbatim from attune-author's ``staleness.py`` during the
attune-author consolidation (``docs/specs/attune-author-consolidation/``).
The hashing here MUST stay byte-compatible with the hashes stored in
existing ``.help/`` files, so the algorithm (semantic hash via
:class:`~attune.authoring.symbols.SymbolExtractor`) is preserved exactly.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from attune.authoring.manifest import (
    Feature,
    FeatureManifest,
    is_safe_feature_name,
    load_manifest,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXCLUDED_DIRS = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    ".git",
}

# Regex to parse the HTML comment footer written by attune-author's doc generator:
# <!-- attune-generated: source_hash=abc123 feature=foo kind=how-to generated_at=2026-04-23 -->
_DOC_FOOTER_RE = re.compile(
    r"<!--\s*attune-generated:\s*(.*?)\s*-->",
    re.DOTALL,
)
_DOC_ATTR_RE = re.compile(r"(\w+)=(\S+)")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FeatureStaleness:
    """Staleness status for one feature's ``.help/`` templates.

    Attributes:
        feature: Feature name.
        is_stale: True if source hash differs from stored.
        current_hash: SHA-256 of current source files.
        stored_hash: Hash from concept.md frontmatter (or None if absent).
        matched_files: Source files that matched the globs.
    """

    feature: str
    is_stale: bool
    current_hash: str
    stored_hash: str | None
    matched_files: list[str] = field(default_factory=list)


@dataclass
class DocStaleness:
    """Staleness status for one project doc file in ``docs/``.

    Attributes:
        feature: Feature name that owns this doc.
        doc_path: Relative path to the doc file (e.g., ``docs/how-to/foo.md``).
        kind: Doc kind (``how-to``, ``architecture``, etc.).
        is_stale: True if source hash differs from stored, or file is absent.
        missing: True if the doc file doesn't exist yet.
        current_hash: SHA-256 of current source files.
        stored_hash: Hash from the HTML comment footer (or None if absent).
    """

    feature: str
    doc_path: str
    kind: str
    is_stale: bool
    missing: bool
    current_hash: str
    stored_hash: str | None = None


@dataclass
class StalenessReport:
    """Combined staleness report across help templates and project docs.

    Attributes:
        help_entries: Per-feature staleness for ``.help/`` templates.
        doc_entries: Per-doc staleness for ``docs/`` generated files.
        manual_features: Features skipped because the manifest marks
            them ``status: manual`` — their content is owned elsewhere
            (hand-written or projected), so hash tracking doesn't
            apply to them.
    """

    help_entries: list[FeatureStaleness] = field(default_factory=list)
    doc_entries: list[DocStaleness] = field(default_factory=list)
    manual_features: list[str] = field(default_factory=list)

    @property
    def stale_count(self) -> int:
        """Total stale items across both sections."""
        return sum(1 for e in self.help_entries if e.is_stale) + sum(
            1 for e in self.doc_entries if e.is_stale
        )

    @property
    def current_count(self) -> int:
        """Total up-to-date items across both sections."""
        return sum(1 for e in self.help_entries if not e.is_stale) + sum(
            1 for e in self.doc_entries if not e.is_stale
        )

    @property
    def stale_features(self) -> list[str]:
        """Names of features with stale help templates."""
        return [e.feature for e in self.help_entries if e.is_stale]

    @property
    def stale_docs(self) -> list[DocStaleness]:
        """Doc entries that are stale or missing."""
        return [e for e in self.doc_entries if e.is_stale]


# ---------------------------------------------------------------------------
# Source hashing
# ---------------------------------------------------------------------------


def _is_excluded(path: Path) -> bool:
    """Return True if any path component is an excluded directory."""
    return any(part in _EXCLUDED_DIRS for part in path.parts)


def _collect_matched_files(feature: Feature, root: Path) -> list[str]:
    """Resolve a feature's glob patterns to a sorted list of relative paths."""
    matched: list[str] = []
    for pattern in feature.files:
        glob_pattern = pattern
        if glob_pattern.endswith("**"):
            glob_pattern += "/*"
        for path in sorted(root.glob(glob_pattern)):
            if path.is_file() and not _is_excluded(path):
                rel = path.relative_to(root).as_posix()
                if rel not in matched:
                    matched.append(rel)
    return sorted(matched)


def compute_semantic_hash(
    feature: Feature,
    project_root: str | Path,
    extractor: object | None = None,
) -> tuple[str, list[str]]:
    """Compute a semantic SHA-256 hash of a feature's Python source files.

    For each matched ``.py`` file, hashes the normalized *signature* of
    every public symbol (function, class, method). Docstring edits,
    body-only changes, and formatter passes do not change the hash;
    parameter, return-type, decorator, or base-class changes do.

    Non-``.py`` files fall back to a byte-level SHA-256 per file.

    Args:
        feature: The feature to hash.
        project_root: Project root for resolving globs.
        extractor: Optional ``SymbolExtractor`` instance (for testing/reuse).

    Returns:
        Tuple of (hex digest, sorted list of matched relative paths).
    """
    from attune.authoring.symbols import SymbolExtractor

    if extractor is None:
        extractor = SymbolExtractor()

    root = Path(project_root)
    matched = _collect_matched_files(feature, root)

    hash_parts: list[str] = []
    for rel_path in matched:
        abs_path = root / rel_path
        try:
            if abs_path.suffix == ".py":
                try:
                    for record in extractor.extract(abs_path):
                        hash_parts.append(f"{rel_path}::{record.qualname}::{record.signature_hash}")
                except SyntaxError:
                    content = abs_path.read_bytes()
                    hash_parts.append(f"{rel_path}::{hashlib.sha256(content).hexdigest()}")
            else:
                content = abs_path.read_bytes()
                hash_parts.append(f"{rel_path}::{hashlib.sha256(content).hexdigest()}")
        except OSError as e:
            logger.warning("Cannot read %s: %s", rel_path, e)

    final = hashlib.sha256("\n".join(sorted(hash_parts)).encode("utf-8")).hexdigest()
    return final, matched


def compute_source_hash(
    feature: Feature,
    project_root: str | Path,
) -> tuple[str, list[str]]:
    """Compute SHA-256 hash of a feature's source files.

    For pure-Python features (all matched files are ``.py``), delegates to
    ``compute_semantic_hash`` so that docstring edits and formatter passes
    do not trigger spurious staleness. Mixed-content and non-Python features
    use legacy byte-concatenation.

    Args:
        feature: The feature to hash.
        project_root: Project root for resolving globs.

    Returns:
        Tuple of (hex digest, sorted list of matched relative paths).
    """
    root = Path(project_root)
    matched = _collect_matched_files(feature, root)

    if matched and all((root / p).suffix == ".py" for p in matched):
        return compute_semantic_hash(feature, root)

    hasher = hashlib.sha256()
    for rel_path in matched:
        try:
            content = (root / rel_path).read_bytes()
            hasher.update(content)
        except OSError as e:
            logger.warning("Cannot read %s: %s", rel_path, e)

    return hasher.hexdigest(), matched


# ---------------------------------------------------------------------------
# Help template staleness (YAML frontmatter format)
# ---------------------------------------------------------------------------


def _read_frontmatter_value(text: str, key: str) -> str | None:
    """Extract a value from YAML frontmatter.

    Args:
        text: Full file content.
        key: Frontmatter key (e.g. ``"source_hash"``).

    Returns:
        Stripped value string, or None if not found.
    """
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _read_stored_hash_from_template(
    feature_name: str,
    help_dir: Path,
) -> str | None:
    """Read source_hash from a feature's concept.md frontmatter.

    Args:
        feature_name: Feature name (directory under .help/templates/).
        help_dir: Path to the .help/ directory.

    Returns:
        The stored source_hash or None if absent.
    """
    if not is_safe_feature_name(feature_name):
        return None
    concept = help_dir / "templates" / feature_name / "concept.md"
    if not concept.exists():
        return None
    try:
        text = concept.read_text(encoding="utf-8")
    except OSError:
        return None
    return _read_frontmatter_value(text, "source_hash")


# ---------------------------------------------------------------------------
# Project doc staleness (HTML comment footer format)
# ---------------------------------------------------------------------------


def parse_doc_footer(text: str) -> dict[str, str]:
    """Parse an attune-generated HTML comment footer.

    The footer format is::

        <!-- attune-generated: source_hash=abc123 feature=foo
             kind=how-to generated_at=2026-04-23 -->

    The comment may appear anywhere in the file but is conventionally
    the last line.

    Args:
        text: Full file content.

    Returns:
        Dict of key→value pairs extracted from the comment.
        Empty dict if no attune-generated comment is found.
    """
    match = _DOC_FOOTER_RE.search(text)
    if not match:
        return {}
    return dict(_DOC_ATTR_RE.findall(match.group(1)))


def build_doc_footer(
    source_hash: str,
    feature: str,
    kind: str,
    generated_at: str,
) -> str:
    """Build an attune-generated HTML comment footer line.

    Args:
        source_hash: SHA-256 digest of the feature's source files.
        feature: Feature name.
        kind: Doc kind (e.g., ``"how-to"``).
        generated_at: ISO date string (e.g., ``"2026-04-23"``).

    Returns:
        Single-line HTML comment string (no trailing newline).
    """
    return (
        f"<!-- attune-generated: source_hash={source_hash} "
        f"feature={feature} kind={kind} generated_at={generated_at} -->"
    )


def _read_stored_hash_from_doc(
    doc_path: str,
    project_root: Path,
) -> str | None:
    """Read source_hash from an HTML comment footer in a doc file.

    Args:
        doc_path: Path relative to project_root.
        project_root: Absolute project root.

    Returns:
        source_hash value or None if absent.
    """
    full_path = project_root / doc_path
    if not full_path.exists():
        return None
    try:
        text = full_path.read_text(encoding="utf-8")
    except OSError:
        return None
    attrs = parse_doc_footer(text)
    return attrs.get("source_hash")


# ---------------------------------------------------------------------------
# Unified staleness check
# ---------------------------------------------------------------------------


def check_staleness(
    manifest: FeatureManifest,
    help_dir: str | Path,
    project_root: str | Path,
    features: list[str] | None = None,
) -> StalenessReport:
    """Check staleness across help templates and project docs.

    For each feature in the manifest:

    - **Help templates**: reads ``source_hash`` from
      ``.help/templates/<feature>/concept.md`` frontmatter.
    - **Project docs**: for each path in ``doc_paths`` /
      ``arch_path``, reads ``source_hash`` from the HTML comment
      footer at the bottom of the generated file. Reports a doc as
      stale if the hash mismatches or the file is absent.

    Args:
        manifest: The feature manifest.
        help_dir: Path to the .help/ directory.
        project_root: Project root for resolving source globs and doc paths.
        features: Optional list of feature names to check.
            Defaults to all features in the manifest.

    Returns:
        StalenessReport with separate help_entries and doc_entries.
    """
    help_path = Path(help_dir)
    root = Path(project_root)
    help_entries: list[FeatureStaleness] = []
    doc_entries: list[DocStaleness] = []
    manual_features: list[str] = []

    names = features if features is not None else list(manifest.features.keys())

    for name in names:
        feat = manifest.features.get(name)
        if not feat:
            logger.warning("Feature '%s' not in manifest", name)
            continue

        if feat.status == "manual":
            manual_features.append(name)
            continue

        current_hash, matched = compute_source_hash(feat, root)

        # --- Help template staleness ---
        stored_hash = _read_stored_hash_from_template(name, help_path)
        help_entries.append(
            FeatureStaleness(
                feature=name,
                is_stale=stored_hash != current_hash,
                current_hash=current_hash,
                stored_hash=stored_hash,
                matched_files=matched,
            )
        )

        # --- Project doc staleness ---
        doc_paths: list[tuple[str, str]] = []  # (path, kind)
        for p in feat.doc_paths:
            doc_paths.append((p, _infer_kind(feat, "doc_path")))
        if feat.arch_path:
            doc_paths.append((feat.arch_path, "architecture"))

        for doc_path, kind in doc_paths:
            full = root / doc_path
            missing = not full.exists()
            stored = _read_stored_hash_from_doc(doc_path, root)
            doc_entries.append(
                DocStaleness(
                    feature=name,
                    doc_path=doc_path,
                    kind=kind,
                    is_stale=missing or stored != current_hash,
                    missing=missing,
                    current_hash=current_hash,
                    stored_hash=stored,
                )
            )

    return StalenessReport(
        help_entries=help_entries,
        doc_entries=doc_entries,
        manual_features=manual_features,
    )


def check_workspace_staleness(
    workspace: str | Path,
    features: list[str] | None = None,
) -> StalenessReport:
    """Check staleness for a workspace using the conventional ``.help/`` layout.

    Convenience wrapper for callers that just have a project root and
    want the answer to "are any templates/docs out of date?" without
    knowing the manifest loader or where ``.help/`` lives. The workspace
    serves as both the project root (for resolving source globs) and
    the parent of ``.help/`` (for the manifest and template hashes).

    If ``<workspace>/.help/features.yaml`` is absent, returns an empty
    report rather than raising — a workspace without a manifest has no
    templates to be stale about.

    Args:
        workspace: Project root containing ``.help/`` (typically a git
            repo root).
        features: Optional list of feature names to check. Defaults to
            all features in the manifest.

    Returns:
        StalenessReport (empty if no manifest is present).
    """
    root = Path(workspace)
    help_dir = root / ".help"
    try:
        manifest = load_manifest(help_dir)
    except FileNotFoundError:
        return StalenessReport()
    return check_staleness(manifest, help_dir, root, features=features)


def _infer_kind(feat: Feature, path_field: str) -> str:
    """Infer the doc kind for a path field.

    Uses ``doc_kinds`` from the manifest when available; falls back to
    ``"how-to"`` for ``doc_path`` and ``"architecture"`` for
    ``arch_path``.

    Args:
        feat: The Feature entry.
        path_field: Which path attribute is being resolved
            (``"doc_path"`` or ``"arch_path"``).

    Returns:
        Kind string.
    """
    if path_field == "arch_path":
        return "architecture"
    # First non-architecture kind in doc_kinds, or "how-to"
    for kind in feat.doc_kinds:
        if kind != "architecture":
            return kind
    return "how-to"
