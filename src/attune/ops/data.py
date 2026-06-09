"""Read-only accessors for data the dashboard surfaces.

All accessors fail soft: if the data file is missing or malformed, they return
empty results instead of raising. This keeps the UI useful on a fresh install.
"""

from __future__ import annotations

import contextlib
import heapq
import json
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from attune.ops.config import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelemetrySummary:
    total_requests: int
    total_cost: float
    total_savings: float
    by_workflow: list[tuple[str, int, float]]
    by_day: list[tuple[str, int, float]]
    last_event_at: str | None


@dataclass(frozen=True)
class WorkflowEntry:
    name: str
    description: str
    stages: int
    tier_map: dict[str, str]


@dataclass(frozen=True)
class PathArgSpec:
    """How a workflow accepts a scope path on the CLI.

    The CLI's ``attune workflow run --path`` always sends ``path=<value>``
    into ``workflow.execute(**input_data)``. Most workflows consume it
    directly. A few use a different kwarg name (``project_root``,
    ``src_path``, ``cwd``). The ops runner uses this registry to rewrite
    the kwarg name before subprocess spawn so the scope picker works
    uniformly across all workflows.

    Attributes:
        kwarg: The kwarg name the workflow's ``execute()`` actually
            consumes. ``"path"`` for the majority; one of
            ``"project_root"``, ``"src_path"``, ``"cwd"`` for the
            aliased minority.
        required: True if the workflow errors when the kwarg is missing.
            The ops runner should not submit a scope-less run for these
            (``test-audit`` is the current example).
    """

    kwarg: str
    required: bool = False


# Per-workflow path-arg registry. Source: docs/specs/ops-runner-tier2/audit.md.
#
# Three categories surfaced by the audit:
#   A — 12 workflows consume ``kwargs.get("path", "")`` directly.
#   B —  2 workflows (release-prep, secure-release) declare ``path`` as a
#         signature kwarg.
#   C —  5 workflows use a different kwarg name.
#
# A + B share ``kwarg="path"`` in this registry; C carries the actual name.
# The drift-guard test in tests/unit/ops/test_path_support_registry.py
# asserts (a) every registered workflow has an entry, and (b) each entry's
# kwarg name actually appears in the workflow's execute() source.
PATH_ARG_REGISTRY: dict[str, PathArgSpec] = {
    # Category A — kwargs.get("path", "")
    "bug-predict": PathArgSpec(kwarg="path"),
    "code-review": PathArgSpec(kwarg="path"),
    "deep-review": PathArgSpec(kwarg="path"),
    "dependency-check": PathArgSpec(kwarg="path"),
    "discovery-sweep": PathArgSpec(kwarg="path"),
    "doc-audit": PathArgSpec(kwarg="path"),
    "doc-gen": PathArgSpec(kwarg="path"),
    "perf-audit": PathArgSpec(kwarg="path"),
    "refactor-plan": PathArgSpec(kwarg="path"),
    "research-synthesis": PathArgSpec(kwarg="path"),
    "security-audit": PathArgSpec(kwarg="path"),
    "simplify-code": PathArgSpec(kwarg="path"),
    "test-gen": PathArgSpec(kwarg="path"),
    # Category B — direct signature kwarg ``path: str = "."``
    "release-prep": PathArgSpec(kwarg="path"),
    "secure-release": PathArgSpec(kwarg="path"),
    # Category C — aliased to a different kwarg name
    "doc-orchestrator": PathArgSpec(kwarg="path"),
    # health-check + orchestrated-health-check migrated to `path` in
    # workflow-path-arg-unification PR-1 (2026-05-13).
    "health-check": PathArgSpec(kwarg="path"),
    "orchestrated-health-check": PathArgSpec(kwarg="path"),
    # rag-code-gen migrated to `path` in workflow-path-arg-unification
    # PR-4 (2026-05-13); `cwd` and `path` are semantically identical
    # for this workflow per Phase 0.2 confirmation in #296.
    "rag-code-gen": PathArgSpec(kwarg="path"),
    # test-audit migrated to `path` in workflow-path-arg-unification
    # PR-3 (2026-05-13); required=True preserved (workflow errors
    # when missing).
    "test-audit": PathArgSpec(kwarg="path", required=True),
}


@dataclass(frozen=True)
class Feature:
    """One feature from ``.help/features.yaml`` for the scope picker.

    ``path`` is a single representative repo-relative path derived from
    the feature's ``files`` list: prefer a directory glob (entry ending
    in ``/**``, stripped of the suffix); otherwise the first non-glob
    entry. ``None`` when the feature has no addressable scope (empty
    ``files`` or only mid-name globs like ``code_review_*.py``).
    """

    name: str
    description: str
    path: str | None
    tags: tuple[str, ...] = ()


