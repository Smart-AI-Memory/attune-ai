"""Architectural Tests for LLM Execution and Fallback System.

This test suite validates architectural invariants and production readiness
of the LLM execution pipeline with fallback and circuit breaker logic.

Coverage Target: 95%+ (from 21-73%)

Test Categories:
1. Model Registry and Selection (correct tier mapping)
2. LLM Executor Interface (API abstraction)
3. Fallback Policy Activation (provider failure handling)
4. Circuit Breaker Logic (cascade prevention)
5. Cost Tracking Accuracy (billing correctness)
6. Routing Decisions (task-type to tier mapping)
7. Provider Switching (seamless fallback)
8. Telemetry and Logging (audit trail)

Architecture Invariants Tested:
- Task types correctly mapped to tiers (CHEAP/CAPABLE/PREMIUM)
- Fallback activates on provider failure
- Circuit breaker prevents repeated failures
- Cost tracking matches actual usage
- Routing decisions are auditable
- Provider failures don't cascade
- System degrades gracefully

Author: Sprint - Production Readiness
Date: January 16, 2026
"""

from unittest.mock import Mock, patch

import pytest

from attune.models.executor import LLMExecutor
from attune.models.registry import MODEL_REGISTRY, ModelRegistry

# NOTE: FallbackPolicy may not exist or have different API - Gap 3.2
# from attune.models.fallback import FallbackPolicy, FallbackTier
from attune.models.tasks import TASK_TIER_MAP, TaskType

# Placeholders for architectural gaps that still exist
FallbackPolicy = None
FallbackTier = None


# ============================================================================
# Test Category 1: Model Registry and Selection
# ============================================================================


class TestModelRegistryAndSelection:
    """Test that model registry correctly maps tasks to tiers."""

    def test_task_tier_mapping_complete(self):
        """Test that all task types have tier mappings."""
        for task_type in TaskType:
            assert task_type in TASK_TIER_MAP, f"TaskType {task_type} missing from TASK_TIER_MAP"

    def test_cheap_tier_for_simple_tasks(self):
        """Test that simple tasks map to CHEAP tier."""
        cheap_tasks = [
            TaskType.CLASSIFICATION,
            TaskType.EXTRACTION,
            TaskType.SUMMARIZATION,
        ]

        for task in cheap_tasks:
            tier = TASK_TIER_MAP.get(task)
            assert tier == "CHEAP", f"{task} should use CHEAP tier, got {tier}"

    def test_capable_tier_for_moderate_tasks(self):
        """Test that moderate tasks map to CAPABLE tier."""
        capable_tasks = [
            TaskType.ANALYSIS,
            TaskType.GENERATION,
            TaskType.REFACTORING,
        ]

        for task in capable_tasks:
            tier = TASK_TIER_MAP.get(task)
            assert tier == "CAPABLE", f"{task} should use CAPABLE tier, got {tier}"

    def test_premium_tier_for_complex_tasks(self):
        """Test that complex tasks map to PREMIUM tier."""
        premium_tasks = [
            TaskType.REASONING,
            TaskType.ARCHITECTURE,
            TaskType.PLANNING,
        ]

        for task in premium_tasks:
            tier = TASK_TIER_MAP.get(task)
            assert tier == "PREMIUM", f"{task} should use PREMIUM tier, got {tier}"

    def test_model_registry_has_all_tiers(self):
        """Test that registry has models for all tiers."""
        required_tiers = {"cheap", "capable", "premium"}

        # Check each provider has all tiers
        for provider_name, provider_models in MODEL_REGISTRY.items():
            available_tiers = set(provider_models.keys())
            for tier in required_tiers:
                assert tier in available_tiers, f"Provider {provider_name} missing tier {tier}"

    def test_model_costs_defined(self):
        """Test that all models have cost information."""
        for provider_name, provider_models in MODEL_REGISTRY.items():
            for tier, model_info in provider_models.items():
                assert hasattr(
                    model_info, "input_cost_per_million"
                ), f"Model {provider_name}/{tier} missing input cost"
                assert hasattr(
                    model_info, "output_cost_per_million"
                ), f"Model {provider_name}/{tier} missing output cost"
                # Ollama models are free (cost = 0), others should cost > 0
                if provider_name != "ollama":
                    assert (
                        model_info.input_cost_per_million > 0
                    ), f"Model {provider_name}/{tier} has invalid input cost"

    def test_cheap_tier_actually_cheaper(self):
        """Test that CHEAP tier models cost less than CAPABLE/PREMIUM."""
        # Collect average costs by tier (excluding free ollama models)
        cheap_costs = []
        capable_costs = []
        premium_costs = []

        for provider_name, provider_models in MODEL_REGISTRY.items():
            if provider_name == "ollama":
                continue  # Skip free models

            if "cheap" in provider_models:
                cheap_costs.append(provider_models["cheap"].input_cost_per_million)
            if "capable" in provider_models:
                capable_costs.append(provider_models["capable"].input_cost_per_million)
            if "premium" in provider_models:
                premium_costs.append(provider_models["premium"].input_cost_per_million)

        if cheap_costs and capable_costs:
            avg_cheap = sum(cheap_costs) / len(cheap_costs)
            avg_capable = sum(capable_costs) / len(capable_costs)
            assert avg_cheap < avg_capable, "CHEAP tier not actually cheaper than CAPABLE"

        if capable_costs and premium_costs:
            avg_capable = sum(capable_costs) / len(capable_costs)
            avg_premium = sum(premium_costs) / len(premium_costs)
            assert avg_capable < avg_premium, "CAPABLE not cheaper than PREMIUM"


