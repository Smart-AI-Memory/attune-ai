"""Secure MemDocs Integration for Enterprise Privacy.

This module is a backward-compatibility shim. The implementation has been
split into focused modules for maintainability:

- long_term_types.py: Data classes, enums, exceptions
- long_term_classification.py: Classification logic, access control
- long_term_integration.py: SecureMemDocsIntegration class
- encryption.py: EncryptionManager
- storage_backend.py: MemDocsStorage
- simple_storage.py: LongTermMemory

All public APIs are re-exported here so existing imports continue to work:

    from attune.memory.long_term import SecureMemDocsIntegration
    from attune.memory.long_term import Classification, LongTermMemory

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

# Re-export encryption
from .encryption import HAS_ENCRYPTION, EncryptionManager

# Re-export classification and access control
from .long_term_classification import (
    FINANCIAL_KEYWORDS,
    HEALTHCARE_KEYWORDS,
    INTERNAL_PATTERN_TYPES,
    PROPRIETARY_KEYWORDS,
    SENSITIVE_PATTERN_TYPES,
    check_access,
    classify_pattern,
)

# Re-export the main integration class
from .long_term_integration import SecureMemDocsIntegration

# Re-export types
from .long_term_types import (
    DEFAULT_CLASSIFICATION_RULES,
    Classification,
    ClassificationRules,
    PatternMetadata,
    PermissionError,
    SecurePattern,
    SecurityError,
)

# Re-export security components
from .security.audit_logger import AuditEvent, AuditLogger
from .security.pii_scrubber import PIIScrubber
from .security.secrets_detector import SecretsDetector

# Re-export storage
from .simple_storage import LongTermMemory
from .storage_backend import MemDocsStorage

__all__ = [
    # Types (from long_term_types.py)
    "Classification",
    "ClassificationRules",
    "DEFAULT_CLASSIFICATION_RULES",
    "PatternMetadata",
    "SecurePattern",
    "SecurityError",
    "PermissionError",
    # Classification (from long_term_classification.py)
    "classify_pattern",
    "check_access",
    "HEALTHCARE_KEYWORDS",
    "FINANCIAL_KEYWORDS",
    "PROPRIETARY_KEYWORDS",
    "SENSITIVE_PATTERN_TYPES",
    "INTERNAL_PATTERN_TYPES",
    # Encryption (from encryption.py)
    "EncryptionManager",
    "HAS_ENCRYPTION",
    # Storage (from storage_backend.py)
    "MemDocsStorage",
    # Simple storage (from simple_storage.py)
    "LongTermMemory",
    # Security (from security/)
    "AuditEvent",
    "AuditLogger",
    "PIIScrubber",
    "SecretsDetector",
    # Main integration (from long_term_integration.py)
    "SecureMemDocsIntegration",
]
