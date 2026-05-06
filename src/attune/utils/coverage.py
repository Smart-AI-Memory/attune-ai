"""Helpers for picking the right ``--cov=<target>`` argument per project.

Several agents and orchestrators run ``pytest --cov`` against arbitrary
projects, not just attune-ai itself. Hard-coding ``--cov=src`` (or the
attune-ai package list) makes those tools report 0% coverage on any
project that uses a different layout (e.g. ``sidecar/<pkg>``,
``packages/<pkg>``, or a flat top-level package).

:func:`detect_coverage_targets` reads ``pyproject.toml`` to pick a
sensible target list.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


def detect_coverage_targets(codebase_path: str | Path) -> list[str]:
    """Return one or more ``--cov`` arguments for ``codebase_path``.

    Heuristic, in priority order:

    1. ``[tool.coverage.run] source`` in ``pyproject.toml``.
    2. ``[tool.hatch.build.targets.wheel] packages`` (covers projects that
       ship from a non-``src/`` layout, e.g. attune-gui's ``sidecar/attune_gui``).
    3. The package name from ``[project] name`` if a directory of the same
       name (or its dashes-to-underscores form) exists under ``src/`` or at
       the root.
    4. Fall back to ``["src"]`` for the conventional layout.

    The return value is always a non-empty list so callers can iterate.
    """
    root = Path(codebase_path)
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return ["src"]
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ["src"]

    cov_run = data.get("tool", {}).get("coverage", {}).get("run", {})
    sources = cov_run.get("source") or cov_run.get("source_pkgs")
    if isinstance(sources, list) and sources:
        return [str(s) for s in sources]

    hatch_packages = (
        data.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages")
    )
    if isinstance(hatch_packages, list) and hatch_packages:
        return [str(p) for p in hatch_packages]

    name = data.get("project", {}).get("name")
    if isinstance(name, str) and name:
        for candidate in (name, name.replace("-", "_")):
            if (root / "src" / candidate).is_dir():
                return [f"src/{candidate}"]
            if (root / candidate).is_dir():
                return [candidate]

    return ["src"]


def detect_coverage_target(codebase_path: str | Path) -> str:
    """Convenience wrapper for callers that only want one target."""
    return detect_coverage_targets(codebase_path)[0]
