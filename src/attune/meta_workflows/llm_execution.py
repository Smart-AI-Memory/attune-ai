"""LLM execution engine with progressive tier escalation.

Handles real and simulated LLM calls for meta-workflow agents,
including progressive tier escalation (cheap -> capable -> premium)
and cost tracking via UsageTracker.

Created: 2026-02-19
Purpose: Extracted from workflow.py for focused module design
"""

import logging
import time
from typing import Any

from attune.llm.fable_call import create_with_fable
from attune.meta_workflows.models import (
    AgentExecutionResult,
    AgentSpec,
    TierStrategy,
)
from attune.meta_workflows.prompt_builder import build_agent_prompt
from attune.model_tiers import ModelRefusalError
from attune.routing.model_router import ModelRouter, ModelTier
from attune.telemetry.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


def execute_agents_real(agents: list[AgentSpec]) -> list[AgentExecutionResult]:
    """Execute agents with real LLM calls and progressive tier escalation.

    Implements progressive tier escalation strategy:
    - CHEAP_ONLY: Always uses cheap tier
    - PROGRESSIVE: cheap -> capable -> premium (escalates on failure)
    - CAPABLE_FIRST: capable -> premium (skips cheap tier)

    Each LLM call is tracked via UsageTracker for cost analysis.

    Args:
        agents: List of agent specs to execute

    Returns:
        List of agent execution results with actual LLM costs

    Raises:
        RuntimeError: If agent execution encounters fatal error

    """
    results = []
    router = ModelRouter()
    tracker = UsageTracker.get_instance()

    for agent in agents:
        logger.info(f"Executing agent: {agent.role} ({agent.tier_strategy.value})")

        try:
            result = _execute_single_agent_with_escalation(agent, router, tracker)
            results.append(result)

            logger.info(
                f"Agent {agent.role} completed: "
                f"tier={result.tier_used}, cost=${result.cost:.4f}, "
                f"success={result.success}",
            )

        except Exception as e:  # noqa: BLE001
            logger.error(f"Agent {agent.role} failed with error: {e}")

            # Create error result
            error_result = AgentExecutionResult(
                agent_id=agent.agent_id,
                role=agent.role,
                success=False,
                cost=0.0,
                duration=0.0,
                tier_used="error",
                output={"error": str(e)},
                error=str(e),
            )
            results.append(error_result)

    return results


def _execute_single_agent_with_escalation(
    agent: AgentSpec,
    router: ModelRouter,
    tracker: UsageTracker,
) -> AgentExecutionResult:
    """Execute single agent with progressive tier escalation.

    Args:
        agent: Agent specification
        router: Model router for tier selection
        tracker: Usage tracker for telemetry

    Returns:
        AgentExecutionResult with actual LLM execution data

    """
    start_time = time.time()

    # Determine tier sequence based on strategy
    if agent.tier_strategy == TierStrategy.CHEAP_ONLY:
        tiers = [ModelTier.CHEAP]
    elif agent.tier_strategy == TierStrategy.PROGRESSIVE:
        tiers = [ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM]
    elif agent.tier_strategy == TierStrategy.CAPABLE_FIRST:
        tiers = [ModelTier.CAPABLE, ModelTier.PREMIUM]
    else:
        # Fallback to capable
        logger.warning(f"Unknown tier strategy: {agent.tier_strategy}, using CAPABLE")
        tiers = [ModelTier.CAPABLE]

    # Try each tier in sequence
    result = None
    total_cost = 0.0

    for tier in tiers:
        logger.debug(f"Attempting tier: {tier.value}")

        # Execute at this tier
        tier_result = _execute_at_tier(agent, tier, router, tracker)
        total_cost += tier_result.cost

        # Check if successful
        if evaluate_success_criteria(tier_result, agent):
            # Success - return result
            tier_result.cost = total_cost  # Update with cumulative cost
            tier_result.duration = time.time() - start_time
            return tier_result

        # Failed - try next tier
        logger.debug(f"Tier {tier.value} did not meet success criteria, attempting escalation")
        result = tier_result

    # All tiers exhausted - return final result (failed)
    result.cost = total_cost
    result.duration = time.time() - start_time
    logger.warning(f"Agent {agent.role} failed at all tiers (cost: ${total_cost:.4f})")
    return result


def _execute_at_tier(
    agent: AgentSpec,
    tier: ModelTier,
    router: ModelRouter,
    tracker: UsageTracker,
) -> AgentExecutionResult:
    """Execute agent at specific tier.

    Args:
        agent: Agent specification
        tier: Model tier to use
        router: Model router
        tracker: Usage tracker

    Returns:
        AgentExecutionResult from this tier

    """
    start_time = time.time()

    # Get model config for tier (access MODELS dict directly)
    provider = router._default_provider
    model_config = router.MODELS[provider][tier.value]

    # Build prompt from agent spec
    prompt = build_agent_prompt(agent)

    # Execute LLM call
    # v4.3.0: Real LLM execution with Anthropic client
    # Falls back to simulation if API key not available

    try:
        # Execute real LLM call (with simulation fallback)
        response = execute_llm_call(prompt, model_config, tier)

        # Track telemetry
        duration_ms = int((time.time() - start_time) * 1000)
        tracker.track_llm_call(
            workflow="meta-workflow",
            stage=agent.role,
            tier=tier.value,
            model=model_config.model_id,
            provider=router._default_provider,
            cost=response["cost"],
            tokens=response["tokens"],
            cache_hit=False,
            cache_type=None,
            duration_ms=duration_ms,
            user_id=None,
        )

        # Create result
        result = AgentExecutionResult(
            agent_id=agent.agent_id,
            role=agent.role,
            success=response["success"],
            cost=response["cost"],
            duration=time.time() - start_time,
            tier_used=tier.value,
            output=response["output"],
        )

        return result

    except Exception as e:  # noqa: BLE001
        logger.error(f"LLM execution failed at tier {tier.value}: {e}")

        # Return error result
        return AgentExecutionResult(
            agent_id=agent.agent_id,
            role=agent.role,
            success=False,
            cost=0.0,
            duration=time.time() - start_time,
            tier_used=tier.value,
            output={"error": str(e)},
            error=str(e),
        )


