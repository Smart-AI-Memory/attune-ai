"""Spec reader for pipeline plan files.

Reads ``.claude/plans/*.md`` files and extracts XML
``<task>`` blocks into ``DecomposedTask`` objects.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from pathlib import Path

from attune.wizards.decomposer import DecomposedTask, TaskDecomposer

logger = logging.getLogger(__name__)


def read_spec(plan_path: str) -> list[DecomposedTask]:
    """Read a plan file and extract XML task blocks.

    Args:
        plan_path: Path to a markdown plan file containing
            XML ``<task>`` elements.

    Returns:
        Ordered list of ``DecomposedTask`` objects. Returns
        an empty list if the file has no ``<task>`` elements.

    Raises:
        FileNotFoundError: If plan_path does not exist.
        ValueError: If plan_path is empty.

    """
    if not plan_path:
        raise ValueError("plan_path must be a non-empty string")

    path = Path(plan_path)
    if not path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    content = path.read_text(encoding="utf-8")

    # Use the existing XML parser from TaskDecomposer.
    # The parser is an instance method but uses no instance state
    # beyond helper methods, so we create a minimal instance.
    parser = TaskDecomposer(workflow=None)
    tasks = parser._parse_tasks_from_xml(content)

    logger.info(
        "Read %d tasks from %s",
        len(tasks),
        plan_path,
    )
    return tasks