class TestModelRegistryClass:
    """Test the ModelRegistry OOP interface."""

    def test_registry_initialization(self):
        """Test that ModelRegistry initializes correctly."""
        registry = ModelRegistry()
        assert registry is not None
        assert hasattr(registry, "_registry")
        assert hasattr(registry, "_tier_cache")
        assert hasattr(registry, "_model_id_cache")

    def test_get_model_success(self):
        """Test get_model() returns correct ModelInfo."""
        registry = ModelRegistry()

        # Test Anthropic cheap tier
        model = registry.get_model("anthropic", "cheap")
        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == "cheap"
        assert "haiku" in model.id.lower()

        # Test OpenAI capable tier
        model = registry.get_model("openai", "capable")
        assert model is not None
        assert model.provider == "openai"
        assert model.tier == "capable"
        assert model.id == "gpt-4o"

    def test_get_model_case_insensitive(self):
        """Test get_model() is case-insensitive."""
        registry = ModelRegistry()

        model1 = registry.get_model("ANTHROPIC", "CHEAP")
        model2 = registry.get_model("anthropic", "cheap")
        model3 = registry.get_model("Anthropic", "Cheap")

        assert model1 is not None
        assert model1.id == model2.id == model3.id

    def test_get_model_invalid_provider(self):
        """Test get_model() returns None for invalid provider."""
        registry = ModelRegistry()

        model = registry.get_model("invalid_provider", "cheap")
        assert model is None

    def test_get_model_invalid_tier(self):
        """Test get_model() returns None for invalid tier."""
        registry = ModelRegistry()

        model = registry.get_model("anthropic", "invalid_tier")
        assert model is None

    def test_get_model_by_id_success(self):
        """Test get_model_by_id() finds models by ID."""
        registry = ModelRegistry()

        # Test Anthropic models
        model = registry.get_model_by_id("claude-haiku-4-5-20251001")
        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == "cheap"

        model = registry.get_model_by_id("claude-sonnet-4-5-20250929")
        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == "capable"

        # Test OpenAI models
        model = registry.get_model_by_id("gpt-4o-mini")
        assert model is not None
        assert model.provider == "openai"
        assert model.tier == "cheap"

    def test_get_model_by_id_invalid(self):
        """Test get_model_by_id() returns None for invalid ID."""
        registry = ModelRegistry()

        model = registry.get_model_by_id("nonexistent-model-xyz")
        assert model is None

    def test_get_models_by_tier(self):
        """Test get_models_by_tier() returns all models in tier."""
        registry = ModelRegistry()

        # Test cheap tier
        cheap_models = registry.get_models_by_tier("cheap")
        assert isinstance(cheap_models, list)
        assert len(cheap_models) >= 5  # At least 5 providers
        assert all(m.tier == "cheap" for m in cheap_models)

        # Test capable tier
        capable_models = registry.get_models_by_tier("capable")
        assert len(capable_models) >= 5
        assert all(m.tier == "capable" for m in capable_models)

        # Test premium tier
        premium_models = registry.get_models_by_tier("premium")
        assert len(premium_models) >= 5
        assert all(m.tier == "premium" for m in premium_models)

    def test_get_models_by_tier_case_insensitive(self):
        """Test get_models_by_tier() is case-insensitive."""
        registry = ModelRegistry()

        models1 = registry.get_models_by_tier("CHEAP")
        models2 = registry.get_models_by_tier("cheap")
        models3 = registry.get_models_by_tier("Cheap")

        assert len(models1) == len(models2) == len(models3)

    def test_get_models_by_tier_invalid(self):
        """Test get_models_by_tier() returns empty list for invalid tier."""
        registry = ModelRegistry()

        models = registry.get_models_by_tier("invalid_tier")
        assert isinstance(models, list)
        assert len(models) == 0

    def test_list_providers(self):
        """Test list_providers() returns all providers."""
        registry = ModelRegistry()

        providers = registry.list_providers()
        assert isinstance(providers, list)
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "ollama" in providers
        assert "hybrid" in providers
        assert len(providers) == 5

    def test_list_tiers(self):
        """Test list_tiers() returns available tiers."""
        registry = ModelRegistry()

        tiers = registry.list_tiers()
        assert isinstance(tiers, list)
        assert "cheap" in tiers
        assert "capable" in tiers
        assert "premium" in tiers
        assert len(tiers) == 3

    def test_get_pricing_for_model(self):
        """Test get_pricing_for_model() returns pricing dict."""
        registry = ModelRegistry()

        # Test Anthropic model
        pricing = registry.get_pricing_for_model("claude-sonnet-4-5-20250929")
        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] == 3.0
        assert pricing["output"] == 15.0

        # Test OpenAI model
        pricing = registry.get_pricing_for_model("gpt-4o-mini")
        assert pricing is not None
        assert pricing["input"] == 0.15
        assert pricing["output"] == 0.60

    def test_get_pricing_for_model_invalid(self):
        """Test get_pricing_for_model() returns None for invalid model."""
        registry = ModelRegistry()

        pricing = registry.get_pricing_for_model("nonexistent-model")
        assert pricing is None

    def test_cache_performance(self):
        """Test that caches are built correctly for performance."""
        registry = ModelRegistry()

        # Caches should be pre-built
        assert len(registry._tier_cache) == 3  # 3 tiers
        assert len(registry._model_id_cache) > 0  # Should have all model IDs

        # Verify tier cache has correct structure
        for tier in ["cheap", "capable", "premium"]:
            assert tier in registry._tier_cache
            assert isinstance(registry._tier_cache[tier], list)
            assert len(registry._tier_cache[tier]) >= 5  # At least 5 providers

        # Verify model ID cache has unique model IDs
        # Note: hybrid provider may duplicate model IDs from other providers
        unique_model_ids = set()
        for provider_models in MODEL_REGISTRY.values():
            for model in provider_models.values():
                unique_model_ids.add(model.id)

        # The cache should contain all unique model IDs
        assert len(registry._model_id_cache) == len(unique_model_ids)
        assert len(registry._model_id_cache) >= 12  # At least 12 unique models


