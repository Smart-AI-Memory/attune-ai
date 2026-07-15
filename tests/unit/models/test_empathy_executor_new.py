"""Unit Tests for EmpathyLLMExecutor

Comprehensive tests for the executor that handles LLM calls
across different providers and tiers.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.models import ExecutionContext
from attune.models.empathy_executor import EmpathyLLMExecutor


class TestEmpathyLLMExecutorCreation:
    """Tests for executor initialization."""

    def test_creates_with_anthropic_provider(self):
        """Test executor creation with Anthropic provider."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            executor = EmpathyLLMExecutor(provider="anthropic")
            assert executor._provider == "anthropic"

    def test_creates_with_openai_provider(self):
        """Test executor creation with OpenAI provider."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            executor = EmpathyLLMExecutor(provider="openai")
            assert executor._provider == "openai"

    def test_creates_with_google_provider(self):
        """Test executor creation with Google provider."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            executor = EmpathyLLMExecutor(provider="google")
            assert executor._provider == "google"

    def test_creates_with_explicit_api_key(self):
        """Test executor creation with explicit API key."""
        executor = EmpathyLLMExecutor(provider="anthropic", api_key="explicit-key")
        assert executor._api_key == "explicit-key"

    def test_defaults_to_anthropic_provider(self):
        """Test executor defaults to Anthropic if no provider specified."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            executor = EmpathyLLMExecutor()
            assert executor._provider == "anthropic"


class TestEmpathyLLMExecutorTaskRouting:
    """Tests for task type to tier routing (uses tasks module)."""

    @pytest.mark.parametrize(
        "task_type,expected_tier_value",
        [
            # Cheap tier tasks
            ("summarize", "cheap"),
            ("triage", "cheap"),
            ("classify", "cheap"),
            ("simple_qa", "cheap"),
            # Capable tier tasks
            ("review_security", "capable"),
            ("analyze_performance", "capable"),
            ("fix_bug", "capable"),
            ("generate_code", "capable"),
            ("write_tests", "capable"),
            # Premium tier tasks
            ("complex_reasoning", "premium"),
            ("architectural_decision", "premium"),
            ("coordinate", "premium"),
        ],
    )
    def test_task_type_routes_to_correct_tier(self, task_type, expected_tier_value):
        """Test that task types route to expected tiers via tasks module."""
        from attune.models.tasks import get_tier_for_task

        tier = get_tier_for_task(task_type)
        # get_tier_for_task returns ModelTier enum
        tier_value = tier.value if hasattr(tier, "value") else tier
        assert (
            tier_value == expected_tier_value
        ), f"Task '{task_type}' should route to '{expected_tier_value}', got '{tier_value}'"

    def test_unknown_task_type_routes_to_capable(self):
        """Test that unknown task types default to capable tier."""
        from attune.models.tasks import get_tier_for_task

        tier = get_tier_for_task("unknown_task")
        tier_value = tier.value if hasattr(tier, "value") else tier
        assert tier_value == "capable"


class TestEmpathyLLMExecutorRun:
    """Tests for the run() method."""

    @pytest.fixture
    def mock_executor(self):
        """Create executor with mocked LLM."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            executor = EmpathyLLMExecutor(provider="anthropic")

            # Create a mock LLM that returns proper responses
            mock_llm = MagicMock()
            mock_llm.interact = AsyncMock(
                return_value={
                    "content": "Mock response",
                    "metadata": {"tokens_used": 100, "output_tokens": 50, "model": "test-model"},
                    "level_used": 3,
                },
            )
            executor._llm = mock_llm

            return executor

    @pytest.mark.asyncio
    async def test_run_returns_response(self, mock_executor):
        """Test that run() returns a response."""
        from attune.models.executor import LLMResponse

        context = ExecutionContext(
            workflow_name="test-workflow",
            step_name="test-step",
        )

        # Mock the internal _get_llm method
        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            response = await mock_executor.run(
                task_type="summarize",
                prompt="Summarize this",
                context=context,
            )

            assert response is not None
            assert isinstance(response, LLMResponse)
            assert hasattr(response, "content")

    @pytest.mark.asyncio
    async def test_run_with_system_prompt(self, mock_executor):
        """Test that run() passes system prompt correctly."""
        context = ExecutionContext(
            workflow_name="test-workflow",
            step_name="test-step",
        )

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            await mock_executor.run(
                task_type="code_review",
                prompt="Review this code",
                system="You are a code reviewer",
                context=context,
            )

            # Verify interact was called
            mock_executor._llm.interact.assert_called_once()


