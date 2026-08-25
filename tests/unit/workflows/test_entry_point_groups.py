"""Entry-point group wiring for workflow/plugin discovery (#2238).

Regression guards for the phantom-read fix: ``discover_workflows`` must
read the primary ``attune.workflows`` group (previously only the legacy
``empathy.workflows`` group was read, so primary-group registrations
were silently ignored), and the plugin registry must read the
``empathy_framework.plugins`` legacy group that pyproject historically
registered but nothing consumed.
"""

from unittest.mock import patch

import pytest

from attune.workflows import discover_workflows


class _FakeWorkflow:
    """Minimal class satisfying the discovery contract (has execute)."""

    def execute(self):  # pragma: no cover - contract marker only
        """Satisfy the hasattr(cls, "execute") discovery check."""


class _FakeLegacyWorkflow(_FakeWorkflow):
    pass


def _entry_points_stub(mapping):
    """Return a callable mimicking importlib.metadata.entry_points(group=...)."""

    def _stub(*, group):
        return mapping.get(group, [])

    return _stub


class _LoadableEntryPoint:
    """Duck-typed entry point whose load() returns a preset class."""

    def __init__(self, name: str, cls):
        self.name = name
        self._cls = cls

    def load(self):
        return self._cls


class TestWorkflowEntryPointGroups:
    def test_primary_group_is_discovered(self):
        eps = {"attune.workflows": [_LoadableEntryPoint("my-flow", _FakeWorkflow)]}
        with patch("attune.workflows.importlib.metadata.entry_points", _entry_points_stub(eps)):
            discovered = discover_workflows(include_defaults=False)
        assert discovered == {"my-flow": _FakeWorkflow}

    def test_legacy_group_still_discovered(self):
        eps = {"empathy.workflows": [_LoadableEntryPoint("old-flow", _FakeLegacyWorkflow)]}
        with patch("attune.workflows.importlib.metadata.entry_points", _entry_points_stub(eps)):
            discovered = discover_workflows(include_defaults=False)
        assert discovered == {"old-flow": _FakeLegacyWorkflow}

    def test_primary_wins_over_legacy_on_same_name(self):
        eps = {
            "attune.workflows": [_LoadableEntryPoint("dup", _FakeWorkflow)],
            "empathy.workflows": [_LoadableEntryPoint("dup", _FakeLegacyWorkflow)],
        }
        with patch("attune.workflows.importlib.metadata.entry_points", _entry_points_stub(eps)):
            discovered = discover_workflows(include_defaults=False)
        assert discovered["dup"] is _FakeWorkflow

    def test_legacy_group_logs_deprecation_warning(self, caplog):
        eps = {"empathy.workflows": [_LoadableEntryPoint("old-flow", _FakeLegacyWorkflow)]}
        with patch("attune.workflows.importlib.metadata.entry_points", _entry_points_stub(eps)):
            with caplog.at_level("WARNING", logger="attune.workflows"):
                discover_workflows(include_defaults=False)
        assert any("empathy.workflows" in r.message for r in caplog.records)

    def test_class_without_execute_is_ignored(self):
        class NoExecute:
            pass

        eps = {"attune.workflows": [_LoadableEntryPoint("bad", NoExecute)]}
        with patch("attune.workflows.importlib.metadata.entry_points", _entry_points_stub(eps)):
            discovered = discover_workflows(include_defaults=False)
        assert "bad" not in discovered


class TestPluginRegistryLegacyGroups:
    def test_both_legacy_groups_are_read(self):
        from attune.plugins import registry as reg

        assert reg._ENTRY_POINT_GROUP == "attune.plugins"
        assert "attune_framework.plugins" in reg._LEGACY_ENTRY_POINT_GROUPS
        assert "empathy_framework.plugins" in reg._LEGACY_ENTRY_POINT_GROUPS

    def test_empathy_framework_group_plugin_is_discovered(self, monkeypatch):
        from attune.plugins import registry as reg
        from attune.plugins.base import BasePlugin, PluginMetadata

        class _StubPlugin(BasePlugin):
            def get_metadata(self):
                return PluginMetadata(
                    name="Stub",
                    version="1.0.0",
                    domain="stub",
                    description="stub",
                    author="t",
                    license="Apache-2.0",
                    requires_core_version="1.0.0",
                )

            def register_workflows(self):
                return {}

        calls = []

        def _fake_entry_points(*, group):
            calls.append(group)
            if group == "empathy_framework.plugins":
                return [_LoadableEntryPoint("stub", _StubPlugin)]
            return []

        monkeypatch.setattr(reg, "entry_points", _fake_entry_points)
        monkeypatch.setattr(reg, "_discovery_cache", None)
        registry = reg.PluginRegistry()
        registry.auto_discover()
        try:
            assert "empathy_framework.plugins" in calls
            assert registry.get_plugin("stub") is not None
        finally:
            reg._discovery_cache = None


class TestMCPServerRename:
    def test_attune_server_is_canonical(self):
        from attune.mcp.server import AttuneMCPServer

        assert AttuneMCPServer.__name__ == "AttuneMCPServer"

    def test_legacy_alias_warns_and_aliases(self):
        import attune.mcp.server as server_mod

        with pytest.warns(DeprecationWarning, match="AttuneMCPServer"):
            legacy = server_mod.EmpathyMCPServer
        assert legacy is server_mod.AttuneMCPServer

    def test_package_level_alias_resolves(self):
        import attune.mcp as mcp_pkg

        with pytest.warns(DeprecationWarning):
            legacy = mcp_pkg.EmpathyMCPServer
        assert legacy is mcp_pkg.AttuneMCPServer

    def test_unknown_attribute_still_raises(self):
        import attune.mcp.server as server_mod

        with pytest.raises(AttributeError):
            _ = server_mod.NoSuchThing


class TestPluginBaseWorkflowContract:
    def test_contract_is_level_free(self):
        """15.0.0: the plugin contract carries no empathy_level (D2/D7)."""
        import pytest

        from attune.plugins.base import BaseWorkflow

        class Minimal(BaseWorkflow):
            async def analyze(self, context):
                return {}

            def get_required_context(self):
                return ["x"]

        wf = Minimal(name="m", domain="software")
        assert not hasattr(wf, "empathy_level")
        assert not hasattr(wf, "get_empathy_level")

        with pytest.raises(TypeError):
            Minimal(name="m", domain="software", empathy_level=4)
