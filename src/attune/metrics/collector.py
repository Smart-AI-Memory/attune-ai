"""Metrics collector stub (deprecated).

This module is a placeholder for legacy code compatibility.
The functionality has been moved to other modules.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


class MetricsCollector:
    """Deprecated metrics collector class.

    This class is maintained for backward compatibility but is deprecated.
    """

    def __init__(self, db_path: str | None = None):
        """Initialize metrics collector.

        Args:
            db_path: Path to database (deprecated parameter)

        """
        self.db_path = db_path

    def collect(self):
        """Collect metrics (deprecated)."""
        return {}

    def get_stats(self):
        """Get statistics (deprecated)."""
        return {}
