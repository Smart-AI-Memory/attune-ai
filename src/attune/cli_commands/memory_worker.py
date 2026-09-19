"""Lazy optional Harness memory route; existing memory commands are unchanged."""

from __future__ import annotations

import json
import os


def cmd_memory_worker(argv: list[str]) -> int:
    """Dispatch the explicit worker route without enabling product usage uploads."""
    os.environ["ATTUNE_USAGE_PING"] = "0"
    if os.environ.get("ATTUNE_MEMORY_WORKER") == "0":
        print(
            json.dumps({"status": "disabled", "detail": "Optional memory worker route is disabled"})
        )
        return 2
    try:
        from attune_harness.memory_cli import main
    except ImportError:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "detail": "Install optional Harness memory support (attune-ai[harness])",
                }
            )
        )
        return 2
    return main(argv)
