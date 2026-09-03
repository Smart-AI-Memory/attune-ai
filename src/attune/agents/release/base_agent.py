"""Base release agent with progressive tier escalation.

Provides the ReleaseAgent base class and the _run_command helper used
by all specialized release agents.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from typing import Any

from attune.agents.state.store import AgentStateStore
from attune.llm.fable_call import create_with_fable
from attune.model_tiers import ModelRefusalError
from attune.models.registry import TIER_PRICING

from .release_models import (
    ANTHROPIC_AVAILABLE,
    LLM_MODE,
    ReleaseAgentResult,
    Tier,
    anthropic,
    get_model_config,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Command Runner
# =============================================================================


def _run_command(
    cmd: list[str],
    cwd: str = ".",
    timeout: int = 120,
) -> tuple[int, str, str]:
    """Run a shell command safely and return (returncode, stdout, stderr).

    Args:
        cmd: Command and arguments as list
        cwd: Working directory
        timeout: Maximum command runtime in seconds.

    Returns:
        Tuple of (return_code, stdout, stderr)

    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
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
        state_store: AgentStateStore | None = None,
    ) -> None:
        """Initialize the release agent.

        Args:
            agent_id: Unique identifier for this agent instance.
            role: Human-readable role name.
            redis_client: Optional Redis connection for coordination.
            state_store: Optional persistent state store.
        """
        self.agent_id = agent_id
        self.role = role
        self.redis = redis_client
        self.state_store = state_store
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

        model = get_model_config()[tier.value]

        try:
            # Premium tier resolves to fable — the helper routes fable
            # models via the beta namespace (+ server-side opus fallback)
            # and raises ModelRefusalError on refusal; non-fable models
            # take the exact pre-tier path.
            response = create_with_fable(
                self.llm_client,
                model=model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            tier_pricing = TIER_PRICING[tier.value]
            cost = (
                input_tokens * tier_pricing["input"] / 1_000_000
                + output_tokens * tier_pricing["output"] / 1_000_000
            )

            self.total_cost += cost
            self.total_tokens += input_tokens + output_tokens

            # First TEXT block, not content[0] — fable responses can lead
            # with a thinking block that has no .text (fable_call docstring).
            response_text = ""
            for block in response.content or []:
                if hasattr(block, "text"):
                    response_text = block.text
                    break

            return response_text, {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
            }

        except ModelRefusalError as e:
            # The whole fable -> opus fallback chain refused — record the
            # fable_refusal telemetry event, then keep the graceful
            # rule-based fallback contract.
            from attune.models.telemetry import log_fable_refusal

            log_fable_refusal(e, workflow=self.role, model=model)
            logger.error(f"LLM refusal for {self.role}: {e}")
            return "", {"model": "fallback", "cost": 0.0, "error": str(e)}
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: LLM calls may fail for many reasons; graceful fallback
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

        # Record execution start in persistent state
        exec_id: str | None = None
        if self.state_store is not None:
            exec_id = self.state_store.record_start(
                self.agent_id,
                self.role,
                input_summary=codebase_path,
            )

        # Try CHEAP first
        self.current_tier = Tier.CHEAP
        self._register_heartbeat(status="running", task="Analyzing")

        success, findings = self._execute_tier(codebase_path, Tier.CHEAP)

        # Escalate to CAPABLE if needed. A tier may mark its failure
        # ``retryable: False`` when a stronger model cannot change the
        # outcome (a tool that did not run, unreadable tool output) —
        # re-running it would spend two more tool runs and two LLM calls
        # on a result that is already final.
        if not success and findings.get("retryable", True):
            escalated = True
            self.current_tier = Tier.CAPABLE
            self._register_heartbeat(status="escalating", task="Retrying")
            success, findings = self._execute_tier(codebase_path, Tier.CAPABLE)

        # Escalate to PREMIUM if still failing
        if not success and findings.get("retryable", True):
            self.current_tier = Tier.PREMIUM
            self._register_heartbeat(status="escalating", task="Premium retry")
            success, findings = self._execute_tier(codebase_path, Tier.PREMIUM)

        execution_time = (time.time() - start) * 1000

        # Signal completion
        self._signal_completion(findings)
        self._register_heartbeat(status="idle", task="")

        # Record completion in persistent state
        if self.state_store is not None and exec_id is not None:
            if success:
                self.state_store.record_completion(
                    self.agent_id,
                    exec_id,
                    success=success,
                    findings=findings,
                    score=findings.get("score", 0.0),
                    cost=self.total_cost,
                    execution_time_ms=execution_time,
                    tier_used=self.current_tier.value,
                    confidence=findings.get("confidence", 0.8),
                )
            else:
                self.state_store.record_failure(
                    self.agent_id,
                    exec_id,
                    error=findings.get(
                        "error",
                        "Execution failed after tier escalation",
                    ),
                )

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
