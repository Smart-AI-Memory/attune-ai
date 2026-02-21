"""Security Module for Attune AI.

Re-exports security components from attune.memory.security for
convenience. Consumers can use either:

    from attune.security import PIIScrubber
    from attune.memory.security import PIIScrubber

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune.memory.security import (
    AuditEvent,
    AuditLogger,
    PIIDetection,
    PIIPattern,
    PIIScrubber,
    SecretDetection,
    SecretsDetector,
    SecretType,
    SecurityViolation,
    Severity,
    detect_secrets,
)
from attune.security.path_validation import _validate_file_path

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "PIIDetection",
    "PIIPattern",
    "PIIScrubber",
    "SecretDetection",
    "SecretType",
    "SecretsDetector",
    "SecurityViolation",
    "Severity",
    "_validate_file_path",
    "detect_secrets",
]
