"""Read-only accessors for data the dashboard surfaces.

All accessors fail soft: if the data file is missing or malformed, they return
empty results instead of raising. This keeps the UI useful on a fresh install.
"""

from __future__ import annotations

import contextlib
import heapq
import json
import logging
import statistics
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from attune.ops.config import Config, attune_home

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
    "release-gate": PathArgSpec(kwarg="path"),
    "release-notes": PathArgSpec(kwarg="path"),
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
    # Category D — the scope path IS the edit boundary, not a scan
    # root (outcome-first-fix Phase 2). `fix` consumes `scope_paths`
    # and errors without it; the workflow normalizes a bare string
    # into a one-element list for this runner path.
    "fix": PathArgSpec(kwarg="scope_paths", required=True),
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
    # Default to the UTC date, not local ``date.today()``: ``by_day``
    # buckets are keyed by the UTC date of each event (see ``_to_day``),
    # so a local "today" would read the wrong bucket in the evening for
    # non-UTC users (e.g. US Eastern after ~20:00, UTC is already
    # tomorrow). Mixing clocks is the same bug class as #867.
    today = today or datetime.now(timezone.utc).date()
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


def _parse_usage_event(line: str) -> tuple[float, float, str, str] | None:
    """Parse one ``usage.jsonl`` line into ``(cost, savings, workflow, ts)``.

    Returns ``None`` for blank or non-JSON lines (silently skipped —
    they must not count toward totals). Field fallbacks, all pinned by
    ``test_data_characterization.py``:

    - cost: ``total_cost`` → ``cost`` → 0.0 (an explicit ``null``
      total_cost does NOT fall through to ``cost`` — dict.get only
      defaults on a MISSING key).
    - workflow: ``workflow`` → ``event_type`` → ``"unknown"`` (an
      empty-string workflow is falsy and falls through).
    - ts: ``usage.jsonl`` events use the ``ts`` key (v1.0 schema in
      UsageTracker._format_entry); ``timestamp`` is the legacy
      fallback for rotated archives that predate the rename. Without
      it every event silently misses the by_day bucketing and Home's
      KPI tiles read zero.
    """
    line = line.strip()
    if not line:
        return None
    try:
        event: dict[str, Any] = json.loads(line)
    except json.JSONDecodeError:
        return None
    cost = float(event.get("total_cost", event.get("cost", 0.0)) or 0.0)
    savings = float(event.get("savings", 0.0) or 0.0)
    workflow = str(event.get("workflow") or event.get("event_type") or "unknown")
    ts = str(event.get("ts") or event.get("timestamp") or "")
    return cost, savings, workflow, ts


#: Cache for the full usage.jsonl aggregation, keyed by file identity
#: (mtime_ns, size) + the aggregation parameters. The file is
#: append-only and unbounded, and every dashboard/telemetry request
#: re-parsed it in full (11.5.0 self-review Medium). One entry per
#: telemetry path; a new append changes mtime/size and invalidates.
_telemetry_summary_cache: dict[str, tuple[tuple[int, int, int, str], TelemetrySummary]] = {}


def _clear_telemetry_summary_cache() -> None:
    """Test hook — flushes the per-process telemetry summary cache."""
    _telemetry_summary_cache.clear()


