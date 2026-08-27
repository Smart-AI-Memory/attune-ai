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
from pathlib import Path

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


REMOVED_MODULE_PATHS = (
    "attune.coordination",
    "attune.persistence",
    "attune.redis_memory",
    "attune.redis_memory_coordination",
    "attune.redis_memory_patterns",
    "attune.redis_memory_storage",
    "attune.state_manager",
)


@pytest.mark.parametrize("module_path", REMOVED_MODULE_PATHS)
def test_removed_module_paths_stay_removed(module_path: str) -> None:
    """Module files removed in 16.0.0 must not quietly return.

    The attribute checks above cannot see a restored MODULE FILE —
    ``import attune.state_manager`` would succeed again without any
    top-level export changing (cross-review finding, 2026-08-27).
    Checked against the package's own directory rather than via
    importlib: in a worktree, the editable install's meta-path finder
    resurrects deleted submodules from the MAIN checkout, so an
    import-based check is environment-dependent while the file check
    is not.
    """
    pkg_dir = Path(attune.__file__).parent
    stem = module_path.removeprefix("attune.")
    assert not (
        pkg_dir / f"{stem}.py"
    ).exists(), f"{module_path} was removed in 16.0.0 and must not be restored"
