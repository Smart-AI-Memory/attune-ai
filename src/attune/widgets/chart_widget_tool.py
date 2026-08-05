"""chart_render_widget — spec (or patch) in, kernel-injected HTML out.

This module is the sanctioned chartkit loader: it reads the built
artifact ``chartkit/dist/kernel.min.js`` as bytes and never imports
kernel source. Specs persist per chart_id in the session memory
backend so a later turn can send a patch instead of the full spec.

Degradation is legible by design (D5): when no backend is reachable,
patches are rejected with an instruction to re-send the full spec —
never a silent fallback.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from attune.widgets.chart_spec import ChartSpecError, validate_chart_spec

logger = logging.getLogger(__name__)

_KERNEL_PATH = Path(__file__).resolve().parent / "chartkit" / "dist" / "kernel.min.js"
_CHART_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_TTL_SECONDS = 8 * 3600

BACKEND_DOWN_MSG = (
    "Chart persistence is unavailable (no memory backend reachable), so the "
    "current spec cannot be loaded to apply a patch. Re-send the FULL chart "
    "spec for this chart_id instead of a patch."
)
NO_STORED_SPEC_MSG = (
    "No stored spec found for chart_id {chart_id!r} (it may have expired). "
    "Re-send the FULL chart spec instead of a patch."
)
KERNEL_MISSING_MSG = (
    "chartkit kernel artifact is missing ({path}). Build it with "
    "'npm run build' in src/attune/widgets/chartkit/ (CI builds it "
    "automatically)."
)


def _resolve_backend() -> Any | None:
    try:
        from attune.memory.session_stash import resolve_backend

        return resolve_backend()
    except Exception as exc:  # noqa: BLE001 — no backend is a handled state
        logger.info("chart persistence backend unavailable: %s", exc)
        return None


def merge_patch(target: Any, patch: Any) -> Any:
    """RFC 7386 JSON Merge Patch — mirrors the kernel's applyPatch."""
    if not isinstance(patch, dict):
        return patch
    out: dict[str, Any] = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            out.pop(key, None)
        else:
            out[key] = merge_patch(out.get(key), value)
    return out


def _chart_key(chart_id: str) -> str:
    return f"chart:{chart_id}"


def _build_html(chart_id: str, spec_dict: dict[str, Any]) -> str:
    if not _KERNEL_PATH.exists():
        raise FileNotFoundError(KERNEL_MISSING_MSG.format(path=_KERNEL_PATH))
    kernel = _KERNEL_PATH.read_text(encoding="utf-8")
    payload = json.dumps(spec_dict).replace("<", "\\u003c")
    container = f"chartkit-{chart_id}"
    return (
        f'<div id="{container}"></div>\n'
        f"<script>\n{kernel}\n"
        f"ChartKit.render(document.getElementById({json.dumps(container)}), "
        f"{payload});\n"
        f"</script>"
    )


def render_chart_widget(
    chart_id: str,
    spec: dict[str, Any] | None = None,
    patch: dict[str, Any] | None = None,
    backend: Any | None = None,
) -> dict[str, Any]:
    """Create or update a chart widget.

    Args:
        chart_id: Stable identifier for the chart ([A-Za-z0-9_-], <=64).
        spec: Full chart spec (create / replace).
        patch: RFC 7386 merge patch against the stored spec (update).
        backend: Memory backend override for tests; resolved when None.

    Returns:
        {success, html, chart_id, persistence} on success;
        {success: False, error | problems} on failure — errors are
        phrased so the calling model can self-correct.

    """
    if not isinstance(chart_id, str) or not _CHART_ID_RE.match(chart_id):
        return {
            "success": False,
            "error": "chart_id must match [A-Za-z0-9_-]{1,64}",
        }
    if spec is None and patch is None:
        return {
            "success": False,
            "error": "Provide 'spec' (create/replace) or 'patch' (update).",
        }

    target = backend if backend is not None else _resolve_backend()
    key = _chart_key(chart_id)

    if spec is None and patch is not None:
        if target is None:
            return {"success": False, "error": BACKEND_DOWN_MSG}
        try:
            stored = target.retrieve(key)
        except Exception as exc:  # noqa: BLE001 — degrade legibly, but on the record
            logger.warning("chart spec retrieve failed for %s: %s", key, exc)
            stored = None
        if not isinstance(stored, dict):
            return {
                "success": False,
                "error": NO_STORED_SPEC_MSG.format(chart_id=chart_id),
            }
        spec = merge_patch(stored, patch)

    try:
        validated = validate_chart_spec(spec)
    except ChartSpecError as exc:
        return {"success": False, "problems": exc.problems}

    spec_dict = validated.model_dump(exclude_none=True)

    persistence = "unavailable — the next update must re-send the full spec"
    if target is not None:
        try:
            if target.stash(key, spec_dict, ttl=_TTL_SECONDS):
                persistence = "stored — next update may send a patch"
        except Exception as exc:  # noqa: BLE001 — best-effort, but on the record
            logger.warning("chart spec stash failed for %s: %s", key, exc)

    try:
        html = _build_html(chart_id, spec_dict)
    except FileNotFoundError as exc:
        return {"success": False, "error": str(exc)}

    return {
        "success": True,
        "chart_id": chart_id,
        "html": html,
        "persistence": persistence,
    }
