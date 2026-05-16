"""HTTP routes for the discovery-sweep dashboard surface.

Phase 2B + Phase 3 of ``docs/specs/discovery-sweep-ops-integration/``.

Three endpoints, all gated upstream by ``ATTUNE_OPS_SWEEP_RESULTS=1``:

- ``GET /api/workflows/discovery-sweep/results/{scope_hash}`` — JSON
  payload of the latest persisted ``SweepResult`` for a scope, or 404.
  Powers the detail page's data load and any external consumer.
- ``GET /api/workflows/discovery-sweep/chips?scope=<path>`` — JSON
  ``{scope_hash, queue, questions, rejected, has_result}`` for the
  workflow-list row chips. Accepts a raw scope path (or empty for
  project-wide) and computes the hash server-side so the JS side
  doesn't need to. Always returns 200; "no sweep yet" is conveyed via
  ``has_result=False``, not a 404, so the chip renderer can degrade to
  zeros without an error branch.
- ``GET /workflows/discovery-sweep/results/{scope_hash}`` — HTML
  detail page rendering each finding via the generic finding-row
  layout. Accepts ``?bucket=queue|questions|rejected`` to filter.
  Returns 404 if no sweep has been recorded for that scope.

The JSON route was originally registered at the bare URL in Phase 2B;
Phase 3 moves it under ``/api/`` so the bare URL is free for the HTML
detail page. Migration is internal-only — no published consumers.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from attune.ops import data, sweep_results
from attune.ops.config import Config

router = APIRouter()

# scope_hash is sha256-truncated-to-16-hex by sweep_results.scope_hash;
# the route validates the format defensively so a junk path can't slip
# through to read_result() and trigger a filesystem lookup of something
# attacker-controlled.
_SCOPE_HASH_RE = re.compile(r"^[0-9a-f]{16}$")

_VALID_BUCKETS = ("queue", "questions", "rejected")


def _project_root(request: Request) -> Config:
    return request.app.state.config


@router.get("/api/workflows/discovery-sweep/results/{scope_hash}")
async def get_sweep_result(scope_hash: str, request: Request) -> JSONResponse:
    """Return the latest sweep result for a scope-hash, or 404.

    The path parameter must be exactly 16 lowercase hex characters
    (the shape :func:`sweep_results.scope_hash` produces). Anything
    else returns 400 — read_result would fall back to a missing-file
    404 anyway, but rejecting malformed shapes early gives a clearer
    operator-facing error.
    """
    if not _SCOPE_HASH_RE.match(scope_hash):
        raise HTTPException(
            status_code=400,
            detail="scope_hash must be 16 lowercase hex characters",
        )

    config = _project_root(request)
    result = sweep_results.read_result(scope_hash, config)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"no sweep result for scope {scope_hash}",
        )
    return JSONResponse(content=result)


@router.get("/api/workflows/discovery-sweep/chips")
async def get_sweep_chips(request: Request, scope: str = "") -> JSONResponse:
    """Return chip counts for an arbitrary scope path.

    Accepts the raw path the scope picker sends to the runner. Hashes
    it server-side so JS doesn't have to. Empty string = project-wide.
    Always 200: ``has_result=False`` is the "no sweep yet" signal
    instead of a 404, so the chip renderer can degrade to zeros with
    a single response shape.
    """
    config = _project_root(request)
    # Project-wide means "the project root" — match the runner's
    # interpretation of an empty scope (RunnerService resolves it
    # against project_root).
    scope_path = scope or str(config.project_root)
    counts = data.read_sweep_chip_counts(scope_path, config)
    return JSONResponse(
        content={
            "scope_hash": counts.scope_hash,
            "scope_path": scope_path,
            "queue": counts.queue,
            "questions": counts.questions,
            "rejected": counts.rejected,
            "has_result": counts.has_result,
        }
    )


# Severity → CSS class for the per-finding rows on the detail page. The
# tokens here mirror the parent discovery-sweep spec's Phase 3.2 color
# choices so the markdown CLI output and the dashboard stay visually
# consistent (per design.md's "Reusing the parent's color tokens").
_SEVERITY_CHIP = {
    "critical": "chip-danger",
    "high": "chip-danger",
    "medium": "chip-warn",
    "low": "chip-muted",
    "info": "chip-muted",
}


def _normalize_findings(bucket: str, raw: list[Any]) -> list[dict[str, Any]]:
    """Shape each bucket's entries into a uniform row dict.

    ``queue`` is a list of :class:`Finding` dicts directly. ``questions``
    and ``rejected`` wrap each Finding inside a parent dict with extra
    routing metadata (``reason``/``next_step`` for questions, ``rule``
    for rejected). Normalize all three to the same row shape so the
    template renders one loop.
    """
    rows: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        if bucket == "queue":
            finding = entry
            extra = None
        else:
            inner = entry.get("finding")
            if not isinstance(inner, dict):
                continue
            finding = inner
            if bucket == "questions":
                extra = {
                    "label": "Why",
                    "value": entry.get("reason") or "",
                    "follow_up": entry.get("next_step") or "",
                }
            else:  # rejected
                extra = {
                    "label": "Rule",
                    "value": entry.get("rule") or "",
                    "follow_up": "",
                }
        severity = str(finding.get("severity", "")).lower()
        rows.append(
            {
                "source": str(finding.get("source", "")),
                "severity": severity,
                "severity_chip": _SEVERITY_CHIP.get(severity, "chip-muted"),
                "title": str(finding.get("title", "")),
                "description": str(finding.get("description", "")),
                "file": finding.get("file"),
                "line": finding.get("line"),
                "evidence": finding.get("evidence"),
                "confidence": finding.get("confidence"),
                "tags": list(finding.get("tags") or ()),
                "extra": extra,
            }
        )
    return rows


@router.get("/workflows/discovery-sweep/results/{scope_hash}", response_class=HTMLResponse)
async def sweep_detail_page(scope_hash: str, request: Request) -> HTMLResponse:
    """Scope-keyed detail page for the latest discovery-sweep result.

    Renders each bucket as a section, with severity chips on every
    finding row. ``?bucket=queue|questions|rejected`` filters to one
    bucket; absence renders all three. Unknown bucket names are
    ignored (no filter applied) rather than returning 400 — that
    matches the surrounding dashboard's tolerant query-param style.
    """
    if not _SCOPE_HASH_RE.match(scope_hash):
        raise HTTPException(
            status_code=400,
            detail="scope_hash must be 16 lowercase hex characters",
        )

    config = _project_root(request)
    result = sweep_results.read_result(scope_hash, config)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"no sweep result for scope {scope_hash}. Run "
                "`attune workflow run discovery-sweep --path <P>` first."
            ),
        )

    bucket_filter = request.query_params.get("bucket") or ""
    bucket_filter = bucket_filter if bucket_filter in _VALID_BUCKETS else ""

    queue = _normalize_findings("queue", result.get("queue") or [])
    questions = _normalize_findings("questions", result.get("questions") or [])
    rejected = _normalize_findings("rejected", result.get("rejected") or [])
    metadata = result.get("metadata") or {}

    sections = [
        ("queue", "Queue", queue, "Findings ready for review."),
        (
            "questions",
            "Questions",
            questions,
            "Findings the engine couldn't auto-route — needs your call.",
        ),
        (
            "rejected",
            "Rejected",
            rejected,
            "Findings filtered out by deterministic rules.",
        ),
    ]
    visible_sections = [s for s in sections if s[0] == bucket_filter] if bucket_filter else sections

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "sweep_detail.html",
        {
            "request": request,
            "page": "workflows",
            "project_root": str(config.project_root),
            "project_name": data.derive_project_name(config.project_root),
            "attune_home": str(config.attune_home),
            "current_run": None,
            "scope_hash": scope_hash,
            "bucket_filter": bucket_filter,
            "sections": visible_sections,
            "all_section_meta": [(key, label) for key, label, _, _ in sections],
            "totals": {
                "queue": len(queue),
                "questions": len(questions),
                "rejected": len(rejected),
            },
            "metadata": metadata,
        },
    )
