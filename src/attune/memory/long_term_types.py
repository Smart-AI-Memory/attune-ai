"""Type definitions for long-term memory system

This module contains data classes, enums, and exceptions used by the long-term
memory system. Extracted from long_term.py for better modularity and testability.

Key Types:
- Classification: Three-tier security classification system
- ClassificationRules: Security rules per classification level
- PatternMetadata: Metadata for stored patterns
- SecurePattern: Pattern with content and metadata
- SecurityError, PermissionError: Exception types

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Classification(Enum):
    """Three-tier classification system for MemDocs patterns"""

    PUBLIC = "PUBLIC"  # Shareable across organization, anonymized
    INTERNAL = "INTERNAL"  # Team/project only, no PII or secrets
    SENSITIVE = "SENSITIVE"  # Encrypted at rest, access-controlled (HIPAA, finance)


@dataclass
class ClassificationRules:
    """Security rules for each classification level"""

    classification: Classification
    encryption_required: bool
    retention_days: int
    access_level: str  # "all_users", "project_team", "explicit_permission"
    audit_all_access: bool = False


# Default classification rules based on enterprise security policy
DEFAULT_CLASSIFICATION_RULES: dict[Classification, ClassificationRules] = {
    Classification.PUBLIC: ClassificationRules(
        classification=Classification.PUBLIC,
        encryption_required=False,
        retention_days=365,
        access_level="all_users",
        audit_all_access=False,
    ),
    Classification.INTERNAL: ClassificationRules(
        classification=Classification.INTERNAL,
        encryption_required=False,
        retention_days=180,
        access_level="project_team",
        audit_all_access=False,
    ),
    Classification.SENSITIVE: ClassificationRules(
        classification=Classification.SENSITIVE,
        encryption_required=True,
        retention_days=90,
        access_level="explicit_permission",
        audit_all_access=True,
    ),
}


@dataclass
class PatternMetadata:
    """Metadata for stored MemDocs patterns"""

    pattern_id: str
    created_by: str
    created_at: str
    classification: str
    retention_days: int
    encrypted: bool
    pattern_type: str
    sanitization_applied: bool
    pii_removed: int
    secrets_detected: int
    #: The workspace the pattern was created in — the operand INTERNAL
    #: access scoping compares against the reading process's workspace.
    #: Empty means "unknown", which never denies (legacy patterns).
    workspace: str = ""
    access_control: dict[str, Any] = field(default_factory=dict)
    custom_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurePattern:
    """Represents a securely stored pattern"""

    pattern_id: str
    content: str
    metadata: PatternMetadata


class SecurityError(Exception):
    """Raised when security policy is violated"""


class MemoryPermissionError(Exception):
    """Raised when access is denied."""


# Backward-compat alias (deprecated)
PermissionError = MemoryPermissionError
