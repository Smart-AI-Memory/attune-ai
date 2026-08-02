# Outcome-First Fix — Decisions

## D1 — Canonical Fix scenario: hardened failing-test (RATIFIED)

**Chair, 2026-07-30.** The roundtable left the canonical
scenario as an open chair decision. Patrick leaned failing-test;
the lead rendered the counter-case unprompted (plain
failing-test lets the fix target and the verification probe
collapse into one artifact, leaving H2's goal/probe separation
unproven, and it exercises the path attune already serves best).
Three options were presented — hardened failing-test, plain
failing-test, seeded runtime bug with agent-authored regression
test. Chair picked **hardened failing-test**: the failing-test
scenario with plural, distinct done conditions (target test
passes + full fixture suite green + diff confined to source,
not tests). The seeded-runtime-bug option was declined because
an LLM-authored regression test adds nondeterminism to repeated
evaluation; determinism won.

## D2 — "XML task for the Fix proof slice" scoped to Phase 0 (RATIFIED)

**Lead proposed 2026-07-30; chair ratified 2026-07-30.** The ruling says the spec's only executable
unit is a cold-handoff-capable XML task "for the Fix proof
slice." Read literally, the proof slice spans ruling Phases 0–2,
but one XML task covering inventory + contract design + live
execution is multi-session-sized and not cold-handoff-capable.
Interpretation adopted: Task 0 covers ruling Phase 0
(architecture and characterization proof) only; the Phase 1 and
Phase 2 tasks are authored after Phase 0's acceptance passes and
the chair gates each. Counter-reading (one task for the whole
slice) recorded and rejected for handoff size.

## D3 — Initial metric subset of four (RATIFIED)

**Lead proposed 2026-07-30; chair ratified 2026-07-30, as
amended by the codex lane finding below.** The ruling lists ten Phase 3 metrics.
Standing up measurement for all ten during the thin slice risks
building the parallel telemetry system the ruling itself
forbids. Proposal: measure evidence-valid receipt completeness,
verification-failure honesty, time-to-verified-outcome, and
compatibility regressions from Phase 2 onward; the
routing-behavior metrics (false-confident-route,
contract-edit, route-correction, abstention, abandonment)
activate at Phase 4 where their labeled corpus exists anyway.
The full list remains ratified; this only sequences it.
(Amended 2026-07-30: the codex D11 lane caught
false-confident-route rate sitting in the Phase 2 set while the
same decision deferred routing metrics to Phase 4 — it is a
routing metric and moved there.)

## D4 — Spec drafted directly from the roundtable synthesis (NAMED)

**Lead, 2026-07-30.** Per the decision routine, originating a
spec normally offers the `/spec` interview. Skipped here and
named out loud: the roundtable WAS the interview — the ruling
already contains the hypotheses, non-goals, gates, and
counter-case a Stage 1 interview would re-derive. The spec
transcribes the ruling; it does not re-litigate it.

## D5 — In-place source EDITING has no existing workflow; Phase 2 adds ONE fix-capable workflow to the existing registry (PROPOSED)

**Lead, 2026-07-30; precision corrected by the chair in-session
("some existing workflows do alter source files" — confirmed).**
Grep receipts, both sides: (a) workflows that WRITE project
files exist — `test_gen_parallel` writes generated test files
into the tree via `_validate_file_path(...).write_text(...)`
(test_gen_parallel.py:336), `document_gen` writes documents,
`dependency_check_audit` writes an advisories report. (b) No
registry workflow EDITS existing source in place to change
behavior, and no SDK workflow grants agents `Edit`/`Write`
(every `allowed_tools` is `Read`/`Glob`/`Grep`, plus `Agent` in
code_review). The canonical Fix scenario requires exactly (b) —
editing `pricing.py` in place. Interpretation adopted: Phase 2
adds a single `FixWorkflow` INTO the existing registry, riding
the existing `agent_sdk_adapter` executor and `WorkflowResult`
contract; the (a) precedent shows project-tree writes are
already established workflow practice, so a fix-capable
workflow is USING the machinery, not building the parallel
planner/registry/executor H3 forbids. Counter-case: a purist
reading says Phase 2 should halt because "existing machinery"
turned out fix-incapable; rejected — the registry is the
designed extension point and (a) is the precedent. Chair may
overrule.

## D6 — Phase 2 live-fire dogfood receipt (RECORDED)

**Lead, 2026-07-30, chair-authorized spend (Task 2 go).** One real
`attune fix --run` through the real `FixWorkflow` (SDK session,
subscription-first) on a scratch git copy of the canonical
fixture:

```text
workflow finished (success=True) — verifying independently...

🧾 Fix receipt

Changes made (attributed to this run):
  - pricing.py
Probes (evaluated independently):
  - [PASS] .../python -m pytest pricing_suite.py::test_boundary_order_is_bulk -q (exit 0, 561ms)
  - [PASS] .../python -m pytest pricing_suite.py -q (exit 0, 567ms)
Safest next action: review the attributed diff and commit
receipt reflects independently evaluated probes — workflow exit was not trusted
exit code: 0
```

Agent diff (verified by hand): exactly `>` → `>=` at the bulk
boundary plus removal of the then-false seeded-bug comment; no
other paths touched. Ruling Phase 2 acceptance met on the REAL
path: the initially failing target probe passed through a real
CLI/subprocess/file boundary, and the receipt attributed exactly
one in-scope file from the pre-run baseline.

## D7 — Prompt-text persistence: the Fix surface is clean; the ops run record is a generic inherited surface (RECORDED)

