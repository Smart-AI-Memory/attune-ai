"""Guard: the legacy Empathy framework is removed; only ``StateManager``
remains, deprecated.

attune-ai focuses on the Claude Code workflow plugin (MCP tools). The
``EmpathyOS`` core and the 5-level maturity model were REMOVED in 9.0.0.
``StateManager`` is the last vestige still importable and emits
``DeprecationWarning`` pending its own removal. This test pins that:

1. every removed framework symbol now raises ``AttributeError`` (so it
   can't silently creep back into the public surface),
2. ``StateManager`` still warns on access (deprecation can't regress
   before the planned removal), and
3. live product exports do NOT warn (the deprecation set stays scoped to
   the vestigial framework).
"""

from __future__ import annotations

import warnings

import pytest

import attune
from attune import _DEPRECATED_FRAMEWORK

# Symbols removed in 9.0.0 — must no longer be importable from ``attune``.
REMOVED_FRAMEWORK_SYMBOLS = (
    "EmpathyOS",
    "FeedbackLoopDetector",
    "LeveragePointAnalyzer",
    "Level1Reactive",
    "Level2Guided",
    "Level3Proactive",
    "Level4Anticipatory",
    "Level5Systems",
)


def test_deprecation_set_matches_expected() -> None:
    """Only ``StateManager`` remains in the deprecation set after 9.0.0."""
    assert _DEPRECATED_FRAMEWORK == frozenset({"StateManager"})


@pytest.mark.parametrize("name", REMOVED_FRAMEWORK_SYMBOLS)
def test_removed_framework_symbol_raises_attribute_error(name: str) -> None:
    """Accessing a removed framework symbol raises AttributeError."""
    with pytest.raises(AttributeError):
        getattr(attune, name)


@pytest.mark.parametrize("name", sorted(_DEPRECATED_FRAMEWORK))
def test_framework_export_warns(name: str) -> None:
    """Accessing a deprecated framework symbol emits DeprecationWarning."""
    with pytest.warns(DeprecationWarning, match="legacy Empathy framework"):
        getattr(attune, name)


@pytest.mark.parametrize("name", ["EmpathyConfig", "MetricsCollector", "PatternPersistence"])
def test_live_product_export_does_not_warn(name: str) -> None:
    """Live product exports must not be deprecated."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert getattr(attune, name) is not None
