# MemoryGraph Value-Gate — Decisions

## D1 — Straight removal as `feat!:` → 10.0.0 (2026-07-05)

**Decision:** Remove outright in one PR as a breaking change,
riding the next major (10.0.0). No deprecation window.

**Options considered:**

- **Straight removal → 10.0.0 (chosen).** Empathy precedent
  (9.0.0 deleted EmpathyOS outright). Zero usage evidence — 0
  telemetry invocations, no documented user-facing story — means
  a deprecation window protects nobody. Git history is the
  archive.
- Deprecate in 9.8, remove at the next major. Safest for unknown
  pip users, but carries dead code longer and needs a second PR.
- Keep. Overruled — four removal signals fire.

A module-level `__getattr__` in `attune.memory` raises a pointed
error for the removed names (naming the curated-file successor),
so external breakage is informative, not silent.

**Decided by:** Patrick, via AskUserQuestion after impact
walkthrough.

## D2 — Full drag scope (2026-07-05)

**Decision:** The whole dead-path web goes with the graph: the
triad (`graph.py`, `nodes.py`, `edges.py`), `MemoryAwareAgent` +
the never-set `memory_graph_*` factory knobs, the `memory_graph`
health check, their tests, and the doc pages — one coherent PR so
the doc-import gate stays green.

**Alternative rejected:** graph-triad-only (smaller diff, but
leaves knowingly-dead wrapper code and config knobs behind
except-ImportError guards).

**Decided by:** Patrick, via AskUserQuestion.

## D3 — `agent_factory` itself stays (2026-07-05)

**Decision:** Only the memory wrapper is removed. `agent_factory`
is cited as a working pattern in the removing-dead-code rule; its
value-gate, if ever warranted, is a separate exercise with its own
evidence pass.
