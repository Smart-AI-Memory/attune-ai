"""File-based storage backend for long-term memory patterns

Provides simple file-based storage for MemDocs patterns.
Extracted from long_term.py for better modularity and testability.

In production, this can be replaced with actual MemDocs library integration
or other storage backends (Redis, PostgreSQL, etc.).

Key Features:
- JSON-based file storage
- Pattern storage with metadata
- Query support (by classification, creator)
- Path validation for security

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from pathlib import Path
from typing import Any

import structlog

from attune.security.path_validation import _validate_file_path

logger = structlog.get_logger(__name__)


def default_storage_dir() -> str:
    """Resolve the default long-term memory storage directory.

    Anchors to ``~/.attune/memdocs_storage`` so long-term patterns do not
    scatter across whatever directory a process happens to be launched
    from — a CWD-relative default silently splits (and appears to lose)
    memory when the same install is started from different projects.

    For backward compatibility, an existing ``memdocs_storage`` directory
    under the current working directory (the historical default location)
    is preferred so already-stored data is never stranded; its absolute
    path is returned so a later ``chdir`` cannot move the target.

    Returns:
        Absolute path string for the default storage directory.

    """
    legacy = Path.cwd() / "memdocs_storage"
    if legacy.is_dir():
        return str(legacy)
    try:
        home = Path.home()
    except (RuntimeError, OSError):
        # No resolvable home directory — e.g. a Windows account or CI env
        # with USERPROFILE/HOMEDRIVE unset (POSIX falls back to pwd; Windows
        # does not). Degrade to an absolute temp-based root so storage still
        # works and never silently reverts to a CWD-relative path.
        import tempfile

        home = Path(tempfile.gettempdir())
    return str(home / ".attune" / "memdocs_storage")


class MemDocsStorage:
    """Mock/Simple MemDocs storage backend.

    In production, this would integrate with the actual MemDocs library.
    For now, provides a simple file-based storage for testing.
    """

    def __init__(self, storage_dir: str | None = None):
        """Initialize storage backend.

        Args:
            storage_dir: Directory for pattern storage. When ``None``,
                resolves to :func:`default_storage_dir` (home-anchored,
                with a legacy-CWD fallback).

        """
        self.storage_dir = Path(storage_dir if storage_dir is not None else default_storage_dir())
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info("memdocs_storage_initialized", storage_dir=str(self.storage_dir))

    def store(self, pattern_id: str, content: str, metadata: dict[str, Any]) -> bool:
        """Store a pattern.

        Args:
            pattern_id: Unique pattern identifier
            content: Pattern content (may be encrypted)
            metadata: Pattern metadata

        Returns:
            True if successful

        Raises:
            IOError: If storage fails

        """
        try:
            pattern_file = self.storage_dir / f"{pattern_id}.json"

            # Ensure parent directory exists
            pattern_file.parent.mkdir(parents=True, exist_ok=True)

            pattern_data = {"pattern_id": pattern_id, "content": content, "metadata": metadata}

            validated_pattern_file = _validate_file_path(str(pattern_file))
            with open(validated_pattern_file, "w", encoding="utf-8") as f:
                json.dump(pattern_data, f, indent=2)

            logger.debug("pattern_stored", pattern_id=pattern_id)
            return True

        except (OSError, PermissionError, json.JSONDecodeError) as e:
            logger.error("pattern_storage_failed", pattern_id=pattern_id, error=str(e))
            raise

    def retrieve(self, pattern_id: str) -> dict[str, Any] | None:
        """Retrieve a pattern.

        Args:
            pattern_id: Unique pattern identifier

        Returns:
            Pattern data dictionary or None if not found

        """
        try:
            pattern_file = self.storage_dir / f"{pattern_id}.json"

            if not pattern_file.exists():
                logger.warning("pattern_not_found", pattern_id=pattern_id)
                return None

            with open(pattern_file, encoding="utf-8") as f:
                pattern_data: dict[str, Any] = json.load(f)

            logger.debug("pattern_retrieved", pattern_id=pattern_id)
            return pattern_data

        except (OSError, PermissionError, json.JSONDecodeError) as e:
            logger.error("pattern_retrieval_failed", pattern_id=pattern_id, error=str(e))
            return None

    def delete(self, pattern_id: str) -> bool:
        """Delete a pattern.

        Args:
            pattern_id: Unique pattern identifier

        Returns:
            True if deleted, False if not found

        """
        try:
            pattern_file = self.storage_dir / f"{pattern_id}.json"

            if not pattern_file.exists():
                return False

            pattern_file.unlink()
            logger.info("pattern_deleted", pattern_id=pattern_id)
            return True

        except (OSError, PermissionError) as e:
            logger.error("pattern_deletion_failed", pattern_id=pattern_id, error=str(e))
            return False

    def list_patterns(
        self,
        classification: str | None = None,
        created_by: str | None = None,
    ) -> list[str]:
        """List pattern IDs matching criteria.

        Args:
            classification: Filter by classification
            created_by: Filter by creator

        Returns:
            List of pattern IDs

        """
        pattern_ids = []

        for pattern_file in self.storage_dir.glob("*.json"):
            try:
                with open(pattern_file, encoding="utf-8") as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})

                    # Apply filters
                    if classification and metadata.get("classification") != classification:
                        continue
                    if created_by and metadata.get("created_by") != created_by:
                        continue

                    pattern_ids.append(data.get("pattern_id"))

            except Exception:  # noqa: BLE001
                continue

        return pattern_ids