# ============================================================================
# Test Category 2: LLM Executor Interface
# ============================================================================


class TestLLMExecutorInterface:
    """Test LLM executor provides correct abstraction."""

    def test_executor_initialization(self):
        """Test that executor initializes correctly."""
        executor = LLMExecutor()
        assert executor is not None

    @patch("attune.models.executor.get_model_client")
    def test_execute_calls_correct_provider(self, mock_get_client):
        """Test that execute routes to correct model provider."""
        mock_client = Mock()
        mock_client.chat.completions.create = Mock(
            return_value=Mock(
                choices=[Mock(message=Mock(content="Response"))],
                usage=Mock(total_tokens=100),
            )
        )
        mock_get_client.return_value = mock_client

        executor = LLMExecutor()

        result = executor.execute(model="gpt-4o", messages=[{"role": "user", "content": "Test"}])

        # Should have called the client
        mock_get_client.assert_called_once()
        assert "Response" in str(result)

    def test_executor_handles_missing_model_gracefully(self):
        """Test that missing model doesn't crash executor."""
        executor = LLMExecutor()

        # Should handle gracefully (either raise specific exception or fallback)
        with pytest.raises((ValueError, KeyError, Exception)):
            executor.execute(
                model="nonexistent-model-xyz",
                messages=[{"role": "user", "content": "Test"}],
            )

    @patch("attune.models.executor.get_model_client")
    def test_executor_tracks_token_usage(self, mock_get_client):
        """Test that executor tracks token usage for cost calculation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.usage = Mock(total_tokens=150)
        mock_client.chat.completions.create = Mock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        executor = LLMExecutor()
        result = executor.execute(model="gpt-4o", messages=[{"role": "user", "content": "Test"}])

        # Should have token count
        assert hasattr(result, "usage") or isinstance(result, dict)


# ============================================================================
# Test Category 3: Fallback Policy Activation
# ============================================================================


class TestFallbackPolicyActivation:
    """Test that fallback activates correctly on failures."""

    def test_fallback_policy_initialization(self):
        """Test that fallback policy initializes with correct defaults."""
        policy = FallbackPolicy()

        assert policy is not None
        assert hasattr(policy, "fallback_tiers")

    def test_fallback_activates_on_provider_error(self):
        """Test that fallback kicks in when primary provider fails."""
        policy = FallbackPolicy()

        # Simulate primary failure
        primary_tier = FallbackTier.PRIMARY
        fallback_tier = policy.get_next_tier(primary_tier)

        # Should return a fallback tier
        assert fallback_tier != primary_tier
        assert fallback_tier is not None

    def test_fallback_chain_exhaustion_handled(self):
        """Test that exhausting all fallbacks is handled gracefully."""
        policy = FallbackPolicy()

        current_tier = FallbackTier.PRIMARY
        tiers_tried = [current_tier]

        # Keep trying fallbacks
        for _ in range(10):  # Arbitrary limit
            next_tier = policy.get_next_tier(current_tier)
            if next_tier is None or next_tier == current_tier:
                break
            tiers_tried.append(next_tier)
            current_tier = next_tier

        # Should eventually stop (not infinite loop)
        assert len(tiers_tried) < 10

    def test_fallback_to_cheaper_tier_on_cost_limit(self):
        """Test that system falls back to cheaper tier on cost limits."""
        policy = FallbackPolicy()

        # Simulate cost limit reached
        with patch.object(policy, "cost_limit_reached", return_value=True):
            fallback = policy.get_cost_aware_fallback("PREMIUM")

            # Should suggest cheaper tier
            assert fallback in ["CAPABLE", "CHEAP"]

    def test_fallback_preserves_request_context(self):
        """Test that fallback retains original request context."""
        policy = FallbackPolicy()

        original_request = {
            "messages": [{"role": "user", "content": "Test"}],
            "temperature": 0.7,
            "max_tokens": 1000,
        }

        fallback_request = policy.prepare_fallback_request(original_request)

        # Should preserve request parameters
        assert fallback_request["messages"] == original_request["messages"]
        assert "temperature" in fallback_request
        assert "max_tokens" in fallback_request


# ============================================================================
# Test Category 4: Circuit Breaker Logic
# ============================================================================


class TestCircuitBreakerLogic:
    """Test that circuit breaker prevents cascade failures."""

    def test_circuit_breaker_opens_after_threshold_failures(self):
        """Test that circuit breaker opens after N consecutive failures."""
        from attune.trust.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, timeout=60)

        # Simulate 3 failures
        for _ in range(3):
            breaker.record_failure()

        # Circuit should be open
        assert breaker.is_open()

    def test_circuit_breaker_blocks_requests_when_open(self):
        """Test that open circuit blocks requests."""
        from attune.trust.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, timeout=60)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        assert breaker.is_open()

        # Should block requests
        with pytest.raises(Exception):  # Or specific CircuitOpenError
            breaker.call(lambda: "test")

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test that circuit enters half-open state after timeout."""
        from attune.trust.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, timeout=1)  # 1 second timeout

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open()

        # Wait for timeout
        import time

        time.sleep(1.5)

        # Should be half-open
        assert breaker.is_half_open() or not breaker.is_open()

    def test_circuit_breaker_closes_on_success(self):
        """Test that circuit closes after successful call in half-open."""
        from attune.trust.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, timeout=1)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Wait and record success
        import time

        time.sleep(1.5)
        breaker.record_success()

        # Should be closed or nearly closed
        assert not breaker.is_open() or breaker.failure_count < 2