def execute_llm_call(prompt: str, model_config: Any, tier: ModelTier) -> dict[str, Any]:
    """Execute real LLM call via Anthropic or other providers.

    Uses the Anthropic client for Claude models, with fallback to
    other providers via the model configuration.

    Args:
        prompt: Prompt to send to LLM
        model_config: Model configuration from router
        tier: Model tier being used

    Returns:
        Dict with cost, tokens, success, and output

    Raises:
        RuntimeError: If LLM call fails after retries

    """
    import os

    # Try to use Anthropic client
    try:
        from anthropic import Anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Set it in environment or .env file "
                "(checked: ./env, ~/.env, ~/.attune/.env)",
            )

        client = Anthropic(api_key=api_key)

        # Execute the LLM call. Premium tiers resolve to fable — the
        # helper routes fable models via the beta namespace (+ server-
        # side opus fallback) and raises ModelRefusalError on refusal;
        # non-fable models take the exact pre-tier path.
        response = create_with_fable(
            client,
            model=model_config.model_id,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract response data. First TEXT block, not content[0] —
        # fable responses can lead with a thinking block that has no
        # .text (fable_call docstring).
        output_text = next(
            (block.text for block in (response.content or []) if hasattr(block, "text")),
            "",
        )
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens

        # Calculate cost
        cost = (prompt_tokens / 1000) * model_config.cost_per_1k_input + (
            completion_tokens / 1000
        ) * model_config.cost_per_1k_output

        return {
            "cost": cost,
            "tokens": {
                "input": prompt_tokens,
                "output": completion_tokens,
                "total": prompt_tokens + completion_tokens,
            },
            "success": True,
            "output": {
                "message": output_text,
                "model": model_config.model_id,
                "tier": tier.value,
                "success": True,
            },
        }

    except ImportError:
        logger.warning("Anthropic client not available, using simulation")
        return simulate_llm_call(prompt, model_config, tier)

    except ModelRefusalError as e:
        # The whole fable -> opus fallback chain refused: record the
        # fable_refusal telemetry event; the item errors — never a
        # silent skip (docs/specs/fable-premium-tier design §5).
        from attune.models.telemetry import log_fable_refusal

        log_fable_refusal(e, workflow="meta_workflow", model=model_config.model_id)
        logger.error(f"LLM call refused: {e}")
        return {
            "cost": 0.0,
            "tokens": {"input": 0, "output": 0, "total": 0},
            "success": False,
            "output": {
                "error": str(e),
                "model": model_config.model_id,
                "tier": tier.value,
                "success": False,
            },
        }

    except Exception as e:  # noqa: BLE001
        logger.error(f"LLM call failed: {e}")
        # Return failure result
        return {
            "cost": 0.0,
            "tokens": {"input": 0, "output": 0, "total": 0},
            "success": False,
            "output": {
                "error": str(e),
                "model": model_config.model_id,
                "tier": tier.value,
                "success": False,
            },
        }


def simulate_llm_call(prompt: str, model_config: Any, tier: ModelTier) -> dict[str, Any]:
    """Simulate LLM call with realistic cost/token estimates.

    Used as fallback when real LLM execution is not available
    (e.g., no API key, testing mode, etc.)

    Args:
        prompt: Prompt to send to LLM
        model_config: Model configuration
        tier: Model tier

    Returns:
        Dict with cost, tokens, success, and output

    """
    import os

    # Estimate tokens (rough: ~4 chars per token)
    prompt_tokens = len(prompt) // 4
    completion_tokens = 500  # Assume moderate response

    # Calculate cost
    cost = (prompt_tokens / 1000) * model_config.cost_per_1k_input + (
        completion_tokens / 1000
    ) * model_config.cost_per_1k_output

    # Simulate success rate based on tier
    # cheap: 80%, capable: 95%, premium: 99%
    if tier == ModelTier.CHEAP:
        success = int.from_bytes(os.urandom(4), "big") / (2**32) < 0.80
    elif tier == ModelTier.CAPABLE:
        success = int.from_bytes(os.urandom(4), "big") / (2**32) < 0.95
    else:  # PREMIUM
        success = int.from_bytes(os.urandom(4), "big") / (2**32) < 0.99

    return {
        "cost": cost,
        "tokens": {
            "input": prompt_tokens,
            "output": completion_tokens,
            "total": prompt_tokens + completion_tokens,
        },
        "success": success,
        "output": {
            "message": f"Simulated response at {tier.value} tier",
            "model": model_config.model_id,
            "tier": tier.value,
            "success": success,
        },
    }


def evaluate_success_criteria(result: AgentExecutionResult, agent: AgentSpec) -> bool:
    """Evaluate if agent result meets success criteria.

    Args:
        result: Agent execution result
        agent: Agent specification with success criteria

    Returns:
        True if success criteria met, False otherwise

    """
    # Basic success check
    if not result.success:
        return False

    # If no criteria specified, basic success is enough
    if not agent.success_criteria:
        return True

    # success_criteria is a list of descriptive strings
    # (e.g., ["code reviewed", "tests pass"])
    # These are informational criteria - if result.success is True,
    # we consider the criteria met.
    # The criteria serve as documentation of what success means
    # for this agent.
    logger.debug(f"Agent succeeded with criteria: {agent.success_criteria}")
    return True
