"""Test Execution and Coverage Tracking Utilities for Tier 1 Automation.

Provides explicit opt-in utilities for tracking test executions and coverage metrics.
Use these functions when you want to track test/coverage data for Tier 1 monitoring.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import shlex
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

# Import Element for type hints only (defusedxml doesn't expose it)

from attune.models import (
    CoverageRecord,
    FileTestRecord,
    TestExecutionRecord,
    get_telemetry_store,
)

logger = logging.getLogger(__name__)


def run_tests_with_tracking(
    test_suite: str = "unit",
    test_files: list[str] | None = None,
    command: str | None = None,
    workflow_id: str | None = None,
    triggered_by: str = "manual",
) -> TestExecutionRecord:
    """Run tests with explicit tracking (opt-in for Tier 1 monitoring).

    Args:
        test_suite: Test suite name (unit, integration, e2e, all)
        test_files: Specific test files to run (optional)
        command: Custom test command (defaults to pytest)
        workflow_id: Optional workflow ID to link this execution
        triggered_by: Who/what triggered this (manual, workflow, ci, pre_commit)

    Returns:
        TestExecutionRecord with execution results

    Example:
        >>> from attune.workflows.test_runner import run_tests_with_tracking
        >>> result = run_tests_with_tracking(
        ...     test_suite="unit",
        ...     test_files=["tests/unit/test_config.py"],
        ... )
        >>> print(f"Tests passed: {result.success}")

    """
    execution_id = f"test-{uuid.uuid4()}"
    timestamp = datetime.now(timezone.utc).isoformat()
    started_at = datetime.now(timezone.utc)

    # Build command
    if command is None:
        if test_files:
            files_str = " ".join(test_files)
            command = f"pytest {files_str} -v --tb=short"
        elif test_suite == "all":
            command = "pytest tests/ -v --tb=short"
        else:
            command = f"pytest tests/{test_suite}/ -v --tb=short"

    # Determine working directory
    working_directory = str(Path.cwd())

    # Run tests
    logger.info(f"Running tests: {command}")
    try:
        # Use shlex.split to safely parse command without shell=True
        cmd_args = shlex.split(command)
        result = subprocess.run(
            cmd_args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        # Parse pytest output for test counts
        output = result.stdout + result.stderr
        total_tests, passed, failed, skipped, errors = _parse_pytest_output(output)

        success = result.returncode == 0
        exit_code = result.returncode

        # Parse failures from output
        failed_tests = _parse_pytest_failures(output) if failed > 0 or errors > 0 else []

    except subprocess.TimeoutExpired:
        logger.error("Test execution timed out after 600 seconds")
        total_tests, passed, failed, skipped, errors = 0, 0, 0, 0, 1
        success = False
        exit_code = 124  # Timeout exit code
        failed_tests = [{"name": "timeout", "file": "unknown", "error": "Test execution timed out"}]

    except Exception as e:  # noqa: BLE001
        logger.error(f"Test execution failed: {e}")
        total_tests, passed, failed, skipped, errors = 0, 0, 0, 0, 1
        success = False
        exit_code = 1
        failed_tests = [{"name": "execution_error", "file": "unknown", "error": str(e)}]

    # Calculate duration
    completed_at = datetime.now(timezone.utc)
    duration_seconds = (completed_at - started_at).total_seconds()

    # Create test execution record
    record = TestExecutionRecord(
        execution_id=execution_id,
        timestamp=timestamp,
        test_suite=test_suite,
        test_files=test_files or [],
        triggered_by=triggered_by,
        command=command,
        working_directory=working_directory,
        duration_seconds=duration_seconds,
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        success=success,
        exit_code=exit_code,
        failed_tests=failed_tests,
        workflow_id=workflow_id,
    )

    # Log to telemetry store
    try:
        store = get_telemetry_store()
        store.log_test_execution(record)
        logger.info(f"Test execution tracked: {execution_id}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to log test execution: {e}")

    return record


def track_coverage(
    coverage_file: str = "coverage.xml",
    workflow_id: str | None = None,
) -> CoverageRecord:
    """Track test coverage from coverage.xml file (opt-in for Tier 1 monitoring).

    Args:
        coverage_file: Path to coverage.xml file
        workflow_id: Optional workflow ID to link this record

    Returns:
        CoverageRecord with coverage metrics

    Example:
        >>> from attune.workflows.test_runner import track_coverage
        >>> coverage = track_coverage("coverage.xml")
        >>> print(f"Coverage: {coverage.overall_percentage:.1f}%")

    """
    record_id = f"cov-{uuid.uuid4()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    coverage_path = Path(coverage_file)
    if not coverage_path.exists():
        raise FileNotFoundError(f"Coverage file not found: {coverage_file}")

    # Parse coverage.xml
    try:
        # Uses defusedxml when available (see imports), coverage.xml is from trusted pytest/coverage tools
        tree = ET.parse(coverage_path)  # nosec B314
        root = tree.getroot()

        # Get overall metrics
        lines_total = int(root.attrib.get("lines-valid", 0))
        lines_covered = int(root.attrib.get("lines-covered", 0))
        branches_total = int(root.attrib.get("branches-valid", 0))
        branches_covered = int(root.attrib.get("branches-covered", 0))

        if lines_total > 0:
            overall_percentage = (lines_covered / lines_total) * 100
        else:
            overall_percentage = 0.0

        # Get previous coverage if available
        previous_percentage = _get_previous_coverage()

        # Determine trend
        if previous_percentage is not None:
            change = overall_percentage - previous_percentage
            if change > 1.0:
                trend = "improving"
            elif change < -1.0:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Analyze files
        files_analyzed = _analyze_coverage_files(root)

        record = CoverageRecord(
            record_id=record_id,
            timestamp=timestamp,
            overall_percentage=overall_percentage,
            lines_total=lines_total,
            lines_covered=lines_covered,
            branches_total=branches_total,
            branches_covered=branches_covered,
            files_total=files_analyzed["total"],
            files_well_covered=files_analyzed["well_covered"],
            files_critical=files_analyzed["critical"],
            untested_files=files_analyzed["untested"],
            critical_gaps=files_analyzed["gaps"],
            previous_percentage=previous_percentage,
            trend=trend,
            coverage_format="xml",
            coverage_file=str(coverage_path),
            workflow_id=workflow_id,
        )

        # Log to telemetry store
        try:
            store = get_telemetry_store()
            store.log_coverage(record)
            logger.info(f"Coverage tracked: {record_id} ({overall_percentage:.1f}%)")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to log coverage: {e}")

        return record

    except ET.ParseError as e:
        raise ValueError(f"Invalid coverage.xml format: {e}") from e


# Helper functions (extracted to test_runner_helpers.py)

from .test_runner_helpers import (  # noqa: E402 - re-exported
    _analyze_coverage_files,
    _find_test_file,
    _get_previous_coverage,
    _log_file_test,
    _parse_pytest_failures,
    _parse_pytest_output,
)


def track_file_tests(
    source_file: str,
    test_file: str | None = None,
    workflow_id: str | None = None,
) -> FileTestRecord:
    """Track test execution for a specific source file.

    Runs tests associated with a source file and creates a FileTestRecord.

    Args:
        source_file: Path to the source file to test
        test_file: Path to the test file (auto-detected if not provided)
        workflow_id: Optional workflow ID to link this execution

    Returns:
        FileTestRecord with per-file test results

    Example:
        >>> from attune.workflows.test_runner import track_file_tests
        >>> result = track_file_tests("src/attune/config.py")
        >>> print(f"Tests for config.py: {result.last_test_result}")

    """
    timestamp = datetime.now(timezone.utc).isoformat()
    started_at = datetime.now(timezone.utc)

    source_path = Path(source_file)

    # Auto-detect test file if not provided
    if test_file is None:
        test_file = _find_test_file(source_file)

    # Get file modification times
    source_modified_at = None
    tests_modified_at = None

    if source_path.exists():
        source_modified_at = datetime.fromtimestamp(source_path.stat().st_mtime).isoformat() + "Z"

    if test_file:
        test_path = Path(test_file)
        if test_path.exists():
            tests_modified_at = datetime.fromtimestamp(test_path.stat().st_mtime).isoformat() + "Z"

    # Check if we have tests to run
    if test_file is None or not Path(test_file).exists():
        # No tests found for this file
        record = FileTestRecord(
            file_path=source_file,
            timestamp=timestamp,
            last_test_result="no_tests",
            test_count=0,
            test_file_path=test_file,
            source_modified_at=source_modified_at,
            tests_modified_at=tests_modified_at,
            is_stale=False,
            workflow_id=workflow_id,
        )
        _log_file_test(record)
        return record

    # Run pytest for this specific test file
    command = f"pytest {test_file} -v --tb=short"

    logger.info(f"Running tests for {source_file}: {command}")
    try:
        cmd_args = shlex.split(command)
        result = subprocess.run(
            cmd_args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per file
        )

        output = result.stdout + result.stderr
        total_tests, passed, failed, skipped, errors = _parse_pytest_output(output)

        # Determine result status
        if result.returncode == 0:
            last_test_result = "passed"
        elif failed > 0:
            last_test_result = "failed"
        elif errors > 0:
            last_test_result = "error"
        elif skipped == total_tests:
            last_test_result = "skipped"
        else:
            last_test_result = "failed"

        failed_tests = _parse_pytest_failures(output) if failed > 0 or errors > 0 else []
        execution_id = f"file-{uuid.uuid4()}"

    except subprocess.TimeoutExpired:
        logger.error(f"Test execution timed out for {source_file}")
        total_tests, passed, failed, skipped, errors = 0, 0, 0, 0, 1
        last_test_result = "error"
        failed_tests = [{"name": "timeout", "file": test_file, "error": "Timed out"}]
        execution_id = f"file-{uuid.uuid4()}"

    except Exception as e:  # noqa: BLE001
        logger.error(f"Test execution failed for {source_file}: {e}")
        total_tests, passed, failed, skipped, errors = 0, 0, 0, 0, 1
        last_test_result = "error"
        failed_tests = [{"name": "execution_error", "file": test_file, "error": str(e)}]
        execution_id = f"file-{uuid.uuid4()}"

    # Calculate duration
    completed_at = datetime.now(timezone.utc)
    duration_seconds = (completed_at - started_at).total_seconds()

    # Check staleness (source modified after tests last modified)
    is_stale = False
    if source_modified_at and tests_modified_at:
        is_stale = source_modified_at > tests_modified_at

    record = FileTestRecord(
        file_path=source_file,
        timestamp=timestamp,
        last_test_result=last_test_result,
        test_count=total_tests,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        duration_seconds=duration_seconds,
        test_file_path=test_file,
        failed_tests=failed_tests,
        source_modified_at=source_modified_at,
        tests_modified_at=tests_modified_at,
        is_stale=is_stale,
        execution_id=execution_id,
        workflow_id=workflow_id,
    )

    _log_file_test(record)
    return record


def get_file_test_status(file_path: str) -> FileTestRecord | None:
    """Get the latest test status for a specific file.

    Args:
        file_path: Path to the source file

    Returns:
        Latest FileTestRecord or None if no tests recorded

    """
    store = get_telemetry_store()
    return store.get_latest_file_test(file_path)


def get_files_needing_tests(
    stale_only: bool = False,
    failed_only: bool = False,
) -> list[FileTestRecord]:
    """Get files that need test attention.

    Args:
        stale_only: Only return files with stale tests
        failed_only: Only return files with failed tests

    Returns:
        List of FileTestRecord for files needing attention

    """
    store = get_telemetry_store()
    return store.get_files_needing_tests(stale_only=stale_only, failed_only=failed_only)