**Lead, 2026-07-31, Phase 3 G3.** The requirement "sensitive prompt
text is not persisted by default" was verified rather than assumed,
and the answer is split.

**`attune fix` persists nothing.** Verified by an evidence-chain
walk over real files, not a mock: a `--run` with a sentinel request
string writes no file under the repo tree or an isolated `HOME`
containing that string. The request reaches stdout and nothing else.
Telemetry is not a leak path either — `_track_sdk_run_telemetry`
records cost, tokens, and duration only. Pinned by
`test_fix_run_persists_no_file_containing_the_request_text`.

**The ops run record would carry it — but nothing can reach that
path today (CORRECTED 2026-07-31, same day).** The first wording of
this decision said a goal "passed that way lands in the record,"
which implies a reachable exposure. It is not reachable, and the
correction matters enough to state plainly:

- `_persist_run` has exactly one caller, and `persistence_dir` is
  wired ONLY in the ops dashboard server — CLI- and MCP-launched
  runs never write an ops run record at all. So neither
  `attune fix --run` nor `attune workflow run fix --input '{...}'`
  from a terminal persists anything.
- The dashboard's start endpoint (`POST /workflows/{name}/run`,
  `src/attune/ops/routes/runner.py`) reads exactly `path` and
  `trigger` from the body and passes only those to
  `RunnerService.start`. There is no `--input` or `extra_args`
  passthrough; the single `extra_args` caller in the tree is the
  self-heal `diagnose` route passing a run id.
- A dashboard-launched `fix` would therefore fail on "goal argument
  is required" before any record content exists.

What remains true: the writer stores whatever argv it is given, so
the exposure would arrive the day the endpoint grows a free-text
passthrough.

**Decision: record the boundary, do NOT change the ops surface in
this spec.** The behavior is generic to every workflow, predates
this spec, and belongs to the ops/run-record surface — changing it
here would alter behavior for every other workflow from inside a Fix
phase. `test_ops_run_record_would_carry_goal_text_generic_surface`
pins the writer's behavior as CHARACTERIZATION.

**Chair ruling on the carried candidate (Patrick, 2026-07-31):
guard the endpoint, do not redact the writer.** Redaction was
declined — it would change a shared surface for a path no caller can
reach, and would mask argv fields that are genuinely useful when
debugging a failed run. Instead the RISK BOUNDARY is guarded where
it actually lives:
`tests/unit/ops/test_run_start_no_freetext_passthrough.py` asserts
the start endpoint forwards no caller-supplied arguments, that no
prose reaches the subprocess argv or the run record, and that the
body parser still honors exactly two keys. Demonstrated firing: with
an `extra_args` passthrough temporarily wired into the route, the
guard fails on the argv assertion; restored, it passes.

The redaction question is CLOSED unless the endpoint gains a
free-text passthrough — at which point the guard fails and forces
the decision then, with the exposure real rather than theoretical.

## D8 — Untracked-directory scopes broke receipt attribution; fixed by per-file expansion (RECORDED)

**Lead, 2026-07-31, cold first-run UX review (PR #1822).** A
`--run` whose `--scope` was an UNTRACKED directory — the natural
"scratch copy inside the repo" demo flow — produced a false
receipt: the workflow fixed the seeded bug and the probe passed,
yet the receipt read "this run changed no files; the done
conditions were already satisfied before it ran." Two mechanisms
compounded: git porcelain collapses an untracked directory to a
single `dir/` entry (identical before and after the run), and a
directory cannot be content-hashed, so `capture_baseline` held
nothing attributable. The D6 dogfood receipt missed the class
because its scratch copy was its own git repo, giving per-file
porcelain entries.

Fix: baseline capture expands directory entries (scope dirs and
dirty dirs) to per-file hashes, and receipt assembly rescans
those directories so files CREATED by the run are attributed.
Pinned by `test_untracked_scope_dir_edits_are_attributed`;
live-fire re-run of the exact failing scenario now attributes
`pricing.py` with next action "review the attributed diff and
commit." Metric relevance: this was an evidence-valid receipt
completeness failure (D3 set) found only by running the surface
cold — the receipt rendered every section yet the attribution
evidence inside it was false.

## D9 — Feature name RATIFIED: "Fix Receipts" (chair, 2026-08-02)

The chair ratified **"Fix Receipts"** as the feature's public name,
choosing to name the ARTIFACT rather than the process. "Outcome-first"
remains the descriptive adjective (and this spec's slug — unchanged).

Provenance: post-11.2.0 README review. Candidates considered with the
chair: Outcome-First Fix (status quo — describes input, doesn't
brand), Fix Contracts ("contract" overloaded), Verified/Proof-Carrying
Fixes (REJECTED — overclaims: probes are evidence, not proofs). "Fix
Receipts" won on concreteness, extensibility (run receipts, lane
receipts, release receipts already exist in governance vocabulary),
and alignment with the published thesis ("the receipt beats the
promise"). The term "outcome-first" itself was confirmed as this
project's own coinage (born in roundtable
`q-agent-work-report-spec-001`'s sibling thread
`q-outcome-first-attune-ux-001`, chair-promoted 2026-07-30), not an
imported industry term.

Scope of the ruling: prose surfaces (READMEs, feature page, skill
description) land the name in one PR; CLI --help text and code
identifiers are NOT renamed (the surface stays `attune fix`;
`fix_receipt.py` already carries the artifact name). Future receipt
kinds may adopt the family framing ("Attune gives you receipts") but
each needs its own ruling.
