"""Guard: the legacy Empathy framework is fully removed.

attune-ai focuses on the Claude Code workflow plugin (MCP tools). The
``EmpathyOS`` core and the 5-level maturity model were REMOVED in 9.0.0;
``StateManager``, the last deprecated vestige, was removed in 16.0.0
with the ``attune.persistence`` facade. This test pins that:

1. every removed framework symbol now raises ``AttributeError`` (so it
   can't silently creep back into the public surface), and
2. live product exports do NOT emit deprecation warnings.
"""

from __future__ import annotations

import warnings

import pytest

import attune

# Symbols removed in 9.0.0 — must no longer be importable from ``attune``.
REMOVED_FRAMEWORK_SYMBOLS = (
    "EmpathyOS",
    "StateManager",  # removed 16.0.0 with the attune.persistence facade
    "FeedbackLoopDetector",
    "LeveragePointAnalyzer",
    "Level1Reactive",
    "Level2Guided",
    "Level3Proactive",
    "Level4Anticipatory",
    "Level5Systems",
)


@pytest.mark.parametrize("name", REMOVED_FRAMEWORK_SYMBOLS)
def test_removed_framework_symbol_raises_attribute_error(name: str) -> None:
    """Accessing a removed framework symbol raises AttributeError."""
    with pytest.raises(AttributeError):
        getattr(attune, name)


@pytest.mark.parametrize("name", ["EmpathyConfig", "MetricsCollector", "PatternPersistence"])
def test_live_product_export_does_not_warn(name: str) -> None:
    """Live product exports must not be deprecated."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert getattr(attune, name) is not None
