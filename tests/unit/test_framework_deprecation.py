"""Guard: legacy Empathy-framework exports emit ``DeprecationWarning``.

attune-ai focuses on the Claude Code workflow plugin (MCP tools); the
``EmpathyOS`` core and the 5-level maturity model are deprecated as of
the plugin-focus decision (2026-06-25) and slated for removal. This
test pins that:

1. every deprecated symbol warns on access (so the deprecation can't
   silently regress before the planned removal), and
2. a live product export (``EmpathyConfig``) does NOT warn (so the
   deprecation set stays scoped to the vestigial framework).
"""

from __future__ import annotations

import warnings

import pytest

import attune
from attune import _DEPRECATED_FRAMEWORK


def test_deprecation_set_matches_expected() -> None:
    """The deprecated set is exactly the confirmed off-product-path API."""
    assert _DEPRECATED_FRAMEWORK == frozenset(
        {
            "EmpathyOS",
            "FeedbackLoopDetector",
            "LeveragePointAnalyzer",
            "Level1Reactive",
            "Level2Guided",
            "Level3Proactive",
            "Level4Anticipatory",
            "Level5Systems",
        }
    )


@pytest.mark.parametrize("name", sorted(_DEPRECATED_FRAMEWORK))
def test_framework_export_warns(name: str) -> None:
    """Accessing a deprecated framework symbol emits DeprecationWarning."""
    with pytest.warns(DeprecationWarning, match="legacy Empathy framework"):
        getattr(attune, name)


def test_live_product_export_does_not_warn() -> None:
    """A live product export (EmpathyConfig) must not be deprecated."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert attune.EmpathyConfig is not None
