"""Shared utilities for real tool implementations.

Security:
    - All file operations validated with _validate_file_path()

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import sys
from pathlib import Path


def _validate_file_path(path: str) -> Path:
    """Validate file path to prevent path traversal (simplified version).

    Args:
        path: File path to validate

    Returns:
        Validated Path object

    Raises:
        ValueError: If path is invalid
    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")

    if "\x00" in path:
        raise ValueError("path contains null bytes")

    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}") from e

    # Block system directories (cross-platform)
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
        # Note: On macOS, /etc is a symlink to /private/etc, so check both
        dangerous_paths = [
            "/etc",
            "/sys",
            "/proc",
            "/dev",
            "/private/etc",
            "/private/var/root",
            "/usr/bin",
            "/usr/sbin",
            "/bin",
            "/sbin",
        ]
        for dangerous in dangerous_paths:
            if resolved_str.startswith(dangerous + "/") or resolved_str == dangerous:
                raise ValueError(f"Cannot write to system directory: {dangerous}")

    return resolved
