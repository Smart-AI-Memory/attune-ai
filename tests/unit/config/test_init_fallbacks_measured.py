"""In-process (coverage-visible) tests for attune.config's init fallbacks.

``tests/unit/config/test_config_init_fallbacks.py`` already proves both
fallback branches behaviorally — but it does so in a fresh subprocess,
which the coverage tracer cannot see, so the lines still report as missed
on main. These twins exercise the same branches via ``importlib.reload``
in the current process, making the coverage measurable. Both restore the
real module state in ``finally`` and assert the restoration.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest

import attune.config as cfg

pytest.importorskip("yaml")

pytestmark = pytest.mark.unit


class TestYamlUnavailableFallbackMeasured:
    """The `except ImportError` branch guarding the optional PyYAML import."""

    def test_yaml_missing_sets_yaml_available_false(self):
        """When `import yaml` raises, YAML_AVAILABLE lands False, not True."""
        real = sys.modules.get("yaml")
        sys.modules["yaml"] = None  # forces ImportError on `import yaml`
        try:
            importlib.reload(cfg)
            assert cfg.YAML_AVAILABLE is False
        finally:
            if real is not None:
                sys.modules["yaml"] = real
            else:
                sys.modules.pop("yaml", None)
            importlib.reload(cfg)
        assert cfg.YAML_AVAILABLE is True


class TestLegacyConfigSpecFailureFallbackMeasured:
    """The `else` branch when spec_from_file_location yields no loadable spec."""

    def test_spec_none_degrades_legacy_symbols_to_none(self):
        """A None spec degrades every legacy re-export to None, no raise."""
        orig = importlib.util.spec_from_file_location

        def _patched(name, *args, **kwargs):
            if name == "attune_config_legacy":
                return None
            return orig(name, *args, **kwargs)

        importlib.util.spec_from_file_location = _patched
        try:
            importlib.reload(cfg)
            assert cfg.AttuneConfig is None
            assert cfg.EmpathyConfig is None
            assert cfg.load_config is None
            assert cfg.resolve_show_cost is None
        finally:
            importlib.util.spec_from_file_location = orig
            importlib.reload(cfg)
        # Restoration proof: the legacy symbols are real again.
        assert cfg.AttuneConfig is not None
        assert cfg.load_config is not None
