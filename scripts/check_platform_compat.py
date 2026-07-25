#!/usr/bin/env python3
"""Cross-Platform Compatibility Checker for Attune AI

Scans the codebase for common cross-platform issues:
- Hardcoded Unix paths (/var/log, /tmp, etc.)
- open() calls without encoding specified
- os.path operations that should use pathlib

Usage:
    python scripts/check_platform_compat.py [--fix] [--strict]

Options:
    --fix       Show suggested fixes (doesn't modify files)
    --strict    Exit with error code if issues found
    --json      Output results as JSON

Can be integrated into CI:
    - Run as pre-commit hook
    - Add to GitHub Actions workflow
    - Run as part of pytest

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Issue:
    """Represents a cross-platform compatibility issue."""

    file: str
    line: int
    category: str
    message: str
    severity: str  # "error", "warning", "info"
    suggestion: str = ""


@dataclass
class ScanResult:
    """Results of a compatibility scan."""

    issues: list[Issue] = field(default_factory=list)
    files_scanned: int = 0
    errors: int = 0
    warnings: int = 0
    info: int = 0

    def add_issue(self, issue: Issue) -> None:
        """Add an issue and update counts."""
        self.issues.append(issue)
        if issue.severity == "error":
            self.errors += 1
        elif issue.severity == "warning":
            self.warnings += 1
        else:
            self.info += 1


# Patterns to detect
HARDCODED_PATHS = [
    (r'["\']\/var\/log\/', "Hardcoded /var/log path"),
    (r'["\']\/tmp\/', "Hardcoded /tmp path"),
    (r'["\']\/etc\/', "Hardcoded /etc path"),
    (r'["\']\/home\/', "Hardcoded /home path"),
]

#: A ``~/…`` literal is NOT a cross-platform defect on its own —
#: ``expanduser()`` resolves it on every platform, Windows included, and
#: ``"~/.attune/x"`` + ``.expanduser()`` is this repo's portable idiom (and
#: was 15 of the 22 warnings the first baseline froze). It is a bug only
#: when handed straight to a filesystem call unexpanded, which fails
#: everywhere including Linux. So the rule fires on that COMBINATION,
#: never on the literal.
TILDE_LITERAL = re.compile(r'["\']~[\\/]')
FILESYSTEM_CALL = re.compile(
    r"\b(?:open|Path|PurePath|io\.open|os\.\w+|os\.path\.\w+|shutil\.\w+)\s*\(",
)


def docstring_line_numbers(content: str) -> set[int]:
    """1-based line numbers occupied by module/class/function docstrings."""
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return set()

    numbers: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            numbers.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return numbers


def code_lines(content: str) -> list[str]:
    """Split ``content`` into lines with comments and docstrings blanked.

    A scanner that matches prose reports the CODE COMMENT WARNING ABOUT a
    hardcoded path as a hardcoded path — four of the first baseline's 22
    entries were exactly that, including a comment explaining a Windows
    path bug. Blanking keeps line numbers intact so reported lines still
    point at the real source.
    """
    lines = content.split("\n")

    try:
        for token in tokenize.generate_tokens(io.StringIO(content).readline):
            if token.type != tokenize.COMMENT:
                continue
            row, col = token.start
            if 1 <= row <= len(lines):
                lines[row - 1] = lines[row - 1][:col]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Unparseable file — fall back to the raw lines rather than
        # silently scanning nothing.
        lines = content.split("\n")

    for row in docstring_line_numbers(content):
        if 1 <= row <= len(lines):
            lines[row - 1] = ""

    return lines


OPEN_WITHOUT_ENCODING = re.compile(
    r"\bopen\s*\([^)]*\)\s*(?:as\s+\w+)?(?!\s*#.*encoding)",
    re.MULTILINE,
)

OS_PATH_OPERATIONS = [
    (r"\bos\.path\.join\s*\(", "Consider using pathlib.Path instead of os.path.join"),
    (r"\bos\.path\.exists\s*\(", "Consider using Path.exists() instead"),
    (r"\bos\.path\.dirname\s*\(", "Consider using Path.parent instead"),
    (r"\bos\.path\.basename\s*\(", "Consider using Path.name instead"),
]


def scan_file(filepath: Path, result: ScanResult) -> None:
    """Scan a single Python file for compatibility issues."""
    try:
        content = filepath.read_text(encoding="utf-8")
        # Comments and docstrings are prose, not code — scanning them
        # reports discussion of a defect as the defect itself.
        lines = code_lines(content)
        relative_path = str(filepath)

        # Check for hardcoded paths
        for line_num, line in enumerate(lines, 1):
            for pattern, message in HARDCODED_PATHS:
                if re.search(pattern, line):
                    result.add_issue(
                        Issue(
                            file=relative_path,
                            line=line_num,
                            category="hardcoded_path",
                            message=message,
                            severity="warning",
                            suggestion="Use attune.platform_utils for platform-appropriate paths",
                        ),
                    )
            if (
                TILDE_LITERAL.search(line)
                and FILESYSTEM_CALL.search(line)
                and "expanduser" not in line
            ):
                result.add_issue(
                    Issue(
                        file=relative_path,
                        line=line_num,
                        category="hardcoded_path",
                        message="Unexpanded '~' passed to a filesystem call",
                        severity="warning",
                        suggestion='Wrap it: Path("~/…").expanduser()',
                    ),
                )

        # Check for open() without encoding
        for line_num, line in enumerate(lines, 1):
            if "open(" in line and "encoding" not in line:
                # Skip binary mode opens
                if "'rb'" in line or '"rb"' in line or "'wb'" in line or '"wb"' in line:
                    continue
                # Check if it's a text mode open
                if (
                    "'r'" in line
                    or '"r"' in line
                    or "'w'" in line
                    or '"w"' in line
                    or "'a'" in line
                    or '"a"' in line
                ):
                    result.add_issue(
                        Issue(
                            file=relative_path,
                            line=line_num,
                            category="missing_encoding",
                            message="open() without encoding specified",
                            # ERROR, not warning: on Windows a text-mode
                            # open() without encoding uses the locale
                            # codepage (typically cp1252), not UTF-8 —
                            # the highest-yield source of Windows-only
                            # failures in this repo. Gated as of the
                            # encoding-first ratchet; the remaining
                            # warning categories are baselined and will
                            # be promoted in turn.
                            severity="error",
                            suggestion='Add encoding="utf-8" parameter',
                        ),
                    )

        # Check for os.path operations
        for line_num, line in enumerate(lines, 1):
            for pattern, message in OS_PATH_OPERATIONS:
                if re.search(pattern, line):
                    result.add_issue(
                        Issue(
                            file=relative_path,
                            line=line_num,
                            category="os_path",
                            message=message,
                            severity="info",
                            suggestion="Use pathlib.Path for cross-platform path handling",
                        ),
                    )

        result.files_scanned += 1

    except Exception as e:
        result.add_issue(
            Issue(
                file=str(filepath),
                line=0,
                category="scan_error",
                message=f"Could not scan file: {e}",
                severity="error",
            ),
        )


def scan_directory(
    directory: Path,
    exclude_dirs: list[str] | None = None,
) -> ScanResult:
    """Scan a directory for cross-platform compatibility issues."""
    result = ScanResult()
    exclude_dirs = exclude_dirs or [
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        "*.egg-info",
    ]

    for filepath in directory.rglob("*.py"):
        # Skip excluded directories
        skip = False
        for exclude in exclude_dirs:
            if exclude in str(filepath):
                skip = True
                break
        if skip:
            continue

        scan_file(filepath, result)

    return result


def format_text_report(result: ScanResult, show_suggestions: bool = False) -> str:
    """Format scan results as text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("Cross-Platform Compatibility Report")
    lines.append("=" * 60)
    lines.append(f"Files scanned: {result.files_scanned}")
    lines.append(f"Errors: {result.errors}")
    lines.append(f"Warnings: {result.warnings}")
    lines.append(f"Info: {result.info}")
    lines.append("")

    if result.issues:
        # Group by file
        by_file: dict[str, list[Issue]] = {}
        for issue in result.issues:
            if issue.file not in by_file:
                by_file[issue.file] = []
            by_file[issue.file].append(issue)

        for filepath, issues in sorted(by_file.items()):
            lines.append(f"\n{filepath}:")
            for issue in sorted(issues, key=lambda x: x.line):
                icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "•")
                lines.append(f"  {icon} Line {issue.line}: {issue.message}")
                if show_suggestions and issue.suggestion:
                    lines.append(f"      → {issue.suggestion}")
    else:
        lines.append("\n✅ No cross-platform compatibility issues found!")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json_report(result: ScanResult) -> str:
    """Format scan results as JSON."""
    return json.dumps(
        {
            "summary": {
                "files_scanned": result.files_scanned,
                "errors": result.errors,
                "warnings": result.warnings,
                "info": result.info,
                "total_issues": len(result.issues),
            },
            "issues": [
                {
                    "file": issue.file,
                    "line": issue.line,
                    "category": issue.category,
                    "message": issue.message,
                    "severity": issue.severity,
                    "suggestion": issue.suggestion,
                }
                for issue in result.issues
            ],
        },
        indent=2,
    )


