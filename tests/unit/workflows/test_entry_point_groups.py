"""Entry-point seam state for workflow/plugin/wizard discovery.

15.0.0 standardized discovery on the ``attune.*`` groups; 16.0.0
collapsed the ceremony seams entirely (release-16-manifest D1):
workflow discovery reads NO entry points, the plugin registry loads a
static builtin table, the wizard registry loads builtins directly, and
pyproject declares no ``attune.plugins``/``attune.wizards``/
``attune.workflows`` groups. ``attune.memory_backends`` is the one
seam that remains. The ``EmpathyMCPServer`` alias is gone (15.0.0).
"""

import pytest

from attune.workflows import discover_workflows


class TestWorkflowDiscoveryReadsNoEntryPoints:
    """16.0.0: an entry-point-registered workflow is invisible by design."""

    def test_entry_point_workflows_are_not_discovered(self, monkeypatch):
        import importlib.metadata as ilmd

        queried: list[str] = []
        real = ilmd.entry_points

        def _recorder(**kwargs):
            queried.append(kwargs.get("group", "<all>"))
            return real(**kwargs)

        monkeypatch.setattr(ilmd, "entry_points", _recorder)
        discovered = discover_workflows(include_defaults=False)
        assert discovered == {}
        assert "attune.workflows" not in queried


class TestPluginRegistryBuiltinTable:
    """16.0.0: the plugin registry loads a static builtin table."""

    def test_builtin_table_is_the_two_bundled_plugins(self):
        from attune.plugins import registry as reg

        assert [name for name, _, _ in reg._BUILTIN_PLUGINS] == ["software", "redis"]
        assert not hasattr(reg, "_ENTRY_POINT_GROUP")

    def test_auto_discover_never_scans_entry_points(self, monkeypatch):
        import importlib.metadata as ilmd

        from attune.plugins import registry as reg

        def _boom(**kwargs):  # pragma: no cover - failure path
            raise AssertionError("auto_discover must not scan entry points")

        monkeypatch.setattr(ilmd, "entry_points", _boom)
        monkeypatch.setattr(reg, "_discovery_cache", None)
        registry = reg.PluginRegistry()
        try:
            registry.auto_discover()
            assert sorted(registry._plugins) == ["redis", "software"]
        finally:
            reg._discovery_cache = None


class TestPyprojectDeclaresNoCollapsedGroups:
    """A helpful re-add of a collapsed group must fail CI (drift guard)."""

    def test_collapsed_groups_absent_and_memory_backends_present(self):
        from pathlib import Path as _P

        pyproject = _P(__file__).resolve().parents[3] / "pyproject.toml"
        headers = [
            line.strip()
            for line in pyproject.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        ]
        for group in ("attune.plugins", "attune.wizards", "attune.workflows"):
            assert f'[project.entry-points."{group}"]' not in headers, (
                f"the {group} entry-point group was collapsed in 16.0.0 "
                "(release-16-manifest D1) — extension returns via the ruled "
                "extension system, not by re-adding the group"
            )
        assert (
            '[project.entry-points."attune.memory_backends"]' in headers
        ), "attune.memory_backends is the one seam D1 keeps"


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
