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

from pathlib import Path
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


def resolve_current_workspace() -> str:
    """The workspace identity of the RUNNING process.

    Walks up for a ``.git`` marker so any working directory inside one
    checkout resolves to a single identity; falls back to the working
    directory itself. Never raises — an unresolvable cwd (deleted or
    unreadable) yields ``""``, which the INTERNAL rule treats as
    "unknown, cannot prove a match" and refuses for stamped records.

    Returns:
        An absolute path string, or ``""`` when the cwd is unreadable.
    """
    try:
        start = Path.cwd().resolve()
    except OSError:
        return ""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return str(start)


def check_access(
    user_id: str,
    classification: Classification,
    metadata: dict[str, Any],
    *,
    current_workspace: str | None = None,
) -> bool:
    """Check if user has access to pattern based on classification.

    Access rules:
    - PUBLIC: All users
    - INTERNAL: Same workspace (cross-project isolation)
    - SENSITIVE: Creator only

    The workspace being compared against comes from the CALLER, never
    from the record under inspection. Library-review I-3: both operands
    used to be read from the same stored dict, so nothing a caller
    supplied took part in the decision and the branch could not deny —
    and since no writer ever set ``current_workspace``, it never even
    ran. A control that reads as enforcement and enforces nothing is
    worse than a documented absence.

    Args:
        user_id: User requesting access
        classification: Pattern classification
        metadata: Pattern metadata
        current_workspace: The reading process's workspace. Defaults to
            :func:`resolve_current_workspace`. ``""`` means "unknown",
            which DENIES a workspace-stamped record — see the asymmetry
            note at the INTERNAL branch — while an unstamped (legacy)
            record is granted regardless.

    Returns:
        True if access granted, False otherwise

    """
    # PUBLIC: Everyone has access
    if classification == Classification.PUBLIC:
        return True

    # INTERNAL: Workspace-scoped access.
    # Patterns created in one project are invisible from another.
    #
    # The two "unknowns" here are NOT symmetric (codex D11 lane,
    # 2026-08-20). An UNSTAMPED record predates the stamp and there is
    # nothing to enforce, so it is granted for backward compatibility.
    # A STAMPED record whose reader cannot name its own workspace is the
    # opposite case: the claim "invisible from another project" is
    # precisely what cannot be verified, so granting would assert
    # something unproven — and made the whole rule bypassable by running
    # from a deleted or unreadable working directory. That is refused.
    if classification == Classification.INTERNAL:
        pattern_workspace = str(metadata.get("workspace", ""))
        if not pattern_workspace:
            return True  # legacy record, nothing stamped to scope against

        reader_workspace = (
            resolve_current_workspace() if current_workspace is None else str(current_workspace)
        )
        if not reader_workspace:
            logger.warning(
                "internal_access_denied_unknown_workspace",
                user_id=user_id,
                pattern_workspace=pattern_workspace,
            )
            return False

        if pattern_workspace != reader_workspace:
            logger.warning(
                "internal_access_denied",
                user_id=user_id,
                pattern_workspace=pattern_workspace,
                current_workspace=reader_workspace,
            )
            return False

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
    "resolve_current_workspace",
    "classify_pattern",
]
