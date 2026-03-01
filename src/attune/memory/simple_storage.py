"""Simplified long-term storage without security pipeline

Provides basic CRUD operations for long-term persistent storage without
the full security pipeline of SecureMemDocsIntegration. Suitable for
simple storage needs where PII scrubbing and encryption are not required.

Extracted from long_term.py for better modularity and testability.

Features:
- JSON file-based storage
- Classification support (PUBLIC/INTERNAL/SENSITIVE)
- Simple key-value interface
- List keys by classification
- Path validation for security

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from attune.security.path_validation import _validate_file_path

from .long_term_types import Classification

logger = structlog.get_logger(__name__)


class LongTermMemory:
    """Simplified long-term persistent storage interface.

    Provides basic CRUD operations for long-term memory storage without
    the full security pipeline of SecureMemDocsIntegration. Suitable for
    simple persistent storage needs where PII scrubbing and encryption
    are not required.

    Features:
    - JSON file-based storage
    - Classification support (PUBLIC/INTERNAL/SENSITIVE)
    - Simple key-value interface
    - List keys by classification

    Example:
        >>> memory = LongTermMemory(storage_path="./data")
        >>> memory.store("config", {"setting": "value"}, classification="INTERNAL")
        >>> data = memory.retrieve("config")
        >>> keys = memory.list_keys(classification="INTERNAL")

    Note:
        For enterprise features (PII scrubbing, encryption, audit logging),
        use SecureMemDocsIntegration instead.

    """

    def __init__(self, storage_path: str = "./long_term_storage"):
        """Initialize long-term memory storage.

        Args:
            storage_path: Directory path for JSON storage

        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info("long_term_memory_initialized", storage_path=str(self.storage_path))

    def store(
        self,
        key: str,
        data: Any,
        classification: str | Classification | None = None,
    ) -> bool:
        """Store data in long-term memory.

        Args:
            key: Storage key
            data: Data to store (must be JSON-serializable)
            classification: Data classification (PUBLIC/INTERNAL/SENSITIVE)

        Returns:
            True if stored successfully, False otherwise

        Raises:
            ValueError: If key is empty or data is not JSON-serializable
            TypeError: If data cannot be serialized to JSON

        Example:
            >>> memory = LongTermMemory()
            >>> memory.store("user_prefs", {"theme": "dark"}, "INTERNAL")
            True

        """
        if not key or not key.strip():
            raise ValueError(f"key cannot be empty. Got: {key!r}")

        # Validate key for path traversal attacks
        if ".." in key or key.startswith("/") or "\x00" in key:
            logger.error("path_traversal_attempt", key=key)
            return False

        try:
            # Convert classification to string
            classification_str = "INTERNAL"  # Default
            if classification is not None:
                if isinstance(classification, Classification):
                    classification_str = classification.value
                elif isinstance(classification, str):
                    # Validate classification string
                    try:
                        Classification[classification.upper()]
                        classification_str = classification.upper()
                    except KeyError:
                        logger.warning(
                            "invalid_classification",
                            classification=classification,
                            using_default="INTERNAL",
                        )

            # Create storage record
            record = {
                "key": key,
                "data": data,
                "classification": classification_str,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }

            # Store to JSON file
            file_path = self.storage_path / f"{key}.json"
            validated_file_path = _validate_file_path(str(file_path))
            with validated_file_path.open("w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)

            logger.debug("data_stored", key=key, classification=classification_str)
            return True

        except (TypeError, ValueError) as e:
            logger.error("store_failed", key=key, error=str(e))
            raise
        except (OSError, PermissionError) as e:
            logger.error("storage_io_error", key=key, error=str(e))
            return False

    def retrieve(self, key: str) -> Any | None:
        """Retrieve data from long-term memory.

        Args:
            key: Storage key

        Returns:
            Stored data or None if not found

        Raises:
            ValueError: If key is empty

        Example:
            >>> memory = LongTermMemory()
            >>> memory.store("config", {"value": 42})
            >>> data = memory.retrieve("config")
            >>> print(data["value"])
            42

        """
        if not key or not key.strip():
            raise ValueError(f"key cannot be empty. Got: {key!r}")

        try:
            file_path = self.storage_path / f"{key}.json"

            if not file_path.exists():
                logger.debug("key_not_found", key=key)
                return None

            with file_path.open(encoding="utf-8") as f:
                record = json.load(f)

            logger.debug("data_retrieved", key=key)
            return record.get("data")

        except (OSError, PermissionError, json.JSONDecodeError) as e:
            logger.error("retrieve_failed", key=key, error=str(e))
            return None

    def delete(self, key: str) -> bool:
        """Delete data from long-term memory.

        Args:
            key: Storage key

        Returns:
            True if deleted, False if not found or error

        Raises:
            ValueError: If key is empty

        Example:
            >>> memory = LongTermMemory()
            >>> memory.store("temp", {"data": "value"})
            >>> memory.delete("temp")
            True

        """
        if not key or not key.strip():
            raise ValueError(f"key cannot be empty. Got: {key!r}")

        try:
            file_path = self.storage_path / f"{key}.json"

            if not file_path.exists():
                logger.debug("key_not_found_for_deletion", key=key)
                return False

            file_path.unlink()
            logger.info("data_deleted", key=key)
            return True

        except (OSError, PermissionError) as e:
            logger.error("delete_failed", key=key, error=str(e))
            return False

    def list_keys(self, classification: str | Classification | None = None) -> list[str]:
        """List all keys in long-term memory, optionally filtered by classification.

        Args:
            classification: Filter by classification (PUBLIC/INTERNAL/SENSITIVE)

        Returns:
            List of storage keys

        Example:
            >>> memory = LongTermMemory()
            >>> memory.store("public_data", {"x": 1}, "PUBLIC")
            >>> memory.store("internal_data", {"y": 2}, "INTERNAL")
            >>> keys = memory.list_keys(classification="PUBLIC")
            >>> print(keys)
            ['public_data']

        """
        keys = []

        # Convert classification to string if needed
        filter_classification = None
        if classification is not None:
            if isinstance(classification, Classification):
                filter_classification = classification.value
            elif isinstance(classification, str):
                try:
                    Classification[classification.upper()]
                    filter_classification = classification.upper()
                except KeyError:
                    logger.warning("invalid_classification_filter", classification=classification)
                    return []

        try:
            for file_path in self.storage_path.glob("*.json"):
                try:
                    with file_path.open(encoding="utf-8") as f:
                        record = json.load(f)

                    # Apply classification filter if specified
                    if filter_classification is not None:
                        if record.get("classification") != filter_classification:
                            continue

                    keys.append(record.get("key", file_path.stem))

                except (OSError, json.JSONDecodeError):
                    continue

        except (OSError, PermissionError) as e:
            logger.error("list_keys_failed", error=str(e))

        return keys

    def clear(self) -> int:
        """Clear all data from long-term memory.

        Returns:
            Number of keys deleted

        Warning:
            This operation cannot be undone!

        """
        count = 0
        try:
            for file_path in self.storage_path.glob("*.json"):
                try:
                    file_path.unlink()
                    count += 1
                except (OSError, PermissionError):
                    continue

            logger.warning("long_term_memory_cleared", count=count)
            return count

        except (OSError, PermissionError) as e:
            logger.error("clear_failed", error=str(e))
            return count