def read_telemetry_summary(
    config: Config,
    *,
    recent_days: int = 7,
    today: date | None = None,
) -> TelemetrySummary:
    """Aggregate ``usage.jsonl`` into a UI-friendly summary.

    ``today`` is a test injection point — production callers leave it
    ``None`` so the rolling-window cutoff uses the UTC date
    (``datetime.now(timezone.utc).date()``). Tests
    pass an explicit date so fixed-date fixtures (e.g. events dated
    ``2026-05-14``) stay inside the recent-days window regardless of
    when the test actually runs. Mirrors the existing ``now=None``
    injection pattern elsewhere in this module.
    """
    path = config.telemetry_path
    if not path.exists():
        return TelemetrySummary(0, 0.0, 0.0, [], [], None)

    if today is None:
        # UTC, not local — must match ``_to_day``'s clock authority.
        today = datetime.now(timezone.utc).date()

    cache_key: tuple[int, int, int, str] | None = None
    try:
        st = path.stat()
        cache_key = (st.st_mtime_ns, st.st_size, recent_days, today.isoformat())
    except OSError:
        cache_key = None
    if cache_key is not None:
        cached = _telemetry_summary_cache.get(str(path))
        if cached is not None and cached[0] == cache_key:
            return cached[1]

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
                parsed = _parse_usage_event(line)
                if parsed is None:
                    continue
                cost, savings, workflow, ts = parsed

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

    cutoff = today.toordinal() - recent_days
    recent_days_data = sorted(
        (
            (day, by_day_count[day], round(by_day_cost[day], 4))
            for day in by_day_count
            if _ordinal(day) is not None and _ordinal(day) >= cutoff
        ),
        key=lambda row: row[0],
    )

    summary = TelemetrySummary(
        total_requests=total_requests,
        total_cost=round(total_cost, 4),
        total_savings=round(total_savings, 4),
        by_workflow=by_workflow,
        by_day=recent_days_data,
        last_event_at=last_event_at,
    )
    if cache_key is not None:
        _telemetry_summary_cache[str(path)] = (cache_key, summary)
    return summary


def read_memory_summary(path: Path | None = None) -> dict[str, Any]:
    """Aggregate ``memory_events.jsonl`` into a cost summary.

    Reports what the short-term memory hooks (session recall, JIT rule
    recall, the Stop-hook stash) actually inject — measured cost, not a
    savings estimate. See ``plugin/hooks/_memory_telemetry.py`` for the
    producer and event schema.

    Args:
        path: Override the events-file location (tests pass a fixture).
            ``None`` resolves to ``<attune_home>/telemetry/
            memory_events.jsonl``.

    Returns:
        A JSON-serializable dict. A missing file yields a zeroed summary
        (never raises), so callers can render an empty state.
    """
    if path is None:
        path = attune_home() / "telemetry" / "memory_events.jsonl"

    zeroed: dict[str, Any] = {
        "total_events": 0,
        "total_est_tokens": 0,
        "distinct_sessions": 0,
        "by_event": {},
        "by_day": {},
        "per_session_avg_tokens": 0.0,
    }
    if not path.exists():
        return zeroed

    total_events = 0
    total_est_tokens = 0
    sessions: set[str] = set()
    by_event_n: dict[str, int] = defaultdict(int)
    by_event_tokens: dict[str, int] = defaultdict(int)
    by_day_n: dict[str, int] = defaultdict(int)
    by_day_tokens: dict[str, int] = defaultdict(int)

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

                name = str(event.get("event") or "unknown")
                tokens = _as_int(event.get("est_tokens"))
                # Memory events use the ``ts`` key (v1.0 schema in
                # _memory_telemetry.log_memory_event); ``timestamp`` is a
                # defensive fallback. Without it every event misses the
                # by_day bucketing — the same zero-KPI bug the usage
                # reader documents just above.
                ts = str(event.get("ts") or event.get("timestamp") or "")
                sid = event.get("session_id")

                total_events += 1
                total_est_tokens += tokens
                by_event_n[name] += 1
                by_event_tokens[name] += tokens
                if sid:
                    sessions.add(str(sid))

                day = _to_day(ts)
                if day:
                    by_day_n[day] += 1
                    by_day_tokens[day] += tokens
    except OSError:
        return zeroed

    distinct_sessions = len(sessions)
    per_session_avg = round(total_est_tokens / distinct_sessions, 1) if distinct_sessions else 0.0

    return {
        "total_events": total_events,
        "total_est_tokens": total_est_tokens,
        "distinct_sessions": distinct_sessions,
        "by_event": {
            name: {"n": by_event_n[name], "est_tokens": by_event_tokens[name]}
            for name in sorted(by_event_n)
        },
        "by_day": {
            day: {"n": by_day_n[day], "est_tokens": by_day_tokens[day]} for day in sorted(by_day_n)
        },
        "per_session_avg_tokens": per_session_avg,
    }


