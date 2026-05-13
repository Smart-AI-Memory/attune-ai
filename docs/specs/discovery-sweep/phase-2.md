# discovery-sweep — Phase 2

Phase 1 shipped the engine. Phase 2A shipped the
`PatternScanSource` deterministic adapter, the
`DiscoverySweepWorkflow(BaseWorkflow)` CLI wrapper, and
registry registration — so `attune workflow run
discovery-sweep --path <module>` produces real findings
end-to-end. Phase 2B picks up the LLM-wrapping adapters and
the remaining roadmap items below.

## Phase 2A — shipped 2026-05-13

- `PatternScanSource` — deterministic regex-based line scanner
  for bare except, broad exception, eval/exec, subprocess
  shell=True, TODO markers
- `DiscoverySweepWorkflow(BaseWorkflow)` — thin CLI wrapper
  that delegates to `DiscoverySweepEngine`
- Registered in `_LAZY_WORKFLOW_IMPORTS` +
  `_DEFAULT_WORKFLOW_NAMES`
- 22 new tests (pattern scanner, CLI wrapper, registry
  registration)

## P2.1 — Real `FindingSource` adapters

**Goal:** Wrap each existing autonomous sub-workflow as a
`FindingSource` so sweeps produce real findings end-to-end.

**Adapters to ship (priority order):**

1. `BugPredictSource` — wraps `BugPredictionWorkflow`. Cheapest
   first because bug_predict has a structured pattern-based
   output that maps directly to `Finding`.
2. `SecurityAuditSource` — wraps SDK-native `SecurityAuditWorkflow`.
3. `CodeReviewSource` — wraps `CodeReviewWorkflow`.
4. `PerfAuditSource` — wraps `PerfAuditWorkflow`.
5. `DeepReviewSource` — wraps the multi-pass deep-review workflow.

**Per-adapter checklist:**

- Map sub-workflow output → `Finding` fields (file_path, line,
  severity, message, raw_finding preserved)
- Respect `budget_usd` ceiling — either pass to sub-workflow's
  budget knob or short-circuit when nearly out
- Surface real spend on `estimated_spend_usd` (read from
  sub-workflow's cost tracker)
- Integration test against a small fixture path with real LLM
  calls behind a `HAS_API_KEY` skip guard
- Unit test against a mocked sub-workflow result so the
  adapter's translation logic is covered without API spend

## P2.2 — CLI registration

**Goal:** `attune workflow run discovery-sweep --path <module>`
works.

**Approach:** Either (a) make `DiscoverySweepWorkflow` a
`BaseWorkflow` subclass so it slots into the existing registry,
or (b) register a thin adapter that the workflow runner
recognizes. (a) is simpler if the BaseWorkflow constructor
isn't too noisy for the orchestrator's needs.

**Flags to expose:**

- `--path <scope>` (required)
- `--sources <comma-separated names>` — defaults to all
  registered adapters
- `--output-dir <path>` — defaults to `.claude/discovery-queue/`
- `--subworkflow-budget <usd>`, `--sweep-budget <usd>` —
  override env vars
- `--quiet` — silent mode for background-job invocation

**Background-job ergonomics:**

- Compatible with the existing `run_in_background` agent
  pattern
- Progress output goes to stderr; stdout reserved for the
  result summary (the existing CLI convention)

## P2.3 — Auto-fix for `routine`-tagged items

**Goal:** Items tagged `routine` can be opted into a
fire-and-forget fix pass that produces a PR for review.

**Key design constraints:**

- MUST run in a worktree (no fix touches the main checkout)
- MUST stash before each fix (so partial-fix state is
  recoverable)
- MUST run the test suite after each fix; revert if anything
  regresses
- Resolution complexity tag stays the gate — `needs_patrick`
  items never auto-fix

**Open question for Phase 2 planning:** how to bound the
auto-fix budget separately from the sweep budget — they should
not share a cap.

## P2.4 — Workflow retirement evaluation

**Goal:** Decide which existing autonomous workflows the sweep
supersedes.

**Method:** Run the sweep and the candidate workflow on the
same scope, compare outputs. Retirement criteria:

- Sweep's queue is a strict superset of the candidate's
  findings on representative scopes
- Verification quality is at least as good (no new false
  positives in sweep's REJECT output that the candidate would
  have caught)
- Cost-per-finding is comparable or better

**Candidates (initial):** `test_audit`. Most others
(`bug_predict`, `security_audit`, etc.) are consumed by the
sweep as `FindingSource` adapters and retained.

## P2.5 — Multi-module parallelism

**Goal:** Run the sweep on N module scopes concurrently with
shared budget accounting.

**Approach:** `asyncio.gather` across `DiscoverySweepWorkflow`
instances, with a shared `BudgetTracker` and a global ceiling
that all instances coordinate on. Each instance produces its
own sweep-id and output set; results aggregate at the call
site.

**Risks:**

- Shared budget accounting under concurrent updates needs
  locking
- Combined LLM concurrency may hit rate limits — adapter-level
  throttling required

## P2.6 — RAG-grounded verification

**Goal:** Verification rules consult `attune-help` /
`attune-rag` to check whether a finding contradicts a
documented pattern.

**Approach:** A new verification rule type that queries the
RAG index for the finding's pattern + file context. If the
top result is a "this is intentional" lesson or template, the
rule returns REJECT with the cited document.

**Wins over the Phase 1 hard-coded denylist:**

- Rule corpus grows as docs grow — no code change needed
- Citations link findings back to their grounding doc
- Less brittle than substring matching

**Risks:**

- RAG retrieval latency adds to per-finding verification time
- Citation quality depends on attune-help corpus quality —
  already addressed by 0.7.0 polish work but worth monitoring

## Sequencing

P2.1 and P2.2 should ship together — adapters without CLI are
not useful; CLI without adapters is empty. P2.3 builds on the
queue's complexity tag. P2.4 needs P2.1 to have a basis for
comparison. P2.5 and P2.6 are independent and can land any
time post-P2.1.

A reasonable order: **P2.1 + P2.2 (bundled) → P2.4 → P2.3 →
P2.6 → P2.5.**
