"""Path validation for MCP tool inputs.

Defends against CWE-22 (path traversal), null byte injection,
and writes to system directories. Used by every MCP handler
that accepts a user-controlled path.
"""

from __future__ import annotations

from pathlib import Path

# System directories that should never be written or read
# through user-controlled paths.
#
# We check both the original input path AND the resolved path
# against this blocklist. macOS-specific note: /etc, /var, /tmp
# are symlinks to /private/etc, /private/var, /private/tmp, and
# Path.resolve() follows those symlinks. Checking before AND
# after resolution catches symlink bypasses without blocking
# legitimate temp space under /var/folders.
_DANGEROUS_PREFIXES: tuple[str, ...] = (
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/boot",
    "/root",
    "/usr/sbin",
    "/usr/bin",
    "/sbin",
    "/bin",
    "/private/etc",
    "/private/sys",
    "/private/proc",
    "/private/dev",
    "/private/boot",
    "/private/root",
)


def _is_dangerous(path_str: str) -> str | None:
    """Return the matching dangerous prefix, or None."""
    for dangerous in _DANGEROUS_PREFIXES:
        if path_str == dangerous or path_str.startswith(dangerous + "/"):
            return dangerous
    return None


def validate_file_path(
    path: str,
    allowed_dir: str | None = None,
) -> Path:
    """Validate a user-controlled file path.

    Args:
        path: File or directory path from user input.
        allowed_dir: Optional restriction — the resolved path
            must be inside this directory.

    Returns:
        Resolved absolute Path object.

    Raises:
        ValueError: If the path is invalid, contains null
            bytes, escapes the allowed directory, or targets
            a system directory.
    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")

    if "\x00" in path:
        raise ValueError("path contains null bytes")

    # Check the input path BEFORE resolving — catches /etc on macOS
    # where Path.resolve() would follow the /etc -> /private/etc
    # symlink and bypass a post-resolve blocklist check.
    if path.startswith("/"):
        match = _is_dangerous(path)
        if match:
            raise ValueError(f"Cannot access system directory: {match}")

    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}") from e

    # Also check the resolved path — catches relative paths and
    # any symlinks pointing into system dirs.
    match = _is_dangerous(str(resolved))
    if match:
        raise ValueError(f"Cannot access system directory: {match}")

    # Workspace containment check
    if allowed_dir:
        try:
            allowed = Path(allowed_dir).resolve()
            resolved.relative_to(allowed)
        except ValueError as e:
            raise ValueError(f"Path '{path}' is outside allowed directory '{allowed_dir}'") from e

    return resolved
