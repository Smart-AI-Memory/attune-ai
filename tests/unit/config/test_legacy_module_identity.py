"""Regression guard: AttuneConfig carries a real attune.config module identity.

The legacy sibling ``config.py`` used to be loaded via
``importlib.util.spec_from_file_location("attune_config_legacy", ...)``,
which gave every re-exported symbol the synthetic module name
``attune_config_legacy`` — breaking isinstance checks across import
paths, pickling, and registry lookups (flagged High by the 2026-08-08
post-release review, run 031085bf659a). The file is now a real
submodule, ``attune.config.legacy``, imported normally. These tests
fail if the synthetic loader ever comes back.
"""

from __future__ import annotations

import importlib
import pickle
import sys

import pytest

import attune.config
import attune.config.legacy

pytestmark = pytest.mark.unit


class TestLegacyModuleIdentity:
    """The legacy symbols live in a real, importable attune module."""

    def test_attune_config_module_is_real(self):
        """AttuneConfig.__module__ names a real attune.config module."""
        assert attune.config.AttuneConfig.__module__ == "attune.config.legacy"
        mod = importlib.import_module(attune.config.AttuneConfig.__module__)
        assert mod.AttuneConfig is attune.config.AttuneConfig

    def test_no_synthetic_module_registered(self):
        """The synthetic loader name never re-enters sys.modules."""
        assert "attune_config_legacy" not in sys.modules

    def test_isinstance_holds_across_import_paths(self):
        """Instances built via either import path satisfy both isinstance checks."""
        from attune.config import AttuneConfig as PackageConfig
        from attune.config.legacy import AttuneConfig as LegacyConfig

        assert PackageConfig is LegacyConfig
        instance = PackageConfig()
        assert isinstance(instance, PackageConfig)
        assert isinstance(instance, LegacyConfig)

    def test_empathy_config_alias_shares_identity(self):
        """The backward-compat alias is the same class, not a copy."""
        assert attune.config.EmpathyConfig is attune.config.AttuneConfig

    def test_functions_share_identity(self):
        """Re-exported functions are the legacy module's own objects."""
        assert attune.config.load_config is attune.config.legacy.load_config
        assert attune.config.resolve_show_cost is attune.config.legacy.resolve_show_cost

    def test_pickle_round_trip(self):
        """A real module identity makes AttuneConfig instances picklable."""
        instance = attune.config.AttuneConfig(user_id="pickle-check")
        restored = pickle.loads(pickle.dumps(instance))
        assert isinstance(restored, attune.config.AttuneConfig)
        assert restored.user_id == "pickle-check"
