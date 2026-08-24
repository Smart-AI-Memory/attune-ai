"""Chair-ruled reliability badges (roundtable q-workflow-fleet-health-001).

Containment until the fail-closed fixes land: the dashboard must warn
on workflows known to report success their execution does not support.
The fixing PR removes the workflow's ``RELIABILITY_NOTICES`` entry and
updates this test.
"""

from __future__ import annotations

from attune.ops.data import RELIABILITY_NOTICES, WorkflowEntry, list_workflows


def test_noticed_workflows_are_flagged():
    # 2026-08-24: the fail-closed fixes landed (#2222 secure-release,
    # #2209 health-check) with live probe receipts, so their containment
    # notices were removed per this file's own docstring contract. The
    # dict stays as the mechanism for future containment entries; any
    # entry present must carry the warning shape.
    assert set(RELIABILITY_NOTICES) == set()
    for name, text in RELIABILITY_NOTICES.items():
        assert "Known issue" in text, name


def test_list_workflows_carries_the_notice():
    entries = {w.name: w for w in list_workflows()}
    if not entries:  # registry unavailable in this environment
        return
    for name in RELIABILITY_NOTICES:
        assert name in entries, f"{name} missing from the registry"
        assert entries[name].notice == RELIABILITY_NOTICES[name]
    # And un-noticed workflows carry an empty notice.
    clean = next(n for n in entries if n not in RELIABILITY_NOTICES)
    assert entries[clean].notice == ""


def test_workflow_entry_notice_defaults_empty():
    e = WorkflowEntry(name="x", description="d", stages=0, tier_map={})
    assert e.notice == ""