# Per-yaml-file mtime cache: {abs_path: (mtime_ns, features_in_yaml_order)}.
# Stores features in YAML insertion order; ``list_features()`` returns a
# sorted copy, ``most_recent_feature()`` reads the cache directly.
_FEATURES_CACHE: dict[str, tuple[int, list[Feature]]] = {}


def _derive_feature_path(files: list[str]) -> str | None:
    """Pick a representative scope path from a feature's files list.

    Preference order:
      1. First entry ending in ``/**`` (a directory scope) — strip the suffix.
      2. First entry with no glob metacharacters (a single file).
      3. ``None`` otherwise.
    """
    for entry in files:
        if entry.endswith("/**"):
            return entry[: -len("/**")]
    for entry in files:
        if "*" not in entry and "?" not in entry and "[" not in entry:
            return entry
    return None


def _features_in_yaml_order(project_root: Path | str) -> list[Feature]:
    """Parse ``features.yaml`` and return features in YAML insertion order.

    Internal helper. Callers wanting alphabetical display use
    :func:`list_features`; callers wanting the most-recently-added feature
    use :func:`most_recent_feature`. Both share this cached parse.

    Returns ``[]`` on missing file, unreadable file, or malformed YAML.
    Cached by mtime so repeated calls within one server run skip the parse.
    """
    root = Path(project_root).expanduser().resolve()
    yaml_path = root / ".help" / "features.yaml"
    if not yaml_path.is_file():
        return []

    try:
        mtime_ns = yaml_path.stat().st_mtime_ns
    except OSError:
        return []

    cache_key = str(yaml_path)
    cached = _FEATURES_CACHE.get(cache_key)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]

    try:
        import yaml as _yaml
    except ImportError:
        return []
    try:
        text = yaml_path.read_text(encoding="utf-8")
        raw = _yaml.safe_load(text)
    except (OSError, _yaml.YAMLError):
        return []

    if not isinstance(raw, dict):
        return []
    raw_features = raw.get("features")
    if not isinstance(raw_features, dict):
        return []

    out: list[Feature] = []
    for name, spec in raw_features.items():
        if not isinstance(spec, dict):
            continue
        files_raw = spec.get("files") or []
        files = (
            [str(f) for f in files_raw if isinstance(f, str)] if isinstance(files_raw, list) else []
        )
        tags_raw = spec.get("tags") or []
        tags = (
            tuple(str(t) for t in tags_raw if isinstance(t, str))
            if isinstance(tags_raw, list)
            else ()
        )
        out.append(
            Feature(
                name=str(name),
                description=str(spec.get("description") or ""),
                path=_derive_feature_path(files),
                tags=tags,
            )
        )
    _FEATURES_CACHE[cache_key] = (mtime_ns, out)
    return out


def list_features(project_root: Path | str) -> list[Feature]:
    """Return features parsed from ``<project_root>/.help/features.yaml``.

    Returns ``[]`` on missing file, unreadable file, or malformed YAML.
    Result is sorted alphabetically by feature name (findability in the
    picker dropdown). Backed by a mtime-keyed cache shared with
    :func:`most_recent_feature`.
    """
    return sorted(_features_in_yaml_order(project_root), key=lambda f: f.name)


def first_feature(project_root: Path | str) -> Feature | None:
    """Return the alphabetically-first feature with a renderable scope.

    Used by the ops dashboard scope picker as the primary first-load
    fallback when ``localStorage`` has no saved scope. Predictable +
    stable: the same feature is returned regardless of YAML ordering
    changes, so the picker doesn't surprise the user by jumping around
    when features are reordered.

    Only features with a non-``None`` ``path`` are considered, since
    those are the only ones rendered as picker options. When no
    path-bearing feature exists, the dashboard falls through to the
    "All code" option (see :data:`ALL_CODE_PATH`). Returns ``None``
    if ``features.yaml`` is missing, empty, or has no path-bearing
    entries.
    """
    for feature in list_features(project_root):
        if feature.path:
            return feature
    return None