#: Honesty caption shipped verbatim with every intervention-signal
#: readout. The benefit of memory injection cannot be MEASURED from the
#: event log alone (no failure log to correlate against), so this number
#: is an upper bound on interventions, not a savings figure. Keeping the
#: caption a module constant lets a test assert it renders unmodified —
#: the guard against the discredited "memory saves X%" framing.
INTERVENTION_SIGNAL_CAPTION = (
    "Estimate, not measured savings: counts JIT rules surfaced before a "
    "tool call. Each MAY have prevented a mistake, but the log has no "
    "failure record to confirm it — treat this as an upper bound on "
    "helpful interventions, never a cost-savings percentage."
)

#: Appended to the caption ONLY when scored memory_signal verdicts exist
#: in the same aggregation scope (MI-5): the denominator the base
#: caption calls missing is then actually measured. Still never a
#: savings figure.
INTERVENTION_DENOMINATOR_NOTE = (
    " A measured verdict denominator is present for this scope: "
    "wrong_rate is the headline hard-noise metric (chair ruling "
    "2026-07-19); ignored surfacings are expected premium, reported "
    "separately — still not a savings percentage."
)

#: Verdict labels the memory_signal reader admits (memory-feedback-signal
#: MI-2/MI-5); anything else fails schema validation and is dropped.
MEMORY_SIGNAL_LABELS = ("acted_on", "ignored", "wrong", "unscored")


def read_memory_signal(path: Path | None = None) -> dict[str, Any]:
    """Aggregate ``memory_signal`` verdicts into the noise denominator.

    Implements MI-5 of ``docs/specs/memory-feedback-signal``: scoped
    to the events-file family at ``path`` (the live file plus rotated
    ``memory_events.*.jsonl`` siblings in the same directory, so
    rotation-split verdicts still aggregate), deduped on the full
    verdict identity ``(session_id, surfacing_id, item_id)`` keeping
    the latest record, with ``unscored`` counted separately and
    excluded from every rate denominator.

    Rates (chair ruling 2026-07-19, thread ``mem-signal-001``):
    ``wrong_rate = wrong / (acted_on + wrong)`` is the HEADLINE
    hard-noise metric; ``ignored_rate`` and the combined
    ``candidate_noise_rate`` are co-reported, reversible fields.
    Rates are ``None`` (never fabricated zeros) when their
    denominator is empty. This is deliberately not, and must never
    become, a savings figure.

    Args:
        path: Override the live events-file location (tests pass a
            fixture). ``None`` resolves to the default
            ``memory_events.jsonl``.

    Returns:
        JSON-serializable dict with ``counts`` (per label),
        ``scored``, ``unscored``, ``wrong_rate``, ``ignored_rate``,
        ``candidate_noise_rate``, and ``headline`` (the ruled metric
        name). Missing files yield zeroed counts, never an exception.
    """
    if path is None:
        path = attune_home() / "telemetry" / "memory_events.jsonl"

    files: list[Path] = []
    if path.parent.is_dir():
        files = sorted(p for p in path.parent.glob("memory_events.*.jsonl") if p != path)
    if path.exists():
        files.append(path)  # live file last so its records win the dedup

    latest: dict[tuple[str, str, str], str] = {}
    for file in files:
        try:
            with file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec: dict[str, Any] = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("event") != "memory_signal":
                        continue
                    verdict = rec.get("verdict")
                    if verdict not in MEMORY_SIGNAL_LABELS:
                        continue  # schema validation: unknown labels dropped
                    key = (
                        str(rec.get("session_id", "")),
                        str(rec.get("surfacing_id", "")),
                        str(rec.get("item_id", "")),
                    )
                    latest[key] = verdict
        except OSError:
            continue

    counts = dict.fromkeys(MEMORY_SIGNAL_LABELS, 0)
    for verdict in latest.values():
        counts[verdict] += 1
    scored = counts["acted_on"] + counts["ignored"] + counts["wrong"]
    hard_denom = counts["acted_on"] + counts["wrong"]
    return {
        "counts": counts,
        "scored": scored,
        "unscored": counts["unscored"],
        "wrong_rate": (counts["wrong"] / hard_denom) if hard_denom else None,
        "ignored_rate": (counts["ignored"] / scored) if scored else None,
        "candidate_noise_rate": (
            (counts["wrong"] + counts["ignored"]) / scored if scored else None
        ),
        "headline": "wrong_rate",
    }


