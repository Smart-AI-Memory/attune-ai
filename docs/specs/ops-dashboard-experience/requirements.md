# Ops Dashboard Experience — Requirements

**Status:** draft (2026-09-03) — opened on the chair's decision-form
answer ("Open a spec"); no requirement is ruled and no task is
authorized. Discovery is deliberately incomplete: the two seeded
pain points below are chair-picked, and the discovery pass (a
scoping form over the full surface) has not run yet.
**Slug:** `ops-dashboard-experience`
**Provenance:** Patrick uses the ops dashboard (`attune ops`,
`[ops]` extra) daily and named improving it an aspirational goal
(2026-09-02); on 2026-09-03 he picked pain points 1 and 3 from the
candidate list and chose the spec route over a direct fix.
**Budget constraint (binding):** the chair has zero API budget
([project_api_spend_budget]); every phase of this spec must be
implementable and verifiable with no API-billed call — code, tests,
and dashboard fixtures only. Any proposal that needs a paid run to
demonstrate value is out of scope until re-funded.

## Problem

The dashboard is used daily but underserves its own core loop:
paid workflow runs are recorded in a form that cannot be triaged
afterward, and launching the dashboard from anywhere but the main
checkout requires undocumented incantations.

## Seeded pain points (chair-picked 2026-09-02)

**P1 — Run reports lose their findings.**
`~/.attune/ops/runs/<wf>/<id>.json` persists section *titles* with
empty content and an empty `suggestions` list; `/runs/<id>/report`
serves the same truncated object. Re-verified 2026-09-02 on a fresh
run (`code-review/a233ac84e95b`: 5 sections, 0 chars each) — the
full findings table existed only in the launching session's stdout.
A $3–10 run that cannot be re-read afterward is spend with no
artifact, which the zero-budget constraint makes intolerable going
forward.

**P2 — Worktree launch friction.**
From a worktree, `attune ops` needs the MAIN venv (worktree venvs
lack `[ops]` extras), a `PYTHONPATH` override (the editable MAPPING
points at main), and `--project-root` — all undocumented at the
point of failure. The known-good invocation lives only in lessons.

## Candidate requirements (NOT ruled — discovery input)

- **R1 — Persist the full report.** Run records carry complete
  section content and suggestions; `/runs/<id>/report` serves them;
  a regression test asserts a rendered report survives the
  round-trip with content.
- **R2 — Launch doctor.** `attune ops` detects the
  worktree/missing-extra/wrong-root cases and either self-corrects
  or prints the exact working invocation, instead of failing with a
  bare ModuleNotFoundError.
- **R3 — Placement tile.** When host-surface-parity Task 8 lands
  its `placement: local` routing label, ops tiles grow the ruled
  "not a tier" case (accepted cost of that spec's D2) and show
  where a role ran.
- **R4 — Static asset freshness.** `/static/*.js` is served without
  `Cache-Control`, so returning users keep stale JS across releases
  (documented lesson; features silently dark). Add explicit cache
  headers or content-hashed asset names.

## Open questions for the chair (discovery form, next session)

1. Which candidate requirements are in scope, and in what order?
   (Lead's lean: R1 first — it is the pain point that destroys the
   value of money already spent.)
2. Is P1's fix "persist everything" or "persist within a size
   budget"? (Reports can be large; the run dir is unbounded.)
3. Does R2 self-correct (spawn with the right interpreter) or
   teach (print the invocation)?
4. Coverage floor for this spec: repo 85% or the 90% class?

## Non-goals

- No new dashboard pages or visual redesign in this cycle — the
  seeded pain points are about data fidelity and launchability.
- No telemetry expansion; the existing stores are the inputs.
