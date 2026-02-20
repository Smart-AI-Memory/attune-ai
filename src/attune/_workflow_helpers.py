"""Shared helpers for One-Command Workflows.

Utility functions used across morning, ship, fix-all, and learn workflows:
- Pattern loading from JSON files
- Stats persistence (load/save)
- Shell command execution
- Tech debt trend analysis

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from attune.config import _validate_file_path
from attune.logging_config import get_logger

logger = get_logger(__name__)


def _load_patterns(patterns_dir: str = "./patterns") -> dict[str, list]:
    """Load patterns from the patterns directory."""
    patterns: dict[str, list] = {"debugging": [], "security": [], "tech_debt": [], "inspection": []}

    patterns_path = Path(patterns_dir)
    if not patterns_path.exists():
        return patterns

    for pattern_type in patterns:
        file_path = patterns_path / f"{pattern_type}.json"
        if file_path.exists():
            try:
                validated_path = _validate_file_path(str(file_path))
                with open(validated_path) as f:
                    data = json.load(f)
                    patterns[pattern_type] = data.get("patterns", data.get("items", []))
            except (OSError, json.JSONDecodeError, ValueError):
                pass

    return patterns


def _load_stats(empathy_dir: str = ".attune") -> dict[str, Any]:
    """Load usage statistics."""
    stats_file = Path(empathy_dir) / "stats.json"
    if stats_file.exists():
        try:
            validated_path = _validate_file_path(str(stats_file))
            with open(validated_path) as f:
                result: dict[str, Any] = json.load(f)
                return result
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    return {"commands": {}, "last_session": None, "patterns_learned": 0}


def _save_stats(stats: dict, empathy_dir: str = ".attune") -> None:
    """Save usage statistics."""
    stats_dir = Path(empathy_dir)
    stats_dir.mkdir(parents=True, exist_ok=True)

    validated_path = _validate_file_path(str(stats_dir / "stats.json"))
    with open(validated_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)


def _run_command(cmd: list, capture: bool = True) -> tuple:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(cmd, check=False, capture_output=capture, text=True, timeout=300)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except Exception as e:
        return False, str(e)


def _get_tech_debt_trend(patterns_dir: str = "./patterns") -> str:
    """Analyze tech debt trajectory."""
    tech_debt_file = Path(patterns_dir) / "tech_debt.json"
    if not tech_debt_file.exists():
        return "unknown"

    try:
        validated_path = _validate_file_path(str(tech_debt_file))
        with open(validated_path) as f:
            data = json.load(f)

        snapshots = data.get("snapshots", [])
        if len(snapshots) < 2:
            return "insufficient_data"

        recent = snapshots[-1].get("total_items", 0)
        previous = snapshots[-2].get("total_items", 0)

        if recent > previous:
            return "increasing"
        if recent < previous:
            return "decreasing"
        return "stable"
    except (OSError, json.JSONDecodeError, KeyError):
        return "unknown"
