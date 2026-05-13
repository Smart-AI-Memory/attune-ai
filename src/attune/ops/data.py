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
    "health-check": PathArgSpec(kwarg="project_root"),
    "orchestrated-health-check": PathArgSpec(kwarg="project_root"),
    "rag-code-gen": PathArgSpec(kwarg="cwd"),
    "test-audit": PathArgSpec(kwarg="src_path", required=True),
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
                ts = str(event.get("timestamp") or "")

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
