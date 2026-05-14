"""Read-only accessors for data the dashboard surfaces.

All accessors fail soft: if the data file is missing or malformed, they return
empty results instead of raising. This keeps the UI useful on a fresh install.
"""

from __future__ import annotations

import contextlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from attune.ops.config import Config


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
    "doc-orchestrator": PathArgSpec(kwarg="project_root"),
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


# Path passed to workflows when the user picks the "All code" picker
# option. Hardcoded for attune-ai's ``src/`` layout. Downstream projects
# with different code roots can override by editing this constant or by
# threading a config value through the dashboard route — kept simple
# for the v1 ship.
ALL_CODE_PATH = "src/"


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


def read_telemetry_summary(config: Config, *, recent_days: int = 7) -> TelemetrySummary:
    """Aggregate ``usage.jsonl`` into a UI-friendly summary."""
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
                # `ts` is the canonical field name in usage.jsonl
                # (verified 2026-05-14: 19k+ events use `ts`, none use
                # `timestamp`). Accept `timestamp` as a defensive fallback
                # for any future writer that picks the other convention.
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

    by_workflow = sorted(
        ((k, by_workflow_count[k], round(by_workflow_cost[k], 4)) for k in by_workflow_count),
        key=lambda row: row[2],
        reverse=True,
    )[:20]

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
