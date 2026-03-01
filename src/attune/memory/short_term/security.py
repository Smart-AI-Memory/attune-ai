"""Data sanitization - PII scrubbing and secrets detection.

This module handles security-sensitive data processing:
- PII (Personally Identifiable Information) scrubbing
- Secrets detection (API keys, passwords, tokens)
- Data sanitization before storage

Classes:
    DataSanitizer: Handles PII and secrets scrubbing

Dependencies:
    PIIScrubber: External PII detection/removal
    SecretsDetector: External secrets detection

Example:
    >>> from attune.memory.short_term.security import DataSanitizer
    >>> from attune.memory.types import RedisMetrics
    >>> sanitizer = DataSanitizer(
    ...     pii_scrub_enabled=True,
    ...     secrets_detection_enabled=True,
    ...     metrics=RedisMetrics()
    ... )
    >>> clean_data, pii_count = sanitizer.sanitize({"email": "user@example.com"})
    >>> print(f"Scrubbed {pii_count} PII items")

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
from typing import Any

import structlog

from attune.memory.security.pii_scrubber import PIIScrubber
from attune.memory.security.secrets_detector import SecretsDetector
from attune.memory.security.secrets_detector import Severity as SecretSeverity
from attune.memory.types import RedisMetrics, SecurityError

logger = structlog.get_logger(__name__)


class DataSanitizer:
    """Handles data sanitization for short-term memory.

    Provides PII scrubbing and secrets detection to protect
    sensitive information from being stored in Redis.

    PII Detection:
        - Email addresses
        - Social Security Numbers (SSN)
        - Phone numbers
        - Credit card numbers

    Secrets Detection:
        - API keys
        - Passwords
        - Tokens
        - Private keys

    Attributes:
        pii_enabled: Whether PII scrubbing is active
        secrets_enabled: Whether secrets detection is active
        metrics: RedisMetrics instance for tracking

    Example:
        >>> sanitizer = DataSanitizer(
        ...     pii_scrub_enabled=True,
        ...     secrets_detection_enabled=True,
        ...     metrics=RedisMetrics()
        ... )
        >>> data = {"user": "john", "email": "john@example.com"}
        >>> clean, count = sanitizer.sanitize(data)
        >>> print(clean)  # Email will be redacted
        {'user': 'john', 'email': '[EMAIL]'}

    """

    def __init__(
        self,
        pii_scrub_enabled: bool = False,
        secrets_detection_enabled: bool = False,
        metrics: RedisMetrics | None = None,
    ) -> None:
        """Initialize data sanitizer.

        Args:
            pii_scrub_enabled: Enable PII scrubbing (emails, SSN, etc.)
            secrets_detection_enabled: Enable secrets detection (API keys, etc.)
            metrics: Optional RedisMetrics for tracking scrub operations

        """
        self.pii_enabled = pii_scrub_enabled
        self.secrets_enabled = secrets_detection_enabled
        self._metrics = metrics or RedisMetrics()

        # Initialize scrubbers
        self._pii_scrubber: PIIScrubber | None = None
        self._secrets_detector: SecretsDetector | None = None

        if pii_scrub_enabled:
            self._pii_scrubber = PIIScrubber(enable_name_detection=False)
            logger.debug(
                "pii_scrubber_enabled",
                message="PII scrubbing active for data sanitizer",
            )

        if secrets_detection_enabled:
            self._secrets_detector = SecretsDetector()
            logger.debug(
                "secrets_detector_enabled",
                message="Secrets detection active for data sanitizer",
            )

    @property
    def metrics(self) -> RedisMetrics:
        """Get metrics instance."""
        return self._metrics

    def sanitize(self, data: Any) -> tuple[Any, int]:
        """Sanitize data by scrubbing PII and checking for secrets.

        Performs two-step sanitization:
        1. Checks for secrets (API keys, passwords) - blocks if found
        2. Scrubs PII (emails, SSN, phone numbers) - redacts in place

        Args:
            data: Data to sanitize (dict, list, or str)

        Returns:
            Tuple of (sanitized_data, pii_count)
            - sanitized_data: Data with PII redacted
            - pii_count: Number of PII items found and scrubbed

        Raises:
            SecurityError: If critical/high severity secrets are detected

        Example:
            >>> sanitizer = DataSanitizer(pii_scrub_enabled=True)
            >>> data = {"contact": "user@example.com"}
            >>> clean, count = sanitizer.sanitize(data)
            >>> count
            1

        """
        pii_count = 0

        if data is None:
            return data, 0

        # Convert data to string for scanning
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(data)
        elif isinstance(data, str):
            data_str = data
        else:
            # For other types, convert to string
            data_str = str(data)

        # Check for secrets first (before modifying data)
        if self._secrets_detector is not None:
            detections = self._secrets_detector.detect(data_str)
            # Block critical and high severity secrets
            critical_secrets = [
                d
                for d in detections
                if d.severity in (SecretSeverity.CRITICAL, SecretSeverity.HIGH)
            ]
            if critical_secrets:
                self._metrics.secrets_blocked_total += len(critical_secrets)
                secret_types = [d.secret_type.value for d in critical_secrets]
                logger.warning(
                    "secrets_detected_blocked",
                    secret_types=secret_types,
                    count=len(critical_secrets),
                )
                raise SecurityError(
                    f"Cannot store data containing secrets: {secret_types}. "
                    "Remove sensitive credentials before storing.",
                )

        # Scrub PII
        if self._pii_scrubber is not None:
            sanitized_str, pii_detections = self._pii_scrubber.scrub(data_str)
            pii_count = len(pii_detections)

            if pii_count > 0:
                self._metrics.pii_scrubbed_total += pii_count
                self._metrics.pii_scrub_operations += 1
                logger.debug(
                    "pii_scrubbed",
                    pii_count=pii_count,
                    pii_types=[d.pii_type for d in pii_detections],
                )

                # Convert back to original type
                if isinstance(data, dict):
                    try:
                        return json.loads(sanitized_str), pii_count
                    except json.JSONDecodeError:
                        # If PII scrubbing broke JSON structure, return original
                        # This can happen if regex matches part of JSON syntax
                        logger.warning("pii_scrubbing_broke_json_returning_original")
                        return data, 0
                elif isinstance(data, list):
                    try:
                        return json.loads(sanitized_str), pii_count
                    except json.JSONDecodeError:
                        logger.warning("pii_scrubbing_broke_json_returning_original")
                        return data, 0
                else:
                    return sanitized_str, pii_count

        return data, pii_count

    def check_secrets(self, data: Any) -> list[str]:
        """Check data for secrets without blocking.

        Args:
            data: Data to check (dict, list, or str)

        Returns:
            List of detected secret types (empty if none found)

        Example:
            >>> sanitizer = DataSanitizer(secrets_detection_enabled=True)
            >>> secrets = sanitizer.check_secrets({"key": "sk-abc123..."})
            >>> if secrets:
            ...     print(f"Found secrets: {secrets}")

        """
        if self._secrets_detector is None or data is None:
            return []

        # Convert data to string for scanning
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(data)
        elif isinstance(data, str):
            data_str = data
        else:
            data_str = str(data)

        detections = self._secrets_detector.detect(data_str)
        return [d.secret_type.value for d in detections]

    def scrub_pii_only(self, data: Any) -> tuple[Any, int]:
        """Scrub only PII from data (no secrets blocking).

        Args:
            data: Data to scrub (dict, list, or str)

        Returns:
            Tuple of (scrubbed_data, pii_count)

        Example:
            >>> sanitizer = DataSanitizer(pii_scrub_enabled=True)
            >>> clean, count = sanitizer.scrub_pii_only("Email: user@example.com")
            >>> print(clean)  # "Email: [EMAIL]"

        """
        if self._pii_scrubber is None or data is None:
            return data, 0

        # Convert data to string
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(data)
        elif isinstance(data, str):
            data_str = data
        else:
            data_str = str(data)

        sanitized_str, pii_detections = self._pii_scrubber.scrub(data_str)
        pii_count = len(pii_detections)

        if pii_count == 0:
            return data, 0

        # Update metrics
        self._metrics.pii_scrubbed_total += pii_count
        self._metrics.pii_scrub_operations += 1

        # Convert back to original type
        if isinstance(data, dict) or isinstance(data, list):
            try:
                return json.loads(sanitized_str), pii_count
            except json.JSONDecodeError:
                return data, 0
        else:
            return sanitized_str, pii_count
