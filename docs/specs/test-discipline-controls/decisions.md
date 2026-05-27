# Decisions: Test Discipline Controls

> Decision log. Append-only — each entry stamped with date and
> the question it resolves.

**Status:** living document
**Created:** 2026-05-27

---

## D1 — TDD as policy: REJECTED (2026-05-27)

**Question:** should we adopt strict TDD (red-green-refactor) as
the development discipline for this codebase?

**Decision:** No. Adopt the four mechanical controls in
[`requirements.md`](requirements.md) instead.

**Rationale:**

1. **AI agents fake the red phase.** With a human in the loop,
   TDD's value comes from imagining the system, writing a test
   that *requires* it, then building. With an AI agent in the
   driver's seat, the "see red, then build" discipline depends
   on the agent reading the test failure and reasoning about it
   — but agents (notably this one) tend to write the test then
   write the code that exactly satisfies it in the same edit
   window, losing the design pressure. The discipline's value
   evaporates and the cost stays.
2. **Spec-driven development is already this codebase's design
   layer.** `/spec` produces requirements + design + tasks + XML
   prompts with `<validation>`. That IS the up-front thinking
   layer TDD claims. TDD on top of /spec is two parallel design
   structures competing for the same cognitive slot, not
   additive.
3. **Cost: 2-3× more LLM turns per task.** Strict TDD =
   test-red → code → test-green → refactor → test-green. For a
   Phase-1-size task, ~200 tool calls instead of ~50.
   Cost-per-value-added is worst at the moment of highest churn
   (early in a spec, when the API moves).
4. **The four-control proposal addresses the same failure mode
   at lower cost.** The actual gap on PR #485 was (a) happy-
   path-only tests and (b) no measurement gate before push. A
   pre-push coverage hook + branch-enumeration habit + selective
   test-first for new-API modules + regression-first for `fix:`
   commits closes both without imposing red-green on every task.

**What we'd reconsider TDD for:** if patch coverage on agent-
driven PRs stays below 90% three months after this spec lands,
re-open the question. The remaining gap would suggest the
controls are insufficient.

**Reference:** session conversation 2026-05-27 leading to this
spec; PR #485 review where the gap surfaced.

---

## D2 — Coverage bar single source of truth (2026-05-27, pending)

**Question:** where does the patch-coverage threshold live so
the hook + docs + CI can't drift?

**Decision:** **PENDING** — defer to Phase 1 inspection of
current codecov config. Candidates:

- (a) `codecov.yml` — already load-bearing for CI
- (b) `pyproject.toml [tool.coverage.report] fail_under` — already
  on the box, tools respect natively
- (c) `.claude/coverage-bar.json` — new file, both hook + docs
  read it

Lean: (b). Decided in Phase 1 when we read the current
configuration and pick the simplest write path.

---

## D3 — Pre-push hook: opt-in or default-on (2026-05-27)

**Decision:** opt-in via the project's existing settings.json
hook-installer mechanism.

**Rationale:** forcing a `pre-push` onto every contributor's
machine is heavy-handed and breaks non-developer worktrees (CI
runners, ephemeral build agents, fresh clones used for read-only
work). The hook ships in the repo; contributors enable it once
via `attune setup hooks` (or equivalent). Documented in CLAUDE.md
as part of the Phase 1 work.

---

## D4 — `feat:` commits without new test coverage (2026-05-27)

**Question:** does a `feat:` commit that's pure refactor (no new
lines) need to satisfy the coverage gate?

**Decision:** the gate is patch-coverage-based, so refactors that
don't add new lines pass by definition (denominator is 0 →
coverage trivially passes). Dead-code removal also passes
trivially. No special-casing needed in the hook.

**Caveat:** a `feat:` commit that adds 200 lines of code without
tests *and* claims "refactor only" should be reviewed for accuracy
of the claim. Reviewer responsibility, not hook responsibility.
