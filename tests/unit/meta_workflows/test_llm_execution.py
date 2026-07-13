"""Unit tests for attune.meta_workflows.llm_execution module.

Tests simulate_llm_call, evaluate_success_criteria, and
execute_agents_real (with real LLM calls mocked out).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from attune.meta_workflows.models import (
    AgentExecutionResult,
    AgentSpec,
    TierStrategy,
)
from attune.routing.model_router import ModelTier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_spec(
    role: str = "tester",
    tier_strategy: TierStrategy = TierStrategy.CHEAP_ONLY,
    success_criteria: list[str] | None = None,
) -> AgentSpec:
    """Build a minimal AgentSpec for testing."""
    return AgentSpec(
        role=role,
        base_template="generic",
        tier_strategy=tier_strategy,
        success_criteria=success_criteria or [],
    )


def _make_model_config(
    model_id: str = "claude-haiku",
    cost_per_1k_input: float = 0.001,
    cost_per_1k_output: float = 0.005,
) -> MagicMock:
    """Build a minimal mock model config."""
    cfg = MagicMock()
    cfg.model_id = model_id
    cfg.cost_per_1k_input = cost_per_1k_input
    cfg.cost_per_1k_output = cost_per_1k_output
    return cfg


def _make_success_result(agent_id: str = "a1", role: str = "tester") -> AgentExecutionResult:
    return AgentExecutionResult(
        agent_id=agent_id,
        role=role,
        success=True,
        cost=0.001,
        duration=0.1,
        tier_used="cheap",
        output={"message": "ok"},
    )


def _make_failure_result(agent_id: str = "a1", role: str = "tester") -> AgentExecutionResult:
    return AgentExecutionResult(
        agent_id=agent_id,
        role=role,
        success=False,
        cost=0.0,
        duration=0.1,
        tier_used="cheap",
        output={"error": "failed"},
        error="failed",
    )


# ---------------------------------------------------------------------------
# simulate_llm_call
# ---------------------------------------------------------------------------


class TestSimulateLlmCall:
    """Tests for simulate_llm_call()."""

    def test_returns_expected_top_level_keys(self):
        """simulate_llm_call returns a dict with cost, tokens, success, output."""
        from attune.meta_workflows.llm_execution import simulate_llm_call

        model_cfg = _make_model_config()
        result = simulate_llm_call("Hello world", model_cfg, ModelTier.CHEAP)

        assert "cost" in result
        assert "tokens" in result
        assert "success" in result
        assert "output" in result

    def test_tokens_contains_input_output_total(self):
        """tokens dict has input, output, total keys."""
        from attune.meta_workflows.llm_execution import simulate_llm_call

        model_cfg = _make_model_config()
        result = simulate_llm_call("A" * 400, model_cfg, ModelTier.CHEAP)

        tokens = result["tokens"]
        assert "input" in tokens
        assert "output" in tokens
        assert "total" in tokens
        assert tokens["total"] == tokens["input"] + tokens["output"]

    def test_output_contains_model_and_tier(self):
        """output dict contains model and tier fields."""
        from attune.meta_workflows.llm_execution import simulate_llm_call

        model_cfg = _make_model_config(model_id="claude-haiku-3")
        result = simulate_llm_call("test", model_cfg, ModelTier.CAPABLE)

        output = result["output"]
        assert output["model"] == "claude-haiku-3"
        assert output["tier"] == ModelTier.CAPABLE.value

    def test_cost_is_non_negative(self):
        """simulate_llm_call returns non-negative cost."""
        from attune.meta_workflows.llm_execution import simulate_llm_call

        model_cfg = _make_model_config()
        result = simulate_llm_call("x" * 1000, model_cfg, ModelTier.PREMIUM)

        assert result["cost"] >= 0.0

    def test_cheap_tier_success_field_is_bool(self):
        """success field is always a bool."""
        from attune.meta_workflows.llm_execution import simulate_llm_call

        model_cfg = _make_model_config()
        result = simulate_llm_call("test", model_cfg, ModelTier.CHEAP)

        assert isinstance(result["success"], bool)

    def test_premium_tier_success_field_is_bool(self):
        """success field is bool for premium tier too."""
        from attune.meta_workflows.llm_execution import simulate_llm_call

        model_cfg = _make_model_config()
        result = simulate_llm_call("test", model_cfg, ModelTier.PREMIUM)

        assert isinstance(result["success"], bool)

    def test_completion_tokens_fixed_at_500(self):
        """simulate_llm_call uses 500 as default completion tokens."""
        from attune.meta_workflows.llm_execution import simulate_llm_call

        model_cfg = _make_model_config()
        result = simulate_llm_call("test", model_cfg, ModelTier.CHEAP)

        assert result["tokens"]["output"] == 500


# ---------------------------------------------------------------------------
# evaluate_success_criteria
# ---------------------------------------------------------------------------


class TestEvaluateSuccessCriteria:
    """Tests for evaluate_success_criteria()."""

    def test_successful_result_no_criteria_returns_true(self):
        """Result with success=True and no criteria returns True."""
        from attune.meta_workflows.llm_execution import evaluate_success_criteria

        result = _make_success_result()
        agent = _make_agent_spec(success_criteria=[])

        assert evaluate_success_criteria(result, agent) is True

    def test_failed_result_returns_false_regardless_of_criteria(self):
        """Result with success=False always returns False."""
        from attune.meta_workflows.llm_execution import evaluate_success_criteria

        result = _make_failure_result()
        agent = _make_agent_spec(success_criteria=["all tests pass"])

        assert evaluate_success_criteria(result, agent) is False

    def test_successful_result_with_criteria_returns_true(self):
        """Descriptive success criteria are informational — success=True suffices."""
        from attune.meta_workflows.llm_execution import evaluate_success_criteria

        result = _make_success_result()
        agent = _make_agent_spec(success_criteria=["code reviewed", "tests pass"])

        assert evaluate_success_criteria(result, agent) is True

    def test_failed_result_with_no_criteria_returns_false(self):
        """Even with no criteria, success=False means False."""
        from attune.meta_workflows.llm_execution import evaluate_success_criteria

        result = _make_failure_result()
        agent = _make_agent_spec(success_criteria=[])

        assert evaluate_success_criteria(result, agent) is False


# ---------------------------------------------------------------------------
# execute_agents_real
# ---------------------------------------------------------------------------


class TestExecuteAgentsReal:
    """Tests for execute_agents_real() with real LLM calls mocked."""

    def _build_mock_router(self, provider: str = "anthropic") -> MagicMock:
        """Build a mock ModelRouter with MODELS structure."""
        mock_router = MagicMock()
        mock_router._default_provider = provider
        mock_cfg = _make_model_config()
        mock_router.MODELS = {
            provider: {
                "cheap": mock_cfg,
                "capable": mock_cfg,
                "premium": mock_cfg,
            }
        }
        return mock_router

    def test_single_agent_cheap_only_success(self):
        """Single CHEAP_ONLY agent returns one successful result."""
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.CHEAP_ONLY)

        mock_router = self._build_mock_router()
        mock_tracker = MagicMock()
        mock_tracker.track_llm_call = MagicMock()

        success_response = {
            "cost": 0.001,
            "tokens": {"input": 100, "output": 500, "total": 600},
            "success": True,
            "output": {"message": "done", "model": "haiku", "tier": "cheap", "success": True},
        }

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="prompt"),
            patch(
                "attune.meta_workflows.llm_execution.execute_llm_call",
                return_value=success_response,
            ),
        ):
            mock_tracker_cls.get_instance.return_value = mock_tracker
            results = execute_agents_real([agent])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].role == "tester"

    def test_single_agent_returns_agent_execution_result_type(self):
        """execute_agents_real returns AgentExecutionResult objects."""
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.CHEAP_ONLY)
        mock_router = self._build_mock_router()

        success_response = {
            "cost": 0.002,
            "tokens": {"input": 50, "output": 500, "total": 550},
            "success": True,
            "output": {"message": "ok", "model": "haiku", "tier": "cheap", "success": True},
        }

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="p"),
            patch(
                "attune.meta_workflows.llm_execution.execute_llm_call",
                return_value=success_response,
            ),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real([agent])

        assert isinstance(results[0], AgentExecutionResult)

    def test_empty_agents_list_returns_empty_results(self):
        """execute_agents_real returns [] for an empty agent list."""
        from attune.meta_workflows.llm_execution import execute_agents_real

        mock_router = self._build_mock_router()

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real([])

        assert results == []

    def test_agent_exception_returns_error_result(self):
        """If execute_llm_call raises, _execute_at_tier returns a failure result.

        When all tiers fail (success=False), _execute_single_agent_with_escalation
        returns the last tier's result. The outer execute_agents_real wraps any
        uncaught exception into an error result with tier_used="error".

        We simulate an uncaught exception by making build_agent_prompt raise
        so the exception escapes _execute_at_tier entirely.
        """
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.CHEAP_ONLY)
        mock_router = self._build_mock_router()

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch(
                "attune.meta_workflows.llm_execution.build_agent_prompt",
                side_effect=RuntimeError("boom"),
            ),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real([agent])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].tier_used == "error"
        assert "boom" in str(results[0].error)

    def test_progressive_escalation_cheap_fails_capable_succeeds(self):
        """PROGRESSIVE strategy escalates from cheap to capable on failure."""
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.PROGRESSIVE)
        mock_router = self._build_mock_router()

        fail_response = {
            "cost": 0.001,
            "tokens": {"input": 100, "output": 500, "total": 600},
            "success": False,
            "output": {"error": "too dumb", "model": "haiku", "tier": "cheap", "success": False},
        }
        success_response = {
            "cost": 0.005,
            "tokens": {"input": 100, "output": 500, "total": 600},
            "success": True,
            "output": {"message": "done", "model": "sonnet", "tier": "capable", "success": True},
        }

        call_count = [0]

        def side_effect(prompt, model_config, tier):
            call_count[0] += 1
            if tier == ModelTier.CHEAP:
                return fail_response
            return success_response

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="p"),
            patch("attune.meta_workflows.llm_execution.execute_llm_call", side_effect=side_effect),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real([agent])

        assert len(results) == 1
        assert results[0].success is True
        # callable was invoked at least twice (cheap + capable)
        assert call_count[0] >= 2

    def test_capable_first_strategy_starts_at_capable_tier(self):
        """CAPABLE_FIRST skips the cheap tier."""
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.CAPABLE_FIRST)
        mock_router = self._build_mock_router()

        tiers_used: list[str] = []

        def side_effect(prompt, model_config, tier):
            tiers_used.append(tier.value)
            return {
                "cost": 0.003,
                "tokens": {"input": 50, "output": 500, "total": 550},
                "success": True,
                "output": {"message": "ok", "model": "sonnet", "tier": tier.value, "success": True},
            }

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="p"),
            patch("attune.meta_workflows.llm_execution.execute_llm_call", side_effect=side_effect),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            execute_agents_real([agent])

        assert "cheap" not in tiers_used
        assert "capable" in tiers_used

    def test_multiple_agents_all_succeed(self):
        """Multiple agents each produce a result."""
        from attune.meta_workflows.llm_execution import execute_agents_real

        agents = [
            _make_agent_spec(role="analyzer", tier_strategy=TierStrategy.CHEAP_ONLY),
            _make_agent_spec(role="reviewer", tier_strategy=TierStrategy.CHEAP_ONLY),
        ]
        mock_router = self._build_mock_router()

        success_response = {
            "cost": 0.001,
            "tokens": {"input": 50, "output": 500, "total": 550},
            "success": True,
            "output": {"message": "ok", "model": "haiku", "tier": "cheap", "success": True},
        }

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="p"),
            patch(
                "attune.meta_workflows.llm_execution.execute_llm_call",
                return_value=success_response,
            ),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real(agents)

        assert len(results) == 2
        roles = {r.role for r in results}
        assert "analyzer" in roles
        assert "reviewer" in roles


# ---------------------------------------------------------------------------
# execute_llm_call (fallback to simulation on missing API key)
# ---------------------------------------------------------------------------


class TestExecuteLlmCall:
    """Tests for execute_llm_call() fallback behaviour."""

    def test_no_api_key_returns_failure_dict(self):
        """execute_llm_call returns a failure dict (not simulation) when key absent.

        The function catches the ValueError from missing key and returns a
        failure dict with success=False rather than calling simulate_llm_call.
        """
        from attune.meta_workflows.llm_execution import execute_llm_call

        model_cfg = _make_model_config()

        import os

        env_backup = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            result = execute_llm_call("prompt", model_cfg, ModelTier.CHEAP)
        finally:
            if env_backup is not None:
                os.environ["ANTHROPIC_API_KEY"] = env_backup

        assert "cost" in result
        assert "success" in result
        assert result["success"] is False

    def test_import_error_falls_back_to_simulation(self):
        """execute_llm_call falls back to simulate_llm_call if anthropic not installed."""
        from attune.meta_workflows.llm_execution import execute_llm_call

        model_cfg = _make_model_config()

        with patch("attune.meta_workflows.llm_execution.simulate_llm_call") as mock_sim:
            mock_sim.return_value = {
                "cost": 0.0,
                "tokens": {"input": 5, "output": 500, "total": 505},
                "success": False,
                "output": {"message": "sim fallback"},
            }
            # Simulate ImportError by patching the `from anthropic import Anthropic` path
            with patch.dict("sys.modules", {"anthropic": None}):
                result = execute_llm_call("prompt", model_cfg, ModelTier.CHEAP)

        mock_sim.assert_called_once()
        assert "cost" in result


class TestExecuteLlmCallFable:
    """Fable premium path: beta routing, first-TEXT-block, refusal event."""

    def _response(self, blocks, stop_reason="end_turn"):
        resp = MagicMock()
        resp.content = blocks
        resp.stop_reason = stop_reason
        resp.usage.input_tokens = 10
        resp.usage.output_tokens = 5
        return resp

    def _client_module(self, response):
        client = MagicMock()
        client.beta.messages.create.return_value = response
        client.messages.create.return_value = response
        mod = MagicMock()
        mod.Anthropic.return_value = client
        return client, mod

    def test_fable_routes_via_beta_and_reads_first_text_block(self, fake_module, monkeypatch):
        from types import SimpleNamespace

        from attune.meta_workflows.llm_execution import execute_llm_call

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        blocks = [
            SimpleNamespace(type="thinking", thinking="..."),
            SimpleNamespace(type="text", text="fable says hi"),
        ]
        client, mod = self._client_module(self._response(blocks))
        fake_module("anthropic", mod)

        result = execute_llm_call("p", _make_model_config("claude-fable-5"), ModelTier.PREMIUM)

        client.beta.messages.create.assert_called_once()
        client.messages.create.assert_not_called()
        assert result["success"] is True
        assert result["output"]["message"] == "fable says hi"

    def test_non_fable_keeps_plain_namespace(self, fake_module, monkeypatch):
        from types import SimpleNamespace

        from attune.meta_workflows.llm_execution import execute_llm_call

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        blocks = [SimpleNamespace(type="text", text="haiku says hi")]
        client, mod = self._client_module(self._response(blocks))
        fake_module("anthropic", mod)

        result = execute_llm_call("p", _make_model_config("claude-haiku-4-5"), ModelTier.CHEAP)

        client.messages.create.assert_called_once()
        client.beta.messages.create.assert_not_called()
        assert result["output"]["message"] == "haiku says hi"

    def test_refusal_returns_failure_and_records_event(self, fake_module, monkeypatch):
        from attune.meta_workflows.llm_execution import execute_llm_call

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        client, mod = self._client_module(self._response([], stop_reason="refusal"))
        fake_module("anthropic", mod)

        with patch("attune.models.telemetry.log_fable_refusal") as mock_log:
            result = execute_llm_call("p", _make_model_config("claude-fable-5"), ModelTier.PREMIUM)

        assert result["success"] is False
        assert "refused" in result["output"]["error"]
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["model"] == "claude-fable-5"


# ---------------------------------------------------------------------------
# Coverage for previously-missed branches
# ---------------------------------------------------------------------------


class TestUnknownTierStrategy:
    """Cover lines 110-111: PREMIUM_ONLY (or unknown) → fallback to CAPABLE."""

    def test_premium_only_falls_back_to_capable(self):
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.PREMIUM_ONLY)

        mock_router = MagicMock()
        mock_router._default_provider = "anthropic"
        cfg = _make_model_config()
        mock_router.MODELS = {
            "anthropic": {"cheap": cfg, "capable": cfg, "premium": cfg},
        }

        tiers_seen: list[str] = []

        def side_effect(prompt, model_config, tier):
            tiers_seen.append(tier.value)
            return {
                "cost": 0.005,
                "tokens": {"input": 50, "output": 500, "total": 550},
                "success": True,
                "output": {"message": "ok", "model": "x", "tier": tier.value, "success": True},
            }

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="p"),
            patch("attune.meta_workflows.llm_execution.execute_llm_call", side_effect=side_effect),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real([agent])

        # Fallback uses CAPABLE only
        assert tiers_seen == ["capable"]
        assert results[0].success is True


class TestAllTiersExhausted:
    """Cover lines 136-140: all tiers fail → return last failure result."""

    def test_progressive_all_tiers_fail(self):
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.PROGRESSIVE)

        mock_router = MagicMock()
        mock_router._default_provider = "anthropic"
        cfg = _make_model_config()
        mock_router.MODELS = {
            "anthropic": {"cheap": cfg, "capable": cfg, "premium": cfg},
        }

        fail_response = {
            "cost": 0.001,
            "tokens": {"input": 10, "output": 500, "total": 510},
            "success": False,
            "output": {"error": "no", "model": "x", "tier": "?", "success": False},
        }

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="p"),
            patch(
                "attune.meta_workflows.llm_execution.execute_llm_call",
                return_value=fail_response,
            ),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real([agent])

        assert len(results) == 1
        # All three tiers attempted → cumulative cost
        assert results[0].cost > 0.001  # cheap + capable + premium
        # Last attempted tier was premium
        assert results[0].tier_used == "premium"
        assert results[0].success is False


class TestExecuteAtTierExceptionPath:
    """Cover lines 210-214: execute_llm_call raises → error result returned."""

    def test_llm_call_exception_returns_failure_result(self):
        from attune.meta_workflows.llm_execution import execute_agents_real

        agent = _make_agent_spec(tier_strategy=TierStrategy.CHEAP_ONLY)
        mock_router = MagicMock()
        mock_router._default_provider = "anthropic"
        cfg = _make_model_config()
        mock_router.MODELS = {
            "anthropic": {"cheap": cfg, "capable": cfg, "premium": cfg},
        }

        with (
            patch("attune.meta_workflows.llm_execution.ModelRouter", return_value=mock_router),
            patch("attune.meta_workflows.llm_execution.UsageTracker") as mock_tracker_cls,
            patch("attune.meta_workflows.llm_execution.build_agent_prompt", return_value="p"),
            patch(
                "attune.meta_workflows.llm_execution.execute_llm_call",
                side_effect=RuntimeError("api down"),
            ),
        ):
            mock_tracker_cls.get_instance.return_value = MagicMock()
            results = execute_agents_real([agent])

        assert len(results) == 1
        assert results[0].success is False
        # tier_used is "cheap" (the tier that errored), NOT "error" — the
        # exception was caught inside _execute_at_tier, not in execute_agents_real.
        assert results[0].tier_used == "cheap"
        assert "api down" in str(results[0].error)


class TestExecuteLlmCallRealApiSuccess:
    """Cover lines 257-276: Anthropic SDK success path."""

    def test_real_api_success_returns_response(self):
        from attune.meta_workflows.llm_execution import execute_llm_call

        # Build a fake Anthropic SDK module
        fake_block = MagicMock()
        fake_block.text = "real model output"
        fake_response = MagicMock()
        fake_response.content = [fake_block]
        fake_response.usage = MagicMock(input_tokens=120, output_tokens=80)

        fake_client = MagicMock()
        fake_client.messages.create.return_value = fake_response

        fake_anthropic_class = MagicMock(return_value=fake_client)

        # Build a fake module with `Anthropic` attribute
        fake_module = MagicMock()
        fake_module.Anthropic = fake_anthropic_class

        model_cfg = _make_model_config(
            model_id="claude-sonnet-x",
            cost_per_1k_input=2.0,
            cost_per_1k_output=10.0,
        )

        import os

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"anthropic": fake_module}),
        ):
            result = execute_llm_call("Hi there", model_cfg, ModelTier.CAPABLE)

        # Cost = (120/1000)*2.0 + (80/1000)*10.0 = 0.24 + 0.8 = 1.04
        assert result["success"] is True
        assert result["cost"] == 1.04
        assert result["tokens"]["input"] == 120
        assert result["tokens"]["output"] == 80
        assert result["tokens"]["total"] == 200
        assert result["output"]["message"] == "real model output"
        assert result["output"]["model"] == "claude-sonnet-x"
        assert result["output"]["tier"] == ModelTier.CAPABLE.value
        # Sanity: the SDK class was instantiated with the api_key
        fake_anthropic_class.assert_called_once_with(api_key="test-key")
        # Suppress unused import flake
        del os

    def test_real_api_success_empty_content_returns_blank_text(self):
        """Cover the `if response.content else ""` branch for empty content list."""
        from attune.meta_workflows.llm_execution import execute_llm_call

        fake_response = MagicMock()
        fake_response.content = []  # falsy → output_text = ""
        fake_response.usage = MagicMock(input_tokens=10, output_tokens=5)

        fake_client = MagicMock()
        fake_client.messages.create.return_value = fake_response

        fake_module = MagicMock()
        fake_module.Anthropic = MagicMock(return_value=fake_client)

        model_cfg = _make_model_config()

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "k"}),
            patch.dict("sys.modules", {"anthropic": fake_module}),
        ):
            result = execute_llm_call("p", model_cfg, ModelTier.CHEAP)

        assert result["success"] is True
        assert result["output"]["message"] == ""
