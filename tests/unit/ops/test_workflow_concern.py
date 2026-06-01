"""Unit tests for workflow_concern.derive_concern + helpers.

Pure-logic tests — no I/O, no fixtures beyond the module's own data.
Mirrors the shape of ``tests/unit/ops/test_spec_lifecycle.py``.

Coverage targets:
- All 7 concern buckets populated correctly per decisions.md
- derive_concern() handles unknown names without raising
- group_by_concern() returns alphabetically-sorted lists
- concern_counts() populates all 7 buckets (zero for empty)
- Drift-guard: every registered workflow has an explicit concern
"""

from __future__ import annotations

import pytest

from attune.ops.workflow_concern import (
    ALL_CONCERNS,
    concern_counts,
    derive_concern,
    group_by_concern,
)

# ---------------------------------------------------------------------------
# derive_concern() — per-workflow assignments
# ---------------------------------------------------------------------------


class TestDeriveConcernReview:
    """4 workflows in the review bucket."""

    @pytest.mark.parametrize(
        "name",
        ["code-review", "deep-review", "security-audit", "bug-predict"],
    )
    def test_assigned_to_review(self, name):
        assert derive_concern(name) == "review"


class TestDeriveConcernTest:
    """2 workflows in the test bucket."""

    @pytest.mark.parametrize("name", ["test-gen", "test-audit"])
    def test_assigned_to_test(self, name):
        assert derive_concern(name) == "test"


class TestDeriveConcernDocs:
    """3 workflows in the docs bucket."""

    @pytest.mark.parametrize(
        "name",
        ["doc-gen", "doc-audit", "doc-orchestrator"],
    )
    def test_assigned_to_docs(self, name):
        assert derive_concern(name) == "docs"


class TestDeriveConcernRefactor:
    """2 workflows in the refactor bucket."""

    @pytest.mark.parametrize("name", ["simplify-code", "refactor-plan"])
    def test_assigned_to_refactor(self, name):
        assert derive_concern(name) == "refactor"


class TestDeriveConcernAudit:
    """3 workflows in the audit bucket."""

    @pytest.mark.parametrize(
        "name",
        ["discovery-sweep", "perf-audit", "dependency-check"],
    )
    def test_assigned_to_audit(self, name):
        assert derive_concern(name) == "audit"


class TestDeriveConcernMeta:
    """4 workflows in the meta bucket."""

    @pytest.mark.parametrize(
        "name",
        [
            "release-prep",
            "secure-release",
            "orchestrated-health-check",
            "health-check",
        ],
    )
    def test_assigned_to_meta(self, name):
        assert derive_concern(name) == "meta"


class TestDeriveConcernOther:
    """2 workflows in the other bucket."""

    @pytest.mark.parametrize("name", ["rag-code-gen", "research-synthesis"])
    def test_assigned_to_other(self, name):
        assert derive_concern(name) == "other"


# ---------------------------------------------------------------------------
# derive_concern() — trade-off boundary cases
# ---------------------------------------------------------------------------


class TestConcernBoundaries:
    """Workflows whose name suggests one bucket but assignment is another.

    These are the explicit trade-offs ratified in decisions.md. Test
    them as such so future renames or accidental remappings break here
    loudly.
    """

    def test_security_audit_is_review_not_audit(self):
        """`security-audit` is in `review` despite the audit suffix.

        Per decisions.md: review-class workflows are "tell me what's
        wrong with this code"; audit-class is "codebase-wide health
        survey." security-audit is focused, not survey.
        """
        assert derive_concern("security-audit") == "review"

    def test_bug_predict_is_review_not_audit(self):
        """`bug-predict` is in `review` for the same reason."""
        assert derive_concern("bug-predict") == "review"

    def test_doc_orchestrator_is_docs_not_meta(self):
        """`doc-orchestrator` is a domain-specific composer, not a meta
        ops workflow. `meta` is reserved for release/health.
        """
        assert derive_concern("doc-orchestrator") == "docs"

    def test_test_audit_is_test_not_audit(self):
        """`test-audit` is `test` concern despite the audit suffix —
        routed by *purpose* (testing), not name pattern.
        """
        assert derive_concern("test-audit") == "test"

    def test_doc_audit_is_docs_not_audit(self):
        """`doc-audit` is `docs` concern despite the audit suffix —
        routed by *purpose* (documentation), not name pattern.
        """
        assert derive_concern("doc-audit") == "docs"

    def test_perf_audit_is_audit(self):
        """`perf-audit` IS in `audit` — codebase-wide perf survey,
        matches the bucket's "health survey" intent.
        """
        assert derive_concern("perf-audit") == "audit"


# ---------------------------------------------------------------------------
# derive_concern() — unknown / fallback
# ---------------------------------------------------------------------------


class TestDeriveConcernUnknown:
    """Unknown workflow names fall through to `other` without raising."""

    def test_unknown_workflow_falls_through_to_other(self):
        assert derive_concern("totally-made-up-workflow") == "other"

    def test_empty_string_falls_through_to_other(self):
        assert derive_concern("") == "other"

    def test_uppercase_name_falls_through_to_other(self):
        """Concern derivation is case-sensitive — canonical slugs are
        lowercase. Mixed-case names are unknown.
        """
        assert derive_concern("Code-Review") == "other"


