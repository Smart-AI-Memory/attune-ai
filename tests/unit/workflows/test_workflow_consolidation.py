"""Tests for workflow consolidation.

Verifies that:
1. Deprecated slugs are removed from the active registry
2. Migration aliases resolve to correct canonical workflows
3. Deprecated classes emit DeprecationWarning on instantiation
4. Canonical slugs still load correctly

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import warnings

import pytest

from attune.workflows.migration import WORKFLOW_ALIASES, list_migrations, resolve_workflow_migration


class TestRegistryConsolidation:
    """Verify deprecated slugs are removed from the active registry."""

    REMOVED_SLUGS = [
        "pro-review",
        "pr-review",
        "document-manager",
        "orchestrated-release-prep",
        "autonomous-test-gen",
        "progressive-test-gen",
        "test-coverage-boost",
    ]

    CANONICAL_SLUGS = [
        "code-review",
        "doc-gen",
        "doc-orchestrator",
        "release-prep",
        "test-gen",
        "test-gen-parallel",
        "secure-release",
        "bug-predict",
        "security-audit",
        "perf-audit",
        # test-maintenance: removed — utility class, not BaseWorkflow
        # batch-processing: removed — batch API client, not BaseWorkflow
    ]

    def test_removed_slugs_not_in_default_registry(self):
        """Deprecated slugs should not appear in _DEFAULT_WORKFLOW_NAMES."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        for slug in self.REMOVED_SLUGS:
            assert slug not in _DEFAULT_WORKFLOW_NAMES, (
                f"'{slug}' should be removed from _DEFAULT_WORKFLOW_NAMES "
                f"(handled by migration system)"
            )

    def test_canonical_slugs_in_registry(self):
        """Canonical slugs should remain in _DEFAULT_WORKFLOW_NAMES."""
        from attune.workflows import _DEFAULT_WORKFLOW_NAMES

        for slug in self.CANONICAL_SLUGS:
            assert (
                slug in _DEFAULT_WORKFLOW_NAMES
            ), f"Canonical slug '{slug}' missing from _DEFAULT_WORKFLOW_NAMES"

    def test_removed_slugs_have_migration_aliases(self):
        """Every removed slug should have a corresponding migration alias."""
        for slug in self.REMOVED_SLUGS:
            assert (
                slug in WORKFLOW_ALIASES
            ), f"'{slug}' removed from registry but has no migration alias"

    def test_lazy_imports_preserved(self):
        """Deprecated classes should still be importable via lazy loading."""
        from attune.workflows import _LAZY_WORKFLOW_IMPORTS

        preserved_classes = [
            "CodeReviewPipeline",
            "PRReviewWorkflow",
            "DocumentManagerWorkflow",
            "OrchestratedReleasePrepWorkflow",
            "AutonomousTestGenerator",
            "ProgressiveTestGenWorkflow",
        ]
        for cls_name in preserved_classes:
            assert (
                cls_name in _LAZY_WORKFLOW_IMPORTS
            ), f"'{cls_name}' should remain in _LAZY_WORKFLOW_IMPORTS for backward compat"


class TestMigrationAliases:
    """Verify migration aliases resolve to correct canonical workflows."""

    @pytest.mark.parametrize(
        "old_slug,expected_canonical",
        [
            ("pro-review", "code-review"),
            ("pr-review", "code-review"),
            ("document-manager", "doc-gen"),
            ("orchestrated-release-prep", "release-prep"),
            ("autonomous-test-gen", "test-gen-parallel"),
            ("progressive-test-gen", "test-gen-parallel"),
            ("test-coverage-boost", "test-gen"),
            ("secure-release", "release-prep"),
        ],
    )
    def test_alias_resolves_to_canonical(self, old_slug, expected_canonical):
        """Each deprecated slug should resolve to its canonical workflow."""
        resolved_name, kwargs, was_migrated = resolve_workflow_migration(old_slug)
        assert (
            resolved_name == expected_canonical
        ), f"'{old_slug}' resolved to '{resolved_name}', expected '{expected_canonical}'"
        assert was_migrated is True

    def test_canonical_slug_passes_through(self):
        """Canonical slugs should pass through unchanged."""
        name, kwargs, was_migrated = resolve_workflow_migration("code-review")
        assert name == "code-review"
        assert kwargs == {}
        assert was_migrated is False

    def test_pr_review_alias_has_security_mode(self):
        """pr-review alias should forward mode=security."""
        _, kwargs, _ = resolve_workflow_migration("pr-review")
        assert kwargs.get("mode") == "security"

    def test_pro_review_alias_has_premium_mode(self):
        """pro-review alias should forward mode=premium."""
        _, kwargs, _ = resolve_workflow_migration("pro-review")
        assert kwargs.get("mode") == "premium"


class TestDeprecationWarnings:
    """Verify deprecated classes emit DeprecationWarning."""

    def test_document_manager_warns(self):
        """DocumentManagerWorkflow should emit DeprecationWarning."""
        from attune.workflows import DocumentManagerWorkflow

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            DocumentManagerWorkflow()
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "DocumentManagerWorkflow is deprecated" in str(deprecation_warnings[0].message)

    def test_code_review_pipeline_warns(self):
        """CodeReviewPipeline should emit DeprecationWarning."""
        from attune.workflows import CodeReviewPipeline

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CodeReviewPipeline()
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "CodeReviewPipeline is deprecated" in str(deprecation_warnings[0].message)

    def test_pr_review_workflow_warns(self):
        """PRReviewWorkflow should emit DeprecationWarning."""
        from attune.workflows import PRReviewWorkflow

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            PRReviewWorkflow()
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "PRReviewWorkflow is deprecated" in str(deprecation_warnings[0].message)

    def test_orchestrated_release_prep_warns(self):
        """OrchestratedReleasePrepWorkflow should emit DeprecationWarning."""
        from attune.workflows import OrchestratedReleasePrepWorkflow

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            OrchestratedReleasePrepWorkflow()
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "OrchestratedReleasePrepWorkflow is deprecated" in str(
                deprecation_warnings[0].message,
            )


class TestListMigrations:
    """Verify list_migrations() includes all consolidation entries."""

    def test_list_migrations_includes_pr_review(self):
        """list_migrations should include the new pr-review entry."""
        migrations = list_migrations()
        old_names = [m["old_name"] for m in migrations]
        assert "pr-review" in old_names

    def test_all_removed_slugs_in_migrations(self):
        """All removed slugs should appear in list_migrations."""
        migrations = list_migrations()
        old_names = {m["old_name"] for m in migrations}

        removed = [
            "pro-review",
            "pr-review",
            "document-manager",
            "orchestrated-release-prep",
            "autonomous-test-gen",
            "progressive-test-gen",
            "test-coverage-boost",
        ]
        for slug in removed:
            assert slug in old_names, f"'{slug}' missing from list_migrations()"
