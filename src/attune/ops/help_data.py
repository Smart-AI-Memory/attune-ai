"""Help-corpus reads for the ops dashboard's /help page.

Wraps :mod:`attune_rag` (corpus walker + keyword retrieval) and
the on-disk ``.help/templates/`` layout into a small set of
read-only functions the dashboard route + JSON API consume.

See ``docs/specs/ops-help-page/`` for the spec. The data shape
mirrors the mockup HTML the spec ships with.

Zero new deps. Falls back gracefully when ``attune_rag`` isn't
installed (returns empty results rather than 500).
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from attune.ops.config import Config

logger = logging.getLogger(__name__)

# Authority cache TTL for the in-process source-hash drift check.
# Short enough that regen jobs that change staleness state surface
# promptly; long enough that a page-refresh burst doesn't re-hash
# every feature's source per request.
_STALENESS_CACHE_TTL_SECONDS = 5.0

# Process-lifetime cache for the drift check. Keyed on the
# (project_root, help_dir) pair so multiple dashboards in one
# process don't cross-contaminate.
_staleness_cache: dict[tuple[str, str], tuple[float, frozenset[str]]] = {}

# The 11 template kinds attune-author produces per feature. A
# feature with all 11 is "complete"; fewer = an incomplete set.
EXPECTED_KINDS: tuple[str, ...] = (
    "comparison",
    "concept",
    "error",
    "faq",
    "note",
    "quickstart",
    "reference",
    "task",
    "tip",
    "troubleshooting",
    "warning",
)

# Kinds grouped by user intent — drives the "Browse by what you
# need" cards on the home page.
INTENT_GROUPS: dict[str, tuple[str, ...]] = {
    "do": ("task", "quickstart"),
    "solve": ("troubleshooting", "error", "faq"),
    "understand": ("concept",),
    "lookup": ("reference",),
}

# Frontmatter regex — quick parse without pulling in PyYAML.
_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemplateRecord:
    """One template file."""

    feature: str
    kind: str
    path: str
    title: str
    body: str
    generated_at: str | None
    source_hash: str | None
    is_stale: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FeatureSummary:
    """One feature — name + which kinds exist."""

    name: str
    kinds: tuple[str, ...]
    missing_kinds: tuple[str, ...]
    stale_count: int
    has_any_stale: bool

    @property
    def is_complete(self) -> bool:
        return len(self.missing_kinds) == 0

    @property
    def completeness_pct(self) -> int:
        if not EXPECTED_KINDS:
            return 100
        return round(100 * len(self.kinds) / len(EXPECTED_KINDS))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kinds"] = list(self.kinds)
        d["missing_kinds"] = list(self.missing_kinds)
        d["is_complete"] = self.is_complete
        d["completeness_pct"] = self.completeness_pct
        return d


@dataclass(frozen=True)
class SearchHit:
    """One ranked hit from a search query."""

    feature: str
    kind: str
    title: str
    snippet: str
    score: float
    match_reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GapsReport:
    """Coverage-gap signals — incomplete sets + stale templates."""

    incomplete: tuple[FeatureSummary, ...] = field(default_factory=tuple)
    stale: tuple[TemplateRecord, ...] = field(default_factory=tuple)
    total_features: int = 0
    total_templates: int = 0
    complete_features: int = 0

    @property
    def completeness_pct(self) -> int:
        if self.total_features == 0:
            return 0
        return round(100 * self.complete_features / self.total_features)

    @property
    def fresh_pct(self) -> int:
        if self.total_templates == 0:
            return 0
        stale_n = len(self.stale)
        return round(100 * (self.total_templates - stale_n) / self.total_templates)

    def to_dict(self) -> dict:
        return {
            "incomplete": [f.to_dict() for f in self.incomplete],
            "stale": [t.to_dict() for t in self.stale],
            "total_features": self.total_features,
            "total_templates": self.total_templates,
            "complete_features": self.complete_features,
            "completeness_pct": self.completeness_pct,
            "fresh_pct": self.fresh_pct,
        }


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def corpus_root(config: Config) -> Path:
    """Return the ``.help/templates/`` directory for this project.

    The dashboard reads templates from the project root's ``.help``
    directory — same source attune-author writes to.
    """
    return config.project_root / ".help" / "templates"


def list_features(config: Config) -> list[FeatureSummary]:
    """All features in the corpus, alphabetical.

    Staleness comes from an in-process source-hash drift check
    (the authoritative signal). Falls back to per-template
    age-based check when the manifest can't be loaded.
    """
    root = corpus_root(config)
    if not root.exists():
        return []
    stale = _stale_features(config.project_root, config.project_root / ".help")
    out: list[FeatureSummary] = []
    for feat_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        out.append(_summarize_feature(feat_dir, stale_features=stale))
    return out


def get_template(config: Config, feature: str, kind: str) -> TemplateRecord | None:
    """Load one template by feature + kind. None if missing.

    Staleness uses the in-process source-hash drift check; falls
    back to age-based when the manifest can't be loaded.
    """
    if not _safe_slug(feature) or not _safe_slug(kind):
        return None
    path = corpus_root(config) / feature / f"{kind}.md"
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("help_data: cannot read %s: %s", path, exc)
        return None
    stale = _stale_features(config.project_root, config.project_root / ".help")
    return _parse_template(feature, kind, path, raw, stale_features=stale)


def search(config: Config, query: str, *, limit: int = 20) -> list[SearchHit]:
    """Run a keyword search against the corpus.

    Returns ranked hits. Empty list when attune-rag isn't installed
    or the corpus is empty — both are graceful degradations.

    Builds inline summaries (first non-empty paragraph after the
    frontmatter) for each template and passes them to the retriever
    via ``extra_summaries``. attune-rag's KeywordRetriever weights
    summary hits ~1.5x content hits, so without a summary it
    returns zero results regardless of content matches — see the
    existing CLAUDE.md lesson "Metadata can reach a retriever with
    zero signal if the sidecar schema doesn't match the loader's
    expected shape."
    """
    if not query or not query.strip():
        return []
    root = corpus_root(config)
    if not root.exists():
        return []
    try:
        from attune_rag import DirectoryCorpus, KeywordRetriever
    except ImportError:
        logger.info("help_data: attune-rag not installed, search disabled")
        return []

    try:
        summaries = _build_inline_summaries(root)
        corpus = DirectoryCorpus(root, extra_summaries=summaries)
        retriever = KeywordRetriever()
        hits = list(retriever.retrieve(query, corpus, k=limit))
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: search must not 500 the dashboard. Log and
        # return empty.
        logger.warning("help_data: search failed: %s", exc)
        return []

    out: list[SearchHit] = []
    for hit in hits:
        path = Path(hit.entry.path)
        feature, kind = _feature_kind_from_path(path)
        if feature is None or kind is None:
            continue
        title = _title_from_content(hit.entry.content) or f"{feature} / {kind}"
        snippet = _snippet(hit.entry.content, query, max_len=240)
        out.append(
            SearchHit(
                feature=feature,
                kind=kind,
                title=title,
                snippet=snippet,
                score=float(hit.score),
                match_reason=str(hit.match_reason or ""),
            )
        )
    return out


def _build_inline_summaries(root: Path) -> dict[str, str]:
    """Walk the corpus and extract a one-paragraph summary per template.

    Used by :func:`search` to give attune-rag's retriever something
    to score against. The summary is the first non-empty paragraph
    after the frontmatter, truncated to ~400 chars.

    Returns a dict keyed by path-relative-to-root (the shape
    DirectoryCorpus expects from ``extra_summaries``).
    """
    out: dict[str, str] = {}
    for md_file in root.rglob("*.md"):
        try:
            rel = str(md_file.relative_to(root))
        except ValueError:
            continue
        try:
            raw = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _FRONTMATTER_RE.match(raw)
        body = m.group("body") if m else raw
        summary = _first_paragraph(body, max_chars=400)
        if summary:
            out[rel] = summary
    return out


def _first_paragraph(body: str, *, max_chars: int = 400) -> str:
    """First non-empty, non-heading paragraph of a markdown body."""
    paragraph_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            if paragraph_lines:
                break
            continue
        if stripped.startswith("#") or stripped.startswith("```"):
            if paragraph_lines:
                break
            continue
        paragraph_lines.append(stripped)
    text = " ".join(paragraph_lines)
    if len(text) > max_chars:
        text = text[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return text


#: TTL for the full-corpus template-record walk. Matches the
#: staleness cache: the dashboard hits coverage_gaps +
#: recently_regenerated back-to-back per page load, and each walk is
#: one file read per template (the N+1 the 11.5.0 self-review
#: flagged).
_RECORDS_CACHE_TTL_SECONDS = 5.0
_records_cache: dict[str, tuple[float, list[TemplateRecord]]] = {}


def _all_template_records(
    config: Config, features: list[FeatureSummary] | None = None
) -> list[TemplateRecord]:
    """Every parseable template record — ONE corpus walk, TTL-cached."""
    key = str(corpus_root(config))
    now = time.monotonic()
    cached = _records_cache.get(key)
    if cached is not None and (now - cached[0]) < _RECORDS_CACHE_TTL_SECONDS:
        return cached[1]
    feats = features if features is not None else list_features(config)
    records: list[TemplateRecord] = []
    for feat in feats:
        for kind in feat.kinds:
            rec = get_template(config, feat.name, kind)
            if rec is not None:
                records.append(rec)
    _records_cache[key] = (now, records)
    return records


def _clear_records_cache() -> None:
    """Test hook — flushes the per-process record-walk cache."""
    _records_cache.clear()


def coverage_gaps(config: Config) -> GapsReport:
    """Compute incomplete sets + stale templates across the corpus."""
    features = list_features(config)
    if not features:
        return GapsReport()

    incomplete = tuple(f for f in features if not f.is_complete)
    complete_features = sum(1 for f in features if f.is_complete)
    total_features = len(features)
    total_templates = sum(len(f.kinds) for f in features)

    stale = [r for r in _all_template_records(config, features) if r.is_stale]
    # Sort stale by oldest first (most-stale at top).
    stale.sort(key=lambda r: r.generated_at or "")

    return GapsReport(
        incomplete=incomplete,
        stale=tuple(stale),
        total_features=total_features,
        total_templates=total_templates,
        complete_features=complete_features,
    )


def recently_regenerated(
    config: Config,
    *,
    limit: int = 5,
    features: list[FeatureSummary] | None = None,
) -> list[TemplateRecord]:
    """N most-recently-generated templates across the corpus.

    Pass ``features`` when the caller already holds
    :func:`list_features` output to avoid recomputing it.
    """
    records = [r for r in _all_template_records(config, features) if r.generated_at is not None]
    records.sort(key=lambda r: r.generated_at or "", reverse=True)
    return records[:limit]


def featured_topics(
    config: Config, features: list[FeatureSummary] | None = None
) -> list[FeatureSummary]:
    """Curated list of high-leverage features for the home page.

    v1: hard-coded shortlist of features the dashboard wants to
    nudge users toward. Falls back to "first N features" if any of
    the curated picks aren't in the corpus. Pass ``features`` when
    the caller already holds :func:`list_features` output.
    """
    curated = (
        "security-audit",
        "smart-test",
        "bug-predict",
        "deep-review",
        "release-prep",
    )
    if features is None:
        features = list_features(config)
    by_name = {f.name: f for f in features}
    out = [by_name[name] for name in curated if name in by_name]
    if len(out) < 3:
        # Fallback — first few features alphabetically.
        out = list(by_name.values())[:5]
    return out


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def _safe_slug(s: str) -> bool:
    """True if ``s`` matches the feature/kind slug shape.

    Defense in depth against path-traversal in /api/help/template/...
    """
    return bool(s) and bool(_SLUG_RE.match(s)) and ".." not in s


def _summarize_feature(
    feat_dir: Path, *, stale_features: frozenset[str] | None = None
) -> FeatureSummary:
    """Scan a feature directory for its kinds + freshness.

    ``stale_features`` is the authoritative set from
    :func:`_stale_features` (source-hash drift). When ``None`` the
    function falls back to per-template age-based staleness — used
    in tests and when the manifest can't be loaded.
    """
    name = feat_dir.name
    kinds: list[str] = []
    if stale_features is None:
        # Fallback: age-based per-template check.
        stale_count = 0
        for kind in EXPECTED_KINDS:
            path = feat_dir / f"{kind}.md"
            if not path.is_file():
                continue
            kinds.append(kind)
            if _is_template_stale(path):
                stale_count += 1
    else:
        # Authority path: if the feature is in the source-hash
        # drift set, every kind it has is treated as stale (the
        # source files drifted; all derived templates need
        # regen). If not in the set, nothing is stale.
        for kind in EXPECTED_KINDS:
            path = feat_dir / f"{kind}.md"
            if path.is_file():
                kinds.append(kind)
        stale_count = len(kinds) if name in stale_features else 0
    missing = tuple(k for k in EXPECTED_KINDS if k not in kinds)
    return FeatureSummary(
        name=name,
        kinds=tuple(kinds),
        missing_kinds=missing,
        stale_count=stale_count,
        has_any_stale=stale_count > 0,
    )


def _is_template_stale(path: Path, *, stale_features: frozenset[str] | None = None) -> bool:
    """Per-template freshness check (hash-based only).

    A template is stale iff its parent feature is in
    ``stale_features`` — the source-hash drift set. When
    ``stale_features`` is ``None`` (drift undeterminable), the
    dashboard cannot determine drift, so it reports
    ``False`` (assume fresh). The previous age-based fallback was
    dropped: a template's age in days is not a proxy for whether
    its content matches the current source.
    """
    if stale_features is None:
        return False
    # path is .../<feature>/<kind>.md
    feature = path.parent.name
    return feature in stale_features


# ---------------------------------------------------------------------------
# Source-hash drift — the real staleness signal (in-process)
# ---------------------------------------------------------------------------


def _stale_features(project_root: Path, help_dir: Path) -> frozenset[str] | None:
    """Return features whose ``.help/`` templates have drifted from source.

    Computes source-hash drift **in-process** via
    :func:`attune.authoring.staleness.check_staleness` — the same
    semantic-hash algorithm the retired ``attune-author status`` CLI
    used, now absorbed into :mod:`attune.authoring`. Result cached
    for :data:`_STALENESS_CACHE_TTL_SECONDS` per
    ``(project_root, help_dir)`` key.

    Manual / single-sourced features with no ``files:`` globs are
    reported as *untracked (N/A)*, not stale: hash-drift is
    undefined for a feature with no source to hash, so evaluating
    them would flag every projector-owned feature as permanently
    stale (leftover stored hash ≠ the empty-input hash — see
    ``docs/specs/attune-author-consolidation/decisions.md`` D9).
    They are excluded from the drift check and from the result.

    Returns:
        - ``frozenset[str]``: feature names with source-hash drift
          in their ``.help/`` templates (empty set = all in sync,
          which now includes the all-manual repo).
        - ``None`` when the manifest can't be loaded (no ``.help/``
          manifest, parse error) or the drift check raises —
          callers fall back to age-based staleness, the same signal
          the old code returned when the CLI was unavailable.
    """
    key = (str(project_root), str(help_dir))
    now = time.monotonic()
    cached = _staleness_cache.get(key)
    if cached is not None and (now - cached[0]) < _STALENESS_CACHE_TTL_SECONDS:
        return cached[1]

    try:
        from attune.authoring.manifest import load_manifest
        from attune.authoring.staleness import check_staleness
    except ImportError as exc:
        logger.warning("help_data: attune.authoring unavailable: %s", exc)
        return None

    try:
        manifest = load_manifest(help_dir)
    except (OSError, ValueError) as exc:
        logger.info(
            "help_data: cannot load manifest from %s: %s; using age fallback",
            help_dir,
            exc,
        )
        return None

    # Manual/single-sourced features (no ``files:`` globs) have no
    # source to hash — report as untracked (N/A), not stale (D9).
    tracked = [name for name, feat in manifest.features.items() if feat.files]
    if not tracked:
        stale = frozenset()
        _staleness_cache[key] = (now, stale)
        return stale

    try:
        report = check_staleness(manifest, help_dir, project_root, features=tracked)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: staleness is advisory. Any failure (unreadable
        # source, malformed glob) falls back to age-based staleness
        # rather than 500-ing the dashboard.
        logger.warning("help_data: check_staleness failed: %s; using age fallback", exc)
        return None

    stale = frozenset(report.stale_features)
    _staleness_cache[key] = (now, stale)
    return stale


def _clear_staleness_cache() -> None:
    """Test hook — flushes the per-process staleness cache."""
    _staleness_cache.clear()


def _parse_template(
    feature: str,
    kind: str,
    path: Path,
    raw: str,
    *,
    stale_features: frozenset[str] | None = None,
) -> TemplateRecord:
    """Split frontmatter + body, build a TemplateRecord.

    Staleness is hash-based only: a template is stale iff its
    parent feature is in ``stale_features`` (the source-hash drift
    set). When ``stale_features`` is ``None`` (drift undeterminable),
    the dashboard cannot determine drift and reports
    ``is_stale=False`` — see ``_is_template_stale``.
    """
    m = _FRONTMATTER_RE.match(raw)
    if m:
        fm = m.group("fm")
        body = m.group("body")
    else:
        fm = ""
        body = raw
    generated_at = _extract_frontmatter_field(fm, "generated_at")
    source_hash = _extract_frontmatter_field(fm, "source_hash")
    title = _title_from_content(body) or f"{feature} / {kind}"

    is_stale = stale_features is not None and feature in stale_features

    return TemplateRecord(
        feature=feature,
        kind=kind,
        path=str(path.relative_to(path.parents[2])) if len(path.parents) >= 3 else str(path),
        title=title,
        body=body,
        generated_at=generated_at,
        source_hash=source_hash,
        is_stale=is_stale,
    )


def _extract_frontmatter_field(fm: str, key: str) -> str | None:
    """Pull a top-level key from YAML-shaped frontmatter without PyYAML."""
    pattern = rf"^{re.escape(key)}\s*:\s*(.+?)\s*$"
    for line in fm.splitlines():
        m = re.match(pattern, line)
        if m:
            value = m.group(1).strip()
            # Strip surrounding quotes if present.
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            return value
    return None


def _title_from_content(content: str) -> str | None:
    """First ``# H1`` line, stripped of the leading hash."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def _feature_kind_from_path(path: Path) -> tuple[str | None, str | None]:
    """Split ``security-audit/task.md`` into ``("security-audit", "task")``."""
    parts = path.parts
    if len(parts) < 2:
        return (None, None)
    feature = parts[-2]
    kind = path.stem
    if not _safe_slug(feature) or not _safe_slug(kind):
        return (None, None)
    return (feature, kind)


def _snippet(content: str, query: str, *, max_len: int = 240) -> str:
    """Build a snippet around the first query-term hit in content."""
    if not content:
        return ""
    terms = [t for t in query.lower().split() if len(t) >= 3]
    lower = content.lower()
    hit_pos = -1
    for term in terms:
        pos = lower.find(term)
        if pos >= 0:
            hit_pos = pos
            break
    if hit_pos < 0:
        return content[:max_len].strip().replace("\n", " ")
    start = max(0, hit_pos - 60)
    end = min(len(content), hit_pos + max_len - 60)
    fragment = content[start:end].replace("\n", " ").strip()
    if start > 0:
        fragment = "…" + fragment
    if end < len(content):
        fragment = fragment + "…"
    return fragment


def _format_kinds(kinds: Iterable[str]) -> str:
    """Comma-joined kinds — used in API responses."""
    return ", ".join(kinds)
