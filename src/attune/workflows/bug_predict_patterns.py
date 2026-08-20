"""Bug Prediction Pattern Detection Helpers.

Module-level helper functions for detecting bug-prone code patterns.
Extracted from bug_predict.py for maintainability.

Functions:
    _load_bug_predict_config: Load config from attune.config.yml
    _should_exclude_file: Glob-based file exclusion
    _is_acceptable_broad_exception: Context-aware exception analysis
    _has_problematic_exception_handlers: Broad exception detection
    _is_dangerous_eval_usage: eval/exec security scanning with false-positive filtering
    _remove_docstrings: Docstring removal for scanning
    _is_security_policy_line: Security documentation detection

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import fnmatch
import re
from pathlib import Path

import yaml


def _load_bug_predict_config() -> dict:
    """Load bug_predict configuration from attune.config.yml.

    Returns:
        Dict with bug_predict settings, or defaults if not found.

    """
    defaults = {
        "risk_threshold": 0.7,
        "exclude_files": [],
        "acceptable_exception_contexts": ["version", "config", "cleanup", "optional"],
    }

    config_paths = [
        Path("attune.config.yml"),
        Path("attune.config.yaml"),
        Path(".empathy.yml"),
        Path(".empathy.yaml"),
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    # A scalar config makes `"bug_predict" in config`
                    # raise TypeError; only a mapping can carry the key
                    # (library-review C3).
                    if isinstance(config, dict) and "bug_predict" in config:
                        bug_config = config["bug_predict"]
                        return {
                            "risk_threshold": bug_config.get(
                                "risk_threshold",
                                defaults["risk_threshold"],
                            ),
                            "exclude_files": bug_config.get(
                                "exclude_files",
                                defaults["exclude_files"],
                            ),
                            "acceptable_exception_contexts": bug_config.get(
                                "acceptable_exception_contexts",
                                defaults["acceptable_exception_contexts"],
                            ),
                        }
            except (yaml.YAMLError, OSError):
                pass

    return defaults


def _should_exclude_file(file_path: str, exclude_patterns: list[str]) -> bool:
    """Check if a file should be excluded based on glob patterns.

    Args:
        file_path: Path to the file
        exclude_patterns: List of glob patterns (e.g., "**/test_*.py")

    Returns:
        True if the file matches any exclusion pattern.

    """
    # Normalise to forward slashes for consistent matching
    normalised = file_path.replace("\\", "/")

    for pattern in exclude_patterns:
        if "**" in pattern:
            # Convert ** glob to fnmatch: replace ** with multi-segment wildcard
            # e.g. "**/test_*.py" -> "*test_*.py" (matches any depth)
            # e.g. "tests/**" -> "tests/*" (matches anything under tests/)
            # Convert ** globs to fnmatch patterns
            # "tests/**" should match "tests/unit/test_foo.py" (any depth)
            fn_pattern = pattern.replace("**", "*")
            # Also try with PurePosixPath.match semantics for recursive globs
            from pathlib import PurePosixPath

            if PurePosixPath(normalised).match(pattern):
                return True
            if fnmatch.fnmatch(normalised, fn_pattern):
                return True
        elif fnmatch.fnmatch(normalised, pattern) or fnmatch.fnmatch(
            Path(file_path).name,
            pattern,
        ):
            return True

    return False


def _check_version_context(before_text: str, after_text: str) -> bool:
    """Check for version/metadata detection with fallback."""
    if any(kw in before_text for kw in ["get_version", "version", "metadata", "__version__"]):
        return any(kw in after_text for kw in ["return", "dev", "unknown", "0.0.0"])
    return False


def _check_config_context(before_text: str, after_text: str) -> bool:
    """Check for config loading with default fallback."""
    if any(kw in before_text for kw in ["config", "settings", "yaml", "json", "load"]):
        return any(kw in after_text for kw in ["pass", "default", "fallback"])
    return False


def _check_optional_context(before_text: str, after_text: str) -> bool:
    """Check for optional import/feature detection."""
    if "import" in before_text or "hasattr" in before_text:
        return any(kw in after_text for kw in ["pass", "none", "false"])
    return False


def _check_cleanup_context(before_text: str, _after_text: str) -> bool:
    """Check for cleanup/teardown code."""
    return any(kw in before_text for kw in ["__del__", "__exit__", "cleanup", "close", "teardown"])


def _check_logging_context(_before_text: str, after_text: str) -> bool:
    """Check for explicit logging then re-raise or return."""
    return "log" in after_text and ("raise" in after_text or "return" in after_text)


_CONTEXT_CHECKERS: dict[str, object] = {
    "version": _check_version_context,
    "config": _check_config_context,
    "optional": _check_optional_context,
    "cleanup": _check_cleanup_context,
    "logging": _check_logging_context,
}

_INTENTIONAL_KEYWORDS = ["fallback", "ignore", "optional", "best effort", "graceful", "intentional"]


def _is_acceptable_broad_exception(
    line: str,
    context_before: list[str],
    context_after: list[str],
    acceptable_contexts: list[str] | None = None,
) -> bool:
    """Check if a broad exception handler is acceptable based on context.

    Acceptable patterns (configurable via acceptable_contexts):
    - version: Version/metadata detection with fallback
    - config: Config loading with default fallback
    - optional: Optional feature detection (imports, hasattr)
    - cleanup: Cleanup/teardown code
    - logging: Logging-only handlers that re-raise

    Args:
        line: The line containing the except clause
        context_before: Lines before the except
        context_after: Lines after the except (the handler body)
        acceptable_contexts: List of context types to accept (from config)

    Returns:
        True if the exception handler is acceptable, False if problematic.

    """
    if acceptable_contexts is None:
        acceptable_contexts = ["version", "config", "cleanup", "optional"]

    before_text = "\n".join(context_before[-5:]).lower()
    after_text = "\n".join(context_after[:5]).lower()

    for ctx in acceptable_contexts:
        checker = _CONTEXT_CHECKERS.get(ctx)
        if checker and checker(before_text, after_text):
            return True

    # Always accept: Comment explains the broad catch is intentional
    if "# " in after_text and any(kw in after_text for kw in _INTENTIONAL_KEYWORDS):
        return True

    return False


def _has_problematic_exception_handlers(
    content: str,
    file_path: str,
    acceptable_contexts: list[str] | None = None,
) -> bool:
    """Check if file has problematic broad exception handlers.

    Filters out acceptable uses like version detection, config fallbacks,
    and optional feature detection.

    Args:
        content: File content to check
        file_path: Path to the file
        acceptable_contexts: List of acceptable context types from config

    Returns:
        True if problematic exception handlers found, False otherwise.

    """
    if "except:" not in content and "except Exception:" not in content:
        return False

    lines = content.splitlines()
    problematic_count = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for broad exception patterns (string search, not code execution)
        if stripped.startswith("except:") or stripped.startswith("except Exception"):
            context_before = lines[max(0, i - 5) : i]
            context_after = lines[i + 1 : min(len(lines), i + 6)]

            if not _is_acceptable_broad_exception(
                stripped,
                context_before,
                context_after,
                acceptable_contexts,
            ):
                problematic_count += 1

    # Only flag if there are problematic handlers
    return problematic_count > 0


def _has_no_eval_exec(content: str) -> bool:
    """Return True if content has no eval( or exec( at all."""
    return "eval(" not in content and "exec(" not in content


_SCANNER_TEST_PATTERNS = ["test_bug_predict", "test_scanner", "test_security_scan"]

_FIXTURE_STRIP_REGEXES = [
    (r"write_text\s*\([^)]*\)", re.DOTALL),
    (r'write_text\s*\("""[\s\S]*?"""\)', 0),
    (r"write_text\s*\('''[\s\S]*?'''\)", 0),
]


def _all_eval_in_fixtures(content: str) -> bool:
    """Return True if all eval/exec occurrences are inside write_text() calls."""
    cleaned = content
    for pattern, flags in _FIXTURE_STRIP_REGEXES:
        cleaned = re.sub(pattern, "", cleaned, flags=flags)
    return _has_no_eval_exec(cleaned)


def _is_detection_code_line(line: str) -> bool:
    """Check if a line uses eval/exec in a detection context (string literals, regexes)."""
    # Check for "in content/text/code/source" pattern
    if " in " in line and any(kw in line for kw in ("content", "text", "code", "source")):
        return True
    # Check if eval/exec is inside a string literal
    if re.search(r'["\'][^"\']*eval\([^"\']*["\']', line):
        return True
    if re.search(r'["\'][^"\']*exec\([^"\']*["\']', line):
        return True
    # Check for raw string regex patterns containing eval/exec
    if re.search(r"r['\"][^'\"]*(?:eval|exec)[^'\"]*['\"]", line):
        return True
    return False


def _is_dangerous_eval_usage(content: str, file_path: str) -> bool:
    """Check if file contains dangerous eval/exec usage, filtering false positives.

    Excludes:
    - String literals used for detection (e.g., 'if "eval(" in content')
    - Comments mentioning eval/exec (e.g., '# SECURITY FIX: Use json.loads() instead of eval()')
    - JavaScript's safe regex.exec() method
    - Pattern definitions for security scanners
    - Test fixtures: code written via write_text() or similar for testing
    - Scanner test files that deliberately contain example bad patterns
    - Docstrings documenting security policies (e.g., "No eval() or exec() usage")
    - Security policy documentation in comments

    Returns:
        True if dangerous eval/exec usage is found, False otherwise.

    """
    if _has_no_eval_exec(content):
        return False

    # Exclude scanner test files
    file_name = file_path.lower()
    if any(pattern in file_name for pattern in _SCANNER_TEST_PATTERNS):
        return False

    # Check for test fixture patterns
    fixture_patterns = [
        r'write_text\s*\(\s*["\'][\s\S]*?(?:eval|exec)\s*\(',
        r'write_text\s*\(\s*"""[\s\S]*?(?:eval|exec)\s*\(',
        r"write_text\s*\(\s*'''[\s\S]*?(?:eval|exec)\s*\(",
    ]
    if any(re.search(p, content, re.MULTILINE) for p in fixture_patterns):
        if _all_eval_in_fixtures(content):
            return False

    # For JavaScript/TypeScript files, check for regex.exec() which is safe
    if file_path.endswith((".js", ".ts", ".tsx", ".jsx")):
        content_without_regex_exec = re.sub(r"\.\s*exec\s*\(", ".SAFE_EXEC(", content)
        if _has_no_eval_exec(content_without_regex_exec):
            return False

    # Remove docstrings before line-by-line analysis
    content_without_docstrings = _remove_docstrings(content)

    # Check each line for real dangerous usage
    for line in content_without_docstrings.splitlines():
        stripped = line.strip()

        # Skip comment lines
        if stripped.startswith(("#", "//", "*")):
            continue
        if _is_security_policy_line(stripped):
            continue
        if _has_no_eval_exec(line):
            continue
        if _is_detection_code_line(line):
            continue
        # Skip JavaScript regex.exec() - pattern.exec(text)
        if re.search(r"\w+\.exec\s*\(", line):
            continue

        # This looks like real dangerous usage
        return True

    return False


def _remove_docstrings(content: str) -> str:
    """Remove docstrings from Python content to avoid false positives.

    Docstrings often document security policies (e.g., "No eval() usage")
    which should not trigger the scanner.

    Args:
        content: Python source code

    Returns:
        Content with docstrings replaced by placeholder comments.

    """
    # Remove triple-quoted strings (docstrings)
    # Match """ ... """ and ''' ... ''' including multiline
    content = re.sub(r'"""[\s\S]*?"""', "# [docstring removed]", content)
    content = re.sub(r"'''[\s\S]*?'''", "# [docstring removed]", content)
    return content


def _is_security_policy_line(line: str) -> bool:
    """Check if a line is documenting security policy rather than using eval/exec.

    Args:
        line: Stripped line of code

    Returns:
        True if this appears to be security documentation.

    """
    line_lower = line.lower()

    # Patterns indicating security policy documentation
    policy_patterns = [
        r"no\s+eval",  # "No eval" or "no eval()"
        r"no\s+exec",  # "No exec" or "no exec()"
        r"never\s+use\s+eval",
        r"never\s+use\s+exec",
        r"avoid\s+eval",
        r"avoid\s+exec",
        r"don'?t\s+use\s+eval",
        r"don'?t\s+use\s+exec",
        r"prohibited.*eval",
        r"prohibited.*exec",
        r"security.*eval",
        r"security.*exec",
    ]

    for pattern in policy_patterns:
        if re.search(pattern, line_lower):
            return True

    # Check for list item documentation (e.g., "- No eval() or exec() usage")
    if line.startswith("-") and ("eval" in line_lower or "exec" in line_lower):
        # If it contains "no", "never", "avoid", it's policy documentation
        if any(word in line_lower for word in ["no ", "never", "avoid", "don't", "prohibited"]):
            return True

    return False
