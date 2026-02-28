"""Security Audit Triage Stage.

Mixin providing the triage stage for SecurityAuditWorkflow.
Extracted from security_audit.py for maintainability.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import re
from pathlib import Path

from .base import ModelTier
from .security_audit_patterns import (
    SECURITY_EXAMPLE_PATHS,
    SECURITY_PATTERNS,
    SKIP_DIRECTORIES,
    TEST_FILE_PATTERNS,
)

logger = logging.getLogger(__name__)


class TriageStageMixin:
    """Mixin providing the triage stage for security audit workflows."""

    async def _triage(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Quick scan for common vulnerability patterns.

        Uses regex patterns to identify potential security issues
        across the codebase for further analysis.
        """
        target_path = input_data.get("path", ".")
        file_types = input_data.get("file_types", [".py", ".ts", ".tsx", ".js", ".jsx"])

        findings: list[dict] = []
        files_scanned = 0

        target = Path(target_path)
        if target.exists():
            # Handle both file and directory targets
            files_to_scan: list[Path] = []
            if target.is_file():
                # Single file - check if it matches file_types
                if any(str(target).endswith(ext) for ext in file_types):
                    files_to_scan = [target]
            else:
                # Directory - recursively find all matching files
                for ext in file_types:
                    for file_path in target.rglob(f"*{ext}"):
                        # Skip excluded directories
                        if any(skip in str(file_path) for skip in SKIP_DIRECTORIES):
                            continue
                        files_to_scan.append(file_path)

            for file_path in files_to_scan:
                try:
                    content = file_path.read_text(errors="ignore")
                    lines = content.split("\n")
                    files_scanned += 1

                    for vuln_type, vuln_info in SECURITY_PATTERNS.items():
                        for pattern in vuln_info["patterns"]:
                            matches = list(re.finditer(pattern, content, re.IGNORECASE))
                            for match in matches:
                                # Find line number and get the line content
                                line_num = content[: match.start()].count("\n") + 1
                                line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                                # Skip if file is a security example/test file
                                file_name = str(file_path)
                                if any(exp in file_name for exp in SECURITY_EXAMPLE_PATHS):
                                    continue

                                # Skip if this looks like detection/scanning code
                                if self._is_detection_code(line_content, match.group()):
                                    continue

                                # Phase 2: Skip safe SQL parameterization patterns
                                if vuln_type == "sql_injection":
                                    if self._is_safe_sql_parameterization(
                                        line_content,
                                        match.group(),
                                        content,
                                    ):
                                        continue

                                # Skip fake/test credentials
                                if vuln_type == "hardcoded_secret":
                                    if self._is_fake_credential(match.group()):
                                        continue

                                # Phase 2: Skip safe random usage (tests, demos, documented)
                                if vuln_type == "insecure_random":
                                    if self._is_safe_random_usage(
                                        line_content,
                                        file_name,
                                        content,
                                    ):
                                        continue

                                # Skip command_injection in documentation strings
                                if vuln_type == "command_injection":
                                    if self._is_documentation_or_string(
                                        line_content,
                                        match.group(),
                                    ):
                                        continue

                                # Check if this is a test file - downgrade to informational
                                is_test_file = any(
                                    re.search(pat, file_name) for pat in TEST_FILE_PATTERNS
                                )

                                # Skip test file findings for hardcoded_secret (expected in tests)
                                if is_test_file and vuln_type == "hardcoded_secret":
                                    continue

                                findings.append(
                                    {
                                        "type": vuln_type,
                                        "file": str(file_path),
                                        "line": line_num,
                                        "match": match.group()[:100],
                                        "severity": (
                                            "low" if is_test_file else vuln_info["severity"]
                                        ),
                                        "owasp": vuln_info["owasp"],
                                        "is_test": is_test_file,
                                    },
                                )
                except OSError:
                    continue

        # Phase 3: Apply AST-based filtering for command injection
        findings = self._apply_phase3_filtering(findings)

        # Auth strategy integration
        self._apply_auth_strategy(target, input_data)

        input_tokens = len(str(input_data)) // 4
        output_tokens = len(str(findings)) // 4

        return (
            {
                "findings": findings,
                "files_scanned": files_scanned,
                "finding_count": len(findings),
                **input_data,
            },
            input_tokens,
            output_tokens,
        )

    def _apply_phase3_filtering(self, findings: list[dict]) -> list[dict]:
        """Apply AST-based Phase 3 filtering for command injection findings.

        Args:
            findings: List of raw findings from triage scan.

        Returns:
            Filtered findings list.

        """
        try:
            from .security_audit_phase3 import apply_phase3_filtering

            # Separate command injection findings
            cmd_findings = [f for f in findings if f["type"] == "command_injection"]
            other_findings = [f for f in findings if f["type"] != "command_injection"]

            # Apply Phase 3 filtering to command injection
            filtered_cmd = apply_phase3_filtering(cmd_findings)

            # Combine back
            findings = other_findings + filtered_cmd

            logger.info(
                f"Phase 3: Filtered command_injection from {len(cmd_findings)} to {len(filtered_cmd)} "
                f"({len(cmd_findings) - len(filtered_cmd)} false positives removed)",
            )
        except ImportError:
            logger.debug("Phase 3 module not available, skipping AST-based filtering")
        except Exception as e:
            logger.warning(f"Phase 3 filtering failed: {e}")

        return findings

    def _apply_auth_strategy(self, target: Path, input_data: dict) -> None:
        """Detect codebase size and recommend auth mode.

        Args:
            target: Path to scan target.
            input_data: Original input data dict.

        """
        if not self.enable_auth_strategy:
            return

        try:
            from attune.models import (
                count_lines_of_code,
                get_auth_strategy,
                get_module_size_category,
            )

            # Calculate codebase size
            codebase_lines = 0
            if target.exists():
                if target.is_file():
                    codebase_lines = count_lines_of_code(target)
                elif target.is_dir():
                    # Sum lines across all Python files
                    for py_file in target.rglob("*.py"):
                        try:
                            codebase_lines += count_lines_of_code(py_file)
                        except Exception:
                            pass

            if codebase_lines > 0:
                # Get auth strategy (first-time setup if needed)
                strategy = get_auth_strategy()

                # Get recommended auth mode
                recommended_mode = strategy.get_recommended_mode(codebase_lines)
                self._auth_mode_used = recommended_mode.value

                # Get size category
                size_category = get_module_size_category(codebase_lines)

                # Log recommendation
                logger.info(f"Codebase: {target} ({codebase_lines} LOC, {size_category})")
                logger.info(f"Recommended auth mode: {recommended_mode.value}")

                # Get cost estimate
                cost_estimate = strategy.estimate_cost(codebase_lines, recommended_mode)

                if recommended_mode.value == "subscription":
                    logger.info(
                        f"Cost: {cost_estimate['quota_cost']} "
                        f"(fits in {cost_estimate['fits_in_context']} context)",
                    )
                else:  # API
                    logger.info(
                        f"Cost: ~${cost_estimate['monetary_cost']:.4f} (1M context window)",
                    )

        except Exception as e:
            # Don't fail workflow if auth strategy fails
            logger.warning(f"Auth strategy detection failed: {e}")
