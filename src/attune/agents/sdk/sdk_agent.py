"""SDK-wrapped agent with progressive tier escalation.

Wraps ``claude_agent_sdk.query()`` while preserving the attune tier
escalation, Redis heartbeat, cost tracking, and persistent state patterns
used by ``ReleaseAgent`` and ``CDSAgent``.

When the SDK is not installed the agent falls back to direct
``anthropic.Anthropic`` message calls (identical to the existing agents).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from attune.agents.release.release_models import (
    ANTHROPIC_AVAILABLE,
    MODEL_CONFIG,
    Tier,
    anthropic,
)
from attune.agents.state.store import AgentStateStore

from .sdk_models import SDK_AVAILABLE, SDKAgentResult, SDKExecutionMode

logger = logging.getLogger(__name__)


class SDKAgent:
    """Agent that delegates to the Anthropic Agent SDK when available.

    Preserves the CHEAP -> CAPABLE -> PREMIUM escalation strategy and
    Redis heartbeat pattern shared with ``ReleaseAgent`` and ``CDSAgent``.

    Args:
        agent_id: Unique identifier for this agent instance.
        role: Human-readable role name.
        system_prompt: System-level instructions for the agent.
        mode: SDK execution mode (TOOLS_ONLY or FULL_SDK).
        redis_client: Optional Redis connection for coordination.
        state_store: Optional persistent state store.

    """

    def __init__(
        self,
        agent_id: str | None = None,
        role: str = "SDK Agent",
        system_prompt: str = "",
        mode: SDKExecutionMode = SDKExecutionMode.TOOLS_ONLY,
        redis_client: Any | None = None,
        state_store: AgentStateStore | None = None,
    ) -> None:
        self.agent_id = agent_id or f"sdk-agent-{uuid4().hex[:8]}"
        self.role = role
        self.system_prompt = system_prompt
        self.mode = mode
        self.redis = redis_client
        self.state_store = state_store
        self.current_tier = Tier.CHEAP
        self.total_cost = 0.0
        self.total_tokens = 0

        # Anthropic client for fallback / TOOLS_ONLY mode
        self.llm_client: Any | None = None
        if ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.llm_client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Heartbeat (identical pattern to ReleaseAgent / CDSAgent)
    # ------------------------------------------------------------------

    def _register_heartbeat(self, status: str = "running", task: str = "") -> None:
        """Register agent liveness in Redis (no-op if unavailable).

        Args:
            status: Current agent status.
            task: Human-readable description of current task.

        """
        if self.redis is None:
            return
        try:
            key = f"sdk:agent:heartbeat:{self.agent_id}"
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
        except Exception as e:
            # INTENTIONAL: Redis is optional, don't fail on connection issues
            logger.debug(f"Heartbeat failed (non-fatal): {e}")

    # ------------------------------------------------------------------
    # SDK query wrapper
    # ------------------------------------------------------------------

    def _call_sdk_query(self, prompt: str, tier: Tier) -> tuple[str, dict[str, Any]]:
        """Call the Agent SDK (or fallback to Messages API).

        Args:
            prompt: User prompt to send.
            tier: Model tier to use.

        Returns:
            Tuple of (response_text, metadata_dict).

        """
        model = MODEL_CONFIG[tier.value]

        # --- Full SDK path ---
        if SDK_AVAILABLE and self.mode == SDKExecutionMode.FULL_SDK:
            try:
                import claude_agent_sdk  # type: ignore[import-untyped]

                result = claude_agent_sdk.query(
                    prompt=prompt,
                    model=model,
                    system=self.system_prompt,
                )
                response_text = getattr(result, "text", str(result))
                cost = getattr(result, "cost", 0.0)
                self.total_cost += cost
                return response_text, {
                    "model": model,
                    "cost": cost,
                    "sdk": True,
                }
            except Exception as e:
                logger.warning(f"SDK query failed, falling back: {e}")
                # Fall through to Messages API

        # --- Messages API fallback ---
        if not self.llm_client:
            return "", {"model": "rule_based", "cost": 0.0, "sdk": False}

        try:
            response = self.llm_client.messages.create(
                model=model,
                max_tokens=1024,
                system=self.system_prompt,
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
                "sdk": False,
            }
        except Exception as e:
            logger.error(f"LLM call failed for {self.role}: {e}")
            return "", {"model": "fallback", "cost": 0.0, "error": str(e), "sdk": False}

    # ------------------------------------------------------------------
    # Tier execution
    # ------------------------------------------------------------------

    def _execute_tier(self, input_data: dict[str, Any], tier: Tier) -> tuple[bool, dict[str, Any]]:
        """Execute the agent at a specific tier.

        Subclasses can override this for domain-specific logic. The default
        implementation sends the input as a JSON prompt and attempts to parse
        a JSON response.

        Args:
            input_data: Structured input for the agent.
            tier: Current model tier.

        Returns:
            Tuple of (success, findings_dict).

        """
        prompt = json.dumps(input_data, indent=2, default=str)
        response_text, meta = self._call_sdk_query(prompt, tier)

        if not response_text:
            return False, {"error": "No response", "tier": tier.value, **meta}

        # Try to parse JSON response
        try:
            findings = json.loads(response_text)
        except json.JSONDecodeError:
            findings = {"raw_response": response_text}

        findings["tier"] = tier.value
        findings["mode"] = "sdk" if meta.get("sdk") else "messages_api"
        return True, findings

    # ------------------------------------------------------------------
    # Main process entry point
    # ------------------------------------------------------------------

    def process(self, input_data: dict[str, Any]) -> SDKAgentResult:
        """Process input with progressive tier escalation.

        Args:
            input_data: Structured input for the agent.

        Returns:
            SDKAgentResult with findings and metadata.

        """
        start = time.time()
        escalated = False

        # Record start in persistent state
        exec_id: str | None = None
        if self.state_store is not None:
            exec_id = self.state_store.record_start(
                self.agent_id,
                self.role,
                input_summary=str(list(input_data.keys())),
            )

        # Try CHEAP first
        self.current_tier = Tier.CHEAP
        self._register_heartbeat(status="running", task="Analyzing")
        success, findings = self._execute_tier(input_data, Tier.CHEAP)

        # Escalate to CAPABLE if needed
        if not success:
            escalated = True
            self.current_tier = Tier.CAPABLE
            self._register_heartbeat(status="escalating", task="Retrying")
            success, findings = self._execute_tier(input_data, Tier.CAPABLE)

        # Escalate to PREMIUM if still failing
        if not success:
            self.current_tier = Tier.PREMIUM
            self._register_heartbeat(status="escalating", task="Premium retry")
            success, findings = self._execute_tier(input_data, Tier.PREMIUM)

        execution_time = (time.time() - start) * 1000
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
                    error=findings.get("error", "Execution failed after tier escalation"),
                )

        return SDKAgentResult(
            agent_id=self.agent_id,
            role=self.role,
            success=success,
            tier_used=self.current_tier.value,
            mode=self.mode,
            findings=findings,
            score=findings.get("score", 0.0),
            confidence=findings.get("confidence", 0.8 if success else 0.3),
            cost=self.total_cost,
            execution_time_ms=execution_time,
            escalated=escalated,
            sdk_used=findings.get("mode") == "sdk",
            error=findings.get("error"),
        )
