"""Pins for workflow catalog visibility (chair-directed 2026-08-24).

Known-broken workflows are hidden from user-facing catalogs until
their probes pass; argument-requiring workflows are hidden from the
dashboard only. Hiding is presentation-only — the registry resolves
every name.
"""

from __future__ import annotations

from attune.workflows import get_workflow
from attune.workflows.visibility import (
    DASHBOARD_HIDDEN_WORKFLOWS,
    HIDDEN_WORKFLOWS,
    is_hidden,
    visible_entries,
)


def test_hidden_sets_carry_reasons() -> None:
    for name, reason in {**HIDDEN_WORKFLOWS, **DASHBOARD_HIDDEN_WORKFLOWS}.items():
        assert reason.strip(), name


def test_hidden_names_still_resolve_in_registry() -> None:
    # Hiding is presentation-only: probes, API launches, and the ops
    # runner must keep working.
    for name in {**HIDDEN_WORKFLOWS, **DASHBOARD_HIDDEN_WORKFLOWS}:
        assert get_workflow(name) is not None


def test_catalog_surface_hides_broken_only() -> None:
    assert is_hidden("test-gen")
    assert is_hidden("doc-gen")
    assert not is_hidden("fix")  # arg-requiring: fine on CLI/MCP
    assert not is_hidden("security-audit")


def test_dashboard_surface_hides_both_tiers() -> None:
    assert is_hidden("test-gen", surface="dashboard")
    assert is_hidden("fix", surface="dashboard")
    assert is_hidden("rag-code-gen", surface="dashboard")
    assert not is_hidden("security-audit", surface="dashboard")


def test_visible_entries_filters_by_surface() -> None:
    entries = [{"name": n} for n in ("security-audit", "test-gen", "fix")]
    assert [e["name"] for e in visible_entries(entries)] == ["security-audit", "fix"]
    assert [e["name"] for e in visible_entries(entries, surface="dashboard")] == ["security-audit"]


def test_ops_dashboard_list_respects_dashboard_tier() -> None:
    from attune.ops import data

    visible = {w.name for w in data.list_workflows()}
    everything = {w.name for w in data.list_workflows(include_hidden=True)}
    if not everything:  # registry unavailable in this environment
        return
    hidden = everything - visible
    assert hidden == set(HIDDEN_WORKFLOWS) | set(DASHBOARD_HIDDEN_WORKFLOWS)