def estimate_intervention_signal(path: Path | None = None) -> dict[str, Any]:
    """Estimate a LABELED benefit signal from ``jit_recall`` surfacings.

    Counts how often the JIT recall hook surfaced a rule right before a
    tool call. This is deliberately NOT a savings number: the event log
    records what was injected, not whether a failure was actually
    avoided, so the honest reading is an upper bound on helpful
    interventions. Every caller must render :data:`INTERVENTION_SIGNAL_CAPTION`
    alongside these figures. See ``memory_cost_claim_grounding`` for why a
    real savings claim needs a separate benchmark.

    Args:
        path: Override the events-file location (tests pass a fixture).
            ``None`` resolves to the default ``memory_events.jsonl``.

    Returns:
        JSON-serializable dict with ``rule_surfacings`` (int),
        ``distinct_rules`` (int), ``top_rules`` (list of ``[rule, count]``,
        highest first), and ``caption`` (the verbatim honesty string).
        A missing file yields zeroed counts, never an exception.
    """
    if path is None:
        path = attune_home() / "telemetry" / "memory_events.jsonl"

    rule_counts: dict[str, int] = defaultdict(int)
    surfacings = 0

    if path.exists():
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
                    if event.get("event") != "jit_recall":
                        continue
                    rules = event.get("rules") or []
                    if not isinstance(rules, list):
                        continue
                    for rule in rules:
                        rule_counts[str(rule)] += 1
                        surfacings += 1
        except OSError:
            rule_counts.clear()
            surfacings = 0

    top_rules = heapq.nlargest(10, rule_counts.items(), key=lambda kv: kv[1])
    result: dict[str, Any] = {
        "rule_surfacings": surfacings,
        "distinct_rules": len(rule_counts),
        "top_rules": [[rule, count] for rule, count in top_rules],
        "caption": INTERVENTION_SIGNAL_CAPTION,
    }
    # MI-5: present the measured noise denominator alongside the upper
    # bound ONLY when at least one valid SCORED verdict exists in the
    # same aggregation scope (this path family). All-unscored, orphaned,
    # or absent verdicts keep the upper-bound-only caption unchanged.
    signal = read_memory_signal(path)
    if signal["scored"] > 0:
        result["noise_denominator"] = signal
        result["caption"] = INTERVENTION_SIGNAL_CAPTION + INTERVENTION_DENOMINATOR_NOTE
    return result


#: Honesty caption for the feedback (noise) signal. A rejection rate is
#: the NOISE side of the insurance ledger — how often a surfaced finding
#: was later dropped as wrong/irrelevant — NOT an inverse-quality score
#: or a savings figure. Kept a constant so a test can assert it renders.
FEEDBACK_SIGNAL_CAPTION = (
    "Noise signal: findings that were surfaced by recall and then "
    "explicitly dropped as wrong/irrelevant/resolved, as a share of "
    "findings stashed. Lower is less noise injected — it is not a "
    "quality score or a savings figure."
)


def estimate_feedback_signal(path: Path | None = None) -> dict[str, Any]:
    """Aggregate ``memory_feedback`` rejections into a noise rate.

    Reads the explicit "this surfaced finding was noise" verdicts
    emitted by the deletion seam (``attune.memory.session_stash``) and
    expresses them as a share of the findings the Stop-hook stashed —
    the net-of-noise half of the memory analyzer. See
    ``project_memory_as_insurance``.

    Args:
        path: Override the events-file location (tests pass a fixture).
            ``None`` resolves to the default ``memory_events.jsonl``.

    Returns:
        JSON-serializable dict: ``rejected`` (total rejected findings),
        ``by_source`` (``{source: count}``), ``findings_written``
        (denominator, from ``session_stash`` events), ``rejection_rate``
        (rejected / written, 0.0 when none written), and ``caption``.
        A missing file yields zeroed counts, never an exception.
    """
    if path is None:
        path = attune_home() / "telemetry" / "memory_events.jsonl"

    rejected = 0
    by_source: dict[str, int] = defaultdict(int)
    findings_written = 0

    if path.exists():
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
                    name = event.get("event")
                    if name == "memory_feedback":
                        count = _as_int(event.get("count"))
                        rejected += count
                        by_source[str(event.get("source") or "unknown")] += count
                    elif name == "session_stash":
                        findings_written += _as_int(event.get("written"))
        except OSError:
            return {
                "rejected": 0,
                "by_source": {},
                "findings_written": 0,
                "rejection_rate": 0.0,
                "caption": FEEDBACK_SIGNAL_CAPTION,
            }

    rate = round(rejected / findings_written, 3) if findings_written else 0.0
    return {
        "rejected": rejected,
        "by_source": {src: by_source[src] for src in sorted(by_source)},
        "findings_written": findings_written,
        "rejection_rate": rate,
        "caption": FEEDBACK_SIGNAL_CAPTION,
    }


