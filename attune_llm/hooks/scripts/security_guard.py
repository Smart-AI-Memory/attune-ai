"""PreToolUse Security Validation Hook.

Intercepts tool calls to enforce coding standards at runtime:
1. Blocks eval()/exec() in Bash commands (CWE-95)
2. Validates file paths in Edit/Write operations (CWE-22)
3. Prevents writes to system directories
4. Blocks null byte injection in paths

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (reason printed to stderr)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Directories that must never be written to (includes macOS /private/* symlinks)
SYSTEM_DIRECTORIES = frozenset(
    {
        "/etc",
        "/sys",
        "/proc",
        "/dev",
        "/boot",
        "/sbin",
        "/usr/sbin",
        "/private/etc",
        "/private/var",
    }
)

# Dangerous patterns in Bash commands
DANGEROUS_BASH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\beval\s*\("),
        "Blocked: eval() is prohibited — use ast.literal_eval() instead (CWE-95)",
    ),
    (
        re.compile(r"\bexec\s*\("),
        "Blocked: exec() is prohibited — use safe alternatives (CWE-95)",
    ),
    (
        re.compile(r"__import__\s*\("),
        "Blocked: __import__() is prohibited — use standard imports (CWE-95)",
    ),
    (
        re.compile(r"subprocess\.call.*shell\s*=\s*True"),
        "Blocked: subprocess with shell=True is a shell injection risk (B602)",
    ),
    (
        re.compile(r"\brm\s+-rf\s+/(?!\S)"),
        "Blocked: rm -rf / is not allowed",
    ),
]

# Commands that search for dangerous patterns (not executing them)
SEARCH_COMMAND_PREFIXES = frozenset(
    {
        "grep",
        "rg",
        "ack",
        "ag",
        "git grep",
        "git log",
        "git diff",
    }
)


def _is_search_command(command: str) -> bool:
    """Check if a command is searching FOR dangerous patterns, not executing them.

    Args:
        command: The bash command string.

    Returns:
        True if the command is a search/grep operation.

    """
    stripped = command.strip()
    # Handle piped commands — check if the base command is a search
    base = stripped.split("|")[0].strip()
    for prefix in SEARCH_COMMAND_PREFIXES:
        if base.startswith(prefix):
            return True
    return False


def validate_bash_command(command: str) -> tuple[bool, str]:
    """Validate a Bash command against security policies.

    Args:
        command: The command string to validate.

    Returns:
        (True, "") if safe, (False, reason) if blocked.

    """
    if not command:
        return True, ""

    # Allow search commands that look for dangerous patterns
    if _is_search_command(command):
        return True, ""

    for pattern, message in DANGEROUS_BASH_PATTERNS:
        if pattern.search(command):
            return False, message

    return True, ""


def validate_file_path(file_path: str) -> tuple[bool, str]:
    """Validate a file path against security policies.

    Args:
        file_path: The file path to validate.

    Returns:
        (True, "") if safe, (False, reason) if blocked.

    """
    if not file_path:
        return True, ""

    # Check for null bytes
    if "\x00" in file_path:
        return False, "Blocked: file path contains null bytes (CWE-22)"

    # Check both raw path and resolved path against system directories
    # (on macOS, /etc resolves to /private/etc via symlink)
    try:
        resolved = str(Path(file_path).resolve())
    except (OSError, RuntimeError) as e:
        return False, f"Blocked: invalid file path — {e}"

    raw_abs = str(Path(file_path).expanduser()) if file_path.startswith("~") else file_path
    paths_to_check = {resolved, raw_abs}

    for check_path in paths_to_check:
        for sys_dir in SYSTEM_DIRECTORIES:
            if check_path.startswith(sys_dir):
                return False, f"Blocked: cannot write to system directory {sys_dir} (CWE-22)"

    return True, ""


def main(context: dict[str, Any]) -> dict[str, Any]:
    """Validate a tool call against security policies.

    Args:
        context: Hook context with tool_name and tool_input from Claude Code.

    Returns:
        {"allowed": True} or {"allowed": False, "reason": "..."}.

    """
    tool_name = context.get("tool_name", "")
    tool_input = context.get("tool_input", {})

    if not tool_name:
        # No tool info — fail closed (block unknown tool calls)
        return {"allowed": False, "reason": "Blocked: missing tool_name in hook context"}

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        allowed, reason = validate_bash_command(command)
        if not allowed:
            return {"allowed": False, "reason": reason}

    elif tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        allowed, reason = validate_file_path(file_path)
        if not allowed:
            return {"allowed": False, "reason": reason}

    return {"allowed": True}


def _read_stdin_context() -> dict[str, Any]:
    """Read hook context from stdin (Claude Code protocol).

    Returns:
        Parsed context dict, or empty dict if stdin is empty/invalid.

    """
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse stdin JSON (fail-closed): %s", e)
    return {"_parse_error": True}


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    context = _read_stdin_context()

    # Fail-closed: if we couldn't parse stdin, block the tool call
    if context.get("_parse_error"):
        print("Blocked: could not parse hook context (fail-closed)", file=sys.stderr)
        sys.exit(2)

    result = main(context)

    if not result.get("allowed", False):
        # Block: print reason to stderr, exit 2
        reason = result.get("reason", "Blocked by security guard")
        print(reason, file=sys.stderr)
        sys.exit(2)

    # Allow: exit 0
    sys.exit(0)
