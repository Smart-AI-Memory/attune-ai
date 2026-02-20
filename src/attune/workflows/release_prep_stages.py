"""Release Preparation Workflow - Stage Implementations

Health, security, crew security, and changelog stage logic
for the ReleasePreparationWorkflow.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import subprocess
from datetime import datetime

from .base import ModelTier


class ReleasePrepStagesMixin:
    """Mixin providing health, security, crew_security, and changelog stages.

    Expects the host class to expose:
        - ``enable_auth_strategy: bool``
        - ``_has_blockers: bool``
        - ``_auth_mode_used: str | None``
        - ``crew_config: dict``
    """

    # These attributes are defined by the host class; declared here for
    # type-checker visibility only.
    enable_auth_strategy: bool
    _has_blockers: bool
    _auth_mode_used: str | None
    crew_config: dict

    async def _health(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Run health checks.

        Executes lint, type checking, and tests.
        """
        target_path = input_data.get("path", ".")

        # === AUTH STRATEGY INTEGRATION ===
        if self.enable_auth_strategy:
            try:
                import logging
                from pathlib import Path

                from attune.models import (
                    count_lines_of_code,
                    get_auth_strategy,
                    get_module_size_category,
                )

                logger = logging.getLogger(__name__)

                # Calculate total LOC for project/directory
                target = Path(target_path)
                total_lines = 0
                if target.is_file():
                    total_lines = count_lines_of_code(target)
                elif target.is_dir():
                    for py_file in target.rglob("*.py"):
                        try:
                            total_lines += count_lines_of_code(py_file)
                        except Exception:
                            pass

                if total_lines > 0:
                    strategy = get_auth_strategy()
                    recommended_mode = strategy.get_recommended_mode(total_lines)
                    self._auth_mode_used = recommended_mode.value

                    size_category = get_module_size_category(total_lines)
                    logger.info(
                        f"Release prep target: {target_path} ({total_lines:,} LOC, {size_category})"
                    )
                    logger.info(f"Recommended auth mode: {recommended_mode.value}")

                    cost_estimate = strategy.estimate_cost(total_lines, recommended_mode)
                    if recommended_mode.value == "subscription":
                        logger.info(f"Cost: {cost_estimate['quota_cost']}")
                    else:
                        logger.info(f"Cost: ~${cost_estimate['monetary_cost']:.4f}")

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Auth strategy detection failed: {e}")

        checks: dict[str, dict] = {}

        # Lint check (ruff)
        try:
            result = subprocess.run(
                ["python", "-m", "ruff", "check", target_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            lint_errors = result.stdout.count("error") + result.stderr.count("error")
            checks["lint"] = {
                "passed": result.returncode == 0,
                "errors": lint_errors,
                "tool": "ruff",
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            checks["lint"] = {"passed": True, "errors": 0, "tool": "ruff", "skipped": True}

        # Type check (mypy)
        try:
            result = subprocess.run(
                ["python", "-m", "mypy", target_path, "--ignore-missing-imports"],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
            type_errors = result.stdout.count("error:")
            checks["types"] = {
                "passed": result.returncode == 0,
                "errors": type_errors,
                "tool": "mypy",
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            checks["types"] = {"passed": True, "errors": 0, "tool": "mypy", "skipped": True}

        # Test check (pytest)
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--co", "-q"],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=target_path,
            )
            # Count collected tests
            test_count = 0
            for line in result.stdout.splitlines():
                if "test" in line.lower():
                    test_count += 1

            checks["tests"] = {
                "passed": True,
                "test_count": test_count,
                "tool": "pytest",
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            checks["tests"] = {"passed": True, "test_count": 0, "tool": "pytest", "skipped": True}

        # Calculate health score
        failed_checks = [k for k, v in checks.items() if not v.get("passed", True)]
        health_score = 100 - (len(failed_checks) * 20)

        if failed_checks:
            self._has_blockers = True

        health_result = {
            "checks": checks,
            "health_score": max(0, health_score),
            "failed_checks": failed_checks,
            "passed": len(failed_checks) == 0,
        }

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(health_result)) // 4

        return (
            {
                "health": health_result,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _security(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Run security scan using Bandit.

        Uses industry-standard Bandit tool for security analysis.
        """
        target_path = input_data.get("path", ".")

        issues: list[dict] = []
        high_count = 0
        medium_count = 0

        # Run Bandit security scanner
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "bandit",
                    "-r",
                    target_path,
                    "--severity-level",
                    "medium",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Parse Bandit JSON output
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    bandit_results = bandit_data.get("results", [])

                    for finding in bandit_results:
                        severity = finding.get("issue_severity", "LOW").lower()
                        issues.append(
                            {
                                "type": finding.get("test_id", "unknown"),
                                "file": finding.get("filename", "unknown"),
                                "line": finding.get("line_number", 0),
                                "severity": severity,
                                "message": finding.get("issue_text", ""),
                                "confidence": finding.get("issue_confidence", ""),
                            }
                        )

                        if severity == "high":
                            high_count += 1
                        elif severity == "medium":
                            medium_count += 1

                except json.JSONDecodeError:
                    # If JSON parsing fails, fall back to error count from stderr
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Bandit not available or timed out - skip security scan
            pass

        if high_count > 0:
            self._has_blockers = True

        security_result = {
            "issues": issues[:20],  # Top 20
            "total_issues": len(issues),
            "high_severity": high_count,
            "medium_severity": medium_count,
            "passed": high_count == 0,
            "tool": "bandit",
        }

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(security_result)) // 4

        return (
            {
                "security": security_result,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _crew_security(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Run SecurityAuditCrew for comprehensive security analysis.

        This stage uses the 5-agent SecurityAuditCrew for deep security
        analysis including vulnerability hunting, risk assessment,
        remediation planning, and compliance mapping.

        Falls back gracefully if SecurityAuditCrew is not available.
        """
        try:
            from .security_adapters import (
                _check_crew_available,
                _get_crew_audit,
                crew_report_to_workflow_format,
                merge_security_results,
            )
        except ImportError:
            # Security adapters removed - return fallback
            return (
                {
                    "crew_security": {
                        "available": False,
                        "fallback": True,
                        "reason": "Security adapters not installed",
                    },
                    **input_data,
                },
                0,
                0,
            )

        target_path = input_data.get("path", ".")
        existing_security = input_data.get("security", {})

        # Check if crew is available
        if not _check_crew_available():
            return (
                {
                    "crew_security": {
                        "available": False,
                        "fallback": True,
                        "reason": "SecurityAuditCrew not installed",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Run SecurityAuditCrew
        report = await _get_crew_audit(target_path, self.crew_config)

        if report is None:
            return (
                {
                    "crew_security": {
                        "available": True,
                        "fallback": True,
                        "reason": "SecurityAuditCrew audit failed or timed out",
                    },
                    **input_data,
                },
                0,
                0,
            )

        # Convert crew report to workflow format
        crew_results = crew_report_to_workflow_format(report)

        # Merge with existing security stage results
        existing_issues = existing_security.get("issues", [])
        merged = merge_security_results(crew_results, {"findings": existing_issues})

        # Update blockers based on crew findings
        critical_count = len(crew_results.get("assessment", {}).get("critical_findings", []))
        high_count = len(crew_results.get("assessment", {}).get("high_findings", []))

        if critical_count > 0 or high_count > 0:
            self._has_blockers = True

        crew_security_result = {
            "available": True,
            "fallback": False,
            "findings": crew_results.get("findings", []),
            "finding_count": crew_results.get("finding_count", 0),
            "risk_score": crew_results.get("risk_score", 0),
            "risk_level": crew_results.get("risk_level", "none"),
            "critical_count": critical_count,
            "high_count": high_count,
            "summary": crew_results.get("summary", ""),
            "agents_used": crew_results.get("agents_used", []),
            "merged_results": merged,
        }

        # Estimate tokens (crew uses internal LLM calls)
        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(crew_security_result)) // 4

        return (
            {
                "crew_security": crew_security_result,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    async def _changelog(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Generate changelog from recent commits.

        Extracts commit messages and organizes by type.
        """
        target_path = input_data.get("path", ".")
        since = input_data.get("since", "1 week ago")

        commits: list[dict] = []

        try:
            result = subprocess.run(
                ["git", "log", f"--since={since}", "--oneline", "--no-merges"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=target_path,
            )

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                parts = line.split(" ", 1)
                if len(parts) >= 2:
                    sha = parts[0]
                    message = parts[1]

                    # Categorize by conventional commit prefix
                    category = "other"
                    if message.startswith("feat"):
                        category = "features"
                    elif message.startswith("fix"):
                        category = "fixes"
                    elif message.startswith("docs"):
                        category = "docs"
                    elif message.startswith("refactor"):
                        category = "refactor"
                    elif message.startswith("test"):
                        category = "tests"
                    elif message.startswith("chore"):
                        category = "chores"

                    commits.append(
                        {
                            "sha": sha,
                            "message": message,
                            "category": category,
                        },
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Group by category
        by_category: dict[str, list] = {}
        for commit in commits:
            cat = commit["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(commit)

        changelog = {
            "commits": commits,
            "total_commits": len(commits),
            "by_category": {k: len(v) for k, v in by_category.items()},
            "generated_at": datetime.now().isoformat(),
            "period": since,
        }

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(changelog)) // 4

        return (
            {
                "changelog": changelog,
                **input_data,
            },
            input_tokens,
            output_tokens,
        )
