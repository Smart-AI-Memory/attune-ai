"""PreToolUse Security Validation Hook.

Intercepts tool calls to enforce coding standards at runtime:
1. Blocks eval()/exec() in shell commands (CWE-95)
2. Validates file paths in Edit/Write operations (CWE-22)
3. Prevents writes to system directories (POSIX and Windows)
4. Blocks null byte injection in paths

Cross-platform policy (see README "Platform support"):
- POSIX shells (macOS, Linux, WSL2, Git Bash): deny-pattern
  validation via POSIX_DENY_PATTERNS.
- PowerShell (native Windows, opt-in via
  CLAUDE_CODE_USE_POWERSHELL_TOOL=1): FAIL CLOSED — both deny sets
  apply AND every command segment's first token must be on a strict
  allowlist. Unknown commands are blocked, not silently passed.
- Unknown shell family: treated like PowerShell (strict mode).

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (reason printed to stderr)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import json
import logging
import os
import re
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

logger = logging.getLogger(__name__)

# Force utf-8 on stdout and stderr. On Windows the default cp1252
# encoding can't emit emoji/em-dash and would crash this hook (caught
# by the outer try/except → silent breakage). errors='replace'
# substitutes '?' for any stray non-encodable byte.
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

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
    },
)

# Windows equivalents — compared case-insensitively with normalized
# separators, so C:/windows/system32 and c:\WINDOWS both match.
WINDOWS_SYSTEM_DIRECTORIES: tuple[str, ...] = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
)

# Dangerous patterns in POSIX-family shell commands (bash, zsh, Git Bash)
POSIX_DENY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
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
        # Matches "rm -rf /" only when / is the final path (not /foo).
        # (?!\S) = negative lookahead ensures / is followed by whitespace
        # or end-of-string, so "rm -rf /tmp" is allowed but "rm -rf /"
        # is blocked.
        re.compile(r"\brm\s+-rf\s+/(?!\S)"),
        "Blocked: rm -rf / is not allowed",
    ),
]

# Backwards-compatible alias (pre-cross-platform public name).
DANGEROUS_BASH_PATTERNS = POSIX_DENY_PATTERNS

# Dangerous patterns in PowerShell commands. Applied IN ADDITION to
# the strict allowlist below — defense in depth, and the messages are
# more specific than the generic allowlist block.
POWERSHELL_DENY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(iex|Invoke-Expression)\b", re.IGNORECASE),
        "Blocked: Invoke-Expression is prohibited — PowerShell eval (CWE-95)",
    ),
    (
        re.compile(
            r"\b(iwr|curl|wget|Invoke-WebRequest|Invoke-RestMethod)\b[^|]*\|",
            re.IGNORECASE,
        ),
        "Blocked: piping downloaded content into another command is prohibited",
    ),
    (
        re.compile(r"\bSet-ExecutionPolicy\b", re.IGNORECASE),
        "Blocked: Set-ExecutionPolicy changes are not allowed from hooks",
    ),
    (
        re.compile(r"\bStart-Process\b.*-Verb\s+RunAs", re.IGNORECASE),
        "Blocked: elevation via Start-Process -Verb RunAs is not allowed",
    ),
    (
        re.compile(
            r"\b(Remove-Item|rm|del|rd)\b(?=.*-Recurse)(?=.*-Force)"
            r".*(?:[A-Za-z]:[\\/]\s*$|\\\\)",
            re.IGNORECASE,
        ),
        "Blocked: recursive forced delete of a drive root is not allowed",
    ),
    (
        re.compile(r"\b(eval|exec)\s*\("),
        "Blocked: eval()/exec() is prohibited (CWE-95)",
    ),
]

# Strict allowlist for PowerShell / unknown shell families: the first
# token of every command segment must be one of these. FAIL CLOSED —
# anything not recognized is blocked with a clear message (platform
# policy: native Windows + PowerShell is "limited" support).
STRICT_ALLOWED_FIRST_TOKENS = frozenset(
    {
        "attune",
        "black",
        "cat",
        "cd",
        "dir",
        "echo",
        "gh",
        "git",
        "ls",
        "mkdir",
        "mypy",
        "node",
        "npm",
        "npx",
        "pip",
        "pre-commit",
        "py",
        "pytest",
        "python",
        "ruff",
        "type",
        "uv",
        "where",
    },
)

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
    },
)


def detect_shell_family(context: dict[str, Any]) -> str:
    """Classify the shell family the command will run under.

    Returns one of ``"posix"``, ``"powershell"``, ``"unknown"``.

    Detection order (most to least explicit):
    1. An explicit tool/shell name in the hook payload. NOTE: the
       exact payload shape on native Windows is unverified — run
       .github/workflows/windows-payload-capture.yml (from main) to
       capture real payloads and tighten this; the assumptions are
       documented in tests/unit/hooks/test_cross_platform.py.
    2. On Windows: CLAUDE_CODE_USE_POWERSHELL_TOOL=1 → powershell;
       a configured Git Bash → posix; otherwise unknown.
    3. Non-Windows → posix.

    Unknown NEVER falls through to the permissive posix path — the
    caller applies strict mode (fail closed).
    """
    explicit = str(
        context.get("tool_name", "") or context.get("shell", ""),
    ).lower()
    if "powershell" in explicit or explicit == "pwsh":
        return "powershell"

    if os.name == "nt":
        if os.environ.get("CLAUDE_CODE_USE_POWERSHELL_TOOL") == "1":
            return "powershell"
        if os.environ.get("CLAUDE_CODE_GIT_BASH_PATH"):
            return "posix"
        return "unknown"

    return "posix"


def _is_search_command(command: str) -> bool:
    """Check if a command is searching FOR dangerous patterns, not executing them.

    Args:
        command: The shell command string.

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