#: Default location of the accepted-warning baseline. Root-level, matching
#: the `.secrets.baseline` convention already used here.
DEFAULT_BASELINE = ".platform-compat-baseline.json"


def baseline_key(issue: "Issue") -> str:
    """Stable key for a warning: file + category, NOT line.

    Line numbers shift whenever anything above them moves, so keying on
    them would make the baseline fail on unrelated edits — noise that
    trains people to regenerate it reflexively, which defeats the gate.
    File+category with a count is stable under reformatting and still
    catches "this file grew a new hardcoded path".
    """
    return f"{issue.file}::{issue.category}"


def build_baseline(result: "ScanResult") -> dict[str, int]:
    """Count current warnings per file+category."""
    counts: dict[str, int] = {}
    for issue in result.issues:
        if issue.severity != "warning":
            continue
        counts[baseline_key(issue)] = counts.get(baseline_key(issue), 0) + 1
    return dict(sorted(counts.items()))


def compare_to_baseline(
    result: "ScanResult", baseline: dict[str, int]
) -> tuple[list[str], list[str]]:
    """Return (regressions, improvements) against ``baseline``.

    A regression is a file+category with MORE warnings than accepted, or
    one absent from the baseline entirely. An improvement is one with
    fewer — reported so the baseline can be shrunk and the debt actually
    ratchets down instead of being frozen forever.
    """
    current = build_baseline(result)
    regressions = []
    for key, count in sorted(current.items()):
        accepted = baseline.get(key, 0)
        if count > accepted:
            where = "new" if key not in baseline else f"was {accepted}"
            regressions.append(f"{key}: {count} ({where})")
    improvements = []
    for key, accepted in sorted(baseline.items()):
        count = current.get(key, 0)
        if count < accepted:
            improvements.append(f"{key}: {count} (baseline allows {accepted})")
    return regressions, improvements


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check codebase for cross-platform compatibility issues",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Show suggested fixes",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error if any issues found",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional directories to exclude",
    )
    parser.add_argument(
        "--baseline",
        nargs="?",
        const=DEFAULT_BASELINE,
        help=(
            "Compare warnings against a baseline file and exit 1 on any "
            f"regression (default path: {DEFAULT_BASELINE})"
        ),
    )
    parser.add_argument(
        "--update-baseline",
        nargs="?",
        const=DEFAULT_BASELINE,
        help="Write the current warnings as the accepted baseline",
    )

    args = parser.parse_args()

    # Determine scan path
    scan_path = Path(args.path)
    if not scan_path.exists():
        print(f"Error: Path '{scan_path}' does not exist", file=sys.stderr)
        return 1

    # Run scan
    exclude_dirs = [
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
    ] + args.exclude

    result = scan_directory(scan_path, exclude_dirs)

    # Output results
    if args.json:
        print(format_json_report(result))
    else:
        print(format_text_report(result, show_suggestions=args.fix))

    # Write the baseline and stop — this is the "shrink it" path, run by
    # hand after fixing warnings, never automatically in CI (a baseline
    # that regenerates itself accepts every regression it was meant to
    # catch).
    if args.update_baseline:
        path = Path(args.update_baseline)
        counts = build_baseline(result)
        path.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        total = sum(counts.values())
        print(f"wrote {path} — {total} accepted warning(s) across {len(counts)} file/category")
        return 0

    exit_code = 0

    if args.baseline:
        path = Path(args.baseline)
        if not path.exists():
            print(f"Error: baseline '{path}' does not exist", file=sys.stderr)
            print(
                "Create it with --update-baseline once the current state is accepted.",
                file=sys.stderr,
            )
            return 1
        try:
            baseline = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            print(f"Error: baseline '{path}' is not valid JSON: {exc}", file=sys.stderr)
            return 1
        regressions, improvements = compare_to_baseline(result, baseline)
        if improvements:
            print(f"\n{len(improvements)} file/category improved since the baseline:")
            for line in improvements:
                print(f"  - {line}")
            print(f"Shrink it: python {sys.argv[0]} {args.path} --update-baseline")
        if regressions:
            print(f"\nNEW cross-platform warnings not in the baseline ({len(regressions)}):")
            for line in regressions:
                print(f"  - {line}")
            print("\nFix them, or accept them deliberately with --update-baseline.")
            exit_code = 1
        else:
            print("\nNo new cross-platform warnings.")

    # Exit code
    if args.strict and (result.errors > 0 or result.warnings > 0):
        return 1
    if result.errors > 0:
        return 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
