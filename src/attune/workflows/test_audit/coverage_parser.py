"""Coverage JSON parser for TestAuditWorkflow.

Parses pytest-cov's coverage.json output and prioritizes
modules by test gap size.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModuleCoverage:
    """Coverage data for a single module.

    Attributes:
        path: File path of the module.
        stmts: Total number of statements.
        covered: Number of covered statements.
        missing_lines: Line numbers not covered by tests.
        pct: Coverage percentage (0-100).
        priority: Priority score for test generation.
            Higher = more urgent. Computed as
            ``(1 - pct / 100) * stmts``.

    """

    path: str
    stmts: int
    covered: int
    missing_lines: list[int] = field(default_factory=list)
    pct: float = 0.0
    priority: float = 0.0


def parse_coverage_json(json_path: str) -> list[ModuleCoverage]:
    """Parse pytest-cov's coverage.json output.

    Expects the standard pytest-cov JSON format:
    ``{"files": {"path": {"summary": {"num_statements": N,
    "covered_lines": N, "missing_lines": [...]}}}}``

    Args:
        json_path: Path to the coverage.json file.

    Returns:
        List of ModuleCoverage objects, one per file.

    Raises:
        FileNotFoundError: If json_path does not exist.
        ValueError: If json_path cannot be parsed as
            valid coverage JSON.

    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Coverage file not found: {json_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid coverage JSON at {json_path}: {exc}") from exc

    if not isinstance(data, dict):
        # The docstring promises ValueError for invalid coverage JSON;
        # without this a non-object file raised AttributeError from the
        # .get below instead (library-review C3).
        raise ValueError(
            f"Unexpected coverage JSON structure in {json_path}: "
            f"expected an object, got {type(data).__name__}"
        )

    files = data.get("files", {})
    if not isinstance(files, dict):
        raise ValueError(
            f"Unexpected coverage JSON structure in {json_path}: "
            "'files' key missing or not a dict"
        )

    modules: list[ModuleCoverage] = []
    for file_path, file_data in files.items():
        summary = file_data.get("summary", {})
        stmts = summary.get("num_statements", 0)
        covered = summary.get("covered_lines", 0)
        missing_lines = file_data.get("missing_lines", [])

        if stmts == 0:
            pct = 100.0
        else:
            pct = (covered / stmts) * 100.0

        priority = (1.0 - pct / 100.0) * stmts

        modules.append(
            ModuleCoverage(
                path=file_path,
                stmts=stmts,
                covered=covered,
                missing_lines=list(missing_lines),
                pct=round(pct, 2),
                priority=round(priority, 2),
            )
        )

    return modules


def prioritize_modules(
    modules: list[ModuleCoverage],
    min_threshold: float = 50.0,
) -> list[ModuleCoverage]:
    """Sort modules by priority and filter below threshold.

    Modules with coverage above ``min_threshold`` percent are
    excluded. The remaining modules are sorted by priority
    score descending: ``(1 - pct/100) * stmts``.

    Args:
        modules: List of ModuleCoverage objects.
        min_threshold: Minimum coverage percentage. Modules below
            this threshold are included; modules at or above are
            excluded. Default: 50.0.

    Returns:
        Sorted list of ModuleCoverage objects below threshold,
        highest priority first.

    """
    candidates = [m for m in modules if m.pct < min_threshold]
    candidates.sort(key=lambda m: m.priority, reverse=True)
    return candidates


def group_into_batches(
    modules: list[ModuleCoverage],
    max_batches: int = 5,
) -> list[dict]:
    """Group modules into batches by subsystem (package path).

    Modules sharing the same immediate parent package are
    grouped together. If the number of distinct subsystems
    exceeds ``max_batches``, smaller subsystems are merged
    into the last batch.

    Args:
        modules: Prioritized list of ModuleCoverage objects.
        max_batches: Maximum number of batches to produce.

    Returns:
        List of batch dicts, each with keys:
        - ``batch_id``: str, e.g. ``"batch_0"``
        - ``subsystem``: str, the package prefix
        - ``modules``: list of ModuleCoverage objects

    """
    if not modules:
        return []

    # Group by immediate parent package
    groups: dict[str, list[ModuleCoverage]] = {}
    for module in modules:
        parts = module.path.replace("\\", "/").split("/")
        # Use up to the second-to-last component as the subsystem key
        if len(parts) >= 2:
            subsystem = "/".join(parts[:-1])
        else:
            subsystem = parts[0] if parts else "root"
        groups.setdefault(subsystem, []).append(module)

    # Sort subsystems by total priority descending
    sorted_subsystems = sorted(
        groups.items(),
        key=lambda kv: sum(m.priority for m in kv[1]),
        reverse=True,
    )

    batches: list[dict] = []
    for i, (subsystem, group_modules) in enumerate(sorted_subsystems):
        if i < max_batches - 1:
            batches.append(
                {
                    "batch_id": f"batch_{i}",
                    "subsystem": subsystem,
                    "modules": group_modules,
                }
            )
        else:
            # Merge remaining subsystems into the last batch
            if len(batches) < max_batches:
                batches.append(
                    {
                        "batch_id": f"batch_{i}",
                        "subsystem": "other",
                        "modules": group_modules,
                    }
                )
            else:
                batches[-1]["modules"].extend(group_modules)

    return batches