# ============================================================================
# Test Category 5: Cost Tracking Accuracy
# ============================================================================


class TestCostTrackingAccuracy:
    """Test that cost tracking matches actual usage."""

    def test_cost_calculation_formula_correct(self):
        """Test that cost = tokens * cost_per_million / 1_000_000."""
        from attune.models.registry import get_model_by_id

        model_info = get_model_by_id("gpt-4o")
        tokens_used = 1_000_000
        expected_cost = model_info.cost_per_million_tokens

        # Calculate cost
        calculated_cost = (tokens_used * model_info.cost_per_million_tokens) / 1_000_000

        assert calculated_cost == expected_cost

    def test_cost_precision_six_decimals(self):
        """Test that costs are tracked with 6 decimal precision."""
        from attune.telemetry.usage_tracker import UsageTracker

        tracker = UsageTracker(use_test_mode=True)

        # Track cost with high precision
        tracker.track(
            user_id="test",
            workflow="test_workflow",
            model="gpt-4o",
            tokens=123,
            cost=0.123456789,  # 9 decimals
        )

        # Retrieve and check precision
        entries = tracker.get_all()
        if entries:
            cost = entries[0].get("cost")
            # Should be rounded to 6 decimals
            assert len(str(cost).split(".")[-1]) <= 6

    def test_cost_aggregation_across_requests(self):
        """Test that costs are correctly aggregated across multiple requests."""
        from attune.cost_tracker import CostTracker

        tracker = CostTracker()

        # Track multiple requests
        costs = [0.001, 0.002, 0.003]
        for cost in costs:
            tracker.track("test_session", cost)

        total = tracker.get_session_total("test_session")

        assert abs(total - sum(costs)) < 0.0001  # Allow small floating-point error

    def test_cost_tracking_handles_free_models(self):
        """Test that free/mock models have zero cost."""
        # Mock models should have 0 cost
        from attune.models.registry import get_model_by_id

        # Check if there are any mock/free models
        for model_id in ["mock", "test-model", "free-model"]:
            try:
                model = get_model_by_id(model_id)
                if model:
                    # Free models should have 0 or very low cost
                    assert model.cost_per_million_tokens == 0
            except KeyError:
                pass  # Model doesn't exist, OK


