"""Classification and access control logic for long-term memory.

Extracted from long_term.py for modularity. Contains:
- Pattern auto-classification based on content and type
- Access control checks based on classification level
- Keyword constants for classification heuristics

Architecture:
    Content + Type -> classify_pattern() -> Classification
    User + Classification + Metadata -> check_access() -> bool

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from typing import Any

import structlog

from .long_term_types import Classification

logger = structlog.get_logger(__name__)

# ============================================================================
# Classification Keywords
# ============================================================================

# SENSITIVE: Healthcare keywords (HIPAA)
HEALTHCARE_KEYWORDS: list[str] = [
    "patient",
    "medical",
    "diagnosis",
    "treatment",
    "healthcare",
    "clinical",
    "hipaa",
    "phi",
    "medical record",
    "prescription",
]

# SENSITIVE: Financial keywords
FINANCIAL_KEYWORDS: list[str] = [
    "financial",
    "payment",
    "credit card",
    "banking",
    "transaction",
    "pci dss",
    "payment card",
]

# INTERNAL: Proprietary keywords
PROPRIETARY_KEYWORDS: list[str] = [
    "proprietary",
    "confidential",
    "internal",
    "trade secret",
    "company confidential",
    "restricted",
]

# Pattern types that map to SENSITIVE classification
SENSITIVE_PATTERN_TYPES: list[str] = [
    "clinical_protocol",
    "medical_guideline",
    "patient_workflow",
    "financial_procedure",
]

# Pattern types that map to INTERNAL classification
INTERNAL_PATTERN_TYPES: list[str] = [
    "architecture",
    "business_logic",
    "company_process",
]


def classify_pattern(content: str, pattern_type: str) -> Classification:
    """Auto-classify pattern based on content and type.

    Classification heuristics:
    - SENSITIVE: Healthcare, financial, regulated data keywords
    - INTERNAL: Proprietary, confidential, internal keywords
    - PUBLIC: Everything else (general patterns)

    Args:
        content: Pattern content (already PII-scrubbed)
        pattern_type: Type of pattern

    Returns:
        Classification level

    """
    content_lower = content.lower()

    # Check for SENSITIVE indicators
    if any(keyword in content_lower for keyword in HEALTHCARE_KEYWORDS):
        return Classification.SENSITIVE

    if any(keyword in content_lower for keyword in FINANCIAL_KEYWORDS):
        return Classification.SENSITIVE

    # Pattern type based classification
    if pattern_type in SENSITIVE_PATTERN_TYPES:
        return Classification.SENSITIVE

    # Check for INTERNAL indicators
    if any(keyword in content_lower for keyword in PROPRIETARY_KEYWORDS):
        return Classification.INTERNAL

    if pattern_type in INTERNAL_PATTERN_TYPES:
        return Classification.INTERNAL

    # Default to PUBLIC for general patterns
    return Classification.PUBLIC


def check_access(
    user_id: str,
    classification: Classification,
    metadata: dict[str, Any],
) -> bool:
    """Check if user has access to pattern based on classification.

    Access rules:
    - PUBLIC: All users
    - INTERNAL: Users on project team (simplified: always granted for demo)
    - SENSITIVE: Explicit permission required (simplified: creator only)

    Args:
        user_id: User requesting access
        classification: Pattern classification
        metadata: Pattern metadata

    Returns:
        True if access granted, False otherwise

    """
    # PUBLIC: Everyone has access
    if classification == Classification.PUBLIC:
        return True

    # INTERNAL: Check project team membership
    # Simplified: Grant access (production would check team membership)
    if classification == Classification.INTERNAL:
        logger.warning(
            "internal_access_stub",
            user_id=user_id,
            message="INTERNAL stub always grants access; "
            "replace with team membership check in production",
        )
        return True

    # SENSITIVE: Require explicit permission
    # Simplified: Only pattern creator has access
    if classification == Classification.SENSITIVE:
        created_by = str(metadata.get("created_by", ""))
        granted = user_id == created_by

        logger.debug(
            "sensitive_access_check",
            user_id=user_id,
            created_by=created_by,
            granted=granted,
        )

        return bool(granted)

    # Default deny
    return False


__all__ = [
    "FINANCIAL_KEYWORDS",
    "HEALTHCARE_KEYWORDS",
    "INTERNAL_PATTERN_TYPES",
    "PROPRIETARY_KEYWORDS",
    "SENSITIVE_PATTERN_TYPES",
    "check_access",
    "classify_pattern",
]