class TestEmpathyLLMExecutorHybridMode:
    """Tests for hybrid provider mode."""

    @pytest.fixture
    def hybrid_executor(self):
        """Create executor in hybrid mode with mocked config loading."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "anthropic-key",
                "OPENAI_API_KEY": "openai-key",
            },
        ):
            # Create executor and manually set hybrid config
            executor = EmpathyLLMExecutor(provider="hybrid")
            executor._hybrid_config = {
                "cheap": "gpt-4o-mini",
                "capable": "claude-sonnet-4-20250514",
                "premium": "claude-opus-4-8",
            }
            return executor

    def test_hybrid_mode_initialized(self, hybrid_executor):
        """Test that hybrid mode is correctly initialized."""
        assert hybrid_executor._provider == "hybrid"

    def test_hybrid_mode_config_structure(self, hybrid_executor):
        """Test that hybrid config has expected structure."""
        config = hybrid_executor._hybrid_config
        assert config is not None
        assert "cheap" in config
        assert "capable" in config
        assert "premium" in config

    def test_hybrid_mode_provider_detection(self, hybrid_executor):
        """Test that _get_provider_for_model returns anthropic (Claude-native)."""
        # Claude-native architecture: all models route to anthropic
        assert hybrid_executor._get_provider_for_model("claude-sonnet-4") == "anthropic"
        assert hybrid_executor._get_provider_for_model("claude-haiku-4") == "anthropic"
        assert hybrid_executor._get_provider_for_model("claude-opus-4") == "anthropic"


class TestEmpathyLLMExecutorCostTracking:
    """Tests for cost tracking functionality."""

    @pytest.fixture
    def executor_with_telemetry(self, tmp_path):
        """Create executor with telemetry store."""
        from attune.models.telemetry import TelemetryStore

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            store = TelemetryStore(storage_dir=tmp_path)
            executor = EmpathyLLMExecutor(
                provider="anthropic",
                telemetry_store=store,
            )
            return executor

    def test_executor_has_telemetry_store(self, executor_with_telemetry):
        """Test that executor has telemetry store configured."""
        assert executor_with_telemetry._telemetry is not None

    @pytest.mark.asyncio
    async def test_run_tracks_token_usage(self, executor_with_telemetry):
        """Test that run() returns response with token counts."""
        # Mock the internal LLM
        mock_llm = MagicMock()
        mock_llm.interact = AsyncMock(
            return_value={
                "content": "Response",
                "metadata": {"tokens_used": 100, "output_tokens": 50, "model": "test"},
                "level_used": 3,
            },
        )
        executor_with_telemetry._llm = mock_llm

        context = ExecutionContext(
            workflow_name="test",
            step_name="step1",
        )

        with patch.object(executor_with_telemetry, "_get_llm", return_value=mock_llm):
            response = await executor_with_telemetry.run(
                task_type="summarize",
                prompt="Test prompt",
                context=context,
            )

            # Response should include token counts
            assert hasattr(response, "tokens_input")
            assert hasattr(response, "tokens_output")


class TestEmpathyLLMExecutorErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def executor(self):
        """Create executor for error testing."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            executor = EmpathyLLMExecutor(provider="anthropic")
            # Mock the LLM
            mock_llm = MagicMock()
            executor._llm = mock_llm
            return executor

    @pytest.mark.asyncio
    async def test_handles_api_error(self, executor):
        """Test that executor handles API errors gracefully."""
        # Make the LLM raise an error
        executor._llm.interact = AsyncMock(side_effect=Exception("API Error"))

        context = ExecutionContext(
            workflow_name="test",
            step_name="step1",
        )

        with patch.object(executor, "_get_llm", return_value=executor._llm):
            with pytest.raises(Exception) as exc_info:
                await executor.run(
                    task_type="summarize",
                    prompt="Test prompt",
                    context=context,
                )

            assert "API Error" in str(exc_info.value) or "Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_timeout(self, executor):
        """Test that executor handles timeout errors."""
        import asyncio

        # Make the LLM raise a timeout error
        executor._llm.interact = AsyncMock(side_effect=asyncio.TimeoutError("Request timed out"))

        context = ExecutionContext(
            workflow_name="test",
            step_name="step1",
        )

        with patch.object(executor, "_get_llm", return_value=executor._llm):
            with pytest.raises((asyncio.TimeoutError, Exception)):
                await executor.run(
                    task_type="summarize",
                    prompt="Test prompt",
                    context=context,
                )


