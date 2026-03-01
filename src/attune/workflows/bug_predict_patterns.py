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
                    if config and "bug_predict" in config:
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
    for pattern in exclude_patterns:
        # Handle ** patterns for recursive matching
        if "**" in pattern:
            # Convert ** glob to fnmatch-compatible pattern
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix, suffix = parts
                # Check if file path contains the pattern structure
                if prefix and not file_path.startswith(prefix.rstrip("/")):
                    continue
                if suffix and fnmatch.fnmatch(file_path, f"*{suffix}"):
                    return True
                if not suffix and fnmatch.fnmatch(file_path, f"*{prefix}*"):
                    return True
        elif fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(
            Path(file_path).name,
            pattern,
        ):
            return True

    return False


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
    # Default acceptable contexts if not provided
    if acceptable_contexts is None:
        acceptable_contexts = ["version", "config", "cleanup", "optional"]

    # Join context for pattern matching
    before_text = "\n".join(context_before[-5:]).lower()
    after_text = "\n".join(context_after[:5]).lower()

    # Acceptable: Version/metadata detection
    if "version" in acceptable_contexts:
        if any(kw in before_text for kw in ["get_version", "version", "metadata", "__version__"]):
            if any(kw in after_text for kw in ["return", "dev", "unknown", "0.0.0"]):
                return True

    # Acceptable: Config loading with fallback to defaults
    if "config" in acceptable_contexts:
        if any(kw in before_text for kw in ["config", "settings", "yaml", "json", "load"]):
            if "pass" in after_text or "default" in after_text or "fallback" in after_text:
                return True

    # Acceptable: Optional import/feature detection
    if "optional" in acceptable_contexts:
        if "import" in before_text or "hasattr" in before_text:
            if "pass" in after_text or "none" in after_text or "false" in after_text:
                return True

    # Acceptable: Cleanup with pass (often in __del__ or context managers)
    if "cleanup" in acceptable_contexts:
        if any(kw in before_text for kw in ["__del__", "__exit__", "cleanup", "close", "teardown"]):
            return True

    # Acceptable: Explicit logging then re-raise or return error
    if "logging" in acceptable_contexts:
        if "log" in after_text and ("raise" in after_text or "return" in after_text):
            return True

    # Always accept: Comment explains the broad catch is intentional
    if "# " in after_text and any(
        kw in after_text
        for kw in ["fallback", "ignore", "optional", "best effort", "graceful", "intentional"]
    ):
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

        # Check for broad exception patterns
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
    # Check if file even contains eval or exec
    if "eval(" not in content and "exec(" not in content:
        return False

    # Exclude scanner test files (they deliberately contain example bad patterns)
    scanner_test_patterns = [
        "test_bug_predict",
        "test_scanner",
        "test_security_scan",
    ]
    file_name = file_path.lower()
    if any(pattern in file_name for pattern in scanner_test_patterns):
        return False

    # Check for test fixture patterns - eval/exec inside write_text() or heredoc strings
    # These are test data being written to temp files, not actual dangerous code
    fixture_patterns = [
        r'write_text\s*\(\s*["\'][\s\S]*?(?:eval|exec)\s*\(',  # write_text("...eval(...")
        r'write_text\s*\(\s*"""[\s\S]*?(?:eval|exec)\s*\(',  # write_text("""...eval(...""")
        r"write_text\s*\(\s*'''[\s\S]*?(?:eval|exec)\s*\(",  # write_text('''...eval(...''')
    ]
    for pattern in fixture_patterns:
        if re.search(pattern, content, re.MULTILINE):
            # All eval/exec occurrences might be in fixtures - do deeper check
            # Remove fixture content and see if any eval/exec remains
            content_without_fixtures = re.sub(
                r"write_text\s*\([^)]*\)",
                "",
                content,
                flags=re.DOTALL,
            )
            content_without_fixtures = re.sub(
                r'write_text\s*\("""[\s\S]*?"""\)',
                "",
                content_without_fixtures,
            )
            content_without_fixtures = re.sub(
                r"write_text\s*\('''[\s\S]*?'''\)",
                "",
                content_without_fixtures,
            )
            if "eval(" not in content_without_fixtures and "exec(" not in content_without_fixtures:
                return False

    # For JavaScript/TypeScript files, check for regex.exec() which is safe
    if file_path.endswith((".js", ".ts", ".tsx", ".jsx")):
        # Remove all regex.exec() calls (these are safe)
        content_without_regex_exec = re.sub(r"\.\s*exec\s*\(", ".SAFE_EXEC(", content)
        # If no eval/exec remains, it was all regex.exec()
        if "eval(" not in content_without_regex_exec and "exec(" not in content_without_regex_exec:
            return False

    # Remove docstrings before line-by-line analysis
    # This prevents false positives from documentation that mentions eval/exec
    content_without_docstrings = _remove_docstrings(content)

    # Check each line for real dangerous usage
    lines = content_without_docstrings.splitlines()
    for line in lines:
        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue

        # Skip security policy documentation (e.g., "- No eval() or exec()")
        if _is_security_policy_line(stripped):
            continue

        # Check for eval( or exec( in this line
        if "eval(" not in line and "exec(" not in line:
            continue

        # Skip if it's inside a string literal for detection purposes
        # e.g., 'if "eval(" in content' or "pattern = r'eval\('"
        detection_patterns = [
            r'["\'].*eval\(.*["\']',  # "eval(" or 'eval(' in a string
            r'["\'].*exec\(.*["\']',  # "exec(" or 'exec(' in a string
            r"in\s+\w+",  # Pattern like 'in content'
            r'r["\'].*eval',  # Raw string regex pattern
            r'r["\'].*exec',  # Raw string regex pattern
        ]

        is_detection_code = False
        for pattern in detection_patterns:
            if re.search(pattern, line):
                # Check if it's really detection code
                if " in " in line and (
                    "content" in line or "text" in line or "code" in line or "source" in line
                ):
                    is_detection_code = True
                    break
                # Check if it's a string literal being defined (eval or exec)
                if re.search(r'["\'][^"\']*eval\([^"\']*["\']', line):
                    is_detection_code = True
                    break
                if re.search(r'["\'][^"\']*exec\([^"\']*["\']', line):
                    is_detection_code = True
                    break
                # Check for raw string regex patterns containing eval/exec
                if re.search(r"r['\"][^'\"]*(?:eval|exec)[^'\"]*['\"]", line):
                    is_detection_code = True
                    break

        if is_detection_code:
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
