# Decisions: Memory NodeType Friction Log

Running log of friction points (and good fits) observed while using
the 4 curated `NodeType` members (`USER_CONTEXT`, `FEEDBACK`,
`PROJECT_CONTEXT`, `REFERENCE`, PR #1207) for real curated-memory
writes. See `requirements.md` for the graduation criteria (R4).

Entry format: date, what was being recorded, which type/field, fit
(clean / friction), notes.

---

## Fix notes (not friction entries)

Bugs found in the mechanism itself, before any real dogfood usage,
don't belong in the friction log proper (R1 scopes friction to real
curated-memory writes) — logged here instead so future readers don't
mistake a pre-existing implementation gap for a taxonomy-fit problem.

- **2026-07-01 — `add_finding()` dropped `status` entirely.** A
  `/code-review` of PR #1207 found that `MemoryGraph.add_finding()`
  never read `finding["status"]` — every node created through the
  real public API silently got the dataclass default `status="open"`,
  regardless of what the caller passed. This predates #1207, but it
  falsified the PR's stated design (curated-memory nodes get
  `active`/`superseded`/`stale`) for every node actually written via
  `add_finding`, and the new regression test
  (`test_loads_curated_memory_node_via_real_add_finding`) didn't catch
  it because it asserted `.type` but not `.status`. Fixed:
  `add_finding` now passes `status=finding.get("status", "open")`
  ([graph.py](../../../src/attune/memory/graph.py)); the regression
  test now asserts `status == "active"` on reload
  ([test_graph.py](../../../tests/unit/memory/test_graph.py)). Not a
  taxonomy/field-fit signal — a plain implementation bug, caught
  before real usage began.

---

_(no friction entries yet — log starts on first real `add_finding()`
call using one of the 4 new types)_
