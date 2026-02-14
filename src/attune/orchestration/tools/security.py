"""Security tools — security auditing with bandit.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SecurityReport:
    """Security audit report from bandit."""

    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    issues_by_file: dict[str, list[dict[str, Any]]]
    passed: bool


class RealSecurityAuditor:
    """Runs real security audit using bandit."""

    def __init__(self, project_root: str = "."):
        """Initialize security auditor.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root).resolve()

    def audit(self, target_path: str = "src") -> SecurityReport:
        """Run security audit on codebase.

        Args:
            target_path: Path to audit (default: src)

        Returns:
            SecurityReport with vulnerability findings

        Raises:
            RuntimeError: If security audit fails
        """
        logger.info(f"Running security audit on {target_path}")

        try:
            # Run bandit with JSON output
            cmd = [
                "bandit",
                "-r",
                target_path,
                "-f",
                "json",
                "-q",  # Quiet mode - suppress progress bar and log messages
                "-ll",  # Only report medium and above
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Parse JSON output
            try:
                bandit_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                # Bandit might not be installed or JSON output malformed
                logger.warning(f"Bandit not available or returned invalid JSON: {e}")
                stdout = result.stdout if isinstance(result.stdout, str) else ""
                stderr = result.stderr if isinstance(result.stderr, str) else ""
                logger.debug(f"Bandit stdout: {stdout[:500]}")
                logger.debug(f"Bandit stderr: {stderr[:500]}")
                return SecurityReport(
                    total_issues=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    issues_by_file={},
                    passed=True,
                )

            # Count issues by severity
            results = bandit_data.get("results", [])
            critical_count = sum(1 for r in results if r.get("issue_severity") == "CRITICAL")
            high_count = sum(1 for r in results if r.get("issue_severity") == "HIGH")
            medium_count = sum(1 for r in results if r.get("issue_severity") == "MEDIUM")
            low_count = sum(1 for r in results if r.get("issue_severity") == "LOW")

            # Group by file
            issues_by_file = {}
            for issue in results:
                filepath = issue.get("filename", "unknown")
                if filepath not in issues_by_file:
                    issues_by_file[filepath] = []
                issues_by_file[filepath].append(
                    {
                        "line": issue.get("line_number"),
                        "severity": issue.get("issue_severity"),
                        "confidence": issue.get("issue_confidence"),
                        "message": issue.get("issue_text"),
                        "test_id": issue.get("test_id"),
                    }
                )

            total_issues = len(results)
            passed = critical_count == 0 and high_count == 0

            logger.info(
                f"Security audit complete: {total_issues} issues "
                f"(critical={critical_count}, high={high_count}, medium={medium_count})"
            )

            return SecurityReport(
                total_issues=total_issues,
                critical_count=critical_count,
                high_count=high_count,
                medium_count=medium_count,
                low_count=low_count,
                issues_by_file=issues_by_file,
                passed=passed,
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("Security audit timed out after 5 minutes")
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            raise RuntimeError(f"Security audit failed: {e}") from e


SECURITY_TOOLS = {
    "security_auditor": RealSecurityAuditor,
}
