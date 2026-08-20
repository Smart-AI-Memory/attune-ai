"""Audit Log Query Engine

Provides query and filter capabilities for audit log data.
Supports nested key access, comparison operators, and date
range filtering.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class AuditQueryMixin:
    """Mixin that adds query capabilities to AuditLogger.

    Requires the host class to have:
    - self.log_path: Path to the audit log file
    """

    log_path: Any

    def query(
        self,
        event_type: str | None = None,
        user_id: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 1000,
        **filters: Any,
    ) -> list[dict]:
        """Query audit logs with filters.

        Provides search and analysis capabilities for audit data.

        Args:
            event_type: Filter by event type
                (llm_request, store_pattern, etc.)
            user_id: Filter by user ID
            status: Filter by status (success, failed, blocked)
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of events to return
            **filters: Additional key-value filters
                (supports nested keys with __)

        Returns:
            List of matching audit events as dictionaries

        Example:
            >>> events = logger.query(
            ...     event_type="llm_request",
            ...     status="failed",
            ... )
            >>> events = logger.query(
            ...     event_type="security_violation",
            ...     start_date=datetime.now(timezone.utc)
            ...         - timedelta(days=1),
            ... )
            >>> events = logger.query(
            ...     security__pii_detected__gt=5,
            ... )

        """
        results: list[dict[str, object]] = []

        try:
            if not self.log_path.exists():
                return results

            with open(self.log_path, encoding="utf-8") as f:
                for line in f:
                    if len(results) >= limit:
                        break

                    try:
                        event = json.loads(line.strip())

                        # A valid-JSON non-dict row is not an audit
                        # event: unfiltered it was APPENDED to results
                        # as-is (garbage in a security query), and
                        # filtered it raised AttributeError into the
                        # outer handler, truncating the whole query
                        # (library-review E1 widening).
                        if not isinstance(event, dict):
                            logger.warning("Skipping non-object audit log line")
                            continue

                        # Apply filters
                        if event_type and event.get("event_type") != event_type:
                            continue
                        if user_id and event.get("user_id") != user_id:
                            continue
                        if status and event.get("status") != status:
                            continue

                        # Date range filtering. A malformed timestamp on
                        # one line must not abort iteration — without this
                        # ValueError catch, a single bad event ends the
                        # whole query and returns a silent partial result.
                        if start_date or end_date:
                            ts_raw = event.get("timestamp", "")
                            try:
                                event_time = datetime.fromisoformat(
                                    ts_raw.replace("Z", "+00:00"),
                                )
                            except (ValueError, AttributeError):
                                logger.warning(
                                    "Skipping audit log line with " "malformed timestamp: %r",
                                    ts_raw,
                                )
                                continue
                            if start_date and event_time < start_date:
                                continue
                            if end_date and event_time > end_date:
                                continue

                        # Custom filters
                        # (supports nested keys with __)
                        if filters and not _apply_custom_filters(event, filters):
                            continue

                        results.append(event)

                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed audit log line")
                        continue

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Query should not crash on I/O errors
            logger.error(f"Failed to query audit logs: {e}")

        return results


def _apply_custom_filters(
    event: dict[str, Any],
    filters: dict[str, Any],
) -> bool:
    """Apply custom filters to an event.

    Supports nested key access with __ separator and
    comparison operators.

    Args:
        event: The audit event dictionary to filter
        filters: Key-value filter pairs, supporting nested
            keys (e.g., security__pii_detected__gt=5)

    Returns:
        True if the event matches all filters

    """
    for key, value in filters.items():
        # Handle comparison operators
        # (e.g., security__pii_detected__gt=5)
        parts = key.split("__")
        operator = None

        # Use set for O(1) membership testing
        valid_operators = {"gt", "gte", "lt", "lte", "ne"}
        if len(parts) > 1 and parts[-1] in valid_operators:
            operator = parts[-1]
            parts = parts[:-1]

        # Navigate nested dictionary
        current = event
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False

        # Apply comparison
        if (operator == "gt" and not (isinstance(current, int | float) and current > value)) or (
            operator == "gte" and not (isinstance(current, int | float) and current >= value)
        ):
            return False
        if (
            (operator == "lt" and not (isinstance(current, int | float) and current < value))
            or (operator == "lte" and not (isinstance(current, int | float) and current <= value))
            or (operator == "ne" and current == value)
            or (operator is None and current != value)
        ):
            return False

    return True
