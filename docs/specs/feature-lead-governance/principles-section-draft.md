# DRAFT — Principles section for the collaboration contract master

**Status:** DRAFT for chair review — NOT ruled, NOT projected.
**Author:** lead (2026-07-29 session), per the queued chair float
("expand a principles document") and the lead counter-shape: every
principle CITES its enforcer; anything without one is marked
**aspirational** so the gap is visible instead of implied.
**Target on approval:** a `### Principles` section in
`content/collaboration/contract.md` (the projector master), landed
via `scripts/project_collaboration_contract.py` so all three
provider surfaces carry it.

---

## Proposed section text

### Principles

Every principle below names its enforcer — the ratchet, gate, hook,
or drift-guard test that makes it true without anyone remembering
it. A principle marked **aspirational** has no mechanical enforcer
yet: treat it as binding discipline, and treat adding its enforcer
as pickable work.

1. **The receipt beats the promise.** "Configured", "registered",
   and "exited 0" are claims; evidence of the user-visible behavior
   is the receipt. Delegated lanes declare their receipt type at
   launch and the lead re-runs receipts centrally.
   *Enforcer: **aspirational** (ruled discipline —
   `.claude/rules/attune/decision-routine.md` delegation receipts
   + this contract's Verification receipts section; no mechanical
   gate).*

2. **The code is the contract; spec text is a hypothesis.** Before
   executing any spec-named scope, grep the code for the property
   the phase targets and execute against THAT set.
   *Enforcer: **aspirational** (lessons-core rule; no gate can
   check intent — partially backstopped by drift guards below).*

3. **One source, projected — never hand-edited twins.** Skills,
   the collaboration contract, help pages, and docs feature pages
   are projections; edit the master and re-project.
   *Enforcers: `tests/unit/plugins/test_sync_agents_skills.py`
   (skills mirror), `tests/unit/scripts/
   test_project_collaboration_contract.py` (contract blocks),
   `tests/unit/lessons/test_core_mirror.py` (lessons core),
   `tests/unit/authoring/test_projection_drift.py` (authored
   projections) — all fail CI on drift.*

4. **Dangerous constructs are blocked, not discouraged.** No
   `eval`/`exec`, no unvalidated file paths, no bare `except`.
   *Enforcers: `src/attune/hooks/scripts/security_guard.py`
   (PreToolUse block on eval/exec), pre-commit detect-secrets,
   security tests required for file-op code (reviewed, not
   gated — that half is **aspirational**).*

5. **Coverage is a floor, not a goal.** Changed code carries
   ≥80% coverage; the local bar is 85%.
   *Enforcers: `codecov.yml` project+patch gates (80%),
   `tests/unit/ci/test_workflow_yaml.py::
   test_coverage_threshold_is_at_least_80` (the threshold itself
   is drift-guarded).*

6. **CI spends attention, never money.** Per-push/PR workflows run
   keyless (`ANTHROPIC_API_KEY: ""`); the real secret lives only in
   allowlisted, manually-dispatched or budget-capped jobs.
   *Enforcers: `tests/unit/ci/test_ci_spend_guard.py` (secret refs
   allowlisted, non-allowlisted assignments must be `""`),
   `tests/unit/ci/test_workflow_yaml.py`
   (timeouts/pinning/concurrency).*

7. **A failed gatekeeper fails the gate.** A security auditor that
   errors or goes missing fails the Security gate — absence is not
   a pass.
   *Enforcer: sentinel semantics pinned by
   `tests/unit/agents/test_release_prep_team_orchestration.py`
   (chair-ruled 2026-07-29).*

8. **Docs may not cite fiction.** A doc that names a symbol which
   no longer imports fails CI.
   *Enforcers: `doc-import-audit` CI job +
   `tests/unit/test_generated_doc_import_drift.py`; wiring claims
   checked by the `wiring-audit` job.*

9. **Identity and brand drift are ratcheted.** Legacy identifiers
   and retired framing cannot re-enter the tree.
   *Enforcers: G5 brand-drift pre-commit gate +
   `tests/unit/gates/test_brand_drift.py`,
   `tests/unit/gates/test_claim_drift.py`.*

10. **Context is budgeted.** Always-loaded rule bodies fit a
    byte budget; everything else is JIT-recalled via the index.
    *Enforcer: `tests/unit/rules/test_rules_residency_budget.py`.*

11. **Seats advise; the chair promotes; the lead integrates.**
    Cross-provider seats are advisory, the integrating lead owns
    synthesis and central receipt re-runs below the chair, and only
    the chair promotes (R8).
    *Enforcer: **aspirational** (governance ruling, D8/D9 +
    R8 — carried by this contract's text on all provider surfaces;
    inherently procedural).*

12. **Memory is derived, never authored in the serving layer.**
    Durable findings land in the tracked corpus (lessons, spec
    decisions, handoffs); Redis indexes are hydrated projections.
    *Enforcer: **aspirational** (contract text; hydration
    overwrites hand-written keys on the next run, which is a
    ratchet-by-reconstruction, but nothing blocks the direct
    write).*

13. **Simpler is better.** Three clear lines beat one clever
    abstraction: flatten nested conditionals, inline one-use
    helpers, prefer stdlib over custom abstractions, and review
    every change for complexity it didn't need.
    *Enforcer: **aspirational** (ratified design philosophy,
    carried in every provider surface's instructions; simplicity
    is judged in review, not gated).*

14. **A handoff is context, not authority.** The receiving agent
    verifies a handoff against the current Git state and tests
    before continuing; the current worktree, Git state, and test
    results are the shared truth, never hidden chat context.
    *Enforcer: **aspirational** (contract text — Shared truth +
    Handoffs sections; inherently procedural, since the check IS
    the receiving agent's first action).*

15. **Degrade gracefully around the memory layer.** When Redis or
    the memory index is unreachable, skip recall and proceed —
    work is never blocked on the memory layer, and recalled
    results are context to verify, not authority.
    *Enforcers: `tests/unit/memory/test_session_stash.py` (backend
    resolution failure degrades to None, never raises),
    `tests/unit/test_mcp_memory_tools.py` (memory tools degrade
    gracefully when the layer is absent). The SessionStart hydrate
    hook's own fail-open path is untested — the remaining
    **aspirational** half.*

---

## Notes for the chair (not part of the section)

- **The section enforces itself:**
  `tests/unit/gates/test_principles_citations.py` parses the
  numbered principles, extracts every backtick-cited repo path
  (including `path::test_name` forms), and fails if any cited
  enforcer no longer exists — principle 3 applied recursively. On
  ratification the test's target constant moves from this draft
  file to the contract master (one-line change, noted in the
  test).
- Enforcer gaps worth pickable-work rows: (a) a path-validation
  gate for file-op code (principle 4's second half — chip filed);
  (b) a fail-open test for the SessionStart hydrate hook
  (principle 15's second half). Two suspected gaps turned out
  already enforced (`test_ci_spend_guard.py` for keyless CI;
  `test_session_stash.py` for memory-layer degradation) — the
  grep-for-existing-enforcer rule caught both before duplicates
  were built.
- Deliberately NOT included: style rules (black/ruff enforce
  themselves), and anything that is one session's preference
  rather than a cross-provider invariant.
- If approved, the section lands in the master + one projector
  run; the draft file is then deleted (single-source rule,
  principle 3, applied to itself) and the citations test is
  re-pointed at the master in the same PR.
