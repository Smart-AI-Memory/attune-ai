"""Store and retrieve pipeline helpers for SecureMemDocsIntegration.

Contains the PatternPipelineMixin class with helper methods for the
store_pattern and retrieve_pattern security pipelines. These helpers
handle input validation, parallel security scanning, encryption,
access enforcement, and retention checking.

Extracted from long_term_integration.py for modularity.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import structlog

from .long_term_classification import (
    check_access,
    classify_pattern,
    resolve_current_workspace,
)
from .long_term_types import (
    Classification,
    ClassificationRules,
    PatternMetadata,
    PermissionError,
    SecurityError,
)

if TYPE_CHECKING:
    from .encryption import EncryptionManager
    from .security.audit_logger import AuditLogger
    from .security.pii_scrubber import PIIScrubber
    from .security.secrets_detector import SecretsDetector

logger = structlog.get_logger(__name__)


class PatternPipelineMixin:
    """Mixin providing store/retrieve pipeline helpers.

    Requires the host class to provide:
    - self.pii_scrubber: PIIScrubber
    - self.secrets_detector: SecretsDetector
    - self.audit_logger: AuditLogger
    - self.encryption_enabled: bool
    - self.encryption_manager: EncryptionManager | None

    """

    pii_scrubber: PIIScrubber
    secrets_detector: SecretsDetector
    audit_logger: AuditLogger
    encryption_enabled: bool
    encryption_manager: EncryptionManager | None

    @staticmethod
    def _validate_store_inputs(
        content: str,
        pattern_type: str,
        user_id: str,
        custom_metadata: dict[str, Any] | None,
    ) -> None:
        """Validate inputs for store_pattern.

        Args:
            content: Pattern content to validate
            pattern_type: Pattern type to validate
            user_id: User ID to validate
            custom_metadata: Optional metadata dict to validate

        Raises:
            ValueError: If content, pattern_type, or user_id is empty
            TypeError: If custom_metadata is not a dict

        """
        if not content or not content.strip():
            raise ValueError(f"content cannot be empty. Got: {content!r}")
        if not pattern_type or not pattern_type.strip():
            raise ValueError(f"pattern_type cannot be empty. Got: {pattern_type!r}")
        if not user_id or not user_id.strip():
            raise ValueError(f"user_id cannot be empty. Got: {user_id!r}")
        if custom_metadata is not None and not isinstance(custom_metadata, dict):
            raise TypeError(
                "custom_metadata must be dict, " f"got {type(custom_metadata).__name__}",
            )

    def _run_security_pipeline(self, content: str) -> tuple:
        """Run PII scrubbing and secrets detection in parallel.

        Args:
            content: Raw content to scan

        Returns:
            Tuple of (sanitized_content, pii_detections, secrets_found)

        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            pii_future = executor.submit(self.pii_scrubber.scrub, content)
            secrets_future = executor.submit(self.secrets_detector.detect, content)
            sanitized_content, pii_detections = pii_future.result()
            secrets_found = secrets_future.result()
        return sanitized_content, pii_detections, secrets_found

    def _handle_secrets_found(
        self,
        secrets_found: list,
        user_id: str,
        pattern_type: str,
        session_id: str,
    ) -> None:
        """Block storage and raise SecurityError when secrets found.

        Args:
            secrets_found: List of detected secrets
            user_id: User who attempted storage
            pattern_type: Type of pattern
            session_id: Session identifier for audit

        Raises:
            SecurityError: Always raised when secrets are found

        """
        secret_types = [s.secret_type.value for s in secrets_found]
        logger.error(
            "secrets_detected_blocking_storage",
            user_id=user_id,
            secret_count=len(secrets_found),
            types=secret_types,
        )
        self.audit_logger.log_security_violation(
            user_id=user_id,
            violation_type="secrets_in_storage_attempt",
            severity="CRITICAL",
            details={
                "secret_count": len(secrets_found),
                "secret_types": secret_types,
                "pattern_type": pattern_type,
            },
            session_id=session_id,
            blocked=True,
        )
        raise SecurityError(
            "Secrets detected in pattern. Cannot store. " f"Found: {secret_types}",
        )

    @staticmethod
    def _resolve_classification(
        content: str,
        pattern_type: str,
        auto_classify: bool,
        explicit: Classification | None,
    ) -> Classification:
        """Determine classification for a pattern.

        Args:
            content: Sanitized pattern content
            pattern_type: Type of pattern
            auto_classify: Whether to auto-classify
            explicit: Explicit classification override

        Returns:
            Resolved Classification

        """
        if explicit:
            logger.info(
                "explicit_classification",
                classification=explicit.value,
            )
            return explicit
        if auto_classify:
            result = classify_pattern(content, pattern_type)
            logger.info("auto_classification", classification=result.value)
            return result
        logger.info(
            "default_classification",
            classification=Classification.INTERNAL.value,
        )
        return Classification.INTERNAL

    def _apply_encryption(
        self,
        content: str,
        rules: ClassificationRules,
        classification: Classification,
    ) -> tuple[str, bool]:
        """Encrypt content if required by classification rules.

        Args:
            content: Content to potentially encrypt
            rules: Classification rules
            classification: Current classification level

        Returns:
            Tuple of (final_content, encrypted_flag)

        """
        if rules.encryption_required and self.encryption_enabled and self.encryption_manager:
            encrypted_content = self.encryption_manager.encrypt(content)
            logger.info(
                "pattern_encrypted",
                classification=classification.value,
            )
            return encrypted_content, True
        if rules.encryption_required and not self.encryption_enabled:
            logger.warning(
                "encryption_required_but_unavailable",
                classification=classification.value,
                action="storing_unencrypted",
            )
        return content, False

    @staticmethod
    def _build_metadata(
        pattern_id: str,
        user_id: str,
        classification: Classification,
        rules: ClassificationRules,
        encrypted: bool,
        pattern_type: str,
        pii_count: int,
        custom_metadata: dict[str, Any] | None,
    ) -> PatternMetadata:
        """Build PatternMetadata for storage.

        Args:
            pattern_id: Unique pattern identifier
            user_id: User creating the pattern
            classification: Applied classification
            rules: Classification rules
            encrypted: Whether content was encrypted
            pattern_type: Type of pattern
            pii_count: Number of PII items removed
            custom_metadata: Additional custom metadata

        Returns:
            PatternMetadata instance

        """
        return PatternMetadata(
            pattern_id=pattern_id,
            created_by=user_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            classification=classification.value,
            retention_days=rules.retention_days,
            encrypted=encrypted,
            pattern_type=pattern_type,
            sanitization_applied=True,
            pii_removed=pii_count,
            secrets_detected=0,
            # Stamped at write time so INTERNAL scoping has something to
            # compare against — before library-review I-3 nothing wrote
            # this, so the rule could never fire.
            workspace=resolve_current_workspace(),
            access_control={
                "access_level": rules.access_level,
                "audit_required": rules.audit_all_access,
            },
            custom_metadata=custom_metadata or {},
        )

    def _enforce_access(
        self,
        user_id: str,
        pattern_id: str,
        classification: Classification,
        metadata: dict[str, Any],
        session_id: str,
    ) -> None:
        """Check access and raise PermissionError if denied.

        Args:
            user_id: User requesting access
            pattern_id: Pattern being accessed
            classification: Pattern classification
            metadata: Pattern metadata
            session_id: Session identifier for audit

        Raises:
            PermissionError: If access is denied

        """
        granted = check_access(
            user_id=user_id,
            classification=classification,
            metadata=metadata,
        )
        if not granted:
            logger.warning(
                "access_denied",
                pattern_id=pattern_id,
                user_id=user_id,
                classification=classification.value,
            )
            self.audit_logger.log_pattern_retrieve(
                user_id=user_id,
                pattern_id=pattern_id,
                classification=classification.value,
                access_granted=False,
                session_id=session_id,
                status="blocked",
                error="Access denied",
            )
            raise PermissionError(
                f"User {user_id} does not have access to {classification.value} pattern",
            )

    def _decrypt_if_needed(
        self,
        content: str,
        metadata: dict[str, Any],
        pattern_id: str,
    ) -> str:
        """Decrypt content if it was encrypted.

        Args:
            content: Pattern content (possibly encrypted)
            metadata: Pattern metadata
            pattern_id: Pattern identifier for logging

        Returns:
            Decrypted content string

        Raises:
            SecurityError: If encryption is not available

        """
        if not metadata.get("encrypted", False):
            return content
        if not self.encryption_enabled:
            logger.error(
                "decryption_required_but_unavailable",
                pattern_id=pattern_id,
            )
            raise SecurityError("Encryption not available for decryption")
        if self.encryption_manager:
            content = self.encryption_manager.decrypt(content)
        logger.debug("pattern_decrypted", pattern_id=pattern_id)
        return content

    @staticmethod
    def _check_retention(metadata: dict[str, Any], pattern_id: str) -> None:
        """Raise ValueError if pattern retention has expired.

        Args:
            metadata: Pattern metadata containing created_at and
                retention_days
            pattern_id: Pattern identifier for error messages

        Raises:
            ValueError: If the retention period has expired

        """
        created_at = datetime.fromisoformat(metadata["created_at"].replace("Z", "+00:00"))
        retention_days = metadata["retention_days"]
        expiration = created_at + timedelta(days=retention_days)

        if datetime.now(timezone.utc) > expiration:
            logger.warning(
                "pattern_retention_expired",
                pattern_id=pattern_id,
                created_at=metadata["created_at"],
                retention_days=retention_days,
            )
            raise ValueError(
                f"Pattern {pattern_id} has expired retention period "
                f"(created: {metadata['created_at']}, "
                f"retention: {retention_days} days)",
            )


__all__ = [
    "PatternPipelineMixin",
]