# ---------------------------------------------------------------------------
# Spend anomaly alarm — R6 of docs/specs/usage-signals/. Surfaces the
# "$1,200-night" class of event within a day. See decisions.md D13.
# ---------------------------------------------------------------------------

# The z-score bar (3.0) is the textbook outlier threshold. The flat-history
# multiplier (3x) is the spec's explicit fallback for the stddev == 0 case:
# a baseline with no variance can't yield a z-score, so "today is >= 3x the
# flat baseline" stands in. The monthly ceiling + 80% alert fraction mirror
# the Anthropic Console spend limit Patrick set on org 7edead08 ($350/mo
# hard cap, alert at $280) — see the user_monthly_spend_budget memory.
SPEND_Z_THRESHOLD = 3.0
SPEND_FLAT_MULTIPLIER = 3.0
SPEND_MIN_BASELINE_DAYS = 3
MONTHLY_API_CEILING_USD = 350.0
CEILING_ALERT_FRACTION = 0.8


@dataclass(frozen=True)
class SpendAlarm:
    """Daily API-spend anomaly verdict for the dashboard (R6)."""

    level: str  # "ok" | "alarm" | "insufficient_data"
    triggered_by: tuple[str, ...]  # subset of {"daily_anomaly", "ceiling"}
    today_cost: float
    baseline_mean: float
    baseline_days: int
    method: str  # "zscore" | "multiplier" | "none"
    z_score: float | None
    month_to_date: float
    monthly_ceiling: float
    ceiling_pct: float
    source: str  # "account" | "local"
    detail: str  # one-line human explanation


def _daily_anomaly_check(
    baseline: list[float],
    baseline_mean: float,
    today_cost: float,
    *,
    z_threshold: float,
    flat_multiplier: float,
) -> tuple[str, float | None, str | None]:
    """The daily-anomaly trigger: ``(method, z_score, detail)``.

    ``detail`` is non-None exactly when the trigger fires. With
    variance in the baseline the method is ``"zscore"`` (flag at
    ``z >= z_threshold``, inclusive); a flat baseline (stdev == 0)
    falls back to ``"multiplier"`` (flag on STRICTLY exceeding
    ``baseline_mean * flat_multiplier`` — the spec's explicit rule for
    the variance-free $1,200-night case). ``baseline_mean`` arrives
    pre-rounded (4dp) and is used as-is so the z-score matches the
    reported baseline, while stdev is computed from the raw values —
    both pinned by ``test_data_characterization.py``.

    Callers gate on ``min_baseline_days`` before calling; the
    ``len < 2`` guard here only prevents ``statistics.stdev`` from
    raising when that gate is configured down to 1.
    """
    stdev = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0
    if stdev > 0:
        z_score = round((today_cost - baseline_mean) / stdev, 2)
        if z_score >= z_threshold:
            return (
                "zscore",
                z_score,
                f"today ${today_cost:.2f} is {z_score:.1f}σ above the "
                f"${baseline_mean:.2f}/day baseline",
            )
        return "zscore", z_score, None

    # Flat history: baseline_mean > 0 here (baseline keeps non-zero
    # days only), so the ratio is finite; the inf arm is pure defense.
    if today_cost > baseline_mean * flat_multiplier:
        ratio = today_cost / baseline_mean if baseline_mean else float("inf")
        return (
            "multiplier",
            None,
            f"today ${today_cost:.2f} is {ratio:.1f}x the flat "
            f"${baseline_mean:.2f}/day baseline (no variance)",
        )
    return "multiplier", None, None