def workflow_default_scope(workflow_name: str, project_root: Path | str) -> str:
    """Return the default scope for one workflow on first paint.

    Auto-derives by exact-name match against ``features.yaml``: if a
    feature with the same name as the workflow exists and has a
    renderable ``path``, that path is the default. Otherwise returns
    ``""`` (project-wide), which is the safe fallback the picker
    template already renders as the first option.

    Used by the dashboard route to render a per-row
    ``data-scope-default`` attribute on each workflow row, so the JS
    can restore a workflow-appropriate scope on first load instead of
    defaulting every row to the alphabetically-first feature.

    Example match table for the attune-ai ``features.yaml``:

    - ``security-audit`` workflow → ``src/attune/security`` (matches
      the ``security-audit`` feature's ``files: [..., src/attune/
      security/**]`` entry).
    - ``release-prep`` workflow → ``""`` (no matching feature, so
      project-wide is the default — explicitly chosen over surfacing
      an irrelevant scope).
    - ``bug-predict`` workflow → first non-glob ``files`` entry of
      the ``bug-predict`` feature, if any.

    Returns ``""`` when ``features.yaml`` is missing, when there's no
    matching feature, or when the matching feature has ``path=None``
    (e.g. its ``files`` are all mid-name globs).
    """
    for feature in list_features(project_root):
        if feature.name == workflow_name and feature.path:
            return feature.path
    return ""


def derive_project_name(project_root: Path | str) -> str:
    """Return a human-readable project name for the dashboard header.

    Reads the ``[project]`` table's ``name`` field from
    ``<project_root>/pyproject.toml`` when present; falls back to the
    directory basename otherwise. The fallback gives sensible output
    for projects without a ``pyproject.toml`` (Node.js, plain
    directories) while the pyproject path means worktree-launched
    dashboards display the package name (e.g. ``attune-ai``) instead
    of the worktree slug (e.g. ``reverent-brown-937823``).

    Defensive failure modes — none of these surface to the user; the
    dashboard just renders the basename:

    - Missing ``pyproject.toml`` → basename.
    - Unreadable file (perm error, OSError) → basename.
    - Malformed TOML → basename.
    - ``[project]`` table missing or ``name`` field missing → basename.
    - Empty ``name`` value → basename (don't render blank header).

    No-pyproject fallback chain isn't extended to ancestor
    directories: the dashboard's ``--project-root`` is supposed to
    BE the project root. Walking up could surface a parent
    workspace's name (e.g. ``Users``) which is worse than the
    worktree slug.
    """
    root = Path(project_root).expanduser().resolve()
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            return root.name
        # Python 3.11+ ships tomllib; fall back to the stdlib parser.
        try:
            import tomllib
        except ImportError:  # pragma: no cover — Python < 3.11
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                return root.name
        try:
            parsed = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return root.name
        project_table = parsed.get("project")
        if isinstance(project_table, dict):
            name = project_table.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return root.name


@dataclass(frozen=True)
class Session:
    """One Claude Code session — what surfaces on the dashboard's /sessions page.

    Built from a JSONL file in
    ``~/.claude/projects/<encoded-project-root>/<session-id>.jsonl``.
    The JSONL is an event log of queue operations + attachments; we
    care about events with a ``content`` field (the user's prompts)
    for heuristic starter-prompt generation.

    ``source`` is ``"heuristic"`` for S2 (this slice's only path).
    S3 will introduce ``"haiku"`` and ``"cached"`` for LLM-summarized
    prompts and cache hits respectively. Surfacing the source in the
    JSON contract from day 1 means the UI can show a badge later
    without a model-field migration.
    """

    id: str
    started_at: str
    last_activity: str
    duration_seconds: float
    message_count: int
    starter_prompt: str
    source: str = "heuristic"


def _encoded_project_path(project_root: Path | str) -> str:
    """Claude Code encodes its project subdir as ``path.replace('/', '-')``.

    Resolves to absolute first so a relative ``project_root`` arg
    still matches the on-disk encoding. Returns the encoded
    basename only — the caller prepends ``~/.claude/projects/``.

    Three characters are mapped to ``-`` so the resulting string is
    safe to concatenate as a single path segment on every platform:

    - ``/`` — POSIX path separator (matches Claude Code's documented
      encoding).
    - ``\\`` — Windows path separator. ``Path.resolve()`` produces
      backslashes on Windows.
    - ``:`` — Windows drive-letter delimiter (``D:``). Without
      this, the encoded string contains a literal ``D:`` prefix that
      pathlib treats as a drive specifier on subsequent
      ``Path / encoded`` concatenation, silently discarding the
      ``~/.claude/projects/`` prefix and rooting the result at the
      bogus drive.

    POSIX paths never contain backslash or colon, so the two
    Windows-only replacements are no-ops there.
    """
    resolved = str(Path(project_root).expanduser().resolve())
    return resolved.replace("/", "-").replace("\\", "-").replace(":", "-")


