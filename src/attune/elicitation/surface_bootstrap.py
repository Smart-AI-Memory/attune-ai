"""Install the native runtime only after replaying its packaged evidence."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema.exceptions import SchemaError, ValidationError

if sys.version_info >= (3, 11):
    from builtins import ExceptionGroup
else:
    from exceptiongroup import ExceptionGroup

from attune.elicitation.surface_evidence import replay_renderer_evidence
from attune.elicitation.surface_key import load_installation_key
from attune.elicitation.surface_native_evidence import SUBJECT_ID, replay_native_evidence
from attune.elicitation.surface_policy import SurfaceContextStore
from attune.elicitation.surface_registry import (
    SurfaceRegistryError,
    route_evidence_missing,
    validate_inventory,
)
from attune.elicitation.surface_runtime import NATIVE_ROUTE, SurfaceFormRuntime


def packaged_inventory() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load immutable package projections, never paths supplied by tool arguments."""
    package = files("attune.elicitation")
    return tuple(
        json.loads(package.joinpath(name).read_text(encoding="utf-8"))
        for name in ("surface_runtime_registry.json", "surface_runtime_baseline.json")
    )


async def create_surface_runtime(attune_home: Path) -> SurfaceFormRuntime:
    """Verify current installed code and fixtures before installing any authority.

    The key and store are allocated last. Any missing, changed or failed receipt
    prevents activation. No cached report or caller-provided evidence is accepted.
    """
    registry, baseline = packaged_inventory()
    try:
        _, evidence = replay_renderer_evidence()
        _, native = await asyncio.wait_for(replay_native_evidence(registry), timeout=15)
    except (ExceptionGroup, SchemaError, ValidationError, StopIteration) as exc:
        raise SurfaceRegistryError(
            f"native evidence execution failed: {type(exc).__name__}"
        ) from exc
    evidence.update(native)
    report = validate_inventory(
        registry, baseline, evidence, today=datetime.now(timezone.utc).date()
    )
    missing = route_evidence_missing(registry, report, SUBJECT_ID, NATIVE_ROUTE)
    if missing:
        raise SurfaceRegistryError(f"native route evidence missing: {', '.join(sorted(missing))}")
    store = SurfaceContextStore(load_installation_key(attune_home))
    return SurfaceFormRuntime(store, registry, report, subject_id=SUBJECT_ID)