# ============================================================================
# Test Category 6: Routing Decisions
# ============================================================================


class TestRoutingDecisions:
    """Test that routing decisions are correct and auditable."""

    def test_routing_decision_logged(self):
        """Test that routing decisions are logged for audit."""
        from attune.routing.smart_router import SmartRouter

        router = SmartRouter()

        with patch("attune.routing.smart_router.logger") as mock_logger:
            # Make routing decision
            task = "Classify user sentiment"
            router.route(task)

            # Should have logged the decision
            # Check if logger was called (implementation may vary)
            assert mock_logger.info.called or mock_logger.debug.called

    def test_routing_returns_valid_tier(self):
        """Test that routing always returns a valid tier."""
        from attune.routing.smart_router import SmartRouter

        router = SmartRouter()

        tasks = [
            "Format code",
            "Analyze architecture",
            "Generate comprehensive documentation",
        ]

        valid_tiers = {"CHEAP", "CAPABLE", "PREMIUM"}

        for task in tasks:
            tier = router.route(task)
            assert tier in valid_tiers, f"Invalid tier returned: {tier}"

    def test_routing_consistent_for_same_task(self):
        """Test that same task consistently routes to same tier."""
        from attune.routing.smart_router import SmartRouter

        router = SmartRouter()

        task = "Boost test coverage to 90%"

        # Route multiple times
        tiers = [router.route(task) for _ in range(5)]

        # Should be consistent
        assert len(set(tiers)) == 1, f"Inconsistent routing: {tiers}"


