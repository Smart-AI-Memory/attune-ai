"""Dashboard surface for the bulletin curator briefing.

Three endpoints:

- ``GET /curator`` — render the executive summary + ranked item cards.
  Invokes :func:`attune.curator.run_curator` (cached; degrades to an
  offline briefing on LLM failure) and filters out items the user has
  snoozed.
- ``POST /curator/dismiss`` — snooze an item for 14 days. Persists to
  ``<attune_home>/curator/dismissals.json``.
- ``POST /curator/answer`` — record the user's response to an item's
  suggested action (audit journal). The spec-status side-effect the
  design sketches is deferred — see
  ``docs/specs/bulletin-curator/decisions.md`` D5.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse

from attune.curator import run_curator
from attune.ops.security import require_client_token
from attune.security.path_validation import _validate_file_path

from .dashboard import _ctx

logger = logging.getLogger(__name__)

router = APIRouter()

_SNOOZE_DAYS = 14


def _curator_dir(request: Request) -> Path:
    return request.app.state.config.attune_home / "curator"


def _dismissals_path(request: Request) -> Path:
    return _curator_dir(request) / "dismissals.json"


def _load_dismissals(request: Request) -> dict[str, Any]:
    """Load the dismissals map; ``{}`` on missing / malformed file."""
    path = _dismissals_path(request)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _active_dismissed_ids(request: Request) -> set[str]:
    """Item ids whose snooze window hasn't elapsed."""
    now = datetime.now(timezone.utc)
    active: set[str] = set()
    for item_id, rec in _load_dismissals(request).items():
        until = rec.get("snoozed_until") if isinstance(rec, dict) else None
        if not until:
            continue
        try:
            dt = datetime.fromisoformat(str(until))
        except (ValueError, TypeError):
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > now:
            active.add(item_id)
    return active


@router.get("/curator", response_class=HTMLResponse)
async def curator_page(request: Request, refresh: int = 0) -> HTMLResponse:
    """Render the curator briefing, filtering snoozed items."""
    cfg = request.app.state.config
    result = await run_curator(
        project_root=cfg.project_root,
        force_refresh=bool(refresh),
    )
    dismissed = _active_dismissed_ids(request)
    visible = [item for item in result.items if item.id not in dismissed]
    templates = request.app.state.templates
    ctx = _ctx(request, page="curator", result=result, items=visible)
    return templates.TemplateResponse(request, "curator.html", ctx)


@router.post("/curator/dismiss")
async def curator_dismiss(
    request: Request,
    body: dict[str, Any] = Body(...),  # noqa: B008
    _client: None = Depends(require_client_token),  # noqa: B008
) -> JSONResponse:
    """Snooze an item for 14 days.

    Body: ``{"item_id": "..."}``. Writes
    ``<attune_home>/curator/dismissals.json`` with the snooze deadline.
    """
    item_id = str(body.get("item_id") or "").strip()
    if not item_id:
        return JSONResponse({"ok": False, "error": "item_id required"}, status_code=400)

    dismissals = _load_dismissals(request)
    until = datetime.now(timezone.utc) + timedelta(days=_SNOOZE_DAYS)
    dismissals[item_id] = {"snoozed_until": until.isoformat()}

    path = _dismissals_path(request)
    try:
        validated = _validate_file_path(str(path))
        validated.parent.mkdir(parents=True, exist_ok=True)
        tmp = validated.with_suffix(validated.suffix + ".tmp")
        tmp.write_text(json.dumps(dismissals, sort_keys=True), encoding="utf-8")
        tmp.replace(validated)
    except (OSError, ValueError) as exc:
        logger.warning("curator: dismiss write failed for %s: %s", path, exc)
        return JSONResponse({"ok": False, "error": "write failed"}, status_code=500)

    return JSONResponse({"ok": True, "item_id": item_id, "snoozed_until": until.isoformat()})


@router.post("/curator/answer")
async def curator_answer(
    request: Request,
    body: dict[str, Any] = Body(...),  # noqa: B008
    _client: None = Depends(require_client_token),  # noqa: B008
) -> JSONResponse:
    """Record a user's response to an item's suggested action.

    Body: ``{"item_id": "...", "choice": "..."}``. Appends to
    ``<attune_home>/curator/answers.jsonl`` (audit journal). Best-effort:
    a journal failure is logged, not surfaced as an error.
    """
    item_id = str(body.get("item_id") or "").strip()
    choice = str(body.get("choice") or "").strip()
    if not item_id or not choice:
        return JSONResponse(
            {"ok": False, "error": "item_id and choice required"},
            status_code=400,
        )

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "item_id": item_id,
        "choice": choice,
    }
    path = _curator_dir(request) / "answers.jsonl"
    try:
        validated = _validate_file_path(str(path))
        validated.parent.mkdir(parents=True, exist_ok=True)
        with validated.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except (OSError, ValueError) as exc:
        # Best-effort journal — never fail the response on a write hiccup.
        logger.warning("curator: answer journal append failed for %s: %s", path, exc)

    return JSONResponse({"ok": True, "item_id": item_id, "choice": choice})
