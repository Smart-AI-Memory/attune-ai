"""Empathy LLM - Security Module

Security initialization, production environment detection, and security
pipeline processing for EmpathyLLM.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
import time
from typing import Any

from attune.memory import (
    AuditLogger,
    PIIScrubber,
    SecretsDetector,
    SecurityError,
)

logger = logging.getLogger(__name__)


class SecurityMixin:
    """Mixin providing security capabilities for EmpathyLLM.

    Handles PII scrubbing, secrets detection, audit logging,
    and production environment detection.

    Attributes:
        enable_security: Whether security controls are active.
        security_config: Configuration dictionary for security modules.
        pii_scrubber: PII detection and scrubbing instance.
        secrets_detector: Secrets detection instance.
        audit_logger: Audit logging instance.

    """

    # These attributes are declared here for type-checking clarity.
    # They are set by the EmpathyLLM __init__.
    enable_security: bool
    security_config: dict
    pii_scrubber: PIIScrubber | None
    secrets_detector: SecretsDetector | None
    audit_logger: AuditLogger | None

    def _detect_production_environment(self) -> bool:
        """Detect if running in a production environment.

        Checks common environment indicators:
        - NODE_ENV=production
        - ENVIRONMENT=production or ENVIRONMENT=prod
        - FLASK_ENV=production
        - DJANGO_ENV=production
        - RAILWAY_ENVIRONMENT=production (Railway)
        - VERCEL_ENV=production (Vercel)
        - AWS_EXECUTION_ENV (Lambda)
        - KUBERNETES_SERVICE_HOST (K8s)
        - DYNO (Heroku)

        Returns:
            True if production indicators are detected

        """
        import os

        # Explicit production indicators
        production_vars = {
            "NODE_ENV": "production",
            "ENVIRONMENT": ("production", "prod"),
            "FLASK_ENV": "production",
            "DJANGO_ENV": "production",
            "RAILWAY_ENVIRONMENT": "production",
            "VERCEL_ENV": "production",
        }

        for var, expected in production_vars.items():
            value = os.getenv(var, "").lower()
            if isinstance(expected, tuple):
                if value in expected:
                    return True
            elif value == expected:
                return True

        # Platform-specific indicators (presence implies production)
        production_platform_vars = [
            "AWS_EXECUTION_ENV",  # AWS Lambda
            "KUBERNETES_SERVICE_HOST",  # Kubernetes
            "DYNO",  # Heroku
            "RENDER_SERVICE_ID",  # Render
            "FLY_APP_NAME",  # Fly.io
        ]

        for var in production_platform_vars:
            if os.getenv(var):
                return True

        return False

    def _run_security_input_pipeline(
        self,
        user_id: str,
        user_input: str,
    ) -> tuple[str, list[dict], list[dict], dict[str, Any]]:
        """Run the security input pipeline: PII scrubbing and secrets detection.

        Args:
            user_id: Unique user identifier.
            user_input: Raw user input text.

        Returns:
            Tuple of (sanitized_input, pii_detections, secrets_detections,
            security_metadata).

        Raises:
            SecurityError: If secrets detected and block_on_secrets=True.

        """
        pii_detections: list[dict] = []
        secrets_detections: list[dict] = []
        sanitized_input = user_input
        security_metadata: dict[str, Any] = {}

        # Step 1 - PII Scrubbing
        if self.enable_security and self.pii_scrubber:
            sanitized_input, pii_detections = self.pii_scrubber.scrub(user_input)
            security_metadata["pii_detected"] = len(pii_detections)
            security_metadata["pii_scrubbed"] = len(pii_detections) > 0
            if pii_detections:
                logger.info(
                    "PII detected: %d item(s) scrubbed",
                    len(pii_detections),
                )

        # Step 2 - Secrets Detection
        if self.enable_security and self.secrets_detector:
            secrets_detections = self.secrets_detector.detect(sanitized_input)
            security_metadata["secrets_detected"] = len(secrets_detections)

            if secrets_detections:
                block_on_secrets = self.security_config.get("block_on_secrets", True)
                logger.warning(
                    "Secrets detected: %d secret(s), blocking=%s",
                    len(secrets_detections),
                    block_on_secrets,
                )

                # Log security violation
                if self.audit_logger:
                    self.audit_logger.log_security_violation(
                        user_id=user_id,
                        violation_type="secrets_detected",
                        severity="HIGH",
                        details={
                            "secret_count": len(secrets_detections),
                            "secret_types": [s.secret_type.value for s in secrets_detections],
                            "event_type": "llm_request",
                        },
                        blocked=block_on_secrets,
                    )

                if block_on_secrets:
                    raise SecurityError(
                        f"Request blocked: {len(secrets_detections)} secret(s) detected in input. "
                        f"Please remove sensitive credentials before submitting.",
                    )

        return sanitized_input, pii_detections, secrets_detections, security_metadata

    def _run_security_audit_log(
        self,
        user_id: str,
        user_input: str,
        result: dict[str, Any],
        level: int,
        pii_detections: list[dict],
        secrets_detections: list[dict],
        start_time: float,
    ) -> None:
        """Run the security audit logging step after a successful interaction.

        Args:
            user_id: Unique user identifier.
            user_input: Original (unsanitized) user input.
            result: The interaction result dictionary.
            level: Empathy level used.
            pii_detections: List of PII detections from input pipeline.
            secrets_detections: List of secrets detections from input pipeline.
            start_time: Timestamp when the interaction started.

        """
        if not (self.enable_security and self.audit_logger):
            return

        duration_ms = int((time.time() - start_time) * 1000)

        # Calculate approximate sizes
        request_size_bytes = len(user_input.encode("utf-8"))
        response_size_bytes = len(result["content"].encode("utf-8"))

        # Extract memory sources if Claude Memory is enabled
        memory_sources: list[str] = []
        if getattr(self, "_cached_memory", None):
            memory_sources = ["claude_memory"]

        self.audit_logger.log_llm_request(
            user_id=user_id,
            empathy_level=level,
            provider=self.provider.__class__.__name__.replace("Provider", "").lower(),
            model=result.get("metadata", {}).get("model", "unknown"),
            memory_sources=memory_sources,
            pii_count=len(pii_detections),
            secrets_count=len(secrets_detections),
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            duration_ms=duration_ms,
            sanitization_applied=len(pii_detections) > 0,
            classification_verified=True,
            status="success",
        )