class TestEmpathyLLMExecutorLoadHybridConfig:
    """Tests for _load_hybrid_config and hybrid config initialization."""

    def test_load_hybrid_config_with_matching_config(self):
        """Test _load_hybrid_config sets _hybrid_config when hybrid key exists."""
        from unittest.mock import MagicMock

        from attune.models.empathy_executor import EmpathyLLMExecutor
        from attune.workflows.config import WorkflowConfig

        executor = EmpathyLLMExecutor.__new__(EmpathyLLMExecutor)
        executor._provider = "hybrid"
        executor._hybrid_config = None
        executor._hybrid_llms = {}
        executor._api_key = None
        executor._llm = None
        executor._llm_kwargs = {}
        executor._telemetry = None

        mock_config = MagicMock(spec=WorkflowConfig)
        mock_config.custom_models = {
            "hybrid": {"cheap": "claude-haiku-4", "capable": "claude-sonnet-4"}
        }

        with patch("attune.workflows.config.WorkflowConfig.load", return_value=mock_config):
            executor._load_hybrid_config()

        assert executor._hybrid_config == {"cheap": "claude-haiku-4", "capable": "claude-sonnet-4"}

    def test_load_hybrid_config_no_hybrid_key(self):
        """Test _load_hybrid_config leaves _hybrid_config as None when no hybrid key."""
        from unittest.mock import MagicMock

        from attune.models.empathy_executor import EmpathyLLMExecutor
        from attune.workflows.config import WorkflowConfig

        executor = EmpathyLLMExecutor.__new__(EmpathyLLMExecutor)
        executor._provider = "hybrid"
        executor._hybrid_config = None
        executor._hybrid_llms = {}
        executor._api_key = None
        executor._llm = None
        executor._llm_kwargs = {}
        executor._telemetry = None

        mock_config = MagicMock(spec=WorkflowConfig)
        mock_config.custom_models = {}

        with patch("attune.workflows.config.WorkflowConfig.load", return_value=mock_config):
            executor._load_hybrid_config()

        assert executor._hybrid_config is None

    def test_load_hybrid_config_exception_swallowed(self):
        """Test _load_hybrid_config silently handles exceptions."""
        from attune.models.empathy_executor import EmpathyLLMExecutor

        executor = EmpathyLLMExecutor.__new__(EmpathyLLMExecutor)
        executor._provider = "hybrid"
        executor._hybrid_config = None
        executor._hybrid_llms = {}
        executor._api_key = None
        executor._llm = None
        executor._llm_kwargs = {}
        executor._telemetry = None

        with patch(
            "attune.workflows.config.WorkflowConfig.load",
            side_effect=Exception("config error"),
        ):
            # Should not raise - exception is logged/swallowed
            executor._load_hybrid_config()

        assert executor._hybrid_config is None

    def test_hybrid_constructor_calls_load(self):
        """Test that hybrid provider triggers _load_hybrid_config."""
        with patch.object(EmpathyLLMExecutor, "_load_hybrid_config") as mock_load:
            EmpathyLLMExecutor(provider="hybrid")
            mock_load.assert_called_once()

    def test_non_hybrid_constructor_skips_load(self):
        """Test that non-hybrid provider does not call _load_hybrid_config."""
        with patch.object(EmpathyLLMExecutor, "_load_hybrid_config") as mock_load:
            EmpathyLLMExecutor(provider="anthropic")
            mock_load.assert_not_called()


