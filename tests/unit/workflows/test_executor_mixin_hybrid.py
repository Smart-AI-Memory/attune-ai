"""Workflows-layer ownership of the hybrid tier->model config read (#2239).

Edge 1 of the models<->workflows cycle was ``EmpathyLLMExecutor`` reading
``workflows.yaml`` itself. Spec ``models-workflows-layering`` R1 inverts it:
the workflows layer resolves the mapping and injects it as a models-owned
primitive (``dict[str, str]``). These tests pin the workflows half —
the read happens here, and only for hybrid providers.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.executor_mixin import _load_hybrid_tier_models


@pytest.mark.unit
class TestLoadHybridTierModels:
    """The relocated config read, formerly EmpathyLLMExecutor._load_hybrid_config."""

    def test_returns_mapping_when_hybrid_key_present(self) -> None:
        mock_config = MagicMock()
        mock_config.custom_models = {
            "hybrid": {"cheap": "claude-haiku-4", "capable": "claude-sonnet-4"}
        }
        with patch("attune.workflows.config.WorkflowConfig.load", return_value=mock_config):
            assert _load_hybrid_tier_models() == {
                "cheap": "claude-haiku-4",
                "capable": "claude-sonnet-4",
            }

    def test_returns_none_when_no_hybrid_key(self) -> None:
        mock_config = MagicMock()
        mock_config.custom_models = {}
        with patch("attune.workflows.config.WorkflowConfig.load", return_value=mock_config):
            assert _load_hybrid_tier_models() is None

    def test_returns_none_when_load_raises(self) -> None:
        """A broken config degrades to no hybrid routing, never an exception.

        Matches the pre-inversion behavior: the read was best-effort and its
        failure was logged, not propagated to workflow construction.
        """
        with patch(
            "attune.workflows.config.WorkflowConfig.load",
            side_effect=Exception("config error"),
        ):
            assert _load_hybrid_tier_models() is None


@pytest.mark.unit
class TestDefaultExecutorInjection:
    """_create_default_executor injects the mapping only for hybrid providers."""

    @staticmethod
    def _mixin(provider: str):
        from attune.workflows.executor_mixin import ExecutorMixin

        obj = ExecutorMixin.__new__(ExecutorMixin)
        obj._provider_str = provider
        obj._api_key = None
        obj._telemetry_backend = None
        obj._enable_tier_fallback = True  # skip the ResilientExecutor wrapper
        return obj

    def test_hybrid_provider_reads_and_injects(self) -> None:
        mixin = self._mixin("hybrid")
        mapping = {"cheap": "claude-haiku-4"}
        with patch(
            "attune.workflows.executor_mixin._load_hybrid_tier_models",
            return_value=mapping,
        ) as mock_load:
            executor = mixin._create_default_executor()
        mock_load.assert_called_once()
        assert executor._hybrid_config == mapping

    def test_non_hybrid_provider_does_not_read_config(self) -> None:
        """The workflows.yaml read is skipped entirely off the hybrid path.

        Pins the cost property, not just the wiring: a config load on every
        default-executor creation would be a silent regression.
        """
        mixin = self._mixin("anthropic")
        with patch("attune.workflows.executor_mixin._load_hybrid_tier_models") as mock_load:
            executor = mixin._create_default_executor()
        mock_load.assert_not_called()
        assert executor._hybrid_config is None
