"""Code quality agent for Release Preparation Agent Team.

Runs ruff, checks type hints and complexity, and classifies violations
by category. Supports LLM-enhanced quality assessment.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from attune.agents.state.store import AgentStateStore

from .base_agent import ReleaseAgent, _run_command
from .release_models import (
    DEFAULT_QUALITY_GATES,
    LLM_MODE,
    Tier,
)
from .release_parsing import _parse_response

logger = logging.getLogger(__name__)


class CodeQualityAgent(ReleaseAgent):
    """Runs ruff, checks type hints and complexity.

    Rule-based: Runs ruff check, counts violations by category.
    LLM-enhanced: Sends violations to LLM for quality assessment.
    """

    SYSTEM_PROMPT = (
        "You are a code quality reviewer. Analyze the ruff lint results "
        "and provide a quality assessment. Respond in JSON:\n"
        '{"quality_score": 0-10, "confidence": 0.0-1.0, '
        '"categories": {"style": N, "security": N, "complexity": N}, '
        '"recommendations": ["..."]}'
    )

    def __init__(
        self,
        redis_client: Any | None = None,
        state_store: AgentStateStore | None = None,
    ) -> None:
        """Initialize the code quality agent.

        Args:
            redis_client: Optional Redis connection for coordination.
            state_store: Optional persistent state store.
        """
        super().__init__(
            agent_id=f"code-quality-{uuid4().hex[:8]}",
            role="Code Quality",
            redis_client=redis_client,
            state_store=state_store,
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
            return (
                quality_score >= DEFAULT_QUALITY_GATES["min_quality_score"],
                findings,
            )

        except Exception as e:  # noqa: BLE001
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