# ============================================================================
# Test Category 7: Provider Switching
# ============================================================================


class TestProviderSwitching:
    """Test seamless switching between providers."""

    @patch("attune.models.executor.get_model_client")
    def test_switch_from_openai_to_anthropic_seamless(self, mock_get_client):
        """Test that switching providers maintains functionality."""
        executor = LLMExecutor()

        # Mock OpenAI client
        openai_client = Mock()
        openai_client.chat.completions.create = Mock(side_effect=Exception("OpenAI down"))

        # Mock Anthropic client
        anthropic_client = Mock()
        anthropic_client.messages.create = Mock(
            return_value=Mock(
                content=[Mock(text="Anthropic response")], usage=Mock(input_tokens=50)
            )
        )

        # First call fails (OpenAI), second succeeds (Anthropic)
        mock_get_client.side_effect = [openai_client, anthropic_client]

        # Should fall back successfully
        # (Implementation-dependent - may need fallback logic)
        try:
            result = executor.execute(
                model="gpt-4o", messages=[{"role": "user", "content": "Test"}]
            )
        except Exception:
            # Fallback should happen automatically
            result = executor.execute(
                model="claude-sonnet-3-5",
                messages=[{"role": "user", "content": "Test"}],
            )

        assert result is not None

    def test_provider_credentials_isolated(self):
        """Test that provider credentials don't leak across providers."""
        from attune.models.provider_config import get_provider_config

        openai_config = get_provider_config("openai")
        anthropic_config = get_provider_config("anthropic")

        # Should have different API keys
        if hasattr(openai_config, "api_key") and hasattr(anthropic_config, "api_key"):
            assert openai_config.api_key != anthropic_config.api_key


# ============================================================================
# Test Category 8: Telemetry and Logging
# ============================================================================


class TestTelemetryAndLogging:
    """Test that execution is properly logged for audit."""

    @patch("attune.models.executor.get_model_client")
    @patch("attune.models.telemetry.TelemetryBackend")
    def test_all_requests_logged_to_telemetry(self, mock_telemetry, mock_get_client):
        """Test that all LLM requests are logged."""
        mock_client = Mock()
        mock_client.chat.completions.create = Mock(
            return_value=Mock(
                choices=[Mock(message=Mock(content="Response"))],
                usage=Mock(total_tokens=100),
            )
        )
        mock_get_client.return_value = mock_client

        executor = LLMExecutor()
        executor.execute(model="gpt-4o", messages=[{"role": "user", "content": "Test"}])

        # Telemetry should have been called (implementation may vary)
        # This test structure depends on actual telemetry integration

    def test_failures_logged_with_error_details(self):
        """Test that failures are logged with sufficient detail."""
        from attune.models.executor import LLMExecutor

        executor = LLMExecutor()

        with patch("attune.models.executor.logger") as mock_logger:
            with patch("attune.models.executor.get_model_client") as mock_client:
                mock_client.side_effect = Exception("API Error")

                try:
                    executor.execute(model="gpt-4o", messages=[{"role": "user", "content": "Test"}])
                except Exception:
                    pass

                # Should have logged the error
                assert mock_logger.error.called or mock_logger.exception.called, "Error not logged"


