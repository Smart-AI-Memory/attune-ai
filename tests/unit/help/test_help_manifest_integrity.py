"""Regression guard for the ``.help/`` help system against two
classes of drift the content-hash staleness system cannot see.

The staleness system (``attune.help.staleness.compute_source_hash`` /
``check_staleness``) compares a SHA-256 of a feature's *current* source
files to the hash stored in template frontmatter. It catches edits to
files that still exist, but it is blind to:

1. **Manifest globs that reference deleted files.** ``features.yaml``
   can keep globbing ``src/.../deleted.py`` indefinitely — the hash of
   the surviving files simply changes once, and after a refresh the
   manifest looks "current" even though it points at a path that no
   longer exists. (Concretely: the ``fix-test`` feature globbed
   ``src/attune/workflows/test_lifecycle.py`` after that module was
   deleted in #887 — see PR #980 / commit b50af7e0f.)

2. **Templates that document deleted symbols.** All 11 ``fix-test``
   templates described ``TestLifecycleManager``, ``TestTask``,
   ``process_queue()`` and friends — symbols from the deleted module.
   The content hash is computed over *source*, not over the
   *templates*, so a template can name a class that no longer exists
   anywhere and staleness stays green.

These tests close that gap. ``test_manifest_file_references_resolve``
is the hard guard (every manifest ``files`` entry must resolve to real
files on disk). ``test_template_symbols_exist_in_source`` checks that
every backticked ``ClassName`` / ``function()`` a feature's templates
document still appears somewhere in that feature's resolved source.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from attune.help.manifest import Feature, load_manifest
from attune.help.staleness import _is_excluded, compute_source_hash

# tests/unit/help/ -> tests/unit -> tests -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
HELP_DIR = REPO_ROOT / ".help"
TEMPLATES_DIR = HELP_DIR / "templates"

_MANIFEST = load_manifest(HELP_DIR)

# Features that carry source globs (manual/single-sourced features are
# authored or projected and intentionally carry no globs to resolve).
_GENERATED_FEATURES = sorted(
    name for name, feat in _MANIFEST.features.items() if not feat.is_manual
)

# Features that additionally ship a templates/<feature>/ directory.
_FEATURES_WITH_TEMPLATES = sorted(
    name for name in _GENERATED_FEATURES if (TEMPLATES_DIR / name).is_dir()
)

# Backticked `ClassName` (CapWords) and `function()` references.
_CLASS_RE = re.compile(r"`([A-Z][A-Za-z0-9_]+)`")
_FUNC_RE = re.compile(r"`([a-z_][A-Za-z0-9_]*)\(\)`")

# Symbols a template may legitimately reference that do NOT live in the
# feature's own source globs: Python stdlib/typing names plus genuine
# cross-feature symbols (verified to exist elsewhere in the codebase).
_IGNORED_SYMBOLS: frozenset[str] = frozenset(
    {
        # stdlib / typing referenced in prose
        "Path",
        "datetime",
        # cross-feature: help feedback API (src/attune/help/feedback.py)
        "get_template_confidence",
        "record_template_feedback",
        # cross-feature: MCP tool / handler (src/attune/mcp/*)
        "doc_orchestrator",
        # cross-feature: project index (src/attune/project_index/*)
        "ProjectIndex",
    }
)

# Pre-existing dead-symbol drift that is OUT OF SCOPE for this guard's
# originating fix. Each entry is real drift to be cleaned up separately
# — the guard stays strict for everything else so NEW drift in any
# feature fails immediately. Remove entries here as the corresponding
# templates are fixed. (Currently empty: the one known case,
# `WorkflowExecutionError` in code-quality/error.md, was corrected to the
# real `SdkSubprocessError` in this change.)
_KNOWN_DEAD_SYMBOL_DRIFT: dict[str, frozenset[str]] = {}


def _is_glob(pattern: str) -> bool:
    """True if a manifest ``files`` entry is a glob, not a literal path."""
    return any(ch in pattern for ch in "*?[")


def _resolve_glob(pattern: str) -> list[Path]:
    """Resolve a glob pattern against the repo root.

    Mirrors ``compute_source_hash``'s normalization: a trailing ``**``
    is expanded to ``**/*`` so it matches files, not just directories.
    Cache/build directories are excluded the same way staleness does.
    """
    glob_pattern = pattern + "/*" if pattern.endswith("**") else pattern
    return [p for p in REPO_ROOT.glob(glob_pattern) if p.is_file() and not _is_excluded(p)]


def _resolved_source_text(feature: Feature) -> str:
    """Concatenated text of every source file a feature's globs match."""
    _, matched = compute_source_hash(feature, REPO_ROOT)
    parts: list[str] = []
    for rel in matched:
        try:
            parts.append((REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(parts)


def _documented_symbols(feature_name: str) -> set[str]:
    """Extract backticked ClassName / function() symbols from a feature's
    templates, dropping builtins and ALL-CAPS constants/env-vars."""
    import builtins

    builtin_names = set(dir(builtins))
    symbols: set[str] = set()
    for md in sorted((TEMPLATES_DIR / feature_name).glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        symbols |= set(_CLASS_RE.findall(text))
        symbols |= set(_FUNC_RE.findall(text))
    # `DEBUG`, `ERROR`, `PATH`, `ATTUNE_*` etc. are constants / env-vars /
    # log levels, not class references — drop anything fully uppercase.
    return {s for s in symbols if s not in builtin_names and not s.isupper()}


@pytest.mark.unit
class TestManifestFileReferences:
    """Hard guard: manifest globs/paths must resolve to real files."""

    def test_manifest_loads(self) -> None:
        """Sanity: the real manifest parses and has features."""
        assert _MANIFEST.features, "features.yaml has no features"

    @pytest.mark.parametrize("feature_name", _GENERATED_FEATURES)
    def test_manifest_file_references_resolve(self, feature_name: str) -> None:
        """Every ``files`` entry resolves: literal paths exist on disk,
        glob patterns match at least one file.

        This is the hard regression guard for manifest drift — it would
        have failed when ``fix-test`` still globbed the deleted
        ``test_lifecycle.py`` (PR #980).
        """
        feature = _MANIFEST.features[feature_name]
        missing_literals: list[str] = []
        empty_globs: list[str] = []

        for entry in feature.files:
            if _is_glob(entry):
                if not _resolve_glob(entry):
                    empty_globs.append(entry)
            elif not (REPO_ROOT / entry).exists():
                missing_literals.append(entry)

        problems: list[str] = []
        if missing_literals:
            problems.append(f"deleted/missing files: {missing_literals}")
        if empty_globs:
            problems.append(f"globs matching nothing: {empty_globs}")

        assert not problems, (
            f"Feature '{feature_name}' references source that no longer "
            f"exists ({'; '.join(problems)}). Update .help/features.yaml "
            f"to drop the dead reference."
        )


@pytest.mark.unit
class TestTemplateSymbolReferences:
    """Hard guard: documented symbols must still exist in source."""

    @pytest.mark.parametrize("feature_name", _FEATURES_WITH_TEMPLATES)
    def test_template_symbols_exist_in_source(self, feature_name: str) -> None:
        """Every backticked ``ClassName`` / ``function()`` a feature's
        templates document must appear somewhere in that feature's
        resolved source files.

        Catches the deleted-symbol class of drift (e.g. fix-test
        templates documenting ``TestLifecycleManager`` after the module
        was deleted) that content-hash staleness cannot see. A small
        ignore-list covers stdlib + genuine cross-feature symbols; one
        documented allow-list (``_KNOWN_DEAD_SYMBOL_DRIFT``) carries
        pre-existing drift out of scope for this guard's originating fix.
        """
        source_text = _resolved_source_text(_MANIFEST.features[feature_name])
        allowed = _IGNORED_SYMBOLS | _KNOWN_DEAD_SYMBOL_DRIFT.get(feature_name, frozenset())

        unresolved = sorted(
            sym
            for sym in _documented_symbols(feature_name)
            if sym not in allowed and not re.search(rf"\b{re.escape(sym)}\b", source_text)
        )

        assert not unresolved, (
            f"Feature '{feature_name}' templates document symbols not "
            f"found in its source files: {unresolved}. Either the source "
            f"was renamed/deleted (update the templates) or these are "
            f"cross-feature references (add to _IGNORED_SYMBOLS)."
        )
