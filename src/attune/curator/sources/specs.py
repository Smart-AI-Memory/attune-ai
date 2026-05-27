"""Specs source reader — spec status + completion-candidate signals.

Walks ``<project_root>/docs/specs/`` (the default spec root) and
emits one ``SourceItem`` per spec directory. Items carry the spec's
status (parsed from ``**Status:**`` lines in the canonical phase
files), an age signal from the newest ``.md`` mtime, and a flag
indicating whether the completion-candidates detector classified
the spec as ready-to-close.

The completion-candidates side is best-effort: if the detector
raises (network, missing config, etc.), the reader still returns
status + age and just sets ``is_completion_candidate="false"`` for
every item.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from attune.ops.config import build_config
from attune.ops.routes.specs import SpecRecord, _list_specs_in_root

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "specs"
_DEFAULT_SPECS_ROOT = Path("docs/specs")
_DETAIL_CHAR_LIMIT = 500


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """List specs with status, age, and completion-candidate flag.

    Args:
        project_root: Repository root. Specs are discovered at
            ``<project_root>/docs/specs/``.
        since: Unused — kept for Protocol conformance. (Spec status
            doesn't have a since-window in v1.)
    """
    del since  # noqa: F841 — protocol-required arg

    started = time.perf_counter()
    root = (project_root / _DEFAULT_SPECS_ROOT).resolve()

    try:
        specs = _list_specs_in_root(root)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a reader that raises crashes the parallel
        # gather() in the orchestrator. Log + return empty.
        logger.warning("specs: listing failed: %s", exc)
        return _empty_summary(started)

    candidate_slugs = _safe_completion_candidates(project_root, root)

    items: list[SourceItem] = []
    for spec in specs:
        items.append(
            _spec_to_item(
                spec,
                is_candidate=spec.slug in candidate_slugs,
            )
        )

    state_hash = _hash_specs(specs, candidate_slugs)
    fetch_ms = int((time.perf_counter() - started) * 1000)
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=state_hash,
        items=items,
        fetch_ms=fetch_ms,
    )


def _safe_completion_candidates(project_root: Path, specs_root: Path) -> set[str]:
    """Detect completion candidates without crashing the reader.

    The detector hits the GitHub API for PR / issue verification.
    Network failures, missing ``gh`` CLI, and missing remote all
    surface as empty rather than tracebacks.
    """
    try:
        from attune.ops.completion_candidates import detect_candidates

        cfg = build_config(
            project_root=project_root,
            specs_roots=(specs_root,),
            specs_candidates_enabled=True,
        )
        return {c.slug for c in detect_candidates(cfg)}
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: candidate detection is auxiliary. If it
        # fails the reader still produces useful status + age data.
        logger.debug("specs: completion-candidates skipped: %s", exc)
        return set()


def _spec_to_item(spec: SpecRecord, *, is_candidate: bool) -> SourceItem:
    status = _preferred_status(spec) or "unknown"
    age_days = _age_days(spec.last_modified)
    detail_lines: list[str] = []
    for phase in spec.phases:
        if not phase.exists:
            continue
        phase_status = phase.status or "(no status line)"
        detail_lines.append(f"{phase.name}: {phase_status}")
    detail = f"{spec.slug} — status: {status}, age_days: {age_days}. " + "; ".join(detail_lines)
    metadata = {
        "status": status,
        "age_days": str(age_days) if age_days is not None else "unknown",
        "is_completion_candidate": "true" if is_candidate else "false",
    }
    return SourceItem(
        item_id=f"spec:{spec.slug}",
        title=spec.slug,
        detail=_truncate(detail, _DETAIL_CHAR_LIMIT),
        link=f"/specs/{spec.slug}",
        metadata=metadata,
    )


def _preferred_status(spec: SpecRecord) -> str | None:
    """Pick the most authoritative status across the spec's phases.

    Prefers tasks → design → requirements → decisions, matching the
    completion-candidates heuristic. Returns the first non-empty
    status found in that order.
    """
    order = ("tasks", "design", "requirements", "decisions")
    by_name = {p.name: p for p in spec.phases}
    for name in order:
        phase = by_name.get(name)
        if phase and phase.status:
            return phase.status
    return None


def _age_days(last_modified: str | None) -> int | None:
    if not last_modified:
        return None
    try:
        dt = datetime.fromisoformat(last_modified)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    return max(0, delta.days)


def _hash_specs(specs: list[SpecRecord], candidate_slugs: set[str]) -> str:
    """Deterministic hash over (slug, status, last_modified, candidate)."""
    rows = sorted(
        (
            spec.slug,
            _preferred_status(spec) or "",
            spec.last_modified or "",
            spec.slug in candidate_slugs,
        )
        for spec in specs
    )
    joined = "|".join(f"{s}@{st}@{lm}@{c}" for s, st, lm, c in rows)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _empty_summary(started: float) -> SourceSummary:
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=hashlib.sha256(b"").hexdigest()[:16],
        items=[],
        fetch_ms=int((time.perf_counter() - started) * 1000),
    )


def _truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[: limit - 1] + "…"