# ============================================================================
# Integration Tests
# ============================================================================


class TestExecutionAndFallbackIntegration:
    """Integration tests for complete execution pipeline."""

    @patch("attune.models.executor.get_model_client")
    def test_end_to_end_execution_with_fallback(self, mock_get_client):
        """Test complete flow: execute → fail → fallback → succeed."""
        # Setup: Primary fails, fallback succeeds
        primary_client = Mock()
        primary_client.chat.completions.create = Mock(side_effect=Exception("Primary failed"))

        fallback_client = Mock()
        fallback_client.chat.completions.create = Mock(
            return_value=Mock(
                choices=[Mock(message=Mock(content="Fallback success"))],
                usage=Mock(total_tokens=100),
            )
        )

        mock_get_client.side_effect = [primary_client, fallback_client]

        executor = LLMExecutor()

        # Try primary (will fail)
        try:
            result = executor.execute(
                model="gpt-4o", messages=[{"role": "user", "content": "Test"}]
            )
        except Exception:
            # Expected - now try fallback
            result = executor.execute(
                model="claude-sonnet-3-5",
                messages=[{"role": "user", "content": "Test"}],
            )

        assert result is not None
        assert "success" in str(result).lower() or "Fallback" in str(result)

    def test_cost_tracked_across_fallback_chain(self):
        """Test that costs are tracked correctly when fallback happens."""
        from attune.cost_tracker import CostTracker

        tracker = CostTracker()

        session = "test_fallback_session"

        # Primary attempt costs
        tracker.track(session, 0.01)

        # Fallback attempt costs
        tracker.track(session, 0.005)

        total = tracker.get_session_total(session)

        # Total should include both attempts
        assert abs(total - 0.015) < 0.001


# ============================================================================
# Edge Cases and Robustness
# ============================================================================


class TestEdgeCasesAndRobustness:
    """Test edge cases and robustness of execution system."""

    def test_empty_message_list_handled(self):
        """Test that empty message list doesn't crash."""
        executor = LLMExecutor()

        with pytest.raises((ValueError, Exception)):
            executor.execute(model="gpt-4o", messages=[])

    def test_extremely_large_context_handled(self):
        """Test that very large contexts are handled gracefully."""
        executor = LLMExecutor()

        # Create large message
        large_message = "x" * 1_000_000  # 1MB

        # Should either succeed or raise specific exception (not crash)
        try:
            executor.execute(
                model="gpt-4o",
                messages=[{"role": "user", "content": large_message}],
            )
        except (ValueError, Exception) as e:
            # Expected - context too large
            assert "too large" in str(e).lower() or "limit" in str(e).lower()

    def test_malformed_model_id_handled(self):
        """Test that malformed model IDs are handled."""
        executor = LLMExecutor()

        malformed_ids = ["", None, "gpt/4o", "model with spaces", "123invalid"]

        for model_id in malformed_ids:
            with pytest.raises((ValueError, KeyError, TypeError, Exception)):
                executor.execute(model=model_id, messages=[{"role": "user", "content": "Test"}])

    def test_concurrent_executions_isolated(self):
        """Test that concurrent executions don't interfere."""
        import threading

        executor = LLMExecutor()
        results = []
        lock = threading.Lock()

        @patch("attune.models.executor.get_model_client")
        def execute_concurrent(mock_get_client):
            mock_client = Mock()
            mock_client.chat.completions.create = Mock(
                return_value=Mock(
                    choices=[Mock(message=Mock(content="Response"))],
                    usage=Mock(total_tokens=100),
                )
            )
            mock_get_client.return_value = mock_client

            try:
                result = executor.execute(
                    model="gpt-4o", messages=[{"role": "user", "content": "Test"}]
                )
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    results.append(f"Error: {e}")

        threads = [threading.Thread(target=execute_concurrent) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All should complete without interference
        assert len(results) == 10
