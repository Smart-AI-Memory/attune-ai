"""Persistent Storage for Socratic Sessions and Blueprints

Provides multiple storage backends for persisting:
- Socratic sessions (in-progress and completed)
- Workflow blueprints (generated workflows)
- Success metrics history (for feedback loop)

Backends:
- JSONFileStorage: Simple file-based storage (default)
- SQLiteStorage: SQLite database for better querying
- RedisStorage: Redis for distributed/production use

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import heapq
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

from .blueprint import WorkflowBlueprint
from .session import SessionState, SocraticSession
from .success import SuccessEvaluation

logger = logging.getLogger(__name__)


# =============================================================================
# STORAGE INTERFACE
# =============================================================================


class StorageBackend(ABC):
    """Abstract base for storage backends."""

    @abstractmethod
    def save_session(self, session: SocraticSession) -> None:
        """Save a Socratic session."""

    @abstractmethod
    def load_session(self, session_id: str) -> SocraticSession | None:
        """Load a session by ID."""

    @abstractmethod
    def list_sessions(
        self,
        state: SessionState | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions with optional filtering."""

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""

    @abstractmethod
    def save_blueprint(self, blueprint: WorkflowBlueprint) -> None:
        """Save a workflow blueprint."""

    @abstractmethod
    def load_blueprint(self, blueprint_id: str) -> WorkflowBlueprint | None:
        """Load a blueprint by ID."""

    @abstractmethod
    def list_blueprints(
        self,
        domain: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List blueprints with optional filtering."""

    @abstractmethod
    def save_evaluation(
        self,
        blueprint_id: str,
        evaluation: SuccessEvaluation,
    ) -> None:
        """Save a success evaluation for a blueprint."""

    @abstractmethod
    def get_evaluations(
        self,
        blueprint_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get evaluation history for a blueprint."""


# =============================================================================
# JSON FILE STORAGE
# =============================================================================


class JSONFileStorage(StorageBackend):
    """File-based JSON storage.

    Structure:
        base_dir/
            sessions/
                {session_id}.json
            blueprints/
                {blueprint_id}.json
            evaluations/
                {blueprint_id}/
                    {timestamp}.json

    Example:
        >>> storage = JSONFileStorage(".attune/socratic")
        >>> storage.save_session(session)
        >>> loaded = storage.load_session(session.session_id)
    """

    def __init__(self, base_dir: str = ".attune/socratic"):
        """Initialize storage.

        Args:
            base_dir: Base directory for storage
        """
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "sessions"
        self.blueprints_dir = self.base_dir / "blueprints"
        self.evaluations_dir = self.base_dir / "evaluations"

        # Create directories
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.blueprints_dir.mkdir(parents=True, exist_ok=True)
        self.evaluations_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: SocraticSession) -> None:
        """Save a session to JSON file."""
        path = self.sessions_dir / f"{session.session_id}.json"
        data = session.to_dict()

        validated_path = _validate_file_path(str(path))
        with validated_path.open("w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"Saved session {session.session_id}")

    def load_session(self, session_id: str) -> SocraticSession | None:
        """Load a session from JSON file."""
        path = self.sessions_dir / f"{session_id}.json"

        if not path.exists():
            return None

        try:
            with path.open() as f:
                data = json.load(f)
            return SocraticSession.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def list_sessions(
        self,
        state: SessionState | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions with optional state filter."""
        sessions = []

        for path in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            if len(sessions) >= limit:
                break

            try:
                with path.open() as f:
                    data = json.load(f)

                # Filter by state if specified
                if state and data.get("state") != state.value:
                    continue

                sessions.append(
                    {
                        "session_id": data.get("session_id"),
                        "state": data.get("state"),
                        "goal": data.get("goal", "")[:100],
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file."""
        path = self.sessions_dir / f"{session_id}.json"

        if path.exists():
            path.unlink()
            return True
        return False

    def save_blueprint(self, blueprint: WorkflowBlueprint) -> None:
        """Save a blueprint to JSON file."""
        path = self.blueprints_dir / f"{blueprint.id}.json"
        data = blueprint.to_dict()

        validated_path = _validate_file_path(str(path))
        with validated_path.open("w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"Saved blueprint {blueprint.id}")

    def load_blueprint(self, blueprint_id: str) -> WorkflowBlueprint | None:
        """Load a blueprint from JSON file."""
        path = self.blueprints_dir / f"{blueprint_id}.json"

        if not path.exists():
            return None

        try:
            with path.open() as f:
                data = json.load(f)
            return WorkflowBlueprint.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load blueprint {blueprint_id}: {e}")
            return None

    def list_blueprints(
        self,
        domain: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List blueprints with optional domain filter."""
        blueprints = []

        for path in sorted(self.blueprints_dir.glob("*.json"), reverse=True):
            if len(blueprints) >= limit:
                break

            try:
                with path.open() as f:
                    data = json.load(f)

                # Filter by domain if specified
                if domain and data.get("domain") != domain:
                    continue

                blueprints.append(
                    {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "domain": data.get("domain"),
                        "agents_count": len(data.get("agents", [])),
                        "generated_at": data.get("generated_at"),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        return blueprints

    def save_evaluation(
        self,
        blueprint_id: str,
        evaluation: SuccessEvaluation,
    ) -> None:
        """Save an evaluation to JSON file."""
        eval_dir = self.evaluations_dir / blueprint_id
        eval_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = eval_dir / f"{timestamp}.json"

        data = evaluation.to_dict()
        validated_path = _validate_file_path(str(path))
        with validated_path.open("w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_evaluations(
        self,
        blueprint_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get evaluation history for a blueprint."""
        eval_dir = self.evaluations_dir / blueprint_id

        if not eval_dir.exists():
            return []

        evaluations = []
        for path in heapq.nlargest(limit, eval_dir.glob("*.json")):
            try:
                with path.open() as f:
                    evaluations.append(json.load(f))
            except json.JSONDecodeError:
                continue

        return evaluations


# =============================================================================
# SQLITE STORAGE (extracted to sqlite_storage.py)
# =============================================================================

from .sqlite_storage import SQLiteStorage  # noqa: E402, F401 - re-exported

# =============================================================================
# STORAGE MANAGER
# =============================================================================


@dataclass
class StorageConfig:
    """Storage configuration."""

    backend: str = "json"  # json, sqlite, redis
    path: str = ".attune/socratic"
    redis_url: str | None = None


class StorageManager:
    """Manages storage backend lifecycle.

    Example:
        >>> manager = StorageManager(StorageConfig(backend="sqlite"))
        >>> storage = manager.get_storage()
        >>> storage.save_session(session)
    """

    def __init__(self, config: StorageConfig | None = None):
        """Initialize manager.

        Args:
            config: Storage configuration
        """
        self.config = config or StorageConfig()
        self._storage: StorageBackend | None = None

    def get_storage(self) -> StorageBackend:
        """Get or create storage backend."""
        if self._storage is None:
            self._storage = self._create_storage()
        return self._storage

    def _create_storage(self) -> StorageBackend:
        """Create storage backend based on config."""
        if self.config.backend == "sqlite":
            return SQLiteStorage(f"{self.config.path}.db")
        elif self.config.backend == "redis":
            # Redis would be implemented separately
            logger.warning("Redis storage not implemented, using JSON")
            return JSONFileStorage(self.config.path)
        else:
            return JSONFileStorage(self.config.path)


# Default storage instance
_default_storage: StorageBackend | None = None


def get_default_storage() -> StorageBackend:
    """Get the default storage backend."""
    global _default_storage
    if _default_storage is None:
        _default_storage = JSONFileStorage()
    return _default_storage


def set_default_storage(storage: StorageBackend) -> None:
    """Set the default storage backend."""
    global _default_storage
    _default_storage = storage
