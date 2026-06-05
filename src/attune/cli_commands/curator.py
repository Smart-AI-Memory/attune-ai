"""``attune curator`` — terminal rendering of the project briefing.

Consumes the same :class:`attune.curator.CuratorResult` the dashboard
``/curator`` page renders, so both surfaces stay in lockstep. Flags:
``--refresh`` (bypass cache), ``--json`` (machine-readable),
``--max-items N``.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from pathlib import Path
from typing import Any

from attune.curator import run_curator

logger = logging.getLogger(__name__)


def _result_to_dict(result: Any) -> dict[str, Any]:
    """JSON-serializable view of a CuratorResult (datetime → isoformat)."""
    data = dataclasses.asdict(result)
    cached_at = data.get("cached_at")
    if cached_at is not None and not isinstance(cached_at, str):
        data["cached_at"] = cached_at.isoformat()
    return data


def _render(result: Any) -> None:
    """Print the briefing as plain text (no rich dependency)."""
    header = "Briefing"
    if result.model:
        header += f" ({result.model})"
    if result.cost_usd:
        header += f" — ${result.cost_usd:.4f}"
    print(header)
    print()
    if result.summary:
        print(result.summary)
        print()

    if not result.items:
        print("Nothing pressing right now — no items rank above noise.")
        return

    for idx, item in enumerate(result.items, 1):
        print(f"  {idx} [{item.severity}] {item.title}")
        if item.rationale:
            print(f"    {item.rationale}")
        if item.sources:
            print(f"    Sources: {', '.join(item.sources)}")
        action = item.suggested_action
        if action is not None:
            print(f"    Suggest: {_action_hint(action)}")
        print()


def _action_hint(action: Any) -> str:
    if action.kind == "open" and action.url:
        return f"open {action.url}"
    if action.kind == "ask" and action.question:
        choices = f" [{'/'.join(action.choices)}]" if action.choices else ""
        return f"{action.question}{choices}"
    if action.kind == "run" and action.workflow:
        scope = f" on {action.scope}" if action.scope else ""
        return f"run {action.workflow}{scope}"
    if action.kind == "dismiss":
        return "snooze"
    return action.label or action.kind


def cmd_curator(args: Any) -> int:
    """Render the curator briefing for the current project."""
    project_root = Path.cwd()
    result = asyncio.run(
        run_curator(
            project_root=project_root,
            force_refresh=getattr(args, "refresh", False),
            max_items=getattr(args, "max_items", 5),
        )
    )

    if getattr(args, "json", False):
        print(json.dumps(_result_to_dict(result), indent=2))
        return 0

    _render(result)
    return 0
