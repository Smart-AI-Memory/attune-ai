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

---

## D5 — Hook MUST run with `--branch` coverage (2026-05-27)

**Question:** does the pre-push hook run `coverage` in
line-coverage-only or line+branch mode?

**Decision:** **Branch coverage required.** The hook invokes
`coverage run --branch -m pytest <tests>`.

**Rationale:** PR #485's codecov failure was 2 partial branches
flagged at 99.74% patch coverage while local line coverage
reported 100%. The gap: codecov runs branch coverage
(`[coverage:run] branch = true`), and the local
`coverage run -m pytest` (without `--branch`) doesn't. So an
agent running the local-coverage-default workflow sees 100%
and pushes; codecov sees 99.74% and rejects.

If the pre-push hook is going to close this loop, it MUST
match codecov's mode. Line-only would re-introduce the same
discipline gap this spec is built to fix.

Implementation: `scripts/coverage_gate/check_patch.py` passes
`--branch` to `coverage run` and parses the branch-coverage
columns (`Branch`, `BrPart`, `BrMissing`) from the report.
Threshold check intersects touched lines AND touched branches
with the executed set.

**Reference:** PR #485's second codecov-failure cycle
(2026-05-27); see commit c4099ac2 which closed the partials
that line coverage missed.

---

## D6 — Threshold scope: patch-level, not file-level (2026-05-27)

**Question:** does the pre-push hook gate at the patch level
(matches codecov: aggregate coverage of all lines touched in
the push) or at the file level (each touched file must
individually meet the threshold)?

**Decision:** **Patch-level.** The hook computes
`(executed lines in patch) / (total lines in patch)` across
all touched files and compares against the 90% threshold.
Individual files inside a patch may sit below 90% as long as
the aggregate clears the bar.

**Rationale:**

1. **Matches codecov's gate.** Codecov's `codecov/patch`
   check is patch-level. The pre-push hook's whole purpose
   is to catch what codecov will reject — running a stricter
   file-level gate would block pushes that codecov would
   accept, creating the inverse drift this spec is built to
   eliminate.
2. **PR #484 is the worked example.** That PR shipped 92.05%
   patch coverage with `help_regen.py` at 89.25% — codecov
   passed, the work was meaningfully covered, and a
   file-level gate would have blocked it without producing
   a real quality improvement. Borderline files inside
   strong patches are normal; they should not block a push
   when the overall surface is well-tested.
3. **Hot files self-correct over time.** A file that
   chronically sits at 89% will eventually be touched by a
   commit that's small enough that 89% is the patch result,
   not just a file-within-a-patch result. The hook fires
   then. Over a series of commits, weak files self-correct
   because the patch-level gate forces incremental
   improvement at each touch.
4. **File-level is a knob we can add later.** If the
   patch-level gate proves insufficient (e.g. a feature ships
   over many small commits and persistently keeps one file
   at 70%), the hook can grow an opt-in
   `--per-file-threshold` flag. Default stays patch-level.

**Implication for Phase 1 design:** the
`scripts/coverage_gate/check_patch.py` script computes one
aggregate ratio. No per-file breakdown in the failure
message beyond "these files contributed missing lines",
ranked by missing-line count, for diagnostic value only —
not as separate gate conditions.

**Reference:** opportunity surfaced 2026-05-27 during
post-merge review of PR #484 (`docs/specs/ops-help-page`);
locked here so Phase 1 implementation doesn't re-litigate.

---

## 2026-07-20 — CLOSED stale on premise drift (chair: Patrick)

Ruled in the chair-rulings sitting. The motivating premise —
docs say 80% while the codecov patch gate enforces ~90%, so
agents targeting the documented bar get rejected by CI (PR #485)
— has INVERTED since the 2026-05-27 draft: today codecov's patch
gate is 50% (±5%) with project at 80% (±2%), `pyproject.toml`
`fail_under=85`, and CLAUDE.md still says 80%. The strict-gate
pain is gone; the residual misalignment runs the OTHER way (a
patch can land at 50% while docs claim an 80% floor). Controls
3–4 were partially overtaken by process shipped since (delegation
receipts ratified 2026-07-14; the living test-quality-program).
Ruling: close the spec; the one live residue — aligning the
80/85/50 numbers to one story — is a small standalone hygiene
fix, chipped separately, not a four-control spec.
