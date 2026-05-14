"""HTTP route: GET /workflows/discovery-sweep/results/{scope_hash}.

Phase 2B of ``docs/specs/discovery-sweep-ops-integration/``.

Returns the latest persisted SweepResult JSON for a given scope-hash,
or 404 if no sweep has been recorded for that scope yet. The
dashboard's workflow-row chip counts (Phase 3) call this endpoint
to render the per-bucket totals without re-running the sweep.

Scope-hash semantics live in :mod:`attune.ops.sweep_results` — this
router is purely a read-side wrapper around that module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from attune.ops import sweep_results
from attune.ops.config import Config

router = APIRouter()

# scope_hash is sha256-truncated-to-16-hex by sweep_results.scope_hash;
# the route validates the format defensively so a junk path can't
# slip through to read_result() and trigger a filesystem lookup of
# something attacker-controlled.
_SCOPE_HASH_RE = re.compile(r"^[0-9a-f]{16}$")


@router.get("/workflows/discovery-sweep/results/{scope_hash}")
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

    config: Config = request.app.state.config
    result = sweep_results.read_result(scope_hash, config)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"no sweep result for scope {scope_hash}",
        )
    return JSONResponse(content=result)