def _split_command_segments(command: str) -> list[str]:
    """Split a compound command into segments for allowlist checking.

    Splits on newlines, ``;``, ``|``, and ``&`` so a disallowed
    command can't hide behind an allowed prefix.
    """
    segments = re.split(r"[\n;|&]+", command)
    return [seg.strip() for seg in segments if seg.strip()]


def _strict_allowlist_check(command: str) -> tuple[bool, str]:
    """FAIL-CLOSED validation for PowerShell / unknown shell families.

    Every segment's first token must be on
    :data:`STRICT_ALLOWED_FIRST_TOKENS`.
    """
    for segment in _split_command_segments(command):
        tokens = segment.split()
        first = tokens[0] if tokens else ""
        # strip PowerShell call operator and leading path syntax: & "cmd", .\cmd
        first = first.lstrip("&").strip("\"'").lstrip(".\\/").lower()
        if first.endswith(".exe"):
            first = first[:-4]
        if first and first not in STRICT_ALLOWED_FIRST_TOKENS:
            return False, (
                f"Blocked (strict mode): '{first}' is not on the PowerShell "
                "allowlist. Native Windows + PowerShell has limited support — "
                "security validation fails closed. Use Git Bash or WSL2 for "
                "full support, or extend STRICT_ALLOWED_FIRST_TOKENS."
            )
    return True, ""


def validate_shell_command(command: str, family: str = "posix") -> tuple[bool, str]:
    """Validate a shell command against security policies.

    Args:
        command: The command string to validate.
        family: Shell family from :func:`detect_shell_family`.

    Returns:
        (True, "") if safe, (False, reason) if blocked.

    """
    if not command:
        return True, ""

    if family == "posix":
        # Allow search commands that look for dangerous patterns
        if _is_search_command(command):
            return True, ""
        for pattern, message in POSIX_DENY_PATTERNS:
            if pattern.search(command):
                return False, message
        return True, ""

    # powershell + unknown: strict mode — both deny sets, then allowlist.
    for pattern, message in POSIX_DENY_PATTERNS + POWERSHELL_DENY_PATTERNS:
        if pattern.search(command):
            return False, message
    return _strict_allowlist_check(command)


def validate_bash_command(command: str) -> tuple[bool, str]:
    """Validate a POSIX shell command (legacy name; see validate_shell_command)."""
    return validate_shell_command(command, family="posix")


def _looks_like_windows_path(file_path: str) -> bool:
    """True for drive-letter or UNC paths regardless of host OS."""
    return bool(re.match(r"^[A-Za-z]:[\\/]", file_path)) or file_path.startswith("\\\\")


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
        if _looks_like_windows_path(check_path):
            normalized = str(PureWindowsPath(check_path)).lower()
            for win_dir in WINDOWS_SYSTEM_DIRECTORIES:
                if normalized.startswith(win_dir):
                    return False, (f"Blocked: cannot write to system directory {win_dir} (CWE-22)")

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
        # No tool info — fail open to avoid blocking Claude Code
        return {"allowed": True}

    if tool_name == "Bash" or "powershell" in tool_name.lower():
        command = tool_input.get("command", "")
        family = detect_shell_family(context)
        allowed, reason = validate_shell_command(command, family)
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

    Reads BYTES and decodes as UTF-8 explicitly — on Windows the
    text-mode stdin decodes as cp1252 and mangles non-ASCII payloads.

    Returns:
        Parsed context dict, or empty dict if stdin is empty/invalid.

    """
    if sys.stdin.isatty():
        return {}
    try:
        buffer = getattr(sys.stdin, "buffer", None)
        raw = (
            buffer.read().decode("utf-8", errors="replace")
            if buffer is not None
            else sys.stdin.read()
        ).strip()
        if raw:
            return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse stdin JSON (fail-closed): %s", e)
    return {"_parse_error": True}


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    context = _read_stdin_context()

    # Parse error: there is no command text to validate, so blocking
    # would brick every tool call (observed pre-2026). Fail open here;
    # the strict fail-closed path applies when a command IS present
    # but the shell family is PowerShell/unknown.
    if context.get("_parse_error"):
        sys.exit(0)

    result = main(context)

    if not result.get("allowed", False):
        # Block: print reason to stderr, exit 2
        reason = result.get("reason", "Blocked by security guard")
        print(reason, file=sys.stderr)
        sys.exit(2)

    # Allow: exit 0
    sys.exit(0)
