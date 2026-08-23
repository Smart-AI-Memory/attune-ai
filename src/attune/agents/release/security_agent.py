"""Security auditor agent for Release Preparation Agent Team.

Runs bandit on the codebase and classifies vulnerabilities by severity.
Supports LLM-enhanced classification when an API key is available.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from attune.agents.state.store import AgentStateStore

from .base_agent import ReleaseAgent, _run_command
from .release_models import (
    LLM_MODE,
    Tier,
)
from .release_parsing import _parse_response

logger = logging.getLogger(__name__)

# Severity counts parsed from bandit are authoritative for the release
# gate — an LLM response must never lower them, or a hallucinated zero
# count could pass a gate that real findings should fail. A stricter
# LLM count may raise one (fail-closed ratchet, see _execute_tier).
_SEVERITY_COUNT_KEYS = (
    "critical_issues",
    "high_issues",
    "medium_issues",
    "low_issues",
)
_BANDIT_AUTHORITATIVE_KEYS = frozenset(_SEVERITY_COUNT_KEYS) | {"total_findings"}


class SecurityAuditorAgent(ReleaseAgent):
    """Analyzes bandit output and classifies vulnerabilities by severity.

    Rule-based: Runs bandit on the codebase, parses results.
    LLM-enhanced: Sends results to LLM for nuanced classification.
    """

    SYSTEM_PROMPT = (
        "You are a security auditor. Analyze the bandit scan results and "
        "classify vulnerabilities. Respond in JSON:\n"
        '{"critical_issues": N, "high_issues": N, "medium_issues": N, '
        '"low_issues": N, "score": 0-100, "confidence": 0.0-1.0, '
        '"top_findings": [{"file": "...", "issue": "...", '
        '"severity": "..."}]}'
    )

    def __init__(
        self,
        redis_client: Any | None = None,
        state_store: AgentStateStore | None = None,
    ) -> None:
        """Initialize the security audit agent.

        Args:
            redis_client: Optional Redis connection for coordination.
            state_store: Optional persistent state store.
        """
        super().__init__(
            agent_id=f"security-auditor-{uuid4().hex[:8]}",
            role="Security Auditor",
            redis_client=redis_client,
            state_store=state_store,
        )

    def _execute_tier(self, codebase_path: str, tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Run security analysis."""
        try:
            # Run bandit
            returncode, stdout, stderr = _run_command(
                [
                    "uv",
                    "run",
                    "bandit",
                    "-r",
                    "src/",
                    "-f",
                    "json",
                    "--severity-level",
                    "medium",
                    # bandit >= 1.9 writes a rich "Working... 100%" progress
                    # line to STDOUT ahead of the JSON document; -q
                    # suppresses it so stdout is the document alone.
                    "-q",
                ],
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
                        findings.update(
                            {
                                k: v
                                for k, v in llm_findings.items()
                                if k not in _BANDIT_AUTHORITATIVE_KEYS
                            }
                        )
                        # Fail-closed ratchet: a stricter LLM severity
                        # count may raise the bandit value, never lower it.
                        for key in _SEVERITY_COUNT_KEYS:
                            llm_count = llm_findings.get(key)
                            if (
                                isinstance(llm_count, int)
                                and not isinstance(llm_count, bool)
                                and llm_count > findings[key]
                            ):
                                findings[key] = llm_count

            findings["mode"] = "llm" if self.llm_client else "rule_based"
            findings["tier"] = tier.value

            # Success = no critical issues
            critical = findings.get("critical_issues", 0)
            return critical == 0, findings

        except Exception as e:  # noqa: BLE001
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
        # Both degrade paths below carry the -1 sentinel: an auditor that
        # did not run, or whose output could not be read, has produced NO
        # count, and the Security gate treats no count as a failure
        # (contract principle 7 — absence is not a pass).
        if returncode == -1:
            # bandit not installed -- report as unknown
            return {
                "critical_issues": -1,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "score": 50.0,
                "confidence": 0.3,
                "note": "bandit not available",
            }

        try:
            data = json.loads(stdout)
            if not isinstance(data, dict):
                # A bandit build that emits an array or scalar takes the
                # same degrade path as unparseable output — data.get()
                # below is outside this try (library-review C3).
                raise ValueError("bandit output was not a JSON object")
        except ValueError:  # includes json.JSONDecodeError
            return {
                "critical_issues": -1,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "score": 50.0,
                "confidence": 0.5,
                "note": "Could not parse bandit output",
            }

        results = data.get("results", [])
        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }

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
                },
            )

        return {
            # INTENTIONAL: counts CRITICAL+HIGH because the release gate
            # (max_critical_issues: 0) must block on HIGH findings too.
            # The name is historical — renaming would break gate configs
            # and downstream consumers of this payload.
            "critical_issues": (severity_counts["CRITICAL"] + severity_counts["HIGH"]),
            "high_issues": severity_counts["HIGH"],
            "medium_issues": severity_counts["MEDIUM"],
            "low_issues": severity_counts["LOW"],
            "total_findings": total,
            "score": score,
            "confidence": 0.9,
            "top_findings": top_findings,
        }