def spend_alarm(
    daily: dict[str, float],
    *,
    today: date | None = None,
    monthly_ceiling: float = MONTHLY_API_CEILING_USD,
    ceiling_fraction: float = CEILING_ALERT_FRACTION,
    z_threshold: float = SPEND_Z_THRESHOLD,
    flat_multiplier: float = SPEND_FLAT_MULTIPLIER,
    min_baseline_days: int = SPEND_MIN_BASELINE_DAYS,
    source: str = "local",
    month_to_date: float | None = None,
) -> SpendAlarm:
    """Flag anomalous daily API spend and approach to the monthly ceiling.

    ``daily`` maps ``YYYY-MM-DD`` -> total USD cost for that day. The
    function is source-agnostic: pass account-level buckets (preferred —
    they see CI spend) or local ``usage.jsonl`` buckets.

    Two independent triggers raise ``level == "alarm"``:

    1. **Daily anomaly.** Today's spend is an outlier versus the trailing
       baseline of prior *active* (non-zero) days:

       - ``stddev > 0`` -> z-score; flag when ``z >= z_threshold``.
       - **``stddev == 0`` (flat history)** -> the spec's explicit
         fallback: flag when ``today > baseline_mean * flat_multiplier``.
         A variance-free baseline yields no z-score, so the multiplier
         stands in. This is the branch the $1,200-night needs when the
         prior days are all-equal (or there is a single repeated value).

    2. **Ceiling approach.** Month-to-date spend ``>= ceiling_fraction``
       of the monthly ceiling (default 80% of $350). Fires independently
       of the baseline, so even a fresh install with no history alarms
       when month-to-date is already near the cap.

    The baseline excludes today and zero-cost days, so a normal active
    day isn't flagged against a baseline diluted by quiet (zero) days.
    Fewer than ``min_baseline_days`` active prior days -> the daily-anomaly
    check is skipped (``level == "insufficient_data"`` unless the ceiling
    trigger fires); the panel still shows today's number and the gauge.

    Args:
        daily: Day (``YYYY-MM-DD``) -> total USD cost.
        today: Reference date (UTC). Defaults to the current UTC date;
            a test injection point mirroring ``read_telemetry_summary``.
        monthly_ceiling: Monthly API spend cap in USD.
        ceiling_fraction: Fraction of the ceiling that trips the alarm.
        z_threshold: Z-score at/above which today is anomalous.
        flat_multiplier: Multiple of the flat baseline that trips the
            stddev == 0 fallback.
        min_baseline_days: Minimum prior active days to judge anomalies.
        source: ``"account"`` (admin cost-report) or ``"local"``
            (usage.jsonl). Annotates the verdict; ``"local"`` appends a
            CI-blindness note to ``detail``.
        month_to_date: Optional explicit month-to-date total. When given
            (the admin cost-report computes the true full-month figure),
            it overrides summing in-window days — the day window may not
            reach the 1st of the month.

    Returns:
        A :class:`SpendAlarm`.
    """
    today = today or datetime.now(timezone.utc).date()
    today_key = today.isoformat()
    today_cost = round(float(daily.get(today_key, 0.0)), 4)

    month_prefix = today_key[:7]
    if month_to_date is None:
        mtd = round(sum(c for d, c in daily.items() if d[:7] == month_prefix), 4)
    else:
        mtd = round(float(month_to_date), 4)
    ceiling_pct = round(mtd / monthly_ceiling * 100, 1) if monthly_ceiling > 0 else 0.0
    ceiling_hit = monthly_ceiling > 0 and mtd >= monthly_ceiling * ceiling_fraction

    baseline = [c for d, c in daily.items() if d != today_key and c > 0]
    baseline_days = len(baseline)
    baseline_mean = round(statistics.fmean(baseline), 4) if baseline else 0.0

    triggers: list[str] = []
    method = "none"
    z_score: float | None = None
    detail_parts: list[str] = []

    if baseline_days >= min_baseline_days:
        method, z_score, anomaly_detail = _daily_anomaly_check(
            baseline,
            baseline_mean,
            today_cost,
            z_threshold=z_threshold,
            flat_multiplier=flat_multiplier,
        )
        if anomaly_detail is not None:
            triggers.append("daily_anomaly")
            detail_parts.append(anomaly_detail)

    if ceiling_hit:
        triggers.append("ceiling")
        detail_parts.append(
            f"month-to-date ${mtd:.0f} is {ceiling_pct:.0f}% of the "
            f"${monthly_ceiling:.0f} ceiling"
        )

    if triggers:
        level = "alarm"
    elif baseline_days < min_baseline_days:
        level = "insufficient_data"
    else:
        level = "ok"

    if detail_parts:
        detail = "; ".join(detail_parts)
    elif level == "insufficient_data":
        detail = (
            f"only {baseline_days} prior active day(s) — need "
            f"{min_baseline_days} to judge anomalies"
        )
    else:
        detail = f"today ${today_cost:.2f} within normal range"
    if source == "local":
        detail += " (local telemetry only — CI spend not counted)"

    return SpendAlarm(
        level=level,
        triggered_by=tuple(triggers),
        today_cost=today_cost,
        baseline_mean=baseline_mean,
        baseline_days=baseline_days,
        method=method,
        z_score=z_score,
        month_to_date=mtd,
        monthly_ceiling=monthly_ceiling,
        ceiling_pct=ceiling_pct,
        source=source,
        detail=detail,
    )


