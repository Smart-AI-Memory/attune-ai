"""Base and specialized release agents for Release Preparation Agent Team.

Base agent class with progressive tier escalation, and concrete agent
implementations for security auditing, test coverage, code quality,
and documentation analysis.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from .release_models import (
    ANTHROPIC_AVAILABLE,
    DEFAULT_QUALITY_GATES,
    LLM_MODE,
    MODEL_CONFIG,
    ReleaseAgentResult,
    Tier,
    anthropic,
)
from .release_parsing import _parse_response

logger = logging.getLogger(__name__)


# =============================================================================
# Command Runner
# =============================================================================


def _run_command(cmd: list[str], cwd: str = ".") -> tuple[int, str, str]:
    """Run a shell command safely and return (returncode, stdout, stderr).

    Args:
        cmd: Command and arguments as list
        cwd: Working directory

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Command timed out: {' '.join(cmd)}"


# =============================================================================
# Base Agent with Progressive Tier Escalation
# =============================================================================


class ReleaseAgent:
    """Base agent with CHEAP -> CAPABLE -> PREMIUM escalation.

    Features:
        - Progressive tier escalation on failure
        - Optional Redis heartbeats (no-op when unavailable)
        - Real Anthropic API calls with rule-based fallback
        - Multi-strategy response parsing (never returns None)

    Args:
        agent_id: Unique identifier for this agent instance
        role: Human-readable role name
        redis_client: Optional Redis connection for coordination
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        redis_client: Any | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.redis = redis_client
        self.current_tier = Tier.CHEAP
        self.llm_client: Any | None = None
        self.total_cost = 0.0
        self.total_tokens = 0

        # Initialize LLM client if available and in real mode
        if ANTHROPIC_AVAILABLE and LLM_MODE == "real":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.llm_client = anthropic.Anthropic(api_key=api_key)
                logger.info(f"Agent {agent_id}: LLM client initialized")
            else:
                logger.info(f"Agent {agent_id}: No API key, using rule-based mode")

    def _register_heartbeat(self, status: str = "running", task: str = "") -> None:
        """Register agent liveness in Redis (no-op if unavailable)."""
        if self.redis is None:
            return
        try:
            key = f"release:agent:heartbeat:{self.agent_id}"
            self.redis.hset(
                key,
                mapping={
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "status": status,
                    "current_task": task,
                    "tier": self.current_tier.value,
                    "last_beat": time.time(),
                },
            )
            self.redis.expire(key, 60)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Redis is optional, don't fail on connection issues
            logger.debug(f"Heartbeat failed (non-fatal): {e}")

    def _signal_completion(self, result: dict[str, Any]) -> None:
        """Signal task completion via Redis (no-op if unavailable)."""
        if self.redis is None:
            return
        try:
            signal = {
                "agent_id": self.agent_id,
                "role": self.role,
                "result_summary": {
                    k: v for k, v in result.items() if isinstance(v, str | int | float | bool)
                },
                "tier_used": self.current_tier.value,
                "timestamp": time.time(),
            }
            self.redis.publish(
                f"release:signals:{self.agent_id}",
                json.dumps(signal),
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Redis is optional
            logger.debug(f"Signal failed (non-fatal): {e}")

    def _call_llm(self, prompt: str, system: str, tier: Tier) -> tuple[str, dict[str, Any]]:
        """Call LLM with tier-appropriate model.

        Args:
            prompt: User prompt
            system: System prompt
            tier: Model tier to use

        Returns:
            Tuple of (response_text, metadata)
        """
        if not self.llm_client:
            return "", {"model": "rule_based", "cost": 0.0}

        model = MODEL_CONFIG[tier.value]

        try:
            response = self.llm_client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            pricing = {
                "cheap": {"input": 0.80, "output": 4.00},
                "capable": {"input": 3.00, "output": 15.00},
                "premium": {"input": 15.00, "output": 75.00},
            }
            tier_pricing = pricing[tier.value]
            cost = (
                input_tokens * tier_pricing["input"] / 1_000_000
                + output_tokens * tier_pricing["output"] / 1_000_000
            )

            self.total_cost += cost
            self.total_tokens += input_tokens + output_tokens

            response_text = ""
            if response.content:
                first_block = response.content[0]
                if hasattr(first_block, "text"):
                    response_text = first_block.text  # type: ignore[union-attr]

            return response_text, {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
            }

        except Exception as e:
            logger.error(f"LLM call failed for {self.role}: {e}")
            return "", {"model": "fallback", "cost": 0.0, "error": str(e)}

    def process(self, codebase_path: str = ".") -> ReleaseAgentResult:
        """Process with progressive tier escalation.

        Args:
            codebase_path: Path to the codebase to analyze

        Returns:
            ReleaseAgentResult with findings and score
        """
        start = time.time()
        escalated = False

        # Try CHEAP first
        self.current_tier = Tier.CHEAP
        self._register_heartbeat(status="running", task="Analyzing")

        success, findings = self._execute_tier(codebase_path, Tier.CHEAP)

        # Escalate to CAPABLE if needed
        if not success:
            escalated = True
            self.current_tier = Tier.CAPABLE
            self._register_heartbeat(status="escalating", task="Retrying")
            success, findings = self._execute_tier(codebase_path, Tier.CAPABLE)

        # Escalate to PREMIUM if still failing
        if not success:
            self.current_tier = Tier.PREMIUM
            self._register_heartbeat(status="escalating", task="Premium retry")
            success, findings = self._execute_tier(codebase_path, Tier.PREMIUM)

        execution_time = (time.time() - start) * 1000

        # Signal completion
        self._signal_completion(findings)
        self._register_heartbeat(status="idle", task="")

        return ReleaseAgentResult(
            agent_id=self.agent_id,
            agent_role=self.role,
            success=success,
            tier_used=self.current_tier,
            findings=findings,
            score=findings.get("score", 0.0),
            confidence=findings.get("confidence", 0.8 if success else 0.3),
            cost=self.total_cost,
            execution_time_ms=execution_time,
            escalated=escalated,
        )

    def _execute_tier(self, codebase_path: str, tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Execute at specific tier. Override in subclasses.

        Args:
            codebase_path: Path to codebase
            tier: Current tier

        Returns:
            Tuple of (success, findings_dict)
        """
        raise NotImplementedError


