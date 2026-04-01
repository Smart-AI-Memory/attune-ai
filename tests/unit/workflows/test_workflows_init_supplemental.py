"""Supplemental tests for workflows/__init__.py.

Covers functions and branches not tested by test_workflows_init.py:
- is_using_api_fallback
- list_workflows(show_all=True)
- _SDK_NATIVE_WORKFLOWS engine labeling
- _ensure_registry_initialized idempotency
- _lazy_import_workflow ImportError path
- refresh_workflow_registry with config
"""

from __future__ import annotations

import pytest


class TestIsUsingApiFallback:
    """Tests for is_using_api_fallback (deprecated stub)."""

    def test_always_returns_false(self):
        """is_using_api_fallback always returns False."""
        from attune.workflows import is_using_api_fallback

        assert is_using_api_fallback("code-review") is False
        assert is_using_api_fallback("security-audit") is False
        assert is_using_api_fallback("nonexistent") is False


class TestListWorkflowsShowAll:
    """Tests for list_workflows show_all parameter."""

    def test_show_all_returns_all_entries(self):
        """show_all=True includes SDK reverse-map entries."""
        from attune.workflows import list_workflows

        default_list = list_workflows(show_all=False)
        all_list = list_workflows(show_all=True)

        # show_all should return >= default (it never filters)
        assert len(all_list) >= len(default_list)

    def test_engine_field_present(self):
        """Each workflow dict includes an engine field."""
        from attune.workflows import list_workflows

        for wf in list_workflows():
            assert "engine" in wf
            assert wf["engine"] in ("sdk", "native")

    def test_all_workflows_labeled_sdk(self):
        """All workflows are SDK-native (v4.2.0+)."""
        from attune.workflows import list_workflows

        for wf in list_workflows():
            assert wf["engine"] == "sdk", f"{wf['name']} should have engine='sdk'"

    def test_class_field_is_string(self):
        """Each workflow dict has a class field that is a string."""
        from attune.workflows import list_workflows

        for wf in list_workflows():
            assert "class" in wf
            assert isinstance(wf["class"], str)


class TestEnsureRegistryInitialized:
    """Tests for _ensure_registry_initialized."""

    def test_idempotent(self):
        """Calling _ensure_registry_initialized twice does not duplicate."""
        from attune.workflows import (
            WORKFLOW_REGISTRY,
            _ensure_registry_initialized,
        )

        _ensure_registry_initialized()
        count_first = len(WORKFLOW_REGISTRY)

        _ensure_registry_initialized()
        count_second = len(WORKFLOW_REGISTRY)

        assert count_first == count_second


class TestLazyImportFailure:
    """Tests for _lazy_import_workflow error paths."""

    def test_import_error_propagates(self):
        """ImportError from a bad module propagates."""
        from attune.workflows import (
            _LAZY_WORKFLOW_IMPORTS,
            _lazy_import_workflow,
            _loaded_workflow_modules,
        )

        # Temporarily inject a bad entry
        _LAZY_WORKFLOW_IMPORTS["_TestBadWorkflow"] = (
            ".nonexistent_module_xyz",
            "_TestBadWorkflow",
        )
        # Clear cache for this entry
        _loaded_workflow_modules.pop(".nonexistent_module_xyz._TestBadWorkflow", None)

        try:
            with pytest.raises(ImportError):
                _lazy_import_workflow("_TestBadWorkflow")
        finally:
            del _LAZY_WORKFLOW_IMPORTS["_TestBadWorkflow"]


class TestRefreshWorkflowRegistryWithConfig:
    """Tests for refresh_workflow_registry with a config argument."""

    def test_refresh_with_disabled_workflows(self):
        """refresh_workflow_registry respects disabled_workflows config."""
        from attune.workflows import WORKFLOW_REGISTRY, refresh_workflow_registry
        from attune.workflows.config import WorkflowConfig

        config = WorkflowConfig(disabled_workflows=["code-review"])
        refresh_workflow_registry(config=config)

        assert "code-review" not in WORKFLOW_REGISTRY

        # Restore
        refresh_workflow_registry()
        assert "code-review" in WORKFLOW_REGISTRY

    def test_refresh_with_none_config(self):
        """refresh_workflow_registry with None uses defaults."""
        from attune.workflows import WORKFLOW_REGISTRY, refresh_workflow_registry

        refresh_workflow_registry(config=None)

        assert len(WORKFLOW_REGISTRY) > 0