def read_daily_spend(
    config: Config, *, days: int = 35, today: date | None = None
) -> dict[str, float]:
    """Daily API spend (USD) bucketed by ``ts`` from ``usage.jsonl``.

    Returns ``{YYYY-MM-DD: total_cost}`` over the trailing ``days`` days
    (UTC). The window defaults to 35 so the current calendar month is
    always fully covered for the month-to-date gauge even at month-end.

    Buckets by the ``ts`` key (v1.0 schema from
    ``UsageTracker._format_entry``), with ``timestamp`` as a legacy
    fallback — the same field discipline as :func:`read_telemetry_summary`.
    Reading the wrong key is the #867 bug class that made Home read zero.

    Never raises; a missing or unreadable file yields an empty dict.
    """
    path = config.telemetry_path
    if not path.exists():
        return {}
    if today is None:
        today = datetime.now(timezone.utc).date()
    cutoff = today.toordinal() - days
    out: dict[str, float] = defaultdict(float)
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
                ts = str(event.get("ts") or event.get("timestamp") or "")
                day = _to_day(ts)
                if day is None:
                    continue
                ordinal = _ordinal(day)
                if ordinal is None or ordinal < cutoff:
                    continue
                out[day] += _as_float(event.get("total_cost", event.get("cost")))
    except OSError:
        return {}
    return {d: round(c, 4) for d, c in out.items()}


def build_spend_alarm(
    config: Config,
    cost_summary: Any | None = None,
    *,
    today: date | None = None,
) -> SpendAlarm:
    """Assemble the spend alarm, preferring account-level spend.

    Source precedence:

    1. **Account-level** (Anthropic admin cost-report ``CostSummary``):
       captures *everything billed to the org* — including CI, the surface
       the 2026-06-10 ~$1,200 burn actually lived on. This is the source
       R6's "$1,200-night must be visible within a day" requires; local
       telemetry structurally can't see CI spend.
    2. **Local fallback** (``usage.jsonl`` via :func:`read_daily_spend`)
       when no admin key is configured or the fetch failed. Honest about
       the blind spot via ``SpendAlarm.source == "local"``.

    ``cost_summary`` is typed ``Any`` to avoid importing the optional
    ``anthropic_cost`` module (which needs ``httpx``) at import time; the
    caller passes the already-fetched summary from the home route, so no
    extra API call is made.
    """
    by_day = getattr(cost_summary, "by_day", None)
    if cost_summary is not None and by_day:
        daily = {d.isoformat(): float(c) for d, c in by_day}
        return spend_alarm(
            daily,
            today=today,
            source="account",
            month_to_date=cost_summary.month_to_date_usd,
        )
    daily = read_daily_spend(config, today=today)
    return spend_alarm(daily, today=today, source="local")


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