def claude_sessions_dir(project_root: Path | str) -> Path:
    """Return the canonical directory Claude Code stores sessions for this project in.

    Doesn't check existence — callers should treat a non-existent
    dir as "no sessions yet" rather than an error condition (the
    dir is created on first session, which the user may not have
    started in this project).

    Note: in a worktree-heavy dev setup, Claude Code creates a separate
    encoded-key directory per worktree. Use
    :func:`enumerate_project_encoded_keys` to get the full set of dirs
    that belong to this logical project. This function returns only
    the canonical (project-root) key.
    """
    return Path.home() / ".claude" / "projects" / _encoded_project_path(project_root)


def enumerate_project_encoded_keys(project_root: Path | str) -> list[Path]:
    """Return all ``~/.claude/projects/`` dirs belonging to this logical project.

    Claude Code encodes each project-root path as a single directory
    name under ``~/.claude/projects/`` by replacing path separators
    (and Windows drive-letter colons) with ``-``. In a worktree-heavy
    development setup this produces one encoded-key dir per worktree,
    not one per logical project. The empirical scan on attune-ai
    2026-05-15 found 1 canonical key with 44 sessions plus 47
    worktree-encoded keys with 57 sessions — i.e. canonical-only
    lookup misses the majority of recent activity.

    Resolution rule (matches ``docs/specs/ops-sessions-page/decisions.md``
    Decision 1):

    1. Compute encoded prefix from the resolved project root.
    2. Scan ``~/.claude/projects/`` and accept a child dir iff its
       name equals the encoded prefix exactly, OR starts with
       ``<encoded>-`` (the trailing ``-`` separator guards against
       sibling-project false matches like ``attune-ai-something``).

    Returns a list of absolute :class:`Path` objects, in arbitrary
    order — callers that need stable ordering should sort. Returns
    ``[]`` when the parent ``~/.claude/projects/`` directory doesn't
    exist (fresh install with no Claude Code history) or when no
    matching keys are found.

    Cross-spec note: the worktree-inventory spec at
    ``docs/specs/worktree-inventory/`` consumes this same helper.
    The function is exported from ``attune.ops.data`` (no leading
    underscore) so siblings can import it without dipping into a
    private name.
    """
    projects_root = Path.home() / ".claude" / "projects"
    if not projects_root.is_dir():
        return []
    encoded = _encoded_project_path(project_root)
    matches: list[Path] = []
    try:
        children = list(projects_root.iterdir())
    except OSError:
        return []
    for child in children:
        if not child.is_dir():
            continue
        name = child.name
        if name == encoded or name.startswith(f"{encoded}-"):
            matches.append(child)
    return matches


def _heuristic_starter_prompt(content: str, *, char_limit: int = 200) -> str:
    """Truncate a user's first-prompt content to ~``char_limit`` chars.

    Spec calls for first user prompt + last assistant turn, both
    truncated. The Claude Code JSONL we observed only carries the
    user-prompt side via queue-operation enqueue events; there's no
    assistant-turn signal in this event log. S2 ships with the
    user-prompt-only heuristic; S3's Haiku path produces the
    fuller summary independently of this code path.

    Truncation strategy: cut at a word boundary if one falls within
    ``char_limit - 20`` of the limit so we don't slice mid-word.
    Ellipsis appended when truncated.
    """
    s = (content or "").strip().replace("\n", " ")
    # Collapse runs of whitespace so the preview doesn't have gaps.
    s = " ".join(s.split())
    if len(s) <= char_limit:
        return s
    cut = s[:char_limit]
    last_space = cut.rfind(" ")
    if last_space > char_limit - 20:
        cut = cut[:last_space]
    return cut.rstrip() + "…"


