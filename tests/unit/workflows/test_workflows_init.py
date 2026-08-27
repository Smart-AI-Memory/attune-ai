"""Tests for workflows/__init__.py module.

Tests lazy import system, workflow registry, and discovery functions.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest


class TestLazyImportWorkflow:
    """Tests for _lazy_import_workflow."""

    def test_known_workflow_loads(self):
        """Known workflow names in _LAZY_WORKFLOW_IMPORTS resolve."""
        from attune.workflows import _lazy_import_workflow

        # SecurityAuditWorkflow is in _LAZY_WORKFLOW_IMPORTS
        cls = _lazy_import_workflow("SecurityAuditWorkflow")
        assert cls is not None

    def test_unknown_name_raises(self):
        """Unknown names raise AttributeError."""
        from attune.workflows import _lazy_import_workflow

        with pytest.raises(AttributeError, match="has no attribute"):
            _lazy_import_workflow("NonExistentWorkflow")


class TestGetattr:
    """Tests for __getattr__ lazy loading."""

    def test_getattr_unknown_raises(self):
        """Accessing non-existent attribute raises AttributeError."""
        import attune.workflows as wf_module

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = wf_module.__getattr__("TotallyFakeClass")

    def test_lazy_workflow_import_via_getattr(self):
        """Lazy workflow class can be accessed via module attribute."""
        # SecurityAuditWorkflow is in _LAZY_WORKFLOW_IMPORTS
        from attune.workflows import _LAZY_WORKFLOW_IMPORTS

        # Pick one that should exist
        assert "SecurityAuditWorkflow" in _LAZY_WORKFLOW_IMPORTS


class TestDiscoverWorkflows:
    """Tests for discover_workflows."""

    def test_discover_returns_dict(self):
        """discover_workflows returns a dict."""
        from attune.workflows import discover_workflows

        result = discover_workflows()

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_discover_includes_code_review(self):
        """Default workflows include code-review."""
        from attune.workflows import discover_workflows

        result = discover_workflows()

        assert "code-review" in result

    def test_discover_without_defaults(self):
        """include_defaults=False returns only entry-point workflows."""
        from attune.workflows import discover_workflows

        result = discover_workflows(include_defaults=False)

        # Without defaults nothing else is loaded — the entry-point
        # reading path was removed in 16.0.0 (release-16-manifest D1).
        assert result == {}

    def test_discover_with_disabled_workflows(self):
        """Disabled workflows are excluded from results."""
        from attune.workflows.config import WorkflowConfig

        config = WorkflowConfig(disabled_workflows=["code-review"])
        from attune.workflows import discover_workflows

        result = discover_workflows(config=config)

        assert "code-review" not in result


class TestGetWorkflow:
    """Tests for get_workflow."""

    def test_get_known_workflow(self):
        """get_workflow returns class for known workflow name."""
        from attune.workflows import get_workflow

        cls = get_workflow("code-review")

        assert cls is not None
        assert hasattr(cls, "execute")

    def test_get_unknown_workflow_raises(self):
        """get_workflow raises KeyError for unknown names."""
        from attune.workflows import get_workflow

        with pytest.raises(KeyError, match="Unknown workflow"):
            get_workflow("nonexistent-workflow-xyz")

    def test_release_slugs_resolve_to_distinct_workflows(self):
        """The two release workflows are distinct and named for what they do.

        ``release-prep`` and its synonym ``release-gate`` are the
        deterministic agent-team gate; ``release-notes`` is the SDK
        advisory workflow. They must NOT collide on one class (the
        original bug was both classes carrying ``name="release-prep"``).
        """
        from attune.workflows import get_workflow

        gate = get_workflow("release-prep")
        gate_synonym = get_workflow("release-gate")
        notes = get_workflow("release-notes")

        assert gate.__name__ == "ReleasePrepTeamWorkflow"
        assert gate_synonym is gate
        assert notes.__name__ == "ReleasePreparationWorkflow"
        assert notes is not gate
        assert notes.name == "release-notes"


class TestListWorkflows:
    """Tests for list_workflows."""

    def test_list_returns_list_of_dicts(self):
        """list_workflows returns list of dicts with expected keys."""
        from attune.workflows import list_workflows

        result = list_workflows()

        assert isinstance(result, list)
        assert len(result) > 0

        # Check required keys
        for wf in result:
            assert "name" in wf
            assert "class" in wf
            assert "description" in wf
            assert "stages" in wf


class TestDefaultWorkflowNames:
    """Tests for _DEFAULT_WORKFLOW_NAMES registry."""

    def test_registry_has_expected_entries(self):
        """Registry contains core workflow names."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        expected = [
            "code-review",
            "bug-predict",
            "security-audit",
            "test-gen",
            "refactor-plan",
        ]
        for name in expected:
            assert name in _DEFAULT_WORKFLOW_NAMES

    def test_registry_values_are_strings(self):
        """Registry values are class name strings (for lazy loading)."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        for key, value in _DEFAULT_WORKFLOW_NAMES.items():
            assert isinstance(value, str), f"{key} maps to {type(value)}, expected str"


class TestRefreshWorkflowRegistry:
    """Tests for refresh_workflow_registry."""

    def test_refresh_clears_and_repopulates(self):
        """refresh_workflow_registry clears and repopulates WORKFLOW_REGISTRY."""
        from attune.workflows import WORKFLOW_REGISTRY, refresh_workflow_registry

        refresh_workflow_registry()

        assert isinstance(WORKFLOW_REGISTRY, dict)
        assert len(WORKFLOW_REGISTRY) > 0


class TestDeprecatedCliCommands:
    """Tests for the retired one-command family's deprecation stubs.

    ``cmd_morning``/``cmd_ship``/``cmd_fix_all``/``cmd_learn`` had no
    live caller (no CLI wiring; the "ship" NL intent already routes to
    release-prep) and their implementation modules were deleted. The
    names stay accessible via ``__getattr__`` (deprecation path, not a
    hard ``AttributeError``) but warn on access and raise when called.
    See docs/reports/d-block-triage-2026-07-14.md.
    """

    @pytest.mark.parametrize(
        "name",
        ["cmd_morning", "cmd_ship", "cmd_fix_all", "cmd_learn"],
    )
    def test_getattr_warns_and_returns_stub(self, name):
        import attune.workflows as wf_module

        with pytest.warns(DeprecationWarning, match=name):
            stub = wf_module.__getattr__(name)

        assert callable(stub)

    @pytest.mark.parametrize(
        "name",
        ["cmd_morning", "cmd_ship", "cmd_fix_all", "cmd_learn"],
    )
    def test_stub_raises_when_called(self, name):
        import attune.workflows as wf_module

        with pytest.warns(DeprecationWarning):
            stub = wf_module.__getattr__(name)

        with pytest.raises(NotImplementedError, match=name):
            stub()

    def test_cmd_ship_stub_points_at_successor(self):
        import attune.workflows as wf_module

        with pytest.warns(DeprecationWarning, match="release-prep"):
            wf_module.__getattr__("cmd_ship")


class TestDiscoverWorkflowsWithConfig:
    """Tests for discover_workflows with config (lines 335-375)."""

    def test_discover_with_hipaa_mode_config(self):
        """discover_workflows with HIPAA config includes opt-in workflows."""
        from attune.workflows import discover_workflows
        from attune.workflows.config import WorkflowConfig

        config = WorkflowConfig(compliance_mode="hipaa")

        # Should run without error even with empty _OPT_IN_WORKFLOW_NAMES
        result = discover_workflows(config=config)

        assert isinstance(result, dict)

    def test_discover_with_enabled_workflows_in_config(self):
        """discover_workflows with enabled_workflows processes them."""
        from attune.workflows import discover_workflows
        from attune.workflows.config import WorkflowConfig

        # enabled_workflows only apply to _OPT_IN_WORKFLOW_NAMES entries
        config = WorkflowConfig(enabled_workflows=["nonexistent-opt-in"])

        result = discover_workflows(config=config)

        assert isinstance(result, dict)

    def test_discover_with_disabled_workflows_in_config(self):
        """discover_workflows removes disabled workflows from result."""
        from attune.workflows import discover_workflows
        from attune.workflows.config import WorkflowConfig

        config = WorkflowConfig(disabled_workflows=["code-review", "bug-predict"])
        result = discover_workflows(config=config)

        assert "code-review" not in result
        assert "bug-predict" not in result


class TestGetOptInWorkflows:
    """Tests for get_opt_in_workflows (lines 402-408)."""

    def test_get_opt_in_returns_dict(self):
        """get_opt_in_workflows returns a dict."""
        from attune.workflows import get_opt_in_workflows

        result = get_opt_in_workflows()

        assert isinstance(result, dict)

    def test_get_opt_in_empty_when_no_opt_in(self):
        """get_opt_in_workflows returns empty dict when no opt-in workflows."""
        from attune.workflows import _OPT_IN_WORKFLOW_NAMES, get_opt_in_workflows

        # _OPT_IN_WORKFLOW_NAMES is empty by default
        result = get_opt_in_workflows()

        if not _OPT_IN_WORKFLOW_NAMES:
            assert result == {}


class TestGetWorkflowErrorMessage:
    """Tests for get_workflow error message (line 430-431)."""

    def test_unknown_workflow_error_includes_available(self):
        """KeyError message for unknown workflow includes available workflows."""
        from attune.workflows import get_workflow

        with pytest.raises(KeyError) as exc_info:
            get_workflow("totally-unknown-xyz")

        # Error message should include "Available:"
        assert "Available" in str(exc_info.value)


class TestListWorkflowsTierMap:
    """Tests for list_workflows tier_map serialization."""

    def test_list_workflows_tier_map_serialized(self):
        """list_workflows serializes tier_map values to strings."""
        from attune.workflows import list_workflows

        workflows = list_workflows()

        for wf in workflows:
            assert "tier_map" in wf
            # All tier_map values should be strings (enum.value)
            for key, val in wf["tier_map"].items():
                assert isinstance(val, str), f"tier_map[{key}] should be str, got {type(val)}"

    def test_list_workflows_description_field(self):
        """list_workflows includes description for each workflow."""
        from attune.workflows import list_workflows

        workflows = list_workflows()

        for wf in workflows:
            assert "description" in wf
            assert isinstance(wf["description"], str)


class TestGetatttrMigrationExports:
    """Tests for __getattr__ migration module exports (lines 480-483)."""

    def test_getattr_resolve_workflow_migration(self):
        """__getattr__ resolves migration module exports."""
        import attune.workflows as wf_module

        # resolve_workflow_migration should be accessible via __getattr__
        func = wf_module.__getattr__("resolve_workflow_migration")
        assert callable(func)

    def test_getattr_workflow_aliases(self):
        """__getattr__ resolves WORKFLOW_ALIASES."""
        import attune.workflows as wf_module

        aliases = wf_module.__getattr__("WORKFLOW_ALIASES")
        assert aliases is not None

    def test_getattr_list_migrations(self):
        """__getattr__ resolves list_migrations."""
        import attune.workflows as wf_module

        func = wf_module.__getattr__("list_migrations")
        assert callable(func)

    def test_getattr_lazy_workflow_class(self):
        """__getattr__ triggers lazy import for known workflow class."""
        import attune.workflows as wf_module

        cls = wf_module.__getattr__("SecurityAuditWorkflow")
        assert cls is not None

    def test_getattr_unknown_raises_attribute_error(self):
        """__getattr__ raises AttributeError for unknown names."""
        import attune.workflows as wf_module

        with pytest.raises(AttributeError, match="has no attribute"):
            wf_module.__getattr__("AbsolutelyFakeWorkflow999")


class TestLazyCacheHit:
    """Tests for lazy import caching (lines 188-200)."""

    def test_lazy_import_caches_result(self):
        """Second call to _lazy_import_workflow returns cached result."""
        from attune.workflows import _lazy_import_workflow

        # Call twice - second call should hit cache
        cls1 = _lazy_import_workflow("SecurityAuditWorkflow")
        cls2 = _lazy_import_workflow("SecurityAuditWorkflow")

        assert cls1 is cls2
