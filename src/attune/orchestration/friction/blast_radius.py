"""Blast Radius Classifier for Attune AI.

Evaluates structural risk, file path sensitivity, and command
destructiveness to assign a blast radius score from 1 (lowest risk)
to 5 (highest risk).

The classifier is a fast heuristic, not a sandbox: destructive
patterns are checked FIRST (a chained ``ls && rm -rf`` must never
score as read-only), and paths are normalized to forward slashes so
the same file scores identically on Windows and POSIX.
"""

import os
import re

# Path patterns are anchored to a path segment boundary so that e.g.
# ``docs/oauth/notes.md`` does NOT match the ``auth/`` rule.
_CRITICAL_PATH_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"(^|/)auth/",
        r"(^|/)crypto/",
        r"(^|/)security/",
        r"(^|/)database/migrations/",
        r"(^|/)\.env(\.[\w.-]+)?$",
        r"(^|/)AGENTS\.md$",
        r"(^|/)contract\.md$",
    )
)

_DESTRUCTIVE_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        # rm with both recursive and force flags, in any order or grouping
        # (-rf, -fr, -r -f, --recursive --force).
        r"\brm\b(?=[^;|&]*\s-{1,2}[a-z-]*r)(?=[^;|&]*\s-{1,2}[a-z-]*f)",
        r"\bdrop\s+table\b",
        r"\btruncate\b",
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+clean\b[^;|&]*\s-[a-z]*f",
        r"\bgit\s+checkout\s+--\s",
        r"\bgit\s+push\b[^;|&]*(\s--force(-with-lease)?\b|\s-f\b)",
        r"\bgit\s+branch\s+-D\b",
    )
)

_MODIFYING_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bgit\s+commit\b",
        r"\bgit\s+push\b",
        r"\bpip\s+install\b",
        r"\buv\s+(add|pip\s+install)\b",
        r"\bmv\b",
        r"\brm\b",
    )
)

_READ_ONLY_PREFIX = re.compile(
    r"^(ls|git\s+(status|diff|log|show)|cat|head|tail|grep|find|wc"
    r"|pytest|python\s+-m\s+pytest)\b"
)

# Chaining/redirection tokens mean the first token no longer describes
# the whole command — a read-only prefix must not short-circuit.
_SHELL_CHAIN_TOKENS = re.compile(r"[;&|>`]|\$\(|<\(")


class BlastRadiusClassifier:
    """Classifies planned operations into numerical risk levels (1-5)."""

    def __init__(self, workspace_root: str | None = None) -> None:
        """Initialize classifier with optional workspace root.

        Args:
            workspace_root: Base directory for relative path calculation.
        """
        self.workspace_root = os.path.abspath(workspace_root) if workspace_root else os.getcwd()

    def evaluate_file_path(self, target_path: str, is_deletion: bool = False) -> int:
        """Evaluates blast radius score for a target file path.

        Args:
            target_path: Path to the target file.
            is_deletion: Whether the action deletes the target.

        Returns:
            Risk score integer between 1 and 5.
        """
        if not target_path:
            return 1

        rel_path = self._sanitize_and_relativize(target_path)
        base_score = 1

        if is_deletion:
            base_score += 2

        if any(p.search(rel_path) for p in _CRITICAL_PATH_PATTERNS):
            base_score += 3

        return min(5, max(1, base_score))

    def evaluate_command(self, command_line: str) -> int:
        """Evaluates blast radius score for a shell command string.

        Args:
            command_line: Full command line string proposed for execution.

        Returns:
            Risk score integer between 1 and 5.
        """
        if not command_line or not command_line.strip():
            return 1

        cmd = command_line.strip()

        # Destructive patterns dominate everything else, including a
        # read-only first token (``git status; git reset --hard``).
        if any(p.search(cmd) for p in _DESTRUCTIVE_COMMAND_PATTERNS):
            return 5

        # A read-only prefix only proves the command is read-only when
        # nothing is chained, piped, or redirected after it.
        if _READ_ONLY_PREFIX.match(cmd) and not _SHELL_CHAIN_TOKENS.search(cmd):
            return 1

        score = 1
        if any(p.search(cmd) for p in _MODIFYING_COMMAND_PATTERNS):
            score += 2

        return min(5, max(1, score))

    def _sanitize_and_relativize(self, raw_path: str) -> str:
        """Normalizes a path relative to workspace root with '/' separators."""
        abs_path = os.path.abspath(raw_path)
        try:
            rel = os.path.relpath(abs_path, self.workspace_root)
        except ValueError:
            rel = raw_path
        return rel.replace("\\", "/")