# ---------------------------------------------------------------------------
# group_by_concern()
# ---------------------------------------------------------------------------


class TestGroupByConcern:
    """Grouping into per-concern lists."""

    def test_single_workflow_per_bucket(self):
        result = group_by_concern(["code-review", "test-gen"])
        assert result == {"review": ["code-review"], "test": ["test-gen"]}

    def test_multiple_workflows_per_bucket_sorted(self):
        """Names within a bucket sort alphabetically (deterministic)."""
        result = group_by_concern(["security-audit", "deep-review", "code-review", "bug-predict"])
        assert result == {"review": ["bug-predict", "code-review", "deep-review", "security-audit"]}

    def test_empty_input_returns_empty_dict(self):
        assert group_by_concern([]) == {}

    def test_unknown_workflows_grouped_as_other(self):
        result = group_by_concern(["mystery-workflow", "rag-code-gen"])
        assert result == {"other": ["mystery-workflow", "rag-code-gen"]}

    def test_input_order_does_not_affect_bucket_order(self):
        """Buckets appear in the order their first member appears in
        input; intra-bucket order is alphabetical regardless.
        """
        result = group_by_concern(["test-gen", "code-review", "test-audit"])
        assert result["test"] == ["test-audit", "test-gen"]
        assert result["review"] == ["code-review"]


# ---------------------------------------------------------------------------
# concern_counts()
# ---------------------------------------------------------------------------


class TestConcernCounts:
    """Per-bucket counts. All 7 buckets always present."""

    def test_all_seven_buckets_present_in_empty_input(self):
        counts = concern_counts([])
        assert set(counts.keys()) == set(ALL_CONCERNS)
        assert all(v == 0 for v in counts.values())

    def test_counts_match_inputs(self):
        counts = concern_counts(
            [
                "code-review",
                "deep-review",
                "test-gen",
                "doc-gen",
                "doc-audit",
                "doc-orchestrator",
            ]
        )
        assert counts["review"] == 2
        assert counts["test"] == 1
        assert counts["docs"] == 3
        # All other buckets should be 0
        assert counts["refactor"] == 0
        assert counts["audit"] == 0
        assert counts["meta"] == 0
        assert counts["other"] == 0

    def test_unknown_names_count_as_other(self):
        counts = concern_counts(["unknown-1", "unknown-2"])
        assert counts["other"] == 2

    def test_total_count_equals_input_length(self):
        names = [
            "code-review",
            "test-gen",
            "doc-gen",
            "simplify-code",
            "perf-audit",
            "release-prep",
            "rag-code-gen",
        ]
        counts = concern_counts(names)
        assert sum(counts.values()) == len(names)


# ---------------------------------------------------------------------------
# Drift-guard: every registered workflow has an explicit concern
# ---------------------------------------------------------------------------


class TestDriftGuard:
    """If list_workflows() ships a new workflow, this test fails until
    the assignment is added to _WORKFLOW_CONCERNS. Catches the
    'add-a-workflow-without-mapping' drift.
    """

    def test_all_registered_workflows_have_explicit_concern(self):
        """Every workflow returned by attune.workflows.list_workflows()
        must have an explicit (not fallback-to-other) concern mapping.

        Skipped if attune.workflows can't be imported (e.g., not
        installed in the test env). Drift caught at CI level where
        the package is always available.
        """
        try:
            from attune.workflows import list_workflows
        except ImportError:
            pytest.skip("attune.workflows not importable in this env")

        from attune.ops.workflow_concern import _WORKFLOW_CONCERNS  # type: ignore[attr-defined]

        registered = {w["name"] for w in list_workflows()}
        mapped = set(_WORKFLOW_CONCERNS.keys())

        missing = registered - mapped
        assert not missing, (
            f"Registered workflows missing concern mapping: {sorted(missing)}. "
            f"Add them to _WORKFLOW_CONCERNS in src/attune/ops/workflow_concern.py "
            f"and update the assignment table in decisions.md."
        )


# ---------------------------------------------------------------------------
# All concerns is exactly 7 + has the expected names
# ---------------------------------------------------------------------------


class TestAllConcerns:
    """The exported ``ALL_CONCERNS`` tuple is the authoritative list."""

    def test_exactly_seven_concerns(self):
        assert len(ALL_CONCERNS) == 7

    def test_expected_names(self):
        assert set(ALL_CONCERNS) == {
            "review",
            "test",
            "docs",
            "refactor",
            "audit",
            "meta",
            "other",
        }

    def test_order_is_stable(self):
        """The tuple's order matters — chip toolbar renders in this
        order. If the order changes, the wireframe + chip template
        order must change too.
        """
        assert ALL_CONCERNS == (
            "review",
            "test",
            "docs",
            "refactor",
            "audit",
            "meta",
            "other",
        )