def _parse_session(jsonl_path: Path) -> Session | None:
    """Build a :class:`Session` from one JSONL file. Returns None on
    unreadable file (callers skip rather than crash the listing).

    Robust per-line: a malformed JSON line is skipped, not fatal.
    A file with zero parseable lines yields a Session with empty
    timestamps and a "(empty session)" starter prompt — the
    template can render the row OR the caller can filter; we
    surface rather than hide.
    """
    session_id = jsonl_path.stem
    first_ts: str | None = None
    last_ts: str | None = None
    prompt_count = 0
    starter_prompt = ""
    try:
        with jsonl_path.open(encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                ts = event.get("timestamp")
                if isinstance(ts, str) and ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts
                content = event.get("content")
                if isinstance(content, str) and content:
                    prompt_count += 1
                    if not starter_prompt:
                        starter_prompt = _heuristic_starter_prompt(content)
    except OSError:
        return None
    duration = _duration_seconds(first_ts, last_ts)
    return Session(
        id=session_id,
        started_at=first_ts or "",
        last_activity=last_ts or first_ts or "",
        duration_seconds=duration,
        message_count=prompt_count,
        starter_prompt=starter_prompt or "(no prompt recorded)",
        source="heuristic",
    )


def _duration_seconds(first: str | None, last: str | None) -> float:
    """ISO 8601 strings → elapsed seconds; ``0.0`` if either is unparseable."""
    if not first or not last:
        return 0.0
    try:
        a = datetime.fromisoformat(first.replace("Z", "+00:00"))
        b = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return max((b - a).total_seconds(), 0.0)


# Default cap on the number of sessions surfaced on the /sessions page.
# Sized for the budget cap math (decisions.md Decision 5): 20 × ~$0.001/session
# Haiku spend = ~$0.02 worst case, well under the $0.05 per-load cap. Older
# sessions stay on disk for ``cat`` but aren't surfaced. The Resume-most-recent
# card reads independently and is unaffected by this limit.
DEFAULT_SESSION_LIST_CAP = 20


def list_recent_sessions_with_paths(
    project_root: Path | str,
    *,
    days: int = 3,
    limit: int | None = DEFAULT_SESSION_LIST_CAP,
    now: datetime | None = None,
    parser: Callable[[Path], Session | None] | None = None,
) -> list[tuple[Session, Path]]:
    """Same as :func:`list_recent_sessions` but also returns each
    session's source JSONL path.

    Needed by S3b's Haiku wire-up: the summarizer requires the
    on-disk path to compute the last-4KB cache key. Returning the
    path alongside the parsed :class:`Session` avoids re-walking
    the encoded-key dirs for every summarization call.

    Same arguments and failure modes as :func:`list_recent_sessions`.
    Result is sorted by ``last_activity`` desc and capped at
    ``limit``.
    """
    # Local import: a module-level ``timedelta`` import was reverted by
    # the formatter (likely ruff isort considering it unused at the
    # module scope since only this function references it). Re-importing
    # locally is the pragmatic dodge — the cost is negligible because
    # ``from datetime import ...`` is cached after first use anyway.
    from datetime import timedelta

    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    parse = parser or _parse_session

    encoded_dirs = enumerate_project_encoded_keys(project_root)
    if not encoded_dirs:
        return []

    # Per-id newest-mtime entry. Value is (mtime_utc, jsonl_path).
    # Build this first so dedup can choose newest-mtime before parse.
    by_id: dict[str, tuple[datetime, Path]] = {}
    for sessions_dir in encoded_dirs:
        try:
            candidates = list(sessions_dir.glob("*.jsonl"))
        except OSError:
            continue
        for jsonl in candidates:
            try:
                mtime = datetime.fromtimestamp(jsonl.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if mtime < cutoff:
                continue
            session_id = jsonl.stem
            existing = by_id.get(session_id)
            if existing is None:
                by_id[session_id] = (mtime, jsonl)
                continue
            # Duplicate session-id across encoded keys (rare). Keep newest.
            existing_mtime, existing_path = existing
            if mtime > existing_mtime:
                logger.warning(
                    "ops.sessions: duplicate session id %s — keeping newer "
                    "%s (mtime=%s) over %s (mtime=%s)",
                    session_id,
                    jsonl,
                    mtime.isoformat(),
                    existing_path,
                    existing_mtime.isoformat(),
                )
                by_id[session_id] = (mtime, jsonl)
            else:
                logger.warning(
                    "ops.sessions: duplicate session id %s — keeping existing "
                    "%s (mtime=%s) over %s (mtime=%s)",
                    session_id,
                    existing_path,
                    existing_mtime.isoformat(),
                    jsonl,
                    mtime.isoformat(),
                )

    out: list[tuple[Session, Path]] = []
    for _mtime, jsonl in by_id.values():
        session = parse(jsonl)
        if session is None:
            continue
        out.append((session, jsonl))
    out.sort(key=lambda item: item[0].last_activity or "", reverse=True)
    if limit is not None and limit >= 0:
        out = out[:limit]
    return out


def list_recent_sessions(
    project_root: Path | str,
    *,
    days: int = 3,
    limit: int | None = DEFAULT_SESSION_LIST_CAP,
    now: datetime | None = None,
    parser: Callable[[Path], Session | None] | None = None,
) -> list[Session]:
    """Return Session records for this project's last ``days`` of activity.

    Thin wrapper over :func:`list_recent_sessions_with_paths`;
    drops the on-disk path so callers that don't need it (the
    JSON API, the existing test suite) keep the simpler return
    shape.

    Reads ``*.jsonl`` files from every encoded-key directory belonging
    to this logical project (canonical key plus per-worktree keys —
    see :func:`enumerate_project_encoded_keys`) and filters to files
    whose mtime is within ``days`` of ``now`` (default: current UTC
    time). Sessions are deduplicated by id (the JSONL filename's
    stem) — when the same id appears under multiple encoded keys
    (rare; suggests a worktree that was renamed or re-created), the
    newest-mtime copy wins and a WARN log records the conflict.
    Output is sorted most-recently-active first and capped at
    ``limit`` (default :data:`DEFAULT_SESSION_LIST_CAP`).

    Args:
        project_root: The dashboard's project root. Used to compute
            the encoded-key prefix.
        days: Time window for filtering by JSONL mtime.
        limit: Maximum number of sessions to return. ``None`` returns
            all matches (unbounded — only reasonable for callers that
            already know the size, e.g. tests). The list cap exists
            because each session may incur an LLM-summarization spend
            on first render; capping bounds worst-case page-load cost
            (decisions.md Decision 5).
        now: Override the current time (test hook).
        parser: Override the per-file parser (test hook). Defaults to
            :func:`_parse_session`. The parser receives the JSONL
            :class:`Path` and returns a :class:`Session` or ``None``.

    Returns ``[]`` for any failure mode that doesn't raise:
    - No matching encoded-key dirs (user never ran Claude Code here)
    - All matched dirs are empty
    - All JSONLs are older than the cutoff
    - All JSONLs are unreadable (perm, IO)

    A single corrupt file is skipped with a WARN log; the rest of
    the listing still renders. The spec's failure-mode decision:
    "Skip with WARN log, don't surface as broken row — an unreadable
    file is a Claude Code internal issue, not something the user
    can fix from the dashboard."
    """
    return [
        session
        for session, _path in list_recent_sessions_with_paths(
            project_root, days=days, limit=limit, now=now, parser=parser
        )
    ]


# Path passed to workflows when the user picks the "All code" picker
# option. Hardcoded for attune-ai's ``src/`` layout. Downstream projects
# with different code roots can override by editing this constant or by
# threading a config value through the dashboard route — kept simple
# for the v1 ship.
ALL_CODE_PATH = "src/"


# Friendly chip labels for the Workflows tab. The Tier-map column on
# ``workflows.html`` renders ``{stage}: {tier}`` chips; the raw stage
# names (``agent-review``, ``sweep``) and lowercase tier identifiers
# (``cheap``, ``capable``, ``premium``) read like internal jargon.
# ``TIER_LABEL`` maps each tier to a human-readable descriptor;
# ``TIER_TOOLTIP`` explains the descriptor plus the underlying model
# class in a hover affordance per the dashboard's tooltip-positive
# UX rule.
TIER_LABEL: dict[str, str] = {
    "cheap": "Light",
    "capable": "Standard",
    "premium": "Deep",
}

TIER_TOOLTIP: dict[str, str] = {
    "cheap": "Light tier — fast, lowest cost. Uses Haiku.",
    "capable": "Standard tier — balanced quality and cost. Uses Sonnet.",
    "premium": "Deep tier — highest quality, slowest, most expensive. Uses Opus.",
}


@dataclass(frozen=True)
class FamilyVersion:
    package: str
    version: str | None
    source: str  # "installed" | "missing"


@dataclass(frozen=True)
class DailyCost:
    """One day's cost for the home-page sparkline."""

    day: str  # YYYY-MM-DD
    events: int
    cost: float


@dataclass(frozen=True)
class HomeKpis:
    """Summary numbers shown above the fold on the home page."""

    today_events: int
    today_cost: float
    seven_day_cost: float
    seven_day_savings: float
    sparkline: list[DailyCost]  # always exactly 7 entries, oldest first


def home_kpis(summary: TelemetrySummary, *, today: date | None = None) -> HomeKpis:
    """Derive home-page KPIs from a telemetry summary.

    Always returns a 7-entry sparkline (zero-fills missing days) so the SVG
    layout is stable even on a fresh install.
    """
    today = today or date.today()
    by_day_lookup = {row[0]: (row[1], row[2]) for row in summary.by_day}

    sparkline: list[DailyCost] = []
    seven_day_cost = 0.0
    for offset in range(6, -1, -1):
        day = date.fromordinal(today.toordinal() - offset).isoformat()
        events, cost = by_day_lookup.get(day, (0, 0.0))
        seven_day_cost += cost
        sparkline.append(DailyCost(day=day, events=events, cost=cost))

    today_events, today_cost = by_day_lookup.get(today.isoformat(), (0, 0.0))
    return HomeKpis(
        today_events=today_events,
        today_cost=round(today_cost, 4),
        seven_day_cost=round(seven_day_cost, 4),
        seven_day_savings=round(summary.total_savings, 4),
        sparkline=sparkline,
    )


def sparkline_points(values: list[float], *, width: int = 240, height: int = 40) -> str:
    """Render values as an SVG ``polyline`` ``points`` string.

    Empty/all-zero values return an empty string (template renders fallback).
    Y-axis is inverted (SVG origin is top-left); the largest value touches
    the top of the box.
    """
    if not values or all(v == 0 for v in values):
        return ""
    n = len(values)
    span = max(values) or 1.0
    points: list[str] = []
    for i, v in enumerate(values):
        x = (i / max(n - 1, 1)) * width
        y = height - (v / span) * height
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def read_telemetry_summary(
    config: Config,
    *,
    recent_days: int = 7,
    today: date | None = None,
) -> TelemetrySummary:
    """Aggregate ``usage.jsonl`` into a UI-friendly summary.

    ``today`` is a test injection point — production callers leave it
    ``None`` so the rolling-window cutoff uses ``date.today()``. Tests
    pass an explicit date so fixed-date fixtures (e.g. events dated
    ``2026-05-14``) stay inside the recent-days window regardless of
    when the test actually runs. Mirrors the existing ``now=None``
    injection pattern elsewhere in this module.
    """
    path = config.telemetry_path
    if not path.exists():
        return TelemetrySummary(0, 0.0, 0.0, [], [], None)

    total_requests = 0
    total_cost = 0.0
    total_savings = 0.0
    by_workflow_count: dict[str, int] = defaultdict(int)
    by_workflow_cost: dict[str, float] = defaultdict(float)
    by_day_count: dict[str, int] = defaultdict(int)
    by_day_cost: dict[str, float] = defaultdict(float)
    last_event_at: str | None = None

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    continue

                cost = float(event.get("total_cost", event.get("cost", 0.0)) or 0.0)
                savings = float(event.get("savings", 0.0) or 0.0)
                workflow = str(event.get("workflow") or event.get("event_type") or "unknown")
                # ``usage.jsonl`` events use the ``ts`` key (v1.0 schema in
                # UsageTracker._format_entry); ``timestamp`` is kept as a
                # legacy fallback for any rotated archives that predate the
                # rename. Without this fallback every event silently misses
                # the by_day bucketing and Home's KPI tiles read zero.
                ts = str(event.get("ts") or event.get("timestamp") or "")

                total_requests += 1
                total_cost += cost
                total_savings += savings
                by_workflow_count[workflow] += 1
                by_workflow_cost[workflow] += cost

                day = _to_day(ts)
                if day:
                    by_day_count[day] += 1
                    by_day_cost[day] += cost
                if ts:
                    last_event_at = ts
    except OSError:
        return TelemetrySummary(0, 0.0, 0.0, [], [], None)

    # Filter test fixtures, demo stubs, and removed workflows from the
    # top-list. The telemetry file accumulates entries from every
    # workflow that ever ran, so old test fixtures (e.g. those listed
    # in .claude/rules/attune/bug-patterns.md sync logs:
    # "test-tier-fallback", "new-sample-workflow1") pollute the top
    # spenders rollup and distort the "where did my money go?" signal.
    # The current registry is the source of truth — anything not in it
    # is either a removed workflow or a stub from local development.
    # (P2-8 in the 2026-05-14 QA punch list.)
    try:
        canonical_names = {w.name for w in list_workflows()}
    except Exception:  # noqa: BLE001
        # INTENTIONAL: if the registry introspection fails, fall back
        # to showing everything rather than hiding all data.
        canonical_names = None

    def _is_canonical(name: str) -> bool:
        if canonical_names is None:
            return True
        return name in canonical_names

    filtered = [
        (k, by_workflow_count[k], round(by_workflow_cost[k], 4))
        for k in by_workflow_count
        if _is_canonical(k)
    ]
    # heapq.nlargest is O(n log k) where k=20; sorted()[:20] is O(n log n).
    # Same output ordering since both sort by cost descending.
    by_workflow = heapq.nlargest(20, filtered, key=lambda row: row[2])

    if today is None:
        today = date.today()
    cutoff = today.toordinal() - recent_days
    recent_days_data = sorted(
        (
            (day, by_day_count[day], round(by_day_cost[day], 4))
            for day in by_day_count
            if _ordinal(day) is not None and _ordinal(day) >= cutoff
        ),
        key=lambda row: row[0],
    )

    return TelemetrySummary(
        total_requests=total_requests,
        total_cost=round(total_cost, 4),
        total_savings=round(total_savings, 4),
        by_workflow=by_workflow,
        by_day=recent_days_data,
        last_event_at=last_event_at,
    )


@dataclass(frozen=True)
class SweepChipCounts:
    """Per-bucket counts loaded from a persisted discovery-sweep result.

    Used by the workflows-page chip renderer. ``has_result`` distinguishes
    "no sweep has run yet" (all zeros, has_result False) from "the sweep
    ran and produced zero findings" (all zeros, has_result True), so the
    UI can render an empty state vs a "looks clean" state.
    """

    scope_hash: str
    queue: int
    questions: int
    rejected: int
    has_result: bool


def read_sweep_chip_counts(scope_path: str, config: Config) -> SweepChipCounts:
    """Read the latest persisted sweep result for ``scope_path`` and tally chips.

    Missing or corrupt sidecar returns all-zero counts with
    ``has_result=False``. The same is true when the sidecar has the
    expected shape but lists empty buckets (an empty sweep is still
    "ran"; ``has_result=True``). Never raises — this powers a UI that
    must render even when no sweep has ever been recorded.
    """
    from attune.ops import sweep_results

    digest = sweep_results.scope_hash(scope_path)
    data = sweep_results.read_result(digest, config)
    if data is None:
        return SweepChipCounts(
            scope_hash=digest, queue=0, questions=0, rejected=0, has_result=False
        )
    return SweepChipCounts(
        scope_hash=digest,
        queue=len(data.get("queue") or []),
        questions=len(data.get("questions") or []),
        rejected=len(data.get("rejected") or []),
        has_result=True,
    )


def list_workflows() -> list[WorkflowEntry]:
    """Return the registered workflow catalog. Empty if the registry is unavailable."""
    try:
        from attune.workflows import list_workflows as registry_list
    except ImportError:
        return []

    out: list[WorkflowEntry] = []
    try:
        for entry in registry_list():
            stages = entry.get("stages") or []
            tier_map = entry.get("tier_map") or {}
            out.append(
                WorkflowEntry(
                    name=str(entry.get("name", "")),
                    description=str(entry.get("description", "")),
                    stages=len(stages) if isinstance(stages, list) else 0,
                    tier_map={str(k): str(v) for k, v in tier_map.items()},
                )
            )
    except Exception:  # noqa: BLE001
        # INTENTIONAL: registry introspection is best-effort; never fail the dashboard.
        return []
    return sorted(out, key=lambda w: w.name)


def family_versions() -> list[FamilyVersion]:
    """Resolve installed versions for every related attune package."""
    packages = ("attune-ai", "attune-author", "attune-rag", "attune-help", "attune-gui")
    return [_resolve_version(pkg) for pkg in packages]


def env_health(config: Config) -> dict[str, Any]:
    """Lightweight environment snapshot for the Health page."""
    import platform
    import sys as _sys

    home = config.attune_home
    return {
        "python": _sys.version.split()[0],
        "platform": platform.platform(),
        "attune_home": str(home),
        "attune_home_exists": home.exists(),
        "telemetry_present": config.telemetry_path.exists(),
        "memory_dir_present": config.memory_dir.exists(),
        "sessions_dir_present": config.sessions_dir.exists(),
        "project_root": str(config.project_root),
        "anthropic_api_key": bool(_env("ANTHROPIC_API_KEY")),
    }


def _to_day(ts: str) -> str | None:
    if not ts:
        return None
    with contextlib.suppress(ValueError):
        # Tolerate trailing Z, naive, or aware ISO timestamps.
        cleaned = ts.rstrip("Z")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date().isoformat()
    return None


def _ordinal(day: str) -> int | None:
    with contextlib.suppress(ValueError):
        return date.fromisoformat(day).toordinal()
    return None


def _env(name: str) -> str | None:
    import os

    return os.environ.get(name)


def _resolve_version(package: str) -> FamilyVersion:
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _version
    except ImportError:  # pragma: no cover — Python <3.10 not supported
        return FamilyVersion(package=package, version=None, source="missing")
    try:
        return FamilyVersion(package=package, version=_version(package), source="installed")
    except PackageNotFoundError:
        return FamilyVersion(package=package, version=None, source="missing")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: metadata resolution is best-effort.
        return FamilyVersion(package=package, version=None, source="missing")
