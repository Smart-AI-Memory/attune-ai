#!/usr/bin/env python3
"""Project the reviewed registry/baseline into the wheel; refresh executed receipts."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from attune.elicitation.surface_evidence import replay_renderer_evidence
from attune.elicitation.surface_native_evidence import replay_native_evidence
from attune.elicitation.surface_registry import validate_inventory
from attune.security.path_validation import _validate_file_path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/host-surface-parity"
PACKAGE = ROOT / "src/attune/elicitation"


def _text(value: dict) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


async def project(*, write: bool = False) -> None:
    """Replay before projecting; check mode never changes source or package files."""
    registry_path = SPEC / "parity-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    baseline = json.loads((SPEC / "producer_baseline.json").read_text(encoding="utf-8"))
    declarations, evidence = replay_renderer_evidence()
    native, native_evidence = await replay_native_evidence(registry)
    declarations.extend(native)
    evidence.update(native_evidence)
    if write:
        refreshed = {row["key"]: row for row in declarations}
        retained = [row for row in registry["receipts"] if row["key"] not in refreshed]
        registry["receipts"] = sorted(retained + declarations, key=lambda row: row["key"])
        registry["pending_obligations"] = [
            row for row in registry["pending_obligations"] if row["key"] not in refreshed
        ]
    validate_inventory(registry, baseline, evidence, today=datetime.now(timezone.utc).date())
    projections = {
        registry_path: _text(registry),
        PACKAGE / "surface_runtime_registry.json": _text(registry),
        PACKAGE / "surface_runtime_baseline.json": _text(baseline),
    }
    for path, expected in projections.items():
        if write:
            _validate_file_path(str(path), str(ROOT)).write_text(expected, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != expected:
            raise ValueError(f"stale runtime projection: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    asyncio.run(project(write=parser.parse_args().write))
