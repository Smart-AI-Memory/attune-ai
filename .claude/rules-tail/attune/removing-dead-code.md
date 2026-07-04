# Removing Dead Code — Signals and the "Should This Exist?" Gate

**Created:** 2026-06-25
**Source:** interactive-orchestration-access reversal — the catalog +
registry-coverage guards surfaced (and "fixed access to") code that did
not work.

---

## The problem this rule fixes

The discoverability guards (`test_registry_coverage.py`, the `catalog`
skill's `list_capabilities`, the orphan-tool audit) have a one-way
bias: **"registered ⇒ surface it."** They answer *"is every registered
capability reachable by a user?"* but never *"should this capability
exist, and does it actually work?"*

That bias is dangerous in reverse. When a guard reports "this registry
is registered but not surfaced," the reflexive fix is to *add the
surface*. If the underlying engine is dead, you have now spent effort
making broken code more reachable — and shipped a guard that pins the
broken surface in place. This is exactly how the dead wizard-run and
agent-team features shipped: the audit said "surface these," so they
were surfaced, and a "runnable" guard locked them in.

**Before surfacing or "fixing access to" any registered capability,
run the does-it-exist / does-it-work gate below.**

---

## Removal signals (any one is enough to STOP and consider removal)

- **never-worked** — the code is broken against the *current* internal
  APIs (signature drift, deleted dependency) AND has no real end-to-end
  test exercising the costly path. A capability that has never completed
  a real run is a removal signal, not a fix signal.
- **orphaned motivation** — the originating project, use-case, or
  customer is gone. Code carried over from a retired product with no
  current consumer is debt, not a feature.
- **zero usage evidence** — no telemetry, no CLI/MCP/live invocation, no
  caller in the live code paths (only tests and `__init__` exports).
- **stub tell** — self-documented as a stub ("stub", "not yet wired",
  "replaces deleted X", `NotImplementedError`), OR a fake-success
  signature: `success: True` with cost 0, `sdk_used: False`, empty
  findings/output. A function that returns success while doing no work
  is worse than one that raises.
- **surfacing trip-wire** — if making a capability discoverable/runnable
  requires *first fixing broken code* for a feature nobody asked for,
  STOP. The surfacing task has just discovered dead code; switch from
  "add a surface" to "remove the engine."

---

## The gate (run before surfacing OR fixing access)

1. **Find the real run path** and read it end-to-end. Does it call a
   live backend, or a stub / deleted scaffold?
2. **Dogfood it through the REAL path**, not a test fake. A fake that
   omits the costly step (LLM call, network, subprocess) gives false
   confidence — see [[registered-not-working]] in `lessons.md`.
3. **Trace motivation and usage.** Who asked for this? Who calls it now?
4. If two or more removal signals fire, **propose removal** (archive +
   tag) instead of surfacing. Record the reversal in the owning spec's
   `decisions.md`.

A guard should encode this too: only registries with a working,
dogfooded run path belong in the catalog. "Registered" never implies
"should be surfaced."

---

## When general functionality IS wanted later

Generalize a **working** sibling, never resurrect a deleted/stub one.
(Here: `ReleasePrepTeam` / `agent_factory` are working team patterns
threading the same redis/state plumbing as the dead `DynamicTeam` stub —
generalize those, do not revive `SDKAgent`.)

---

## Cross-references

- `.claude/rules/attune/doc-fiction-triage.md` — the pre-flight
  checklist for DOC cleanups: confirm a symbol is actually dead (and
  where its live form lives) BEFORE applying this delete-vs-rewrite gate.
- `.claude/rules/attune/plugin-reference-validation.md` — the forward
  "references resolve" check; this rule is the reverse "should it exist"
  check.
- `tests/unit/plugins/test_registry_coverage.py` — the coverage guards
  this rule constrains.
- `docs/specs/interactive-orchestration-access/decisions.md` — the
  reversal that produced this rule.
