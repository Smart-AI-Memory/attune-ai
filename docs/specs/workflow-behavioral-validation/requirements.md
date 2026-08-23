# Spec: Workflow Behavioral Validation

**Status**: RATIFIED (chair, 2026-08-23) — the two-track direction and
the Principle 5 carve DIRECTION are ratified (see `decisions.md` D1–D9).
The requirements are stable; the DESIGN's enforcement mechanics
(`design.md`) continue to be refined and are resolved in Phase 3
execution against real code + tests. The carve's mechanical
contract-text + enforcer edits remain gated to a separate reviewed
execution PR — no gate/config change lands ahead of that.
**Created**: 2026-08-23
**Origin**: The workflow fleet-health roundtable
(`q-workflow-fleet-health-001`, chair-promoted into
`docs/specs/test-quality-program/`) found that 12 of 20 dashboard
workflows were marked "working" on the strength of a single
small-target run — proof of "exited 0", not of doing the job. The
planted-defect probe harness built in response (PRs #2210, #2211;
results in `test-quality-program/decisions.md`) validated three
verdicts, caught two real defects ([#2213](https://github.com/Smart-AI-Memory/attune-ai/issues/2213),
[#2214](https://github.com/Smart-AI-Memory/attune-ai/issues/2214)),
and caught a vacuous-assertion bug in itself. This spec makes that
harness a standing, second track of the test-quality program.

Sibling of [test-quality-program](../test-quality-program/) —
this spec owns the behavioral track; that spec keeps owning the
coverage track.

---

## Phase 1: Requirements

### Why

The test-quality program has one track: coverage-driven,
module-by-module unit-test work over deterministic code. It works
well there. It serves the product's core value — the ~20 LLM
workflows — worst:

1. **Line coverage on a workflow module is a fictional signal.**
   Unit tests mock the LLM, so a workflow can sit at 90% coverage
   and still ship `secure-release` returning GO on a dead gate or
   `test-gen` emitting no runnable tests. This is the repo's own
   vacuous-test lesson (mock a transport → emptiness-asserting
   tests pass for the wrong reason) applied to the whole workflow
   fleet. Coverage said those workflows were fine; the probes
   caught them in one run each.

2. **"Working" had no behavioral basis.** The dashboard verdict
   was "the CLI exited 0". A workflow that returns findings for
   the wrong reason, or degrades-to-empty, passed that bar.

3. **The failures cluster, and coverage cannot see any of them.**
   The roundtable's Sev1-Sev5 group (secure-release, health-check,
   doc-orchestrator fail-open; doc-gen, research-synthesis
   transport crashes) plus this harness's own finds (test-gen,
   the discovery-sweep dependency-check lane) are all *behavioral*
   defects invisible to line coverage.

The program needs a second track whose unit of evidence is
"does this workflow do its job", not "are its lines exercised".

### Goals

1. **Establish behavioral validation as a first-class track** of
   the test-quality program, with the planted-defect probe
   harness (`scripts/workflow_probe_runner.py`,
   `tests/fixtures/workflow_probes/`) as its seed.

2. **Re-scope the quality bar for LLM workflow behavior** from
   mocked line coverage to a passing planted-defect probe — for
   the behavioral surface only (see the carve-scoping problem
   below, which is this spec's central design task).

3. **Grow probe coverage across the fleet.** Only 5 of ~20
   workflows have fixtures today. Define which workflows get a
   probe, what each probe's receipt is, and track it in a
   registry.

4. **Wire the cadence** the chair chose: pre-release gate
   (blocking), on-workflow-change (labeled/manual), and a weekly
   scheduled advisory audit — none in per-push CI (DEC-6, "CI
   spends attention, never money").

5. **Keep the harness honest.** Free unit guards keep fixtures'
   planted defects present; probe assertions stay behavioral
   ("named the defect"), never exact-match, so LLM
   non-determinism does not make them flaky or vacuous.

### Non-goals

- **Fixing the workflows themselves.** This spec validates and
  tracks; individual defects (#2213, #2214, and the roundtable's
  fail-open group in #2207–#2209) are their own work items. The
  behavioral track's deliverable is the *receipt*, not the fix.
- **Putting billed probes in per-push CI.** Ruled out by DEC-6.
- **Replacing the coverage track.** Deterministic code keeps the
  85% floor and the existing rubric/playbook unchanged.
- **A generic "LLM eval framework".** Scope is planted-defect
  probes against the shipped workflow fleet, not a benchmark
  suite.

### The central design problem — scoping the carve

Chair chose: for workflow modules, a passing probe **replaces**
the coverage floor. The trap: a workflow module is not all LLM.
`execute()` calls the SDK, wrapped in deterministic seams — arg
parsing, path validation, the result adapter, error
classification, budget allocation. The probe validates the LLM
behavior; it says nothing about those seams — and those seams are
exactly where this session's real bugs lived (`_error_result`
path, the findings-key mapping, discovery-sweep budget
allocation).

So the carve **cannot be per-module** (too coarse — the module
holds both kinds of code). The requirement:

> The LLM-execution path graduates to the probe bar; the
> deterministic seams around it keep the coverage floor.

Codecov gates per-file, not per-function, so implementing this
line cleanly is the spec's hardest task. Candidate approaches to
evaluate at design time (not decided here):

- Split each workflow module so the deterministic seams live in a
  separately-covered helper module, and only the thin LLM-driver
  file is carved out.
- Keep the file whole but exclude only the LLM-driver lines via
  targeted `# pragma: no cover` with a documented rationale, and
  let the probe be the driver's receipt.
- Fall back to "coverage advisory" for whole workflow modules
  (measure, don't gate) if a clean line cannot be drawn — the
  pragmatic spelling of the same intent, flagged as the retreat
  position.

### Cadence (chair-chosen)

| Trigger | Behavior | Notes |
|---------|----------|-------|
| Pre-release gate | Blocking | Probe set runs before each release; a failing probe blocks. Fits the existing release-prep flow; billed, budget-capped. |
| On workflow change | Manual / labeled job | When a workflow's code changes, run that workflow's probe. Billed, so labeled-dispatch, never per-push. |
| Weekly scheduled audit | Advisory | Periodic sweep catches env/drift regressions like this session's SDK-pin drift and API-limit exhaustion — regressions no code change would trigger. |
| (On-demand) | Always available | `scripts/workflow_probe_runner.py --run <name>` stays the manual entry point. |

### Public-API / governance impact

- **Principle 5 carve (governance-affecting).** "Coverage is a
  floor, not a goal … Changed code carries ≥85% coverage" is a
  ratified contract principle with mechanical enforcers
  (`codecov.yml`, `test_workflow_yaml.py`'s threshold
  drift-guard). Carving workflow-behavioral surfaces out of it
  requires an explicit chair ruling recorded in this spec's
  `decisions.md`, and edits to the contract text + enforcer
  config. **No gate/config change lands before that ruling.**
- **DEC-6 unaffected.** The behavioral track is billed and
  explicitly out of per-push CI; it composes with, not against,
  the spend-guard.
- **New surface: the probe registry.** A tracked record of which
  workflows have a probe, each probe's receipt type, last run,
  cost, and verdict. Format (spec-decision, defer to design):
  a tracked file under this spec dir, hydrated the same way the
  cross-review R5 ledger is.

### Definition: a "validating probe"

A probe validates a workflow when it:

1. runs the workflow against a fixture carrying a KNOWN defect (or
   a known-good target, for generative workflows like test-gen);
2. asserts a **behavioral** receipt — the workflow named/surfaced
   the planted defect, or its generative output actually runs —
   not an exact string or score;
3. distinguishes a **crash** (transport/SDK/limit error, no
   analysis) from an **analytical miss** (ran, missed the defect)
   — the harness already does this (`_crash_reason`);
4. records its measured spend, and runs only via the manual /
   gated / scheduled surfaces above, never per-push.

### Open questions for design (Phase 2) — RESOLVED (chair, 2026-08-23, D8)

1. Registry format / persistence → **new tracked file** (D3).
2. Carve mechanics → **fleet-wide uniform mechanism** (seam-split for
   the whole fleet), with per-workflow probe-gated activation retained
   (D2/D8). See D8 for the interpretation note.
3. Pre-release gate wiring → **standalone job** (D4); full-fleet budget
   uses the large cap with a **hard $32 ceiling** (D8).
4. Rollout / fixture design → **lead's best judgement** (D5;
   analytical-first).

### Acceptance (Phase 1 done when)

- Chair reviews this requirements doc and rules on the Principle
  5 carve (approve / modify / reject the "replace" direction).
- On approval, Phase 2 (design) drafts the carve mechanics, the
  registry format, and the cadence wiring.