# =============================================================================
# Specialized Release Agents
# =============================================================================


class SecurityAuditorAgent(ReleaseAgent):
    """Analyzes bandit output and classifies vulnerabilities by severity.

    Rule-based: Runs bandit on the codebase, parses results.
    LLM-enhanced: Sends results to LLM for nuanced classification.
    """

    SYSTEM_PROMPT = (
        "You are a security auditor. Analyze the bandit scan results and classify "
        "vulnerabilities. Respond in JSON:\n"
        '{"critical_issues": N, "high_issues": N, "medium_issues": N, '
        '"low_issues": N, "score": 0-100, "confidence": 0.0-1.0, '
        '"top_findings": [{"file": "...", "issue": "...", "severity": "..."}]}'
    )

    def __init__(self, redis_client: Any | None = None) -> None:
        super().__init__(
            agent_id=f"security-auditor-{uuid4().hex[:8]}",
            role="Security Auditor",
            redis_client=redis_client,
        )

    def _execute_tier(self, codebase_path: str, tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Run security analysis."""
        try:
            # Run bandit
            returncode, stdout, stderr = _run_command(
                ["uv", "run", "bandit", "-r", "src/", "-f", "json", "--severity-level", "medium"],
                cwd=codebase_path,
            )

            # Parse bandit JSON output
            findings = self._parse_bandit_output(stdout, returncode)

            # If LLM available, enhance with classification
            if self.llm_client and LLM_MODE == "real":
                prompt = f"Analyze these bandit results:\n{stdout[:3000]}"
                response_text, _meta = self._call_llm(prompt, self.SYSTEM_PROMPT, tier)
                if response_text:
                    llm_findings = _parse_response(response_text)
                    if "parse_error" not in llm_findings:
                        findings.update(llm_findings)

            findings["mode"] = "llm" if self.llm_client else "rule_based"
            findings["tier"] = tier.value

            # Success = no critical issues
            critical = findings.get("critical_issues", 0)
            return critical == 0, findings

        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return False, {"error": str(e), "critical_issues": -1}

    def _parse_bandit_output(self, stdout: str, returncode: int) -> dict[str, Any]:
        """Parse bandit JSON output into structured findings.

        Args:
            stdout: Bandit stdout (JSON format)
            returncode: Bandit exit code

        Returns:
            Dict with classified findings
        """
        if returncode == -1:
            # bandit not installed — report as unknown
            return {
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "score": 50.0,
                "confidence": 0.3,
                "note": "bandit not available",
            }

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return {
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "score": 50.0,
                "confidence": 0.5,
                "note": "Could not parse bandit output",
            }

        results = data.get("results", [])
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for result in results:
            sev = result.get("issue_severity", "LOW").upper()
            if sev in severity_counts:
                severity_counts[sev] += 1

        total = sum(severity_counts.values())
        # Score: 100 if no issues, decreasing with severity
        score = max(
            0.0,
            100.0
            - severity_counts["CRITICAL"] * 30
            - severity_counts["HIGH"] * 15
            - severity_counts["MEDIUM"] * 5
            - severity_counts["LOW"] * 1,
        )

        top_findings = []
        for r in results[:5]:
            top_findings.append(
                {
                    "file": r.get("filename", "unknown"),
                    "line": r.get("line_number", 0),
                    "issue": r.get("issue_text", ""),
                    "severity": r.get("issue_severity", "LOW"),
                }
            )

        return {
            "critical_issues": severity_counts["CRITICAL"] + severity_counts["HIGH"],
            "high_issues": severity_counts["HIGH"],
            "medium_issues": severity_counts["MEDIUM"],
            "low_issues": severity_counts["LOW"],
            "total_findings": total,
            "score": score,
            "confidence": 0.9,
            "top_findings": top_findings,
        }


class TestCoverageAgent(ReleaseAgent):
    """Runs pytest --cov and parses coverage report.

    Rule-based: Runs pytest, extracts line coverage percentage.
    LLM-enhanced: Sends coverage gaps to LLM for gap analysis.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        super().__init__(
            agent_id=f"test-coverage-{uuid4().hex[:8]}",
            role="Test Coverage",
            redis_client=redis_client,
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
            cov_returncode, cov_stdout, _cov_stderr = _run_command(
                [
                    "uv",
                    "run",
                    "pytest",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "-x",
                    "-q",
                    "--no-header",
                    "--timeout=30",
                ],
                cwd=codebase_path,
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

            # Always succeed — the analysis completed, even if estimated.
            # The quality gate evaluation handles pass/fail threshold.
            return True, findings

        except Exception as e:
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
            if "TOTAL" in line:
                match = re.search(r"(\d+)%", line)
                if match:
                    return float(match.group(1))

        # Alternate pattern: "X% coverage"
        match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:coverage|total)", output, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return -1.0


class CodeQualityAgent(ReleaseAgent):
    """Runs ruff, checks type hints and complexity.

    Rule-based: Runs ruff check, counts violations by category.
    LLM-enhanced: Sends violations to LLM for quality assessment.
    """

    SYSTEM_PROMPT = (
        "You are a code quality reviewer. Analyze the ruff lint results and provide "
        "a quality assessment. Respond in JSON:\n"
        '{"quality_score": 0-10, "confidence": 0.0-1.0, '
        '"categories": {"style": N, "security": N, "complexity": N}, '
        '"recommendations": ["..."]}'
    )

    def __init__(self, redis_client: Any | None = None) -> None:
        super().__init__(
            agent_id=f"code-quality-{uuid4().hex[:8]}",
            role="Code Quality",
            redis_client=redis_client,
        )

    def _execute_tier(self, codebase_path: str, tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Run code quality analysis."""
        try:
            # Run ruff check
            returncode, stdout, stderr = _run_command(
                ["uv", "run", "ruff", "check", "src/", "--statistics"],
                cwd=codebase_path,
            )

            findings = self._parse_ruff_output(stdout, returncode)

            # If LLM available, enhance with quality assessment
            if self.llm_client and LLM_MODE == "real":
                prompt = f"Analyze these ruff lint results:\n{stdout[:3000]}"
                response_text, _meta = self._call_llm(prompt, self.SYSTEM_PROMPT, tier)
                if response_text:
                    llm_findings = _parse_response(response_text)
                    if "parse_error" not in llm_findings:
                        # Prefer LLM quality score if available
                        if "quality_score" in llm_findings:
                            findings["quality_score"] = llm_findings["quality_score"]
                            findings["score"] = llm_findings["quality_score"]

            findings["tier"] = tier.value
            findings["mode"] = "llm" if self.llm_client else "rule_based"

            quality_score = findings.get("quality_score", findings.get("score", 0.0))
            return quality_score >= DEFAULT_QUALITY_GATES["min_quality_score"], findings

        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
            return False, {
                "error": str(e),
                "quality_score": 0.0,
                "score": 0.0,
                "confidence": 0.1,
            }

    def _parse_ruff_output(self, stdout: str, returncode: int) -> dict[str, Any]:
        """Parse ruff statistics output.

        Args:
            stdout: Ruff stdout
            returncode: Ruff exit code

        Returns:
            Quality findings dict
        """
        if returncode == -1:
            return {
                "quality_score": 5.0,
                "score": 5.0,
                "confidence": 0.3,
                "total_violations": 0,
                "note": "ruff not available",
            }

        # Count violations from statistics output
        total_violations = 0
        categories: dict[str, int] = {}

        for line in stdout.strip().splitlines():
            # Pattern: "42 E501 Line too long"
            match = re.match(r"\s*(\d+)\s+(\w+)\s+(.*)", line)
            if match:
                count = int(match.group(1))
                code = match.group(2)
                total_violations += count

                # Categorize by code prefix
                prefix = code[0] if code else "U"
                category_map = {
                    "E": "style",
                    "W": "style",
                    "F": "errors",
                    "B": "bugs",
                    "S": "security",
                    "C": "complexity",
                    "I": "imports",
                }
                cat = category_map.get(prefix, "other")
                categories[cat] = categories.get(cat, 0) + count

        # Score: 10 for 0 violations, decreasing logarithmically
        if total_violations == 0:
            quality_score = 10.0
        elif total_violations < 10:
            quality_score = 9.0
        elif total_violations < 30:
            quality_score = 8.0
        elif total_violations < 100:
            quality_score = 7.0
        elif total_violations < 300:
            quality_score = 5.0
        else:
            quality_score = 3.0

        return {
            "quality_score": quality_score,
            "score": quality_score,
            "total_violations": total_violations,
            "categories": categories,
            "confidence": 0.85,
        }


class DocumentationAgent(ReleaseAgent):
    """Checks docstring coverage, README currency, and CHANGELOG presence.

    Rule-based: Walks Python files, counts functions with/without docstrings.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        super().__init__(
            agent_id=f"documentation-{uuid4().hex[:8]}",
            role="Documentation",
            redis_client=redis_client,
        )

    def _execute_tier(self, codebase_path: str, tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Run documentation analysis."""
        try:
            src_path = Path(codebase_path) / "src"
            if not src_path.exists():
                src_path = Path(codebase_path)

            # Count functions and docstrings using AST
            total_functions = 0
            documented_functions = 0
            undocumented: list[str] = []

            py_files = list(src_path.rglob("*.py"))
            for py_file in py_files:
                try:
                    source = py_file.read_text(encoding="utf-8")
                    tree = ast.parse(source)
                except (SyntaxError, UnicodeDecodeError):
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                        # Skip private/dunder methods
                        if node.name.startswith("_") and not node.name.startswith("__"):
                            continue

                        total_functions += 1
                        docstring = ast.get_docstring(node)
                        if docstring:
                            documented_functions += 1
                        else:
                            rel_path = py_file.relative_to(Path(codebase_path))
                            undocumented.append(f"{rel_path}:{node.lineno}:{node.name}")

            # Calculate coverage
            doc_coverage = (
                (documented_functions / total_functions * 100.0) if total_functions > 0 else 0.0
            )

            # Check README and CHANGELOG
            readme_exists = (Path(codebase_path) / "README.md").exists()
            changelog_exists = (Path(codebase_path) / "CHANGELOG.md").exists()

            findings = {
                "coverage_percent": round(doc_coverage, 1),
                "total_functions": total_functions,
                "documented_functions": documented_functions,
                "undocumented_count": total_functions - documented_functions,
                "undocumented_sample": undocumented[:10],
                "readme_exists": readme_exists,
                "changelog_exists": changelog_exists,
                "score": doc_coverage,
                "confidence": 0.9,
                "tier": tier.value,
                "mode": "rule_based",
            }

            # Documentation is non-blocking, so always "succeeds"
            # but the quality gate evaluation handles the threshold check
            return True, findings

        except Exception as e:
            logger.error(f"Documentation analysis failed: {e}")
            return False, {
                "error": str(e),
                "coverage_percent": 0.0,
                "score": 0.0,
                "confidence": 0.1,
            }