def _as_int(value: Any, default: int = 0) -> int:
    """Coerce a record field to int, TOTALLY — never raises (class G2).

    A reader loop that skips malformed JSON has declared per-record
    tolerance; coercing a field with a bare ``int()`` right after breaks
    that promise, because well-formed JSON can still carry
    ``{"est_tokens": "abc"}`` and ``int()`` raises ``ValueError`` past
    the loop's ``except json.JSONDecodeError``. One bad line then costs
    every good record in the file, not just its own.
    """
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    """Coerce a record field to float, TOTALLY — never raises. See _as_int."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


# ---------------------------------------------------------------------------
# US-6 three-panel receipt: reach + freshness (spend is build_spend_alarm)
# ---------------------------------------------------------------------------

#: The five expected reach packages — mirrors ``scripts/reach_snapshot.py``
#: ``PACKAGES`` (the US-4 allowlist). A legacy snapshot without a manifest
#: counts complete only when all five are present.
REACH_PACKAGES: tuple[str, ...] = (
    "attune-ai",
    "attune-rag",
    "attune-help",
    "attune-author",
    "attune-verify",
)

#: US-6: the freshness panel flags a usage.jsonl last-write age above this.
USAGE_STALE_HOURS = 48.0


@dataclass
class ReachPanel:
    """Latest COMPLETE reach snapshot + any newer incomplete one (US-6).

    An incomplete snapshot never replaces the latest complete snapshot —
    it is surfaced separately, labeled incomplete.
    """

    latest_complete: dict[str, Any] | None
    newer_incomplete: dict[str, Any] | None


def _snapshot_is_complete(data: dict[str, Any]) -> bool:
    manifest = data.get("manifest")
    if isinstance(manifest, dict):
        return manifest.get("complete") is True
    pypi = data.get("pypi_recent")
    return isinstance(pypi, dict) and set(REACH_PACKAGES) <= set(pypi)


def read_reach_panel(config: Config) -> ReachPanel:
    """Scan the tracked snapshots dir for the reach panel's data (US-6).

    Reads ``<project_root>/docs/specs/usage-signals/snapshots/*.json``
    newest-first (dated filenames sort chronologically). The first
    complete snapshot wins; incomplete snapshots encountered BEFORE it
    (i.e. newer) are reported separately with their missing packages.
    """
    snap_dir = config.project_root / "docs" / "specs" / "usage-signals" / "snapshots"
    latest_complete: dict[str, Any] | None = None
    newer_incomplete: dict[str, Any] | None = None
    if not snap_dir.is_dir():
        return ReachPanel(None, None)
    for path in sorted(snap_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("ops.reach: unreadable snapshot %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            continue
        if _snapshot_is_complete(data):
            latest_complete = {
                "date": data.get("date") or path.stem,
                "taken_at": data.get("taken_at"),
                "packages": data.get("pypi_recent") or {},
            }
            break
        if newer_incomplete is None:
            pypi = data.get("pypi_recent") if isinstance(data.get("pypi_recent"), dict) else {}
            manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else {}
            missing = manifest.get("missing") or [pkg for pkg in REACH_PACKAGES if pkg not in pypi]
            newer_incomplete = {
                "date": data.get("date") or path.stem,
                "taken_at": data.get("taken_at"),
                "captured": sorted(pypi),
                "missing": missing,
            }
    return ReachPanel(latest_complete=latest_complete, newer_incomplete=newer_incomplete)


@dataclass
class UsageFreshness:
    """Last-write age of ``usage.jsonl`` for the freshness panel (US-6)."""

    exists: bool
    last_write_at: str | None
    age_hours: float | None
    stale: bool  # age > USAGE_STALE_HOURS


def read_usage_freshness(config: Config, *, now: datetime | None = None) -> UsageFreshness:
    """Compute usage.jsonl freshness from file mtime (real boundary)."""
    path = config.telemetry_path
    if not path.is_file():
        return UsageFreshness(exists=False, last_write_at=None, age_hours=None, stale=True)
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError as exc:
        logger.warning("ops.freshness: cannot stat %s: %s", path, exc)
        return UsageFreshness(exists=False, last_write_at=None, age_hours=None, stale=True)
    current = now or datetime.now(timezone.utc)
    age_hours = max((current - mtime).total_seconds(), 0.0) / 3600.0
    return UsageFreshness(
        exists=True,
        last_write_at=mtime.isoformat(),
        age_hours=age_hours,
        stale=age_hours > USAGE_STALE_HOURS,
    )
