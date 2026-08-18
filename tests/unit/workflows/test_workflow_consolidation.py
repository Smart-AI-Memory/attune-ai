"""Tests for workflow consolidation.

Verifies that:
1. Deprecated slugs are removed from the active registry
2. Migration aliases resolve to correct canonical workflows
3. Removed classes stay removed (lazy-import + attribute drift guards)
4. Canonical slugs still load correctly

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

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
        "test-gen-parallel",
    ]

    CANONICAL_SLUGS = [
        "code-review",
        "doc-gen",
        "doc-orchestrator",
        "release-prep",
        "test-gen",
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

    def test_removed_classes_not_lazily_importable(self):
        """Classes removed after their deprecation window stay removed."""
        from attune.workflows import _LAZY_WORKFLOW_IMPORTS

        removed_classes = [
            # Deprecated v4.0 with removal announced for v5.0.0; removed at
            # 11.6.x. The "document-manager" slug still routes to doc-gen
            # via migration.py — only the class is gone.
            "DocumentManagerWorkflow",
        ]
        for cls_name in removed_classes:
            assert (
                cls_name not in _LAZY_WORKFLOW_IMPORTS
            ), f"'{cls_name}' was removed and must not return to _LAZY_WORKFLOW_IMPORTS"


class TestMigrationAliases:
    """Verify migration aliases resolve to correct canonical workflows."""

    @pytest.mark.parametrize(
        "old_slug,expected_canonical",
        [
            ("pro-review", "code-review"),
            ("pr-review", "code-review"),
            ("document-manager", "doc-gen"),
            ("orchestrated-release-prep", "release-prep"),
            ("test-gen-parallel", "test-gen"),
            ("autonomous-test-gen", "test-gen"),
            ("progressive-test-gen", "test-gen"),
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


class TestRemovedClasses:
    """Verify classes removed after their deprecation window stay gone."""

    def test_document_manager_class_removed(self):
        """DocumentManagerWorkflow no longer imports; the slug routes to doc-gen."""
        import attune.workflows

        with pytest.raises(AttributeError, match="DocumentManagerWorkflow"):
            _ = attune.workflows.DocumentManagerWorkflow


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
            "test-gen-parallel",
            "autonomous-test-gen",
            "progressive-test-gen",
            "test-coverage-boost",
        ]
        for slug in removed:
            assert slug in old_names, f"'{slug}' missing from list_migrations()"
