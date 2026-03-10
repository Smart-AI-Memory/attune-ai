"""Path validation utilities for Attune AI.

Provides security-critical file path validation to prevent
path traversal attacks (CWE-22). This module has zero internal
dependencies to avoid circular imports.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import sys
from pathlib import Path


def _validate_file_path(path: str, allowed_dir: str | None = None) -> Path:
    """Validate file path to prevent path traversal and arbitrary writes.

    Args:
        path: File path to validate
        allowed_dir: Optional directory to restrict writes to

    Returns:
        Validated Path object

    Raises:
        ValueError: If path is invalid or unsafe

    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")

    # Check for null bytes
    if "\x00" in path:
        raise ValueError("path contains null bytes")

    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}") from e

    # Check if within allowed directory
    if allowed_dir:
        try:
            allowed = Path(allowed_dir).resolve()
            resolved.relative_to(allowed)
        except ValueError:
            raise ValueError(f"path must be within {allowed_dir}") from None

    # Check for dangerous system paths (cross-platform)
    resolved_str = str(resolved)

    if sys.platform == "win32":
        # Windows system directories
        resolved_lower = resolved_str.lower()
        windows_dangerous = [
            "\\windows\\system32",
            "\\windows\\syswow64",
            "\\windows\\system",
            "\\program files",
            "\\program files (x86)",
        ]
        for dangerous in windows_dangerous:
            if dangerous in resolved_lower:
                raise ValueError(f"Cannot write to system directory: {dangerous}")
        # Also block Unix-style paths on Windows (e.g. /etc/passwd resolves to D:\etc\passwd)
        unix_markers = ["\\etc\\", "\\sys\\", "\\proc\\", "\\dev\\"]
        for marker in unix_markers:
            if marker in resolved_lower or resolved_lower.endswith(marker.rstrip("\\")):
                raise ValueError(f"Cannot write to system directory: {marker.strip(chr(92))}")
    else:
        # Unix/macOS system directories
        # Note: On macOS, /etc is a symlink to /private/etc, so we check both
        dangerous_paths = [
            "/etc",
            "/sys",
            "/proc",
            "/dev",
            "/private/etc",  # macOS: /etc -> /private/etc
            "/private/var/root",  # macOS: root's home directory
            "/usr/bin",  # System binaries
            "/usr/sbin",  # System admin binaries
            "/bin",  # Essential binaries
            "/sbin",  # System binaries
        ]
        for dangerous in dangerous_paths:
            if resolved_str.startswith(dangerous + "/") or resolved_str == dangerous:
                raise ValueError(f"Cannot write to system directory: {dangerous}")

    return resolved
