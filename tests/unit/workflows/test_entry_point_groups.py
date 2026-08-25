"""Entry-point group wiring for workflow/plugin discovery (#2238, 15.0.0).

15.0.0 standardizes discovery on the ``attune.*`` groups only: the
legacy ``empathy.workflows``, ``attune_framework.plugins``, and
``empathy_framework.plugins`` groups are no longer read, and the
``EmpathyMCPServer`` alias is gone.
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

    def test_legacy_group_is_no_longer_read(self):
        """15.0.0: a workflow registered only under empathy.workflows is invisible."""
        eps = {"empathy.workflows": [_LoadableEntryPoint("old-flow", _FakeLegacyWorkflow)]}
        with patch("attune.workflows.importlib.metadata.entry_points", _entry_points_stub(eps)):
            discovered = discover_workflows(include_defaults=False)
        assert discovered == {}

    def test_class_without_execute_is_ignored(self):
        class NoExecute:
            pass

        eps = {"attune.workflows": [_LoadableEntryPoint("bad", NoExecute)]}
        with patch("attune.workflows.importlib.metadata.entry_points", _entry_points_stub(eps)):
            discovered = discover_workflows(include_defaults=False)
        assert "bad" not in discovered


class TestPluginRegistryLegacyGroups:
    def test_only_attune_plugins_group_exists(self):
        from attune.plugins import registry as reg

        assert reg._ENTRY_POINT_GROUP == "attune.plugins"
        assert not hasattr(reg, "_LEGACY_ENTRY_POINT_GROUPS")

    def test_legacy_groups_are_no_longer_read(self, monkeypatch):
        """15.0.0: discovery queries only attune.plugins."""
        from attune.plugins import registry as reg

        calls = []

        def _fake_entry_points(*, group):
            calls.append(group)
            return []

        monkeypatch.setattr(reg, "entry_points", _fake_entry_points)
        monkeypatch.setattr(reg, "_discovery_cache", None)
        registry = reg.PluginRegistry()
        registry.auto_discover()
        try:
            assert calls == ["attune.plugins"]
        finally:
            reg._discovery_cache = None


class TestMCPServerRename:
    def test_attune_server_is_canonical(self):
        from attune.mcp.server import AttuneMCPServer

        assert AttuneMCPServer.__name__ == "AttuneMCPServer"

    def test_legacy_alias_is_gone(self):
        """15.0.0: the EmpathyMCPServer alias no longer resolves anywhere."""
        import attune.mcp as mcp_pkg
        import attune.mcp.server as server_mod

        with pytest.raises(AttributeError):
            _ = server_mod.EmpathyMCPServer
        with pytest.raises(AttributeError):
            _ = mcp_pkg.EmpathyMCPServer
        assert "EmpathyMCPServer" not in mcp_pkg.__all__


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
