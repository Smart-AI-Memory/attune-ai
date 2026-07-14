# Spec: Enforcement vs Documentation for CLAUDE.md Lessons

> `CLAUDE.md` is currently 6500+ lines of append-only lessons.
> Most are reference documentation — interesting once, rarely
> recurring. A small subset are recurring high-cost failure
> patterns that documentation alone hasn't prevented (proven
> by the 2026-05-31 session where I wrote a lesson and
> immediately violated it). This spec separates the two,
> proposes criteria for promotion to mechanical enforcement,
> and establishes the size discipline + retirement metrics
> that keep the enforced set tractable.

**Status:** complete (2026-05-31) — framework approved (cap=10 enforcements) and validated by the first enforcement (worktree-path-guard hook + metrics log, PR #521); all acceptance criteria met; further enforcements ship as out-of-scope follow-up PRs
**Created:** 2026-05-31
**Owner:** —
**Related:**
- The 2026-05-31 morning session that surfaced the framing
  (see PRs #514-#519, lessons appended in #519)
- [`spec-status-self-truthing`](../spec-status-self-truthing/) —
  similar shape: a meta-spec that improves how we operate
  rather than shipping user-facing code

---

## Phase 1: Requirements

**Status:** approved (2026-05-31; see [decisions.md](./decisions.md))

### Problem statement

`CLAUDE.md` lessons are written under the implicit assumption
that "I read this lesson at session start, so I won't repeat
the mistake." That assumption is wrong:

1. **Volume defeats recall.** With 6500+ lines of lessons, no
   specific lesson is salient at the moment of action. I scan
   the file at SessionStart but can't actively hold every lesson
   in working memory while doing the task.
2. **Documentation and action are different cognitive moves.**
   Writing a lesson is a reflective, summarizing act. Catching
   yourself about to repeat the lesson while in flow requires a
   different mental gear — one that documentation alone doesn't
   develop.
3. **Empirical evidence:** on 2026-05-31, I wrote a lesson about
   "Write to bare repo absolute path from worktree pollutes main
   checkout" — and within the same session, while editing the
   very file containing that lesson, I made the exact mistake
   the lesson warns against. The lesson did not prevent the bug
   it documented.

Today, the project treats every lesson identically: append-only,
re-read each session, equally weighted. This conflates two
different artifacts:

- **Documentation** — captures a one-time insight or a quirk for
  future reference. Most lessons. Cost of not enforcing: minor
  re-discovery if pattern recurs.
- **Enforcement candidates** — recurring high-cost failure
  patterns where a mechanical check would prevent the repeat.
  A small subset of lessons. Cost of not enforcing: real time
  loss, state loss, or user-trust loss every time the pattern
  re-fires.

### Scope

**In scope:**

- Define **promotion criteria** that distinguish documentation
  from enforcement candidates.
- Define **mechanical-enforcement shapes** appropriate for the
  attune-ai codebase (pre-tool hooks, pre-commit hooks, shell
  wrappers).
- Define **retirement criteria** so the enforcement set doesn't
  grow indefinitely.
- Define **list-size discipline** — what happens when the
  enforced set exceeds a soft cap.
- Define **metrics** that inform retirement decisions.

**Out of scope:**

- Restructuring `CLAUDE.md` itself. Documentation stays where
  it lives.
- Building any specific enforcement (each is its own follow-up
  PR; the first one — pre-Write worktree-path hook — is queued
  separately).
- Cross-project enforcement (other attune-* repos). This spec
  applies to attune-ai. Other repos can adopt the framework
  later if useful.

### Promotion criteria

A lesson is a candidate for promotion from documentation to
mechanical enforcement when ALL three of:

1. **Recurrence** — Hit ≥2 times in distinct sessions (not just
   twice in one session). The "distinct sessions" qualifier
   matters: a same-session double-hit reflects in-flight
   forgetting, while cross-session recurrence reflects a
   genuinely sticky pattern.
2. **Cost** — Each occurrence costs ≥10 min recovery time OR
   causes irrecoverable state (lost work, leaked secret,
   broke main, misled the user). "Annoying" doesn't qualify;
   "destructive or costly" does.
3. **Mechanical check available** — A pre-flight command,
   hook, env-var validation, or alias exists that catches
   the bad action before it lands. "Be more careful" is NOT
   a mechanical check. If the only available remediation is
   "remember harder," it stays documentation.

A lesson failing any one criterion stays documentation. A
lesson meeting all three becomes an enforcement candidate
requiring Patrick's approval before promotion.

### Mechanical-enforcement shapes

Appropriate shapes for attune-ai's environment:

| Shape | Use when | Example |
|---|---|---|
| **PreToolUse hook** | Catching a bad agent action before it executes | Pre-Write hook validating target path matches session worktree |
| **Pre-commit hook** | Catching a bad commit before it lands | `regenerate-help-templates` skip when the regenerated content is stub-style |
| **Shell wrapper / alias** | Catching a bad CLI invocation | `git pull` wrapper that handles `pull.rebase=true` on dirty trees |
| **Test as drift-guard** | Catching a drift class in CI | `test_all_skill_dirs_referenced_by_attune_hub` |
| **Env-var gate** | Catching a misconfiguration at runtime | `ATTUNE_OPS_SESSIONS_LLM=0` for the budget-cap off-switch |

The shape choice depends on where the dangerous action
originates. Hooks are best when the agent is the source. Shell
wrappers are best when CLI invocations are the source. Tests
are best for static drift.

### List-size discipline

**Soft cap: 10 active enforcements.**

When a new candidate would push the active list past 10:

1. Patrick is notified explicitly: "Adding `<new>` would put
   active enforcements at 11. Approve, or pick a retirement
   candidate from the current list?"
2. He may approve the growth (active count rises) OR retire one
   to make room.
3. The system surfaces current retirement candidates (ranked by
   retirement metrics — see below) to inform the choice.
4. The cap is **advisory**, not enforced. If 12 enforcements all
   pay for themselves, that's the right number. The trigger is
   *attention*, not blocking.

### Retirement metrics

Each active enforcement carries metadata tracked over time:

| Metric | What it measures | Retirement signal |
|---|---|---|
| **Hit rate** | Number of times the enforcement fired and prevented a real bad action | Dropping toward zero over rolling window (e.g. 0 hits in 30 days) |
| **False-alarm rate** | Number of times the enforcement fired on actions that were actually OK | Rising above some threshold (e.g. >20% of fires are false) signals tuning needed or retirement |
| **Override count** | Number of times Patrick explicitly bypassed the enforcement | Rising signals the enforcement isn't well-tuned |
| **Days since last hit** | Time since the enforcement last prevented a real bad action | >30-60 days is a retirement candidate |

Retirement candidates are surfaced in a periodic review
(weekly or monthly cadence, exact shape TBD). Patrick decides
to retire or keep. Retired enforcements become passive
documentation — the lesson stays in `CLAUDE.md` but the
mechanical check is removed.

### Acceptance criteria

This spec is "done" when:

- [x] Promotion criteria documented.
- [x] List-size discipline documented (soft cap 10 + notification
  on growth).
- [x] Retirement metrics enumerated.
- [x] At least one concrete enforcement is in design or
  implementation (the pre-Write worktree-path hook is the
  validating first case — see Phase 4).

### Out of band

The pre-Write worktree-path hook (the first enforcement)
ships in its own PR after this spec lands. Its existence
validates the framework: if we can't ship one mechanical
enforcement using these criteria, the framework is wrong.

---

## Phase 2: Design

**Status:** N/A — see decisions.md.

This is a meta-spec; the framework itself is the design. The
concrete shape for any individual enforcement is in that
enforcement's own spec/PR. The first one — pre-Write
worktree-path hook — is in its own follow-up.

---

## Phase 3: Tasks

**Status:** see decisions.md follow-up plan.

The initial enforcement set:

1. **Pre-Write worktree-path hook** (this session's follow-up
   PR) — closes the bare-repo-absolute-path bug.
2. **Pre-commit `.help` template regen skip** (future) — closes
   the stub-overwrite class.
3. **`git pull` wrapper** for `pull.rebase=true` on dirty trees
   (future) — closes the recurring stash-required pattern.

Each ships as its own PR with its own metrics tracked.

---

## Phase 4: Implementation

**Status:** in flight via follow-up PR (pre-Write worktree-path
hook).
