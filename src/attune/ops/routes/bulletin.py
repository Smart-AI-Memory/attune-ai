"""Read-only API for the multi-actor bulletin.

One endpoint: ``GET /api/bulletin/active`` returns the current
non-stale, non-terminal entries across all actors as JSON. The
dashboard's "Now running across actors" strip polls it.

The route is always mounted; in read-only mode (where the
dashboard runner doesn't write entries itself) it still surfaces
entries written by other actors (CLI runs, scheduled tasks,
other Claude Code sessions).
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from attune.bulletin import FileBulletinBackend

logger = logging.getLogger(__name__)

router = APIRouter()


def _bulletin_dir_for(request: Request):
    """Resolve the bulletin directory from app config.

    ``Config.bulletin_dir`` is the canonical accessor — points at
    ``<attune_home>/bulletin/`` per the multi-actor-bulletin spec.
    """
    cfg = request.app.state.config
    return cfg.bulletin_dir


@router.get("/api/bulletin/active")
async def list_active(request: Request) -> JSONResponse:
    """Return active bulletin entries across all actors.

    Response shape::

        {
          "entries": [
            {
              "actor_id": "...",
              "actor_kind": "...",
              "workflow": "...",
              "run_id": "...",
              "started_at": "...",
              "last_heartbeat": "...",
              "current_status": "running",
              "scope": "...",
              "hostname": null
            },
            ...
          ]
        }

    Stale entries (no heartbeat for > 90s) and terminal entries
    are filtered server-side. Order: most recent heartbeat first.
    Empty list when nothing is in flight or the bulletin directory
    doesn't exist yet.
    """
    backend = FileBulletinBackend(_bulletin_dir_for(request))
    try:
        entries = backend.read_active()
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: route must not 500 if the bulletin is malformed.
        # The bulletin's own read path tolerates malformed lines, so
        # this catches only catastrophic backend errors.
        logger.warning("bulletin route: read failed: %s", exc)
        entries = []

    return JSONResponse({"entries": [asdict(e) for e in entries]})
