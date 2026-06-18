# Product Direction Review — Assessment

**Status:** assessment (2026-06-17) — decisions pending Patrick
**Owner:** Patrick (+ agent)
**Type:** strategic assessment / decision record (not a build spec)
**Trigger:** Patrick asked for a critical review of attune-ai
(2026-06-17 session).

> This is a deliberately single-file artifact. A multi-file spec
> here would be an instance of Finding 3 (scaffolding outweighing
> product). It records evidence and the decisions to make — it does
> not itself schedule work.

---

## Verdict

Not a competence problem. The engineering is unusually disciplined
(privacy-first telemetry, a real institutional-knowledge system,
security rigor). The problem is that the competence is pointed at a
**demand hypothesis that has never been tested**. ~184k lines of
product and ~349k lines of tests, built solo at ~10 commits/day for
90 straight days, for a user base that cannot currently be observed.
Findings 2–6 are downstream of Finding 1.

---

## Evidence (ground truth, 2026-06-17)

| Metric | Value | Source |
|--------|-------|--------|
| Product code | 183,768 LOC / 712 files | `wc` src/attune |
| Test code | 349,399 LOC / 968 files / ~20,160 `test_*` | `wc` tests |
| Test-to-product ratio | 1.9 : 1 | derived |
| Commits, last 90 days | 882 (~9.8/day, every day) | `git log` |
| Last 200 commits: `feat` | 27 (13.5%) | `git log %s` |
| Last 200: test+docs+chore+ci | 148 (74%) | `git log %s` |
| Last 300 commits: ci/hang/flake/runner | 54 (~18%) | `git log` |
| Open spec directories | 49 (most partial/draft/deferred) | `ls docs/specs` |
| `lessons.md` | 9,356 lines | `wc` |
| Dependencies | 311 lines in pyproject | `grep` |
| Version | 8.5.0 (young project) | pyproject |
| Human authors, all time | 1 (Patrick: 197 of last 200) | `git log %an` |
| attune-ai downloads | 636/week, 2,836/month | usage-signals D1 |
| Real behavioral signal | ~0 (opt-in, default-OFF telemetry) | `usage_ping.py` |

The download numbers come from the [usage-signals](../usage-signals/)
spec, whose own headline interpretation is that **our CI is the
biggest "user"** — i.e. downloads are not adoption.

---

## Ranked findings

### 1 — Optimizing a function that can't be measured (existential)

`usage_ping.py` is well-built (frozen 8-key payload, `DO_NOT_TRACK`
honored, default-OFF) and therefore near-zero signal: opt-in
default-off telemetry over an unknown user base transmits nothing in
practice. The only "users" number is the pepy badge, which counts CI,
mirrors, and bots. Every prioritization call across 49 specs, 70
workflow files, the ops dashboard (10k LOC), the socratic subsystem
(14k LOC) is made on taste, not evidence. This is the root cause of
2–6.

**Proof that resolves it:** 5 conversations with humans who ran
attune-ai on a real repo. Not the phone-home endpoint (passive, slow,
opt-in) — actual calls. If 5 can't be found, that is the finding.

### 2 — The test suite guards the wrong thing

1.9 : 1 test-to-code is ballast at this stage, not rigor. The proof is
the project's own blocker: the SDK 0.2 migration is stuck because
17,857 mocked tests are green while real integration systematically
breaks (`project_sdk_0_2_migration_blocked`). 20,160 tests means every
refactor drags a 349k-line anchor, and the suite generates work (70 of
the last 200 commits are `test`). Direction: keep a thin layer of real
non-mocked round-trip tests; stop ratcheting coverage on mocked
internals.

### 3 — Scaffolding outweighs product

13.5% of recent commits add features. The rest maintain the machine
that maintains the machine: a 9,356-line lessons file, 49 specs, 17
hooks, 14 rule docs, 22 CI workflows, 500 docs files, 108 scripts, and
a spec-status-self-truthing spec whose job is to make the other specs
stop lying about their status. MEMORY.md overflowed its own 200-line
limit. Some of this is real leverage (the lessons corpus); the line has
been crossed where process competes with the product for hours.

### 4 — Identity blurred across six packages

The README opens with four pillars (workflows, memory, RAG grounding,
verification) and points at attune-gui, attune-rag, attune-author,
attune-help, attune-lite, attune-redis. That is a platform, the hardest
thing for a solo founder pre-PMF to sell, position, or maintain. 311
dependencies is the cost of that ambition. One sharp tool that 20
people love beats four pillars zero people have evaluated.

### 5 — Version 8.5.0 is major-version inflation

Eight majors in a young project means frequent breaking changes — a tax
levied on users who can't be seen, for a stability contract nobody
relies on. Signals churn, not maturity.

### 6 — CI firefighting is a recurring tar-pit

~18% of recent commits touch CI/hangs/flakes/runners. The project's own
global rules name a "tar-pit trip-wire" for exactly this. The
runner-hang saga (H1–H4, multiple captured frames) is real engineering
and almost certainly not worth its cost relative to validating demand.

---

## Decisions to make (pending Patrick)

These are proposals, not adopted. Record the call inline with a date
when made.

- **DEC-1 — Freeze new product surface for two weeks.** No new specs,
  workflows, or pillars. *(pending)*
- **DEC-2 — Run 5 user conversations.** People who ran attune-ai on a
  real repo. Owner: Patrick. *(pending)*
- **DEC-3 — Pick the one pillar** those users actually used; let the
  others idle. *(pending)*
- **DEC-4 — Stop the test/coverage ratchet;** real round-trip tests
  only. *(pending)*
- **DEC-5 — Time-box CI flake-chasing;** mark unresolved hangs
  known-flaky and move on. *(pending)*

---

## Counterweight (kept honest)

The talent here is real and rare: the privacy engineering is exemplary
and done, the lessons system is genuine institutional memory, security
discipline is mature. None of that is the problem. The problem is aim,
not skill. The highest-value artifact this month is the email that gets
Patrick on a call with a user.

---

## Related

- [usage-signals](../usage-signals/) — download baseline + opt-in ping
  design; already proves downloads ≠ adoption.
- `project_telemetry_local_only` memory — telemetry state and the
  "talk to users" conclusion.
- `project_next_work_sequence` memory — the backlog this assessment
  argues should be paused pending DEC-2.
