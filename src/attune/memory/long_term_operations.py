"""Pattern management operations for SecureMemDocsIntegration.

Contains the PatternOperationsMixin class which provides list, delete,
and statistics operations for secure pattern management. These operations
are used by SecureMemDocsIntegration via mixin inheritance.

Extracted from long_term_integration.py for modularity.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from .long_term_classification import check_access
from .long_term_types import (
    Classification,
    PermissionError,
)
from .security.audit_logger import AuditEvent

if TYPE_CHECKING:
    from .security.audit_logger import AuditLogger
    from .storage_backend import MemDocsStorage

logger = structlog.get_logger(__name__)


class PatternOperationsMixin:
    """Mixin providing pattern list, delete, and statistics operations.

    Requires the host class to provide:
    - self.storage: MemDocsStorage instance
    - self.audit_logger: AuditLogger instance
    - self._check_access(user_id, classification, metadata) -> bool

    """

    storage: MemDocsStorage
    audit_logger: AuditLogger

    def _check_access(
        self,
        user_id: str,
        classification: Classification,
        metadata: dict[str, Any],
    ) -> bool:
        """Check access (provided by host class)."""
        return check_access(user_id, classification, metadata)

    def list_patterns(
        self,
        user_id: str,
        classification: Classification | None = None,
        pattern_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List patterns accessible to user.

        Args:
            user_id: User listing patterns
            classification: Filter by classification
            pattern_type: Filter by pattern type

        Returns:
            List of pattern summaries

        """
        all_pattern_ids = self.storage.list_patterns()
        accessible_patterns = []

        for pattern_id in all_pattern_ids:
            try:
                pattern_data = self.storage.retrieve(pattern_id)
                if not pattern_data:
                    continue

                metadata = pattern_data["metadata"]
                pat_classification = Classification[metadata["classification"]]

                if classification and pat_classification != classification:
                    continue

                if pattern_type and metadata.get("pattern_type") != pattern_type:
                    continue

                if self._check_access(user_id, pat_classification, metadata):
                    accessible_patterns.append(
                        {
                            "pattern_id": pattern_id,
                            "pattern_type": metadata.get("pattern_type"),
                            "classification": metadata["classification"],
                            "created_by": metadata.get("created_by"),
                            "created_at": metadata.get("created_at"),
                            "encrypted": metadata.get("encrypted", False),
                        },
                    )

            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Pattern metadata retrieval is best-effort
                logger.warning(
                    "failed_to_load_pattern_metadata",
                    pattern_id=pattern_id,
                    error=str(e),
                )
                continue

        return accessible_patterns

    def delete_pattern(self, pattern_id: str, user_id: str, session_id: str = "") -> bool:
        """Delete a pattern (with access control).

        Args:
            pattern_id: Pattern to delete
            user_id: User requesting deletion
            session_id: Session identifier

        Returns:
            True if deleted successfully

        Raises:
            PermissionError: If user doesn't have permission to delete
            ValueError: If pattern_id or user_id is empty

        """
        if not pattern_id or not pattern_id.strip():
            raise ValueError(f"pattern_id cannot be empty. Got: {pattern_id!r}")
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        pattern_data = self.storage.retrieve(pattern_id)

        if not pattern_data:
            logger.warning(
                "pattern_not_found_for_deletion",
                pattern_id=pattern_id,
            )
            return False

        metadata = pattern_data["metadata"]

        if metadata.get("created_by") != user_id:
            logger.warning(
                "delete_permission_denied",
                pattern_id=pattern_id,
                user_id=user_id,
                created_by=metadata.get("created_by"),
            )
            raise PermissionError(f"User {user_id} cannot delete pattern {pattern_id}")

        deleted = self.storage.delete(pattern_id)

        if deleted:
            self.audit_logger._write_event(
                AuditEvent(
                    event_type="delete_pattern",
                    user_id=user_id,
                    session_id=session_id,
                    status="success",
                    data={
                        "pattern_id": pattern_id,
                        "classification": metadata["classification"],
                    },
                ),
            )

            logger.info(
                "pattern_deleted",
                pattern_id=pattern_id,
                user_id=user_id,
            )

        return deleted

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about stored patterns.

        Returns:
            Dictionary with pattern statistics

        """
        all_patterns = self.storage.list_patterns()

        stats: dict[str, Any] = {
            "total_patterns": len(all_patterns),
            "by_classification": {
                "PUBLIC": 0,
                "INTERNAL": 0,
                "SENSITIVE": 0,
            },
            "encrypted_count": 0,
            "with_pii_scrubbed": 0,
        }

        for pattern_id in all_patterns:
            try:
                pattern_data = self.storage.retrieve(pattern_id)
                if not pattern_data:
                    continue

                metadata = pattern_data["metadata"]
                classification = metadata.get("classification", "INTERNAL")

                stats["by_classification"][classification] += 1

                if metadata.get("encrypted", False):
                    stats["encrypted_count"] += 1

                if metadata.get("pii_removed", 0) > 0:
                    stats["with_pii_scrubbed"] += 1

            except Exception:  # noqa: BLE001
                # INTENTIONAL: Log but continue aggregating stats
                logger.warning(
                    "Failed to retrieve pattern for stats",
                    pattern_id=pattern_id,
                    exc_info=True,
                )
                continue

        return stats


__all__ = [
    "PatternOperationsMixin",
]
