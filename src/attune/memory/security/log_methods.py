"""Audit Event Logging Methods

Provides the specific logging methods for different event
types: LLM requests, pattern storage/retrieval, and security
violations.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from typing import TYPE_CHECKING, Any

from .events import AuditEvent, SecurityViolation

logger = logging.getLogger(__name__)


class AuditLogMethodsMixin:
    """Mixin that adds event-specific logging methods.

    Requires the host class to have:
    - self._write_event(event): Write an audit event
    - self._handle_security_violation(...): Handle violations
    """

    if TYPE_CHECKING:

        def _write_event(self, event: AuditEvent) -> None: ...
        def _handle_security_violation(
            self,
            user_id: str,
            violation_type: str,
            severity: str,
            details: dict[str, Any],
        ) -> None: ...

    def log_llm_request(
        self,
        user_id: str,
        empathy_level: int,
        provider: str,
        model: str,
        memory_sources: list[str],
        pii_count: int = 0,
        secrets_count: int = 0,
        request_size_bytes: int = 0,
        response_size_bytes: int = 0,
        duration_ms: int = 0,
        memdocs_patterns_used: list[str] | None = None,
        sanitization_applied: bool = True,
        classification_verified: bool = True,
        session_id: str = "",
        ip_address: str = "",
        temperature: float = 0.7,
        status: str = "success",
        error: str = "",
        **kwargs: Any,
    ) -> None:
        """Log an LLM API request.

        Tracks all LLM interactions for compliance and
        monitoring.

        Args:
            user_id: User or service account making the
                request
            empathy_level: Empathy level (1-5) used
            provider: LLM provider (anthropic)
            model: Specific model used
            memory_sources: Which memory sources were loaded
                (enterprise, user, project)
            pii_count: Number of PII items detected
                (not the items themselves)
            secrets_count: Number of secrets detected
            request_size_bytes: Size of the request payload
            response_size_bytes: Size of the response payload
            duration_ms: Request duration in milliseconds
            memdocs_patterns_used: List of MemDocs pattern
                IDs used
            sanitization_applied: Whether PII sanitization
                was applied
            classification_verified: Whether data
                classification was verified
            session_id: Session identifier
            ip_address: Anonymized IP address
                (e.g., first 3 octets only)
            temperature: LLM temperature setting
            status: success, failed, or blocked
            error: Error message if failed
            **kwargs: Additional custom fields

        Example:
            >>> logger.log_llm_request(
            ...     user_id="user@company.com",
            ...     empathy_level=3,
            ...     provider="anthropic",
            ...     model="claude-sonnet-4",
            ...     memory_sources=["enterprise", "user"],
            ...     pii_count=0,
            ...     secrets_count=0,
            ... )

        """
        event = AuditEvent(
            event_type="llm_request",
            user_id=user_id,
            session_id=session_id,
            status=status,
            error=error,
            data={
                "llm": {
                    "provider": provider,
                    "model": model,
                    "empathy_level": empathy_level,
                    "temperature": temperature,
                },
                "memory": {
                    "sources": memory_sources,
                    "total_sources": len(memory_sources),
                    "security_policies_applied": ("enterprise" in memory_sources),
                },
                "memdocs": {
                    "patterns_used": (memdocs_patterns_used or []),
                    "pattern_count": len(memdocs_patterns_used or []),
                },
                "security": {
                    "pii_detected": pii_count,
                    "secrets_detected": secrets_count,
                    "sanitization_applied": (sanitization_applied),
                    "classification_verified": (classification_verified),
                },
                "request": {
                    "size_bytes": request_size_bytes,
                    "duration_ms": duration_ms,
                    "ip_address": ip_address,
                },
                "response": {
                    "size_bytes": response_size_bytes,
                },
                "compliance": {
                    "gdpr_compliant": (pii_count == 0 or sanitization_applied),
                    "hipaa_compliant": (secrets_count == 0 and sanitization_applied),
                    "soc2_compliant": True,
                },
                **kwargs,
            },
        )

        self._write_event(event)

        # Check for security violations
        if secrets_count > 0:
            self._handle_security_violation(
                user_id=user_id,
                violation_type="secrets_detected",
                severity="HIGH",
                details={
                    "secrets_count": secrets_count,
                    "event_type": "llm_request",
                },
            )

    def log_pattern_store(
        self,
        user_id: str,
        pattern_id: str,
        pattern_type: str,
        classification: str,
        pii_scrubbed: int = 0,
        secrets_detected: int = 0,
        retention_days: int = 180,
        encrypted: bool = False,
        session_id: str = "",
        status: str = "success",
        error: str = "",
        **kwargs: Any,
    ) -> None:
        """Log MemDocs pattern storage.

        Tracks pattern creation for compliance and data
        governance.

        Args:
            user_id: User storing the pattern
            pattern_id: Unique identifier for the pattern
            pattern_type: Type of pattern
                (code, architecture, workflow, etc.)
            classification: PUBLIC, INTERNAL, or SENSITIVE
            pii_scrubbed: Number of PII items scrubbed
                before storage
            secrets_detected: Number of secrets found
                (should be 0 for storage)
            retention_days: Retention period in days
            encrypted: Whether pattern is encrypted at rest
            session_id: Session identifier
            status: success, failed, or blocked
            error: Error message if failed
            **kwargs: Additional custom fields

        Example:
            >>> logger.log_pattern_store(
            ...     user_id="user@company.com",
            ...     pattern_id="pattern_abc123",
            ...     pattern_type="architecture",
            ...     classification="INTERNAL",
            ...     pii_scrubbed=2,
            ...     retention_days=180,
            ... )

        """
        event = AuditEvent(
            event_type="store_pattern",
            user_id=user_id,
            session_id=session_id,
            status=status,
            error=error,
            data={
                "pattern": {
                    "pattern_id": pattern_id,
                    "pattern_type": pattern_type,
                    "classification": classification,
                    "encrypted": encrypted,
                    "retention_days": retention_days,
                },
                "security": {
                    "pii_scrubbed": pii_scrubbed,
                    "secrets_detected": secrets_detected,
                    "sanitization_applied": (pii_scrubbed > 0),
                },
                "compliance": {
                    "gdpr_compliant": (secrets_detected == 0),
                    "hipaa_compliant": (classification == "SENSITIVE" and encrypted)
                    or classification != "SENSITIVE",
                    "soc2_compliant": (
                        secrets_detected == 0
                        and classification
                        in [
                            "PUBLIC",
                            "INTERNAL",
                            "SENSITIVE",
                        ]
                    ),
                    "classification_verified": (
                        classification
                        in [
                            "PUBLIC",
                            "INTERNAL",
                            "SENSITIVE",
                        ]
                    ),
                },
                **kwargs,
            },
        )

        self._write_event(event)

        # Check for security violations
        if secrets_detected > 0:
            self._handle_security_violation(
                user_id=user_id,
                violation_type="secrets_in_storage",
                severity="CRITICAL",
                details={
                    "secrets_detected": secrets_detected,
                    "pattern_id": pattern_id,
                    "event_type": "store_pattern",
                },
            )

        if classification == "SENSITIVE" and not encrypted:
            self._handle_security_violation(
                user_id=user_id,
                violation_type="sensitive_not_encrypted",
                severity="HIGH",
                details={
                    "pattern_id": pattern_id,
                    "classification": classification,
                    "event_type": "store_pattern",
                },
            )

    def log_pattern_retrieve(
        self,
        user_id: str,
        pattern_id: str,
        classification: str,
        access_granted: bool = True,
        permission_level: str = "",
        session_id: str = "",
        status: str = "success",
        error: str = "",
        **kwargs: Any,
    ) -> None:
        """Log MemDocs pattern retrieval.

        Tracks pattern access for compliance and security
        monitoring.

        Args:
            user_id: User retrieving the pattern
            pattern_id: Unique identifier for the pattern
            classification: PUBLIC, INTERNAL, or SENSITIVE
            access_granted: Whether access was granted
            permission_level: Permission level used for
                access decision
            session_id: Session identifier
            status: success, failed, or blocked
            error: Error message if failed
            **kwargs: Additional custom fields

        Example:
            >>> logger.log_pattern_retrieve(
            ...     user_id="user@company.com",
            ...     pattern_id="pattern_abc123",
            ...     classification="SENSITIVE",
            ...     access_granted=True,
            ...     permission_level="explicit",
            ... )

        """
        event = AuditEvent(
            event_type="retrieve_pattern",
            user_id=user_id,
            session_id=session_id,
            status=("success" if access_granted else "blocked"),
            error=error,
            data={
                "pattern": {
                    "pattern_id": pattern_id,
                    "classification": classification,
                },
                "access": {
                    "granted": access_granted,
                    "permission_level": permission_level,
                    "audit_required": (classification == "SENSITIVE"),
                },
                "compliance": {
                    "access_logged": True,
                    "hipaa_compliant": (classification == "SENSITIVE"),
                },
                **kwargs,
            },
        )

        self._write_event(event)

        # Log unauthorized access attempts
        if not access_granted:
            self._handle_security_violation(
                user_id=user_id,
                violation_type="unauthorized_access",
                severity=("MEDIUM" if classification == "INTERNAL" else "HIGH"),
                details={
                    "pattern_id": pattern_id,
                    "classification": classification,
                    "event_type": "retrieve_pattern",
                },
            )

    def log_security_violation(
        self,
        user_id: str,
        violation_type: str,
        severity: str,
        details: dict[str, Any],
        session_id: str = "",
        blocked: bool = True,
        **kwargs: Any,
    ) -> None:
        """Log a security policy violation.

        Tracks security incidents for monitoring and
        response.

        Args:
            user_id: User who triggered the violation
            violation_type: Type of violation
                (secrets_detected, pii_in_storage, etc.)
            severity: LOW, MEDIUM, HIGH, or CRITICAL
            details: Additional details about the violation
            session_id: Session identifier
            blocked: Whether the action was blocked
            **kwargs: Additional custom fields

        Example:
            >>> logger.log_security_violation(
            ...     user_id="user@company.com",
            ...     violation_type="secrets_detected",
            ...     severity="HIGH",
            ...     details={
            ...         "secret_type": "api_key",
            ...         "action": "llm_request",
            ...     },  # pragma: allowlist secret
            ...     blocked=True,
            ... )

        """
        violation = SecurityViolation(
            violation_type=violation_type,
            severity=severity,
            details=details,
        )

        event = AuditEvent(
            event_type="security_violation",
            user_id=user_id,
            session_id=session_id,
            status="blocked" if blocked else "logged",
            data={
                "violation": {
                    "type": violation_type,
                    "severity": severity,
                    "details": details,
                    "blocked": blocked,
                },
                "response": {
                    "user_notified": (violation.user_notified),
                    "manager_notified": (violation.manager_notified),
                    "security_team_notified": (violation.security_team_notified),
                },
                "compliance": {
                    "gdpr_compliant": blocked,
                    "hipaa_compliant": blocked,
                    "soc2_compliant": blocked,
                },
                **kwargs,
            },
        )

        self._write_event(event)
