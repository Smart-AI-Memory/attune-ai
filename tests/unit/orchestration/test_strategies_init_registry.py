"""Tests for the ``attune.orchestration._strategies`` package-level registry.

The main ``execution_strategies`` module carries its own registry helpers,
and the existing suite exercises those — leaving this package's
``get_strategy`` error path and ``register_strategy`` unmeasured. These
tests target the package-level functions directly.
"""

from __future__ import annotations

import pytest

from attune.orchestration import _strategies
from attune.orchestration._strategies import SequentialStrategy

pytestmark = pytest.mark.unit


class TestGetStrategyErrorPath:
    """Unknown names raise ValueError naming the available strategies."""

    def test_unknown_name_raises_with_available_list(self):
        with pytest.raises(ValueError, match="Unknown strategy: bogus"):
            _strategies.get_strategy("bogus")

    def test_error_message_names_known_strategies(self):
        with pytest.raises(ValueError) as excinfo:
            _strategies.get_strategy("not-a-strategy")
        message = str(excinfo.value)
        assert "sequential" in message
        assert "conditional" in message


class TestRegisterStrategy:
    """register_strategy makes a class resolvable via get_strategy."""

    def test_registered_class_round_trips(self):
        class _ProbeStrategy(SequentialStrategy):
            pass

        try:
            _strategies.register_strategy("probe", _ProbeStrategy)
            instance = _strategies.get_strategy("probe")
            assert isinstance(instance, _ProbeStrategy)
        finally:
            _strategies._STRATEGY_REGISTRY.pop("probe", None)
        assert "probe" not in _strategies._STRATEGY_REGISTRY

    def test_registered_name_does_not_disturb_core_entries(self):
        class _ProbeStrategy(SequentialStrategy):
            pass

        try:
            _strategies.register_strategy("probe2", _ProbeStrategy)
            assert isinstance(_strategies.get_strategy("sequential"), SequentialStrategy)
        finally:
            _strategies._STRATEGY_REGISTRY.pop("probe2", None)
