"""Concern bucket derivation for workflow names.

Pure logic — takes a workflow name (string slug like ``"code-review"``)
and returns one of seven concern bucket labels:

- ``review``  — code-review, deep-review, security-audit, bug-predict
- ``test``    — test-gen, test-audit
- ``docs``    — doc-gen, doc-audit, doc-orchestrator
- ``refactor``— simplify-code, refactor-plan
- ``audit``   — discovery-sweep, perf-audit, dependency-check
- ``meta``    — release-prep, secure-release, orchestrated-health-check, health-check
- ``other``   — rag-code-gen, research-synthesis

The authoritative assignment table lives at
[docs/specs/ops-workflows-page-refinement/decisions.md](../../../docs/specs/ops-workflows-page-refinement/decisions.md)
§ "Concern bucket assignment". Pre-committed there before this module
landed, per the existing "Pre-committed decision matrices survive
contact with data" lesson.

Unlike ``spec_lifecycle.py`` (which derives a bucket from runtime
state), concern is a **canonical static property** of the workflow
itself. Each workflow lives in exactly one bucket.

Module is pure — no I/O, no project-root awareness. Mirrors the
``spec_lifecycle.derive_lifecycle()`` shape so the ``/workflows``
route can call it the same way.
"""

from __future__ import annotations

from typing import Literal

# Type alias for the 7-bucket concern enum. Mirrors how
# ``spec_lifecycle`` types the lifecycle bucket — string literals for
# easy JSON serialization without needing dataclasses.
Concern = Literal[
    "review",
    "test",
    "docs",
    "refactor",
    "audit",
    "meta",
    "other",
]

# All valid bucket names, ordered for stable UI rendering. Don't reorder
# without updating the wireframe + template chip order.
ALL_CONCERNS: tuple[Concern, ...] = (
    "review",
    "test",
    "docs",
    "refactor",
    "audit",
    "meta",
    "other",
)

# Authoritative assignment. Pre-committed in decisions.md.
#
# Trade-offs ratified there:
# - bug-predict + security-audit live in `review` (not `audit`) because
#   their UX intent matches review-class workflows: "tell me what's
#   wrong with this code." `audit` is for codebase-wide health surveys.
# - doc-orchestrator lives in `docs` even though it's a meta-workflow.
#   `meta` is reserved for release/health ops; doc-orchestrator is a
#   domain-specific composer.
# - Naming consistency: `audit` is BOTH a bucket name AND a workflow-
#   name suffix (`test-audit`, `doc-audit`, `perf-audit`). These are
#   routed by *purpose*, not name pattern.
_WORKFLOW_CONCERNS: dict[str, Concern] = {
    # review
    "code-review": "review",
    "deep-review": "review",
    "security-audit": "review",
    "bug-predict": "review",
    # test
    "test-gen": "test",
    "test-audit": "test",
    # docs
    "doc-gen": "docs",
    "doc-audit": "docs",
    "doc-orchestrator": "docs",
    # refactor — the code-MUTATING bucket
    "simplify-code": "refactor",
    "refactor-plan": "refactor",
    "fix": "refactor",
    # audit
    "discovery-sweep": "audit",
    "perf-audit": "audit",
    "dependency-check": "audit",
    # meta
    "release-prep": "meta",
    "release-gate": "meta",
    "release-notes": "meta",
    "secure-release": "meta",
    "orchestrated-health-check": "meta",
    "health-check": "meta",
    # other
    "rag-code-gen": "other",
    "research-synthesis": "other",
}


def derive_concern(workflow_name: str) -> Concern:
    """Return the concern bucket for one workflow.

    Args:
        workflow_name: The workflow's canonical slug (e.g. ``"code-review"``).

    Returns:
        One of the 7 ``Concern`` values. Unknown workflow names fall
        through to ``"other"`` — the catch-all bucket also used for
        rag-code-gen and research-synthesis. This is intentional: new
        workflows added without an explicit mapping show up in `other`
        rather than crashing the route. The drift-guard test
        (``test_all_registered_workflows_have_concern``) catches the
        missing assignment in CI.

    Never raises.
    """
    return _WORKFLOW_CONCERNS.get(workflow_name, "other")


def group_by_concern(workflow_names: list[str]) -> dict[Concern, list[str]]:
    """Group a list of workflow names by their concern bucket.

    Returns a dict keyed by concern with workflow-name lists as values.
    Buckets are populated in ``ALL_CONCERNS`` order; empty buckets are
    omitted (callers that want stable ordering should iterate
    ``ALL_CONCERNS`` and use ``.get(concern, [])``).

    Within each bucket the names are sorted alphabetically — matches
    D7's sort decision and keeps output deterministic for testing.
    """
    by_concern: dict[Concern, list[str]] = {}
    for name in workflow_names:
        c = derive_concern(name)
        by_concern.setdefault(c, []).append(name)
    for c in by_concern:
        by_concern[c].sort()
    return by_concern


def concern_counts(workflow_names: list[str]) -> dict[Concern, int]:
    """Return per-concern counts for a list of workflow names.

    All 7 buckets are populated (zero for empty buckets) so the chip
    toolbar can render counts without conditional logic. Mirrors the
    ``/specs`` route's ``bucket_counts`` shape.
    """
    counts: dict[Concern, int] = dict.fromkeys(ALL_CONCERNS, 0)
    for name in workflow_names:
        counts[derive_concern(name)] += 1
    return counts
