"""Persistent storage for dynamic team specifications.

Provides CRUD operations for team configurations that can be loaded
and executed by ``DynamicTeamBuilder``.

File structure::

    .attune/orchestration/teams/
    ├── release-team.json
    ├── security-deep-dive.json
    └── custom-analysis.json

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _validate_team_path(path: str, allowed_dir: str) -> Path:
    """Validate that a file path is within the allowed directory.

    Args:
        path: File path to validate.
        allowed_dir: Directory to restrict writes to.

    Returns:
        Validated, resolved Path object.

    Raises:
        ValueError: If path is invalid or outside allowed_dir.

    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")
    if "\x00" in path:
        raise ValueError("path contains null bytes")

    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")

    try:
        allowed = Path(allowed_dir).resolve()
        resolved.relative_to(allowed)
    except ValueError:
        raise ValueError(f"path must be within {allowed_dir}")

    return resolved


def _sanitize_team_name(name: str) -> str:
    """Sanitize a team name for safe filesystem use.

    Args:
        name: Raw team name.

    Returns:
        Filesystem-safe name string.

    Raises:
        ValueError: If name is empty or contains null bytes.

    """
    if not name or not isinstance(name, str):
        raise ValueError("name must be a non-empty string")
    if "\x00" in name:
        raise ValueError("name contains null bytes")

    import re

    sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return sanitized[:200]


# ---------------------------------------------------------------------------
# Team specification dataclass
# ---------------------------------------------------------------------------


@dataclass
class TeamSpecification:
    """Specification for a dynamic agent team.

    Args:
        name: Human-readable team name.
        agents: List of agent configs (template_id, role, tier, tools).
        strategy: Execution strategy (parallel, sequential, two_phase, delegation).
        quality_gates: Dict of gate definitions.
        phases: Optional phase definitions for multi-phase strategies.
        description: Human-readable description.
        tags: Searchable tags.

    """

    name: str
    agents: list[dict[str, Any]]
    strategy: str = "parallel"
    quality_gates: dict[str, Any] = field(default_factory=dict)
    phases: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)

    ALLOWED_STRATEGIES = {"parallel", "sequential", "two_phase", "delegation"}

    def __post_init__(self) -> None:
        """Validate specification fields."""
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.agents:
            raise ValueError("agents list must not be empty")
        if self.strategy not in self.ALLOWED_STRATEGIES:
            raise ValueError(
                f"strategy must be one of {self.ALLOWED_STRATEGIES}, got '{self.strategy}'",
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict.

        Returns:
            Dict representation.

        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamSpecification:
        """Deserialize from a dict.

        Args:
            data: Dict previously produced by ``to_dict()``.

        Returns:
            Reconstructed TeamSpecification.

        """
        # Remove ALLOWED_STRATEGIES if accidentally serialized
        data = {k: v for k, v in data.items() if k != "ALLOWED_STRATEGIES"}
        return cls(**data)


# ---------------------------------------------------------------------------
# Team store
# ---------------------------------------------------------------------------


class TeamStore:
    """Persistent storage for team specifications.

    Args:
        storage_dir: Directory for team JSON files.
            Defaults to ``.attune/orchestration/teams``.

    """

    DEFAULT_DIR = ".attune/orchestration/teams"

    def __init__(self, storage_dir: str | None = None) -> None:
        """Initialize TeamStore with a storage directory.

        Args:
            storage_dir: Directory for team spec JSON files.
                Defaults to ``.attune/orchestration/teams``.

        """
        self._storage_dir = storage_dir or self.DEFAULT_DIR
        self._dir = Path(self._storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, TeamSpecification] = {}

    def save(self, spec: TeamSpecification) -> Path:
        """Save a team specification to disk.

        Args:
            spec: Specification to save.

        Returns:
            Path to the saved JSON file.

        """
        safe_name = _sanitize_team_name(spec.name)
        file_path = self._dir / f"{safe_name}.json"
        validated = _validate_team_path(str(file_path), self._storage_dir)

        with validated.open("w") as f:
            json.dump(spec.to_dict(), f, indent=2)

        self._cache[spec.name] = spec
        logger.info(f"Saved team spec '{spec.name}' to {validated}")
        return validated

    def load(self, name: str) -> TeamSpecification | None:
        """Load a team specification by name.

        Args:
            name: Team name.

        Returns:
            Specification if found, None otherwise.

        """
        if name in self._cache:
            return self._cache[name]

        safe_name = _sanitize_team_name(name)
        file_path = self._dir / f"{safe_name}.json"
        if not file_path.exists():
            return None

        try:
            with file_path.open("r") as f:
                data = json.load(f)
            spec = TeamSpecification.from_dict(data)
            self._cache[name] = spec
            return spec
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to load team spec '{name}': {e}")
            return None

    def list_all(self) -> list[TeamSpecification]:
        """List all saved team specifications.

        Returns:
            List of all specifications.

        """
        specs: list[TeamSpecification] = []
        for json_file in sorted(self._dir.glob("*.json")):
            try:
                with json_file.open("r") as f:
                    data = json.load(f)
                specs.append(TeamSpecification.from_dict(data))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                logger.warning(f"Skipping corrupt file {json_file}: {e}")
        return specs

    def delete(self, name: str) -> bool:
        """Delete a team specification.

        Args:
            name: Team name to delete.

        Returns:
            True if deleted, False if not found.

        """
        safe_name = _sanitize_team_name(name)
        file_path = self._dir / f"{safe_name}.json"

        self._cache.pop(name, None)

        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted team spec '{name}'")
            return True
        return False
