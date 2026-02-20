"""Private helper functions for test runner utilities.

Contains pytest output parsing, coverage XML analysis, test file
discovery, and telemetry logging helpers used by test_runner.py.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

from attune.models import FileTestRecord, get_telemetry_store

logger = logging.getLogger(__name__)


def _parse_pytest_output(output: str) -> tuple[int, int, int, int, int]:
    """Parse pytest output for test counts.

    Returns:
        Tuple of (total_tests, passed, failed, skipped, errors)

    """
    import re

    # Look for pytest summary line like "5 passed, 2 failed, 1 skipped in 1.23s"
    match = re.search(r"(\d+)\s+passed", output)
    passed = int(match.group(1)) if match else 0

    match = re.search(r"(\d+)\s+failed", output)
    failed = int(match.group(1)) if match else 0

    match = re.search(r"(\d+)\s+skipped", output)
    skipped = int(match.group(1)) if match else 0

    match = re.search(r"(\d+)\s+error", output)
    errors = int(match.group(1)) if match else 0

    total_tests = passed + failed + skipped + errors

    return total_tests, passed, failed, skipped, errors


def _parse_pytest_failures(output: str) -> list[dict[str, str]]:
    """Parse pytest output for failure details.

    Returns:
        List of dicts with name, file, error, traceback

    """
    failures = []
    lines = output.split("\n")

    # Simple parser - looks for FAILED lines
    for line in lines:
        if "FAILED " in line:
            parts = line.split("::")
            if len(parts) >= 2:
                file_path = parts[0].replace("FAILED ", "").strip()
                test_name = parts[1].split()[0] if len(parts) > 1 else "unknown"

                failures.append({"name": test_name, "file": file_path, "error": "Test failed"})

    return failures[:10]  # Limit to 10 failures


def _get_previous_coverage() -> float | None:
    """Get previous coverage percentage from telemetry store.

    Returns:
        Previous coverage percentage or None

    """
    try:
        store = get_telemetry_store()
        records = store.get_coverage_history(limit=2)

        if len(records) >= 2:
            # Second-to-last record is the previous one
            return records[-2].overall_percentage
        elif len(records) == 1:
            return records[0].overall_percentage
        else:
            return None

    except Exception:
        return None


def _analyze_coverage_files(root: Element) -> dict[str, Any]:
    """Analyze file-level coverage from XML.

    Returns:
        Dict with total, well_covered, critical, untested, gaps

    """
    files_total = 0
    files_well_covered = 0  # >= 80%
    files_critical = 0  # < 50%
    untested_files = []
    critical_gaps = []

    for package in root.findall(".//package"):
        for class_elem in package.findall("classes/class"):
            files_total += 1
            filename = class_elem.attrib.get("filename", "unknown")
            line_rate = float(class_elem.attrib.get("line-rate", 0))
            coverage_pct = line_rate * 100

            if coverage_pct >= 80:
                files_well_covered += 1
            elif coverage_pct < 50:
                files_critical += 1
                critical_gaps.append(
                    {"file": filename, "coverage": coverage_pct, "priority": "high"}
                )

            if coverage_pct == 0:
                untested_files.append(filename)

    return {
        "total": files_total,
        "well_covered": files_well_covered,
        "critical": files_critical,
        "untested": untested_files[:10],  # Limit to 10
        "gaps": critical_gaps[:10],  # Limit to 10
    }


def _find_test_file(source_file: str) -> str | None:
    """Find the test file for a given source file.

    Uses comprehensive search to find test files:
    1. First checks explicit patterns based on source file location
    2. Falls back to glob search for test_{filename}.py anywhere in tests/

    Args:
        source_file: Path to the source file

    Returns:
        Path to test file or None if not found
    """
    source_path = Path(source_file)
    filename = source_path.stem
    parent = source_path.parent

    # Skip __init__.py - rarely have dedicated tests
    if filename == "__init__":
        return None

    # Build list of explicit patterns to check first (most specific)
    patterns = []

    # Extract module info from source path
    # e.g., src/attune/models/registry.py -> module="models"
    module_name = None
    if "src" in source_path.parts:
        try:
            src_idx = source_path.parts.index("src")
            rel_parts = source_path.parts[src_idx + 1 : -1]  # Exclude src and filename
            if len(rel_parts) >= 2:
                # e.g., ('attune', 'models') -> module_name = 'models'
                module_name = rel_parts[-1]
        except (ValueError, IndexError):
            pass

    # Priority 1: Module-specific test directory
    # e.g., src/attune/models/registry.py -> tests/unit/models/test_registry.py
    if module_name:
        patterns.extend(
            [
                Path("tests") / "unit" / module_name / f"test_{filename}.py",
                Path("tests") / module_name / f"test_{filename}.py",
                Path("tests") / "integration" / module_name / f"test_{filename}.py",
            ]
        )

    # Priority 2: Standard locations
    patterns.extend(
        [
            Path("tests") / "unit" / f"test_{filename}.py",
            Path("tests") / f"test_{filename}.py",
            Path("tests") / "integration" / f"test_{filename}.py",
            parent / f"test_{filename}.py",
        ]
    )

    # Check explicit patterns first
    for pattern in patterns:
        if pattern.exists():
            return str(pattern)

    # Priority 3: Glob search - find test_{filename}.py anywhere in tests/
    tests_dir = Path("tests")
    if tests_dir.exists():
        # Search for exact match first
        matches = list(tests_dir.rglob(f"test_{filename}.py"))
        if matches:
            # Return the first match (preferring shorter paths)
            matches.sort(key=lambda p: len(p.parts))
            return str(matches[0])

    return None


def _log_file_test(record: FileTestRecord) -> None:
    """Log a FileTestRecord to the telemetry store.

    Args:
        record: FileTestRecord to log
    """
    try:
        store = get_telemetry_store()
        store.log_file_test(record)
        logger.info(f"File test tracked: {record.file_path} ({record.last_test_result})")
    except Exception as e:
        logger.warning(f"Failed to log file test: {e}")
