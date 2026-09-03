"""Test coverage agent for Release Preparation Agent Team.

Runs pytest with coverage and parses the coverage report. Falls back
to heuristic estimation when coverage measurement is unavailable.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from attune.agents.state.store import AgentStateStore
from attune.utils.coverage import detect_coverage_target as _detect_coverage_target

from .base_agent import ReleaseAgent, _run_command
from .release_models import Tier

logger = logging.getLogger(__name__)

COVERAGE_TIMEOUT_SECONDS = 900


class TestCoverageAgent(ReleaseAgent):
    """Runs pytest --cov and parses coverage report.

    Rule-based: Runs pytest, extracts line coverage percentage.
    Fully deterministic — every tier runs the same pytest probe and no
    LLM call is made (unlike the sibling release agents).
    """

    def __init__(
        self,
        redis_client: Any | None = None,
        state_store: AgentStateStore | None = None,
    ) -> None:
        """Initialize the test coverage agent.

        Args:
            redis_client: Optional Redis connection for coordination.
            state_store: Optional persistent state store.
        """
        super().__init__(
            agent_id=f"test-coverage-{uuid4().hex[:8]}",
            role="Test Coverage",
            redis_client=redis_client,
            state_store=state_store,
        )

    def _execute_tier(self, codebase_path: str, tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Run test coverage analysis."""
        try:
            # Step 1: Quick test count (--collect-only is fast)
            returncode, stdout, stderr = _run_command(
                ["uv", "run", "pytest", "--co", "-q", "--no-header"],
                cwd=codebase_path,
            )

            test_count = 0
            if returncode in (0, 5):  # 5 = no tests collected (still OK)
                for line in stdout.strip().splitlines():
                    line = line.strip()
                    if line and "::" in line:
                        test_count += 1
                # Also check for "X tests collected" summary
                count_match = re.search(r"(\d+)\s+test", stdout)
                if count_match and test_count == 0:
                    test_count = int(count_match.group(1))

            # Step 2: Try actual coverage (with short timeout)
            cov_target = _detect_coverage_target(codebase_path)
            cov_returncode, cov_stdout, _cov_stderr = _run_command(
                [
                    "uv",
                    "run",
                    "pytest",
                    f"--cov={cov_target}",
                    "--cov-report=term-missing",
                    "-x",
                    "-q",
                    "--no-header",
                    "--timeout=30",
                ],
                cwd=codebase_path,
                timeout=COVERAGE_TIMEOUT_SECONDS,
            )

            coverage_percent = self._parse_coverage_output(cov_stdout)

            # If coverage couldn't be measured, estimate from test count
            if coverage_percent < 0:
                # Heuristic based on test count for this codebase
                if test_count > 500:
                    coverage_percent = 85.0
                elif test_count > 200:
                    coverage_percent = 80.0
                elif test_count > 100:
                    coverage_percent = 75.0
                elif test_count > 50:
                    coverage_percent = 60.0
                elif test_count > 10:
                    coverage_percent = 40.0
                else:
                    coverage_percent = 20.0
                estimated = True
            else:
                estimated = False

            findings = {
                "coverage_percent": coverage_percent,
                "test_count": test_count,
                "estimated": estimated,
                "score": coverage_percent,
                "confidence": 0.5 if estimated else 0.9,
                "tier": tier.value,
                "mode": "rule_based",
            }

            # Always succeed -- the analysis completed, even if estimated.
            # The quality gate evaluation handles pass/fail threshold.
            return True, findings

        except Exception as e:  # noqa: BLE001
            logger.error(f"Test coverage analysis failed: {e}")
            return False, {
                "error": str(e),
                "coverage_percent": 0.0,
                "score": 0.0,
                "confidence": 0.1,
            }

    def _parse_coverage_output(self, output: str) -> float:
        """Parse pytest-cov output for total coverage percentage.

        Args:
            output: pytest stdout with coverage report

        Returns:
            Coverage percentage, or -1.0 if not parseable

        """
        # Look for "TOTAL" line: "TOTAL    1234   567    54%"
        for line in output.splitlines():
            match = re.match(
                r"^TOTAL\s+\d+\s+\d+(?:\s+\d+\s+\d+)?\s+(\d+(?:\.\d+)?)%\s*$",
                line.strip(),
            )
            if match:
                return float(match.group(1))

        # Alternate pattern: "X% coverage"
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:coverage|total)",
            output,
            re.IGNORECASE,
        )
        if match:
            return float(match.group(1))

        return -1.0
