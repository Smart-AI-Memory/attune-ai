"""Validation utilities for Memory Control Panel.

Security validation functions for pattern IDs, agent IDs, classifications,
and file paths. Used by both the MemoryControlPanel class and the API handler.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

from __future__ import annotations

import re
from pathlib import Path

# Pattern ID validation regex - matches format: pat_YYYYMMDDHHMMSS_hexstring
PATTERN_ID_REGEX = re.compile(r"^pat_\d{14}_[a-f0-9]{8,16}$")

# Alternative pattern formats that are also valid
PATTERN_ID_ALT_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{2,63}$")

# Rate limiting configuration
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 100  # Per IP per window


def _validate_pattern_id(pattern_id: str) -> bool:
    """Validate pattern ID to prevent path traversal and injection attacks.

    Args:
        pattern_id: The pattern ID to validate

    Returns:
        True if valid, False otherwise

    """
    if not pattern_id or not isinstance(pattern_id, str):
        return False

    # Check for path traversal attempts
    if ".." in pattern_id or "/" in pattern_id or "\\" in pattern_id:
        return False

    # Check for null bytes
    if "\x00" in pattern_id:
        return False

    # Check length bounds
    if len(pattern_id) < 3 or len(pattern_id) > 64:
        return False

    # Must match one of the valid formats
    return bool(PATTERN_ID_REGEX.match(pattern_id) or PATTERN_ID_ALT_REGEX.match(pattern_id))


def _validate_agent_id(agent_id: str) -> bool:
    """Validate agent ID format.

    Args:
        agent_id: The agent ID to validate

    Returns:
        True if valid, False otherwise

    """
    if not agent_id or not isinstance(agent_id, str):
        return False

    # Check for dangerous characters (path separators, null bytes, command injection)
    # Note: "." and "@" are allowed for email-style user IDs
    if any(c in agent_id for c in ["/", "\\", "\x00", ";", "|", "&"]):
        return False

    # Check length bounds
    if len(agent_id) < 1 or len(agent_id) > 64:
        return False

    # Simple alphanumeric with some allowed chars
    return bool(re.match(r"^[a-zA-Z0-9_@.-]+$", agent_id))


def _validate_classification(classification: str | None) -> bool:
    """Validate classification parameter.

    Args:
        classification: The classification to validate

    Returns:
        True if valid, False otherwise

    """
    if classification is None:
        return True
    if not isinstance(classification, str):
        return False
    return classification.upper() in ("PUBLIC", "INTERNAL", "SENSITIVE")


def _validate_file_path(path: str, allowed_dir: str | None = None) -> Path:
    """Validate file path to prevent path traversal and arbitrary writes.

    Args:
        path: Path to validate
        allowed_dir: Optional directory that must contain the path

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid or outside allowed directory

    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")

    # Check for null bytes
    if "\x00" in path:
        raise ValueError("path contains null bytes")

    try:
        # Resolve to absolute path
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")

    # Check if within allowed directory
    if allowed_dir:
        try:
            allowed = Path(allowed_dir).resolve()
            resolved.relative_to(allowed)
        except ValueError:
            raise ValueError(f"path must be within {allowed_dir}")

    # Check for dangerous system paths (cross-platform)
    import sys

    resolved_str = str(resolved)
    if sys.platform == "win32":
        resolved_lower = resolved_str.lower()
        win_dangerous = [
            "\\windows\\system32",
            "\\windows\\syswow64",
            "\\program files",
        ]
        for dangerous in win_dangerous:
            if dangerous in resolved_lower:
                raise ValueError(f"Cannot write to system directory: {dangerous}")
        for marker in ["\\etc\\", "\\sys\\", "\\proc\\", "\\dev\\"]:
            if marker in resolved_lower or resolved_lower.endswith(marker.rstrip("\\")):
                raise ValueError(f"Cannot write to system directory: {marker.strip(chr(92))}")
    else:
        dangerous_paths = ["/etc", "/sys", "/proc", "/dev"]
        for dangerous in dangerous_paths:
            if resolved_str.startswith(dangerous + "/") or resolved_str == dangerous:
                raise ValueError(f"Cannot write to system directory: {dangerous}")

    return resolved