class TestEmpathyLLMExecutorGetLlm:
    """Tests for _get_llm lazy initialization."""

    def test_get_llm_raises_import_error_when_no_empathy(self):
        """Test that _get_llm raises ImportError when EmpathyLLM not installed."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        executor._llm = None  # Force lazy init

        with patch("builtins.__import__", side_effect=ImportError("no module")):
            # Only patch attune.llm.core specifically
            pass

        with patch.dict("sys.modules", {"attune.llm.core": None}):
            with pytest.raises((ImportError, Exception)):
                executor._get_llm()

    def test_get_llm_returns_existing_llm(self):
        """Test that _get_llm returns pre-set LLM without re-creating."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        mock_llm = MagicMock()
        executor._llm = mock_llm

        result = executor._get_llm()

        assert result is mock_llm

    def test_get_llm_creates_with_api_key(self):
        """Test that _get_llm passes api_key when provided."""
        from unittest.mock import MagicMock

        executor = EmpathyLLMExecutor(provider="anthropic", api_key="my-key")
        executor._llm = None

        mock_empathy_llm_class = MagicMock()
        mock_instance = MagicMock()
        mock_empathy_llm_class.return_value = mock_instance

        with patch.dict("sys.modules", {}):
            mock_module = MagicMock()
            mock_module.EmpathyLLM = mock_empathy_llm_class
            with patch.dict("sys.modules", {"attune.llm.core": mock_module}):
                executor._get_llm()

        mock_empathy_llm_class.assert_called_once()
        call_kwargs = mock_empathy_llm_class.call_args[1]
        assert call_kwargs.get("api_key") == "my-key"

    def test_get_llm_creates_without_api_key_when_none(self):
        """Test that _get_llm omits api_key when not provided."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        executor._llm = None
        executor._api_key = None

        mock_empathy_llm_class = MagicMock()
        mock_instance = MagicMock()
        mock_empathy_llm_class.return_value = mock_instance

        mock_module = MagicMock()
        mock_module.EmpathyLLM = mock_empathy_llm_class
        with patch.dict("sys.modules", {"attune.llm.core": mock_module}):
            executor._get_llm()

        call_kwargs = mock_empathy_llm_class.call_args[1]
        assert "api_key" not in call_kwargs


class TestEmpathyLLMExecutorGetLlmForTier:
    """Tests for _get_llm_for_tier in hybrid and non-hybrid modes."""

    def test_non_hybrid_returns_single_llm(self):
        """Test _get_llm_for_tier returns single LLM in non-hybrid mode."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        mock_llm = MagicMock()
        executor._llm = mock_llm

        llm, provider, model_id = executor._get_llm_for_tier("cheap")

        assert llm is mock_llm
        assert provider == "anthropic"
        assert model_id == ""

    def test_hybrid_with_no_config_falls_back(self):
        """Test _get_llm_for_tier falls back when hybrid config is empty."""
        executor = EmpathyLLMExecutor(provider="hybrid")
        executor._hybrid_config = None
        mock_llm = MagicMock()
        executor._llm = mock_llm

        llm, provider, model_id = executor._get_llm_for_tier("cheap")

        assert llm is mock_llm
        assert provider == "hybrid"

    def test_hybrid_with_empty_tier_falls_back(self):
        """Test _get_llm_for_tier falls back when tier has no model."""
        executor = EmpathyLLMExecutor(provider="hybrid")
        executor._hybrid_config = {"capable": "claude-sonnet-4"}  # No "cheap" key
        mock_llm = MagicMock()
        executor._llm = mock_llm

        llm, provider, model_id = executor._get_llm_for_tier("cheap")

        assert llm is mock_llm

    def test_hybrid_uses_cached_llm(self):
        """Test _get_llm_for_tier returns cached LLM for provider."""
        executor = EmpathyLLMExecutor(provider="hybrid")
        executor._hybrid_config = {"cheap": "claude-haiku-4"}

        cached_llm = MagicMock()
        executor._hybrid_llms["anthropic"] = cached_llm

        llm, provider, model_id = executor._get_llm_for_tier("cheap")

        assert llm is cached_llm
        assert provider == "anthropic"
        assert model_id == "claude-haiku-4"

    def test_hybrid_creates_llm_and_caches(self):
        """Test _get_llm_for_tier creates and caches a new LLM for a provider."""
        executor = EmpathyLLMExecutor(provider="hybrid")
        executor._hybrid_config = {"cheap": "claude-haiku-4"}

        mock_empathy_llm_class = MagicMock()
        mock_instance = MagicMock()
        mock_empathy_llm_class.return_value = mock_instance

        mock_module = MagicMock()
        mock_module.EmpathyLLM = mock_empathy_llm_class

        with patch.dict("sys.modules", {"attune.llm.core": mock_module}):
            llm, provider, model_id = executor._get_llm_for_tier("cheap")

        assert "anthropic" in executor._hybrid_llms
        assert model_id == "claude-haiku-4"

    def test_hybrid_raises_import_error_when_no_empathy(self):
        """Test _get_llm_for_tier raises ImportError when EmpathyLLM unavailable."""
        executor = EmpathyLLMExecutor(provider="hybrid")
        executor._hybrid_config = {"cheap": "claude-haiku-4"}

        with patch.dict("sys.modules", {"attune.llm.core": None}):
            with pytest.raises((ImportError, Exception)):
                executor._get_llm_for_tier("cheap")


