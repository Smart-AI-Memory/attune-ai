"""Secure MemDocs Integration for Enterprise Privacy.

Contains the SecureMemDocsIntegration class which combines PII scrubbing,
secrets detection, and audit logging with MemDocs pattern storage.
Implements three-tier classification (PUBLIC/INTERNAL/SENSITIVE) with
encryption support.

Pipeline:
    User Input -> [PII Scrubbing + Secrets Detection (PARALLEL)]
    -> Classification -> Encryption (if SENSITIVE) -> MemDocs Storage
    -> Audit Logging

Extracted from long_term.py for modularity.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

import structlog

from .encryption import HAS_ENCRYPTION, EncryptionManager
from .long_term_classification import check_access, classify_pattern
from .long_term_operations import PatternOperationsMixin
from .long_term_pipelines import PatternPipelineMixin
from .long_term_types import (
    DEFAULT_CLASSIFICATION_RULES,
    Classification,
    ClassificationRules,
    PermissionError,
    SecurityError,
)
from .security.audit_logger import AuditLogger
from .security.pii_scrubber import PIIScrubber
from .security.secrets_detector import SecretsDetector
from .storage_backend import MemDocsStorage

logger = structlog.get_logger(__name__)


class SecureMemDocsIntegration(PatternPipelineMixin, PatternOperationsMixin):
    """Secure integration between Claude Memory and MemDocs.

    Enforces enterprise security policies from CLAUDE.md with:
    - Automatic PII scrubbing
    - Secrets detection and blocking
    - Three-tier classification
    - Encryption for SENSITIVE data
    - Comprehensive audit logging
    - Access control enforcement

    Example:
        >>> from attune.memory import ClaudeMemoryConfig
        >>> config = ClaudeMemoryConfig(enabled=True, load_enterprise=True)
        >>> integration = SecureMemDocsIntegration(config)
        >>>
        >>> result = integration.store_pattern(
        ...     content="Patient diagnosis: diabetes type 2",
        ...     pattern_type="clinical_protocol",
        ...     user_id="doctor@hospital.com"
        ... )
        >>>
        >>> pattern = integration.retrieve_pattern(
        ...     pattern_id=result["pattern_id"],
        ...     user_id="doctor@hospital.com"
        ... )

    """

    def __init__(
        self,
        claude_memory_config=None,
        storage_dir: str | None = None,
        audit_log_dir: str | None = None,
        classification_rules: dict[Classification, ClassificationRules] | None = None,
        enable_encryption: bool = True,
        master_key: bytes | None = None,
    ):
        """Initialize Secure MemDocs Integration.

        Args:
            claude_memory_config: Configuration for Claude memory
            storage_dir: Directory for MemDocs storage. When None,
                resolves to the home-anchored default store.
            audit_log_dir: Directory for audit logs
            classification_rules: Custom rules (defaults if None)
            enable_encryption: Enable encryption for SENSITIVE patterns
            master_key: Encryption master key (auto-generated if None)

        """
        self.claude_memory_config = claude_memory_config
        self.classification_rules = classification_rules or DEFAULT_CLASSIFICATION_RULES

        # Initialize security components
        self.pii_scrubber = PIIScrubber()
        self.secrets_detector = SecretsDetector()
        self.audit_logger = AuditLogger(
            log_dir=audit_log_dir,
            enable_console_logging=True,
        )

        # Initialize encryption
        self.encryption_enabled = enable_encryption and HAS_ENCRYPTION
        self.encryption_manager: EncryptionManager | None = None
        if self.encryption_enabled:
            self.encryption_manager = EncryptionManager(master_key)
        elif enable_encryption:
            logger.warning(
                "encryption_disabled",
                reason="cryptography library not available",
            )

        # Initialize storage backend
        self.storage = MemDocsStorage(storage_dir)

        # Load security policies
        self.security_policies = self._load_security_policies()

        logger.info(
            "secure_memdocs_initialized",
            encryption_enabled=self.encryption_enabled,
            storage_dir=str(self.storage.storage_dir),
            audit_dir=audit_log_dir,
        )

    def _load_security_policies(self) -> dict[str, Any]:
        """Load security policies from enterprise Claude memory.

        Returns default policies that match the architecture spec.
        """
        policies = {
            "pii_scrubbing_enabled": True,
            "secrets_detection_enabled": True,
            "classification_required": True,
            "audit_logging_enabled": True,
            "retention_enforcement_enabled": True,
        }
        logger.debug("security_policies_loaded", policies=policies)
        return policies

    def store_pattern(
        self,
        content: str,
        pattern_type: str,
        user_id: str,
        auto_classify: bool = True,
        explicit_classification: Classification | None = None,
        session_id: str = "",
        custom_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store a pattern with full security pipeline.

        Args:
            content: Pattern content to store
            pattern_type: Type of pattern
            user_id: User storing the pattern
            auto_classify: Enable automatic classification
            explicit_classification: Override auto-classification
            session_id: Session identifier for audit
            custom_metadata: Additional metadata

        Returns:
            Dictionary with pattern_id, classification, and
            sanitization_report.

        Raises:
            SecurityError: If secrets detected
            ValueError: If content/pattern_type/user_id empty
            TypeError: If custom_metadata is not dict

        """
        logger.info(
            "store_pattern_started",
            user_id=user_id,
            pattern_type=pattern_type,
            auto_classify=auto_classify,
        )

        try:
            self._validate_store_inputs(content, pattern_type, user_id, custom_metadata)

            # PII Scrubbing + Secrets Detection (PARALLEL)
            sanitized_content, pii_detections, secrets_found = self._run_security_pipeline(content)

            pii_count = len(pii_detections)
            if pii_count > 0:
                logger.info(
                    "pii_scrubbed",
                    user_id=user_id,
                    pii_count=pii_count,
                    types=[d.pii_type for d in pii_detections],
                )

            if secrets_found:
                self._handle_secrets_found(secrets_found, user_id, pattern_type, session_id)

            # Classification
            classification = self._resolve_classification(
                sanitized_content,
                pattern_type,
                auto_classify,
                explicit_classification,
            )

            # Encryption
            rules = self.classification_rules[classification]
            final_content, encrypted = self._apply_encryption(
                sanitized_content,
                rules,
                classification,
            )

            # Generate ID and store
            pattern_id = self._generate_pattern_id(user_id, pattern_type)
            metadata = self._build_metadata(
                pattern_id,
                user_id,
                classification,
                rules,
                encrypted,
                pattern_type,
                pii_count,
                custom_metadata,
            )

            self.storage.store(
                pattern_id=pattern_id,
                content=final_content,
                metadata=metadata.__dict__,
            )

            # Audit logging
            self.audit_logger.log_pattern_store(
                user_id=user_id,
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                classification=classification.value,
                pii_scrubbed=pii_count,
                secrets_detected=0,
                retention_days=rules.retention_days,
                encrypted=encrypted,
                session_id=session_id,
                status="success",
            )

            logger.info(
                "pattern_stored_successfully",
                pattern_id=pattern_id,
                classification=classification.value,
                encrypted=encrypted,
            )

            return {
                "pattern_id": pattern_id,
                "classification": classification.value,
                "sanitization_report": {
                    "pii_removed": [{"type": d.pii_type, "count": 1} for d in pii_detections],
                    "pii_count": pii_count,
                    "secrets_detected": 0,
                },
                "metadata": {
                    "encrypted": encrypted,
                    "retention_days": rules.retention_days,
                    "created_at": metadata.created_at,
                },
            }

        except SecurityError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.error(
                "pattern_storage_failed",
                user_id=user_id,
                error=str(e),
            )
            self.audit_logger.log_pattern_store(
                user_id=user_id,
                pattern_id="",
                pattern_type=pattern_type,
                classification="UNKNOWN",
                pii_scrubbed=0,
                secrets_detected=0,
                retention_days=0,
                encrypted=False,
                session_id=session_id,
                status="failed",
                error=str(e),
            )
            raise

    def retrieve_pattern(
        self,
        pattern_id: str,
        user_id: str,
        check_permissions: bool = True,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Retrieve a pattern with access control and decryption.

        Args:
            pattern_id: Unique pattern identifier
            user_id: User retrieving the pattern
            check_permissions: Enforce access control
            session_id: Session identifier for audit

        Returns:
            Dictionary with content and metadata.

        Raises:
            PermissionError: If access denied
            ValueError: If pattern not found or retention expired
            SecurityError: If decryption fails

        """
        if not pattern_id or not pattern_id.strip():
            raise ValueError(f"pattern_id cannot be empty. Got: {pattern_id!r}")
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        logger.info(
            "retrieve_pattern_started",
            pattern_id=pattern_id,
            user_id=user_id,
            check_permissions=check_permissions,
        )

        try:
            pattern_data = self.storage.retrieve(pattern_id)
            if not pattern_data:
                logger.warning("pattern_not_found", pattern_id=pattern_id)
                raise ValueError(f"Pattern {pattern_id} not found")

            content = pattern_data["content"]
            metadata = pattern_data["metadata"]
            classification = Classification[metadata["classification"]]

            if check_permissions:
                self._enforce_access(
                    user_id,
                    pattern_id,
                    classification,
                    metadata,
                    session_id,
                )

            content = self._decrypt_if_needed(content, metadata, pattern_id)
            self._check_retention(metadata, pattern_id)

            self.audit_logger.log_pattern_retrieve(
                user_id=user_id,
                pattern_id=pattern_id,
                classification=classification.value,
                access_granted=True,
                permission_level=metadata["access_control"]["access_level"],
                session_id=session_id,
                status="success",
            )

            logger.info(
                "pattern_retrieved_successfully",
                pattern_id=pattern_id,
                classification=classification.value,
            )

            return {"content": content, "metadata": metadata}

        except (PermissionError, ValueError, SecurityError):
            raise
        except Exception as e:  # noqa: BLE001
            logger.error(
                "pattern_retrieval_failed",
                pattern_id=pattern_id,
                error=str(e),
            )
            self.audit_logger.log_pattern_retrieve(
                user_id=user_id,
                pattern_id=pattern_id,
                classification="UNKNOWN",
                access_granted=False,
                session_id=session_id,
                status="failed",
                error=str(e),
            )
            raise

    # ------------------------------------------------------------------
    # Private helpers (kept on the class for ID generation & delegation)
    # ------------------------------------------------------------------

    def _classify_pattern(self, content: str, pattern_type: str) -> Classification:
        """Delegate to standalone classify_pattern()."""
        return classify_pattern(content, pattern_type)

    def _check_access(
        self,
        user_id: str,
        classification: Classification,
        metadata: dict[str, Any],
    ) -> bool:
        """Delegate to standalone check_access()."""
        return check_access(user_id, classification, metadata)

    def _generate_pattern_id(self, user_id: str, pattern_type: str) -> str:
        """Generate unique pattern ID (pat_{timestamp}_{hash})."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        hash_input = f"{user_id}:{pattern_type}:{timestamp}:{os.urandom(8).hex()}"
        hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        return f"pat_{timestamp}_{hash_digest}"


__all__ = [
    "SecureMemDocsIntegration",
]