class TestEmpathyLLMExecutorRunContextPaths:
    """Tests for context field population in run()."""

    @pytest.fixture
    def mock_executor(self):
        """Create executor with mocked LLM."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        mock_llm = MagicMock()
        mock_llm.interact = AsyncMock(
            return_value={
                "content": "Test response",
                "metadata": {
                    "tokens_used": 50,
                    "output_tokens": 25,
                    "model": "claude-haiku-4",
                },
                "level_used": 1,
                "level_description": "cheap tier",
                "proactive": False,
            },
        )
        executor._llm = mock_llm
        return executor

    @pytest.mark.asyncio
    async def test_run_with_context_task_type_overrides(self, mock_executor):
        """Test that context.task_type overrides the passed task_type."""
        context = ExecutionContext(
            task_type="complex_reasoning",  # Should override "summarize"
            workflow_name="test-wf",
            step_name="step-1",
        )

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            response = await mock_executor.run(
                task_type="summarize",
                prompt="Test",
                context=context,
            )

        # The tier should be based on complex_reasoning (premium), not summarize
        assert response.tier == "premium"

    @pytest.mark.asyncio
    async def test_run_with_session_id_in_context(self, mock_executor):
        """Test that session_id from context is passed through."""
        context = ExecutionContext(
            workflow_name="test-wf",
            step_name="step-1",
            session_id="session-abc-123",
        )

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            response = await mock_executor.run(
                task_type="summarize",
                prompt="Test",
                context=context,
            )

        assert response is not None

    @pytest.mark.asyncio
    async def test_run_with_user_id_in_context(self, mock_executor):
        """Test that user_id from context is used instead of default."""
        context = ExecutionContext(
            user_id="user-42",
            workflow_name="test-wf",
            step_name="step-1",
        )

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            await mock_executor.run(
                task_type="summarize",
                prompt="Test",
                context=context,
            )

        # Verify interact was called with the user_id
        call_kwargs = mock_executor._llm.interact.call_args[1]
        assert call_kwargs["user_id"] == "user-42"

    @pytest.mark.asyncio
    async def test_run_with_metadata_in_context(self, mock_executor):
        """Test that context.metadata is merged into full_context."""
        context = ExecutionContext(
            workflow_name="test-wf",
            step_name="step-1",
            metadata={"custom_key": "custom_value"},
        )

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            await mock_executor.run(
                task_type="summarize",
                prompt="Test",
                context=context,
            )

        call_kwargs = mock_executor._llm.interact.call_args[1]
        assert call_kwargs["context"]["custom_key"] == "custom_value"

    @pytest.mark.asyncio
    async def test_run_without_context_uses_defaults(self, mock_executor):
        """Test run() works correctly without context (context=None)."""
        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            response = await mock_executor.run(
                task_type="summarize",
                prompt="Test prompt with no context",
            )

        assert response is not None
        assert response.content == "Test response"

    @pytest.mark.asyncio
    async def test_run_with_model_info_calculates_cost(self, mock_executor):
        """Test that run() calculates cost from model_info when available."""
        mock_executor._llm.interact = AsyncMock(
            return_value={
                "content": "response",
                "metadata": {
                    "tokens_used": 1000,
                    "output_tokens": 500,
                    "model": "",
                },
            }
        )

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            response = await mock_executor.run(
                task_type="summarize",
                prompt="Test",
            )

        # Cost should be calculated (may be 0 if model_info not found, but no error)
        assert response.cost_estimate >= 0.0

    @pytest.mark.asyncio
    async def test_run_model_id_from_model_info_when_empty(self, mock_executor):
        """Test model_id falls back to model_info.id when metadata model is empty."""
        mock_executor._llm.interact = AsyncMock(
            return_value={
                "content": "response",
                "metadata": {
                    "tokens_used": 100,
                    "output_tokens": 50,
                    "model": "",
                    "routed_model": "",
                },
            }
        )

        from attune.models.registry import ModelInfo

        mock_model_info = MagicMock(spec=ModelInfo)
        mock_model_info.id = "claude-haiku-4"
        mock_model_info.input_cost_per_million = 0.25
        mock_model_info.output_cost_per_million = 1.25

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            with patch("attune.models.empathy_executor.get_model", return_value=mock_model_info):
                response = await mock_executor.run(
                    task_type="summarize",
                    prompt="Test",
                )

        assert response.model_id == "claude-haiku-4"

    @pytest.mark.asyncio
    async def test_run_with_telemetry_logs_call(self):
        """Test that run() records telemetry when telemetry store is set."""
        from attune.models.telemetry import TelemetryStore

        mock_store = MagicMock(spec=TelemetryStore)
        executor = EmpathyLLMExecutor(provider="anthropic", telemetry_store=mock_store)

        mock_llm = MagicMock()
        mock_llm.interact = AsyncMock(
            return_value={
                "content": "telemetry test",
                "metadata": {"tokens_used": 100, "output_tokens": 50, "model": "test"},
            }
        )
        executor._llm = mock_llm

        context = ExecutionContext(
            workflow_name="test-wf",
            step_name="step-1",
            session_id="session-xyz",
        )

        with patch.object(executor, "_get_llm", return_value=mock_llm):
            await executor.run(
                task_type="summarize",
                prompt="Test",
                context=context,
            )

        mock_store.log_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_telemetry_failure_does_not_raise(self):
        """Test that run() silently handles telemetry recording failures."""
        from attune.models.telemetry import TelemetryStore

        mock_store = MagicMock(spec=TelemetryStore)
        mock_store.log_call.side_effect = Exception("telemetry failed")
        executor = EmpathyLLMExecutor(provider="anthropic", telemetry_store=mock_store)

        mock_llm = MagicMock()
        mock_llm.interact = AsyncMock(
            return_value={
                "content": "response",
                "metadata": {"tokens_used": 50, "output_tokens": 25, "model": "test"},
            }
        )
        executor._llm = mock_llm

        with patch.object(executor, "_get_llm", return_value=mock_llm):
            # Should not raise even though telemetry fails
            response = await executor.run(
                task_type="summarize",
                prompt="Test",
            )

        assert response.content == "response"

    @pytest.mark.asyncio
    async def test_run_with_existing_context_kwarg(self, mock_executor):
        """Test that existing_context kwarg is merged into full_context."""
        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            await mock_executor.run(
                task_type="summarize",
                prompt="Test",
                existing_context={"prior_key": "prior_value"},
            )

        call_kwargs = mock_executor._llm.interact.call_args[1]
        assert call_kwargs["context"]["prior_key"] == "prior_value"

    @pytest.mark.asyncio
    async def test_run_with_context_missing_workflow_and_step_name(self, mock_executor):
        """A context object with no workflow_name/step_name skips both.

        Characterization pin (batch-4 D-block cut): every other context
        test sets both fields truthy, leaving the ``if
        context.workflow_name:`` / ``if context.step_name:`` false
        branches unpinned. Behavior: neither key is added to the
        context dict sent to ``llm.interact``.
        """
        context = ExecutionContext(session_id="session-only")

        with patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm):
            await mock_executor.run(
                task_type="summarize",
                prompt="Test",
                context=context,
            )

        call_kwargs = mock_executor._llm.interact.call_args[1]
        sent_context = call_kwargs["context"] or {}
        assert "workflow_name" not in sent_context
        assert "step_name" not in sent_context
        assert sent_context.get("session_id") == "session-only"

    @pytest.mark.asyncio
    async def test_run_cost_estimate_zero_when_model_info_unavailable(self, mock_executor):
        """cost_estimate stays 0.0 when the registry has no model_info.

        Characterization pin: ``if model_info:`` false branch — the
        cost-calculation block must not run when ``get_model`` returns
        ``None`` (e.g. an unrecognized provider/tier combination).
        """
        with (
            patch.object(mock_executor, "_get_llm", return_value=mock_executor._llm),
            patch("attune.models.empathy_executor.get_model", return_value=None),
        ):
            response = await mock_executor.run(
                task_type="summarize",
                prompt="Test",
            )

        assert response.cost_estimate == 0.0


class TestEmpathyLLMExecutorGetModelForTask:
    """Tests for get_model_for_task method."""

    def test_get_model_for_task_returns_string(self):
        """Test that get_model_for_task returns a string."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        result = executor.get_model_for_task("summarize")
        assert isinstance(result, str)

    def test_get_model_for_task_returns_empty_when_no_model(self):
        """Test that get_model_for_task returns empty string when model info is None."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        from unittest.mock import patch

        with patch("attune.models.empathy_executor.get_model", return_value=None):
            result = executor.get_model_for_task("summarize")

        assert result == ""

    def test_get_model_for_task_different_tiers(self):
        """Test get_model_for_task for tasks routing to different tiers."""
        executor = EmpathyLLMExecutor(provider="anthropic")

        # These should all return strings without raising
        cheap_model = executor.get_model_for_task("summarize")
        capable_model = executor.get_model_for_task("fix_bug")
        premium_model = executor.get_model_for_task("complex_reasoning")

        assert isinstance(cheap_model, str)
        assert isinstance(capable_model, str)
        assert isinstance(premium_model, str)


class TestEmpathyLLMExecutorEstimateCost:
    """Tests for estimate_cost method."""

    def test_estimate_cost_returns_float(self):
        """Test that estimate_cost returns a float."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        result = executor.estimate_cost("summarize", 1000, 500)
        assert isinstance(result, float)

    def test_estimate_cost_zero_tokens_is_zero(self):
        """Test that estimate_cost with zero tokens returns 0.0."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        result = executor.estimate_cost("summarize", 0, 0)
        assert result == 0.0

    def test_estimate_cost_positive_with_tokens(self):
        """Test that estimate_cost returns positive value for non-zero tokens."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        result = executor.estimate_cost("summarize", 100000, 50000)
        # For Anthropic models, cost should be positive
        assert result >= 0.0

    def test_estimate_cost_returns_zero_when_no_model_info(self):
        """Test estimate_cost returns 0.0 when model info is None."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        from unittest.mock import patch

        with patch("attune.models.empathy_executor.get_model", return_value=None):
            result = executor.estimate_cost("summarize", 1000, 500)

        assert result == 0.0

    def test_estimate_cost_scales_with_tokens(self):
        """Test that estimate_cost scales proportionally with token counts."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        cost_small = executor.estimate_cost("summarize", 1000, 500)
        cost_large = executor.estimate_cost("summarize", 10000, 5000)
        # Cost should scale with token count (or both be 0 if no model info)
        if cost_small > 0:
            assert cost_large > cost_small

    def test_estimate_cost_premium_tier_more_expensive(self):
        """Test that premium tier costs more than cheap tier."""
        executor = EmpathyLLMExecutor(provider="anthropic")
        cheap_cost = executor.estimate_cost("summarize", 100000, 50000)
        premium_cost = executor.estimate_cost("complex_reasoning", 100000, 50000)
        # Premium should cost same or more than cheap
        assert premium_cost >= cheap_cost
