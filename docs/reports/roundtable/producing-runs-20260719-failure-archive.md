# Producing runs 2026-07-19 — failure archive (chair-promoted 2026-07-22)

**Chair ruling:** archive + queue re-runs. All four V2-P4 producing
runs of 2026-07-19 FAILED before staging (`staged: 0` — TR-6 staging
never occurred, R8 honored; no unruled content ever reached the
chair). Promoted before TTL expiry to preserve the only copies of
the seat draft documents and the failure receipts.

**Why each failed — and why re-runs should succeed now:**

- `spec-lifecycle-gates-…-1` — LINT_DIRTY: codex critique carried an
  uncited item after its one repair round. The citation contract has
  since been taught by worked example (the format-contract lesson).
- `spec-lifecycle-gates-…-2` — INPUT_INVALID: the grounding pack
  path pointed into a since-deleted worktree. Re-arm with a pack at
  a stable tracked path.
- `pipeline-learner-v1` — SEAT_ABSENT ×2: the claude seat's revoked
  OAuth token era; the seat now runs the API-key path (backlog (c)
  ruling, verified in the 07-22 dry-run rehearsal).
- `usage-signals-refresh` — LINT_DIRTY: the antigravity final draft
  omitted convergence tags on every item; the tag contract now ships
  a worked example in the brief.

**Re-run queue (chair-ruled):** re-arm all three subjects post-lift
with stable grounding packs; tracked in the re-run issue referenced
by the session starter.

The salvage value below: complete seat documents (drafts/critiques
— e.g. an 8-item RR draft for pipeline-learner, a 5-item draft for
usage-signals) that future runs or spec sessions can mine.

---

## Thread `producing-spec-lifecycle-gates-20260719-1`

### #1 — question (moderator)

```text
# Grounding pack — spec-lifecycle-gates (producing-run input)

**Subject:** Intelligent progress/quality gates for the spec-driven
development lifecycle, runnable autonomously or chair-gated.
**Provenance:** round-table thread `q-spec-gates-001` (2026-07-19,
promoted to `docs/reports/roundtable/q-spec-gates-001.md`).
**Drafter:** claude (owed per rotation ledger). **Arming:** per-spec
(chair queues this pack; no standing cadence).

## The composed frame the table converged on (seed, not contract)

- Gates sit at the five lifecycle boundaries (brainstorm →
  requirements → design → tasks → execution → verification) plus a
  continuous drift/self-truthing sweep.
- Autonomy split (unanimous): autonomous gates may BLOCK / REVISE /
  REPORT with exact shortfalls; only the chair APPROVES scope,
  irreversible choices, waivers, promotion. Never-auto-promote
  generalizes to never-auto-advance-on-judgment.
- Container (codex): a shared gate protocol — machine-readable
  findings, evidence references, proposed disposition, four states:
  `PASS / REVISE / CHAIR_REQUIRED / BLOCKED`.
- Build path (claude): map each gate onto a SHIPPED mechanism —
  compiler-lint seam (TR-4), corpus-readiness refuse-with-shortfall
  shape (RR-1), doc-import-gate + `[[?slug]]` hatch, producing-run
  caps, central receipt re-run (delegation receipts), curator
  sources for triage, starter-reconciler-style self-truthing.
- Escalation policy (antigravity): blast radius — additive/isolated
  auto-passes; public API, shared schema, security primitives,
  migrations always chair.
- Shared named risk: ceremony inflation / Goodhart on lintable
  formats. Shared mitigation: risk-tiered activation — a small
  mandatory baseline (the fully-mechanical gates) with the full
  ladder only for spec-tier / irreversible work.

## Chair rulings already made (constraints on the draft)

See `decisions.md` in this directory — verdict-ledger location,
flaky-live-fire override path, and fixed-vs-dynamic gate policy are
ruled; the draft must conform, not re-litigate.

## Live probes the drafter must run (PACK discipline)

- Verify each claimed building block exists and name its import
  path/entry point (compiler lints, producing module, readiness
  gate, drift-guard examples, curator sources contract, receipts
  taxonomy source).
- Grep for existing enforcers before proposing any new gate — the
  twice-earned lesson: several "new" gates may already have partial
  tests (e.g. rules-residency budget, doc-import audit, complexity
  ratchet, lessons golden-smoke).
- Count the real chair-interaction cost: how many decisions.md
  rulings per week the current process already generates, so the
  gate ladder's CHAIR_REQUIRED volume is designed against measured
  decision fatigue, not guessed.

## Non-goals to carry into the draft

- No second telemetry pipeline; verdict storage follows the ruled
  ledger location.
- No gate fires on sub-spec-tier work beyond the mandatory baseline
  (the xml-enhanced-prompts "Do NOT use" list is the tier boundary).
- The chair's per-item ruling surface stays decisions.md — gates
  produce candidates and evidence, never rulings.
```

### #2 — event (moderator)

```text
scheduled-assignment
```

### #3 — position (claude)

```text
## Requirements

**RR-1 — Shared gate protocol with a four-state disposition**

Every gate, at every lifecycle boundary, emits the same machine-readable record so a chair or a downstream autonomous step can consume any gate identically. This is the container (codex) contract: findings + evidence references + proposed disposition, with exactly four states — `PASS / REVISE / CHAIR_REQUIRED / BLOCKED`. Without one protocol the gate ladder becomes N bespoke formats and the Goodhart risk compounds.

- A gate record is a structured object carrying: `gate_id`, lifecycle boundary, `state ∈ {PASS, REVISE, CHAIR_REQUIRED, BLOCKED}`, a list of findings each with an evidence reference (file:line, test name, or run-id), and a `proposed_disposition` string.
- A schema test rejects any gate emitting a state outside the four, or a `REVISE`/`BLOCKED` record with zero findings (a block must name its exact shortfall).
- `REVISE` and `BLOCKED` records must state the concrete shortfall in machine-readable form (the corpus-readiness "refuse-with-shortfall" shape, RR-1 in the seed), not a prose summary.

**RR-2 — Gates sit at the five lifecycle boundaries plus a continuous drift sweep**

Gates fire at brainstorm→requirements, requirements→design, design→tasks, tasks→execution, and execution→verification, plus a continuous drift/self-truthing sweep that runs independent of boundary transitions. This is the composed frame the table converged on; the boundaries are where judgment quality is cheapest to enforce and drift is where shipped-but-stale specs are caught.

- Each of the five boundaries has at least one registered gate; a registry test asserts no boundary is uncovered.
- The drift sweep reuses the starter-reconciler self-truthing shape and flags spec-artifact-vs-code divergence (e.g. status field says "approved" but the primary artifact already shipped) as a `REVISE` candidate, never a ruling.
- A gate at a boundary can only observe artifacts that exist at that boundary (a design gate cannot demand execution evidence); the registry records each gate's required inputs.

**RR-3 — Autonomy split: autonomous gates BLOCK/REVISE/REPORT; only the chair APPROVES**

Autonomous gates may block, request revision, or report exact shortfalls; they may never advance scope, ratify an irreversible choice, grant a waiver, or promote. "Never-auto-promote" generalizes to "never-auto-advance-on-judgment" (unanimous table ruling). This is the load-bearing safety property.

- Any transition whose gate emits `CHAIR_REQUIRED` halts until a chair disposition lands in decisions.md; the gate itself writes no ruling.
- A gate that would APPROVE scope, a waiver, a migration, or an irreversible choice is structurally incapable of emitting `PASS` — it can only emit `CHAIR_REQUIRED`, enforced by a test.
- A fully-mechanical gate (deterministic lint/compile/count) may emit `PASS` autonomously; a judgment gate (LLM-scored quality) may emit at most `REVISE`, never autonomous `PASS`.

**RR-4 — Each gate maps onto a shipped enforcer before any new mechanism is built**

The build path (claude) is reuse-first: map each gate onto an existing, verified mechanism and name its import path; only build new where a live grep confirms no partial enforcer exists. The twice-earned lesson (grep-for-existing-enforcer) is that rules-residency budget, doc-import audit, complexity ratchet, and lessons golden-smoke already exist as partial gates.

- Every gate in the registry names its backing mechanism and entry point (compiler-lint seam, producing-run caps, central receipt re-run, curator triage sources, doc-import-gate + `[[?slug]]` hatch, drift-guard tests) or is explicitly flagged `net-new` with a rationale.
- Before any `net-new` gate is added, the spec records a grep receipt showing no existing enforcer (test, ratchet, or CI check) already covers that property.
- The verification gate's evidence bullets re-run receipts centrally (delegation-receipts taxonomy) rather than trusting a lane's self-report.

**RR-5 — Risk-tiered activation: mandatory mechanical baseline, full ladder only for spec-tier work**

A small mandatory baseline of fully-mechanical gates runs everywhere; the full judgment ladder activates only for spec-tier or irreversible work. This is the shared mitigation for the shared named risk — ceremony inflation / Goodhart on lintable formats — so sub-spec-tier work is not taxed.

- The tier boundary is the xml-enhanced-prompts "Do NOT use" list: work on that list runs only the mandatory mechanical baseline, no judgment gates.
- The mandatory baseline is enumerable and small (deterministic gates only); a test asserts the baseline set contains no judgment/LLM-scored gate.
- Activating the full ladder requires the work be classified spec-tier or irreversible; the classification is recorded in the spec, not inferred per-run.

**RR-6 — Blast-radius escalation overrides tier for high-risk surfaces**

Regardless of tier, changes to public API, shared schema, security primitives, or migrations always escalate to `CHAIR_REQUIRED`; additive/isolated changes may auto-pass (antigravity escalation policy). Blast radius, not artifact tier, governs the high-risk surfaces.

- A gate computes a blast-radius classification (additive/isolated vs public-API/shared-schema/security/migration) from the changed paths and diff shape.
- Any change touching a high-risk surface emits `CHAIR_REQUIRED` even when the tier would otherwise allow autonomous `PASS`.
- The high-risk surface list is a named, testable set (not a heuristic prose list) so its coverage can be asserted.

**RR-7 — Verdict ledger reuses the ruled location and is budgeted against measured chair fatigue**

Gate verdicts persist to the chair-ruled ledger location (per decisions.md) — no second telemetry pipeline. The CHAIR_REQUIRED volume the ladder generates must be designed against the *measured* rate of decisions.md rulings the current process already produces, not a guessed rate.

- Verdict storage writes only to the ruled ledger location; a test asserts no new telemetry stream or `attune:memory:*` write path is introduced.
- The spec records a measured count of decisions.md rulings per week under the current process; the ladder's projected CHAIR_REQUIRED volume is stated relative to that measured baseline.
- If the projected CHAIR_REQUIRED rate exceeds the measured baseline by a threshold to be ruled, the excess gates default to `REVISE` (autonomous) rather than `CHAIR_REQUIRED`, keeping chair load bounded.

## Non-goals

- **No second telemetry pipeline.** Verdict storage follows the ledger location ruled in decisions.md; gates do not stand up a parallel stream and never write `attune:memory:*` directly.
- **No gates on sub-spec-tier work beyond the mandatory baseline.** The xml-enhanced-prompts "Do NOT use" list is the tier boundary; trivial/single-file/config work runs only the mechanical baseline.
- **Gates never rule.** They produce candidates, findings, and evidence with a proposed disposition; the chair's per-item ruling surface stays decisions.md. A gate emitting a "ruling" is a defect.
- **No re-litigation of chair rulings.** Verdict-ledger location, flaky-live-fire override path, and fixed-vs-dynamic gate policy are already ruled in decisions.md; this draft conforms.
- **No new enforcer where one exists.** Reuse of the shipped mechanisms (RR-4) is mandatory; net-new gates are the exception, gated on a grep receipt.

## Open questions

- **Live-probe receipts owed.** As DRAFTER (text-only, no tools) I could not run the PACK-discipline live probes. Before this leaves round 1, someone must: (a) confirm each named building block's import path/entry point (compiler lints, producing module, readiness gate, drift-guard examples, curator-sources contract, receipts taxonomy source); (b) grep for the partial enforcers named in RR-4 (rules-residency budget, doc-import audit, complexity ratchet, lessons golden-smoke); (c) produce the measured decisions.md-rulings-per-week baseline RR-7 depends on. Each RR's acceptance bullets are written to be falsifiable by those probes.
- **RR-7 threshold value.** The CHAIR_REQUIRED-over-baseline threshold that triggers auto-downgrade to `REVISE` is left for chair ruling once the measured baseline exists — I decline to guess it.
- **Drift-sweep cadence.** The continuous sweep (RR-2) is "per-spec armed, no standing cadence" per the pack's arming note — confirm it stays event-driven (on artifact write) rather than acquiring a schedule.
```

### #4 — synthesis (moderator)

```text
status: failed
conditions: LINT_DIRTY
staged: 0 | deferred_over_cap: 0

## Failures / degradations (receipts)
{"code": "LINT_DIRTY", "run_id": "producing-spec-lifecycle-gates-20260719-1", "thread": "producing-spec-lifecycle-gates-20260719-1", "round": 2, "seat": "codex", "role": "critic", "detail": "dirty after the one repair round", "evidence": "uncited critique item (no pack/file reference): '12. **RR-7:** Downgrading `CHAIR_REQUIRED` to `REVISE` when '"}
```

## Thread `producing-spec-lifecycle-gates-20260719-2`

### #1 — synthesis (moderator)

```text
status: failed
conditions: INPUT_INVALID
staged: 0 | deferred_over_cap: 0

## Failures / degradations (receipts)
{"code": "INPUT_INVALID", "run_id": "producing-spec-lifecycle-gates-20260719-2", "thread": "producing-spec-lifecycle-gates-20260719-2", "detail": "grounding pack unreadable: [Errno 2] No such file or directory: '/Users/patrickroebuck/attune-ai/.claude/worktrees/follow-up-last-session-cf3b4d/docs/specs/spec-lifecycle-gates/grounding-pack.md'"}
```

## Thread `producing-pipeline-learner-v1-20260719`

### #1 — question (moderator)

```text
# Grounding pack — producing run: pipeline-learner v1 requirements refresh

Task: author REFRESHED v1 requirements for the `pipeline-learner`
spec, grounded in CURRENT code/data reality (2026-07-19 probes
below). The chair will use the staged candidates as input to a
commit-or-kill triage ruling. If the honest position is that some
part of the original design is not viable today, say so in the
requirements (e.g. gate on corpus prerequisites) — do not restate
stale premises.

## PACK-1 — Spec status and history

`docs/specs/pipeline-learner/requirements.md`: **draft** created
2026-05-17; kill proposed at the 2026-07-14 triage, SPARED by the
chair; **commit-or-kill again next triage**. No implementation code
exists (`grep pipeline_learner src/attune/` is empty).

## PACK-2 — The original design (condensed from the draft)

- Problem: pipeline authoring is top-down only (hardcoded Python
  workflow classes); working sequences that emerge in real use are
  never mined or canonicalized.
- Goals: mine run history for frequent multi-step sequences
  (pair-mining v1, 30-min window, min-support ~5 occurrences /
  0.5 ratio); rank by confidence (frequency, ratio, recency,
  manual-fraction — manual sequences weighted above
  ATTUNE_REC-triggered ones); surface via the curator as "save as
  named pipeline?" items; on acceptance scaffold a YAML pipeline +
  sibling evidence.json under `docs/specs/pipelines/`; strictly
  opt-in (learner proposes, chair disposes; never writes without
  acceptance).
- Non-goals: executing pipelines; semantic understanding;
  real-time next-workflow prediction; cross-project mining (v1).
- Acceptance criteria (original): fixture corpus surfaces a known
  7-occurrence pattern; noise filtered; manual-vs-auto weighting
  lowers auto-only confidence; acceptance writes YAML + evidence;
  idempotent re-runs; no silent writes.
- Named input corpus: (1) `~/.attune/ops/runs/<wf>/*.json`
  dashboard run records; (2) `~/.attune/bulletin/archive/*.jsonl`
  rotated bulletin entries; claimed "thousands of runs going back
  months".

## PACK-3 — LIVE premise probes (2026-07-19, current tree/host)

- **Run corpus is nearly EMPTY**: `~/.attune/ops/runs/` has 15
  workflow dirs (bug-predict, code-review, deep-review, ...) but a
  TOTAL of 1 run JSON across all of them. The "thousands of runs"
  premise is false today.
- **Bulletin archive is sparse and stale**: exactly 3 archive
  files — 2026-05-27.jsonl, 2026-06-01.jsonl, 2026-06-06.jsonl —
  plus a live `active.jsonl`. Files are flat under `archive/`
  (not the `YYYY-MM-DD/` dirs the draft describes).
- **The named sibling specs no longer exist**:
  `docs/specs/multi-actor-bulletin/` and
  `docs/specs/bulletin-curator/` are absent (only
  `docs/specs/pipeline-learner/` remains). BUT a curator SHIPPED
  in code: `src/attune/curator/` with sources `bulletin.py`,
  `git_state.py`, `recommendations.py`, `specs.py`, `sweep.py`,
  `telemetry.py` — the surfacing path the draft wanted exists,
  under a different history than the draft cites.
- **ATTUNE_REC is real**: referenced in
  `src/attune/workflows/code_review.py`,
  `src/attune/curator/sources/recommendations.py`,
  `src/attune/ops/runner.py` — the manual-vs-auto weighting
  distinction remains meaningful.
- **Workflow registry**: `_DEFAULT_WORKFLOW_NAMES` in
  `src/attune/workflows/__init__.py` (line ~296) is the
  registration surface; registry drift-guard gates exist and any
  new workflow must be wired into them.

## PACK-4 — What this means (moderator read, not binding)

The mining ALGORITHM design is sound and testable against fixture
corpora regardless of live-corpus size. The VALUE premise (mine
months of rich history) is not true today: either the requirements
gate v1 on a corpus-accumulation prerequisite (instrumentation
that actually persists runs — note 15 dirs exist but only 1 file
landed, suggesting run persistence itself may be broken or
disabled), or the spec should be parked/killed honestly. The
curator integration should target the SHIPPED
`src/attune/curator/` surface, not the absent sibling specs.

## PACK-5 — Citable sources

- docs/specs/pipeline-learner/requirements.md (the 2026-05-17 draft)
- src/attune/curator/sources/ (shipped curator source modules)
- src/attune/workflows/__init__.py (_DEFAULT_WORKFLOW_NAMES)
- src/attune/ops/runner.py (run persistence / ATTUNE_REC)
- ~/.attune/ops/runs/ and ~/.attune/bulletin/archive/ (live corpus
  probes above)
```

### #2 — event (moderator)

```text
scheduled-assignment
```

### #3 — position (antigravity)

```text
## Requirements

**RR-1 — Corpus persistence prerequisite and fixture isolation**
Rationale: Live environment probes reveal that `~/.attune/ops/runs/` contains only 1 JSON run file across 15 workflow directories and `~/.attune/bulletin/archive/` contains only 3 flat log files. The original premise of mining "thousands of runs going back months" is false today. The learner must gate live execution on run persistence health in `src/attune/ops/runner.py` while remaining fully testable against synthetic fixture corpora.
- The pipeline learner validates that live run history meets minimum density thresholds before initiating mining scans.
- The mining engine executes and passes pattern-extraction tests using synthetic fixture corpora regardless of live `~/.attune/ops/runs/` state.

**RR-2 — Sliding-window pair mining**
Rationale: Emerging workflows are discovered by analyzing chronological run histories and bulletin transitions to identify frequent multi-step sequences occurring within a tight operational window.
- The algorithm identifies workflow pairs and sequences executed within a 30-minute window.
- Candidate sequences occurring less than 5 times or below a 0.5 support ratio are filtered out as noise.

**RR-3 — Confidence ranking with ATTUNE_REC weighting**
Rationale: Manually invoked workflow sequences signal intentional user composition, whereas sequences triggered automatically via `ATTUNE_REC` (referenced in `src/attune/ops/runner.py` and `src/attune/curator/sources/recommendations.py`) should carry lower confidence weighting.
- Confidence scores are calculated using sequence frequency, execution success ratio, recency, and manual execution fraction.
- Auto-triggered steps containing `ATTUNE_REC` are weighted lower than manual steps in the final ranking score.

**RR-4 — Integration with shipped curator surface**
Rationale: Mined pipeline proposals must surface to users through the shipped curator module (`src/attune/curator/` and `src/attune/curator/sources/recommendations.py`), replacing references to non-existent sibling specs.
- Discovered high-confidence sequences are fed directly into `src/attune/curator/` as recommendation items.
- The curator UI presents discovered patterns to the user as opt-in "save as named pipeline?" proposals.

**RR-5 — Opt-in YAML and evidence scaffolding**
Rationale: Pipeline canonicalization must strictly require explicit user acceptance (learner proposes, chair disposes) to prevent unvetted schema writes.
- Accepting a curator proposal generates a canonical YAML pipeline definition and a sibling `evidence.json` file under `docs/specs/pipelines/`.
- Scaffolding operations are idempotent and never write or modify files without explicit user confirmation.

**RR-6 — Workflow registry drift compliance**
Rationale: Pipeline steps must align with valid registered workflows defined in `_DEFAULT_WORKFLOW_NAMES` in `src/attune/workflows/__init__.py` and comply with registry drift-guard validation.
- All mined sequence steps are validated against `_DEFAULT_WORKFLOW_NAMES` prior to generating proposals.
- Generated pipeline artifacts adhere to workflow registry drift-guard checks.

## Non-goals

- **Executing pipelines**: Pipeline Learner v1 only mines and scaffolds pipelines; execution is handled by external runners.
- **Semantic understanding**: Mining relies strictly on statistical co-occurrence and confidence scoring, not NLP or semantic analysis of workflow code.
- **Real-time next-step prediction**: The system mines historical logs asynchronously rather than providing live inline predictions during workflow execution.
- **Cross-project mining**: V1 analysis is strictly scoped to single-project local operational history.
- **Unsolicited file modification**: The learner will never automatically create or update files under `docs/specs/pipelines/` without explicit user opt-in.

## Open questions

1. Should fixing run persistence in `src/attune/ops/runner.py` be a strict gating PR for Pipeline Learner v1, or should v1 ship as a fixture-only component until run retention is restored?
2. Should the bulletin parser support both flat archive files (`~/.attune/bulletin/archive/*.jsonl`) and date-nested directory structures to handle historical log variation?
```

### #4 — event (moderator)

```text
fallback
```

### #5 — position (codex)

```text
1. **RR-1:** The central commit-or-kill decision remains unresolved: neither the minimum density thresholds nor the required persistence-health probe is defined, while Open Question 1 still permits a fixture-only release with no usable live input. Specify measurable corpus readiness criteria and make restoration/verification of persistence in `src/attune/ops/runner.py` a prerequisite; otherwise park the learner as directed by PACK-3 and PACK-4.

2. **RR-2:** “Pairs and sequences” silently expands the pair-mining v1 scope from PACK-2. Define v1 as ordered pairs only, including the support-ratio denominator, 30-minute boundary semantics, project/session partitioning, timestamp ordering, duplicate handling, and treatment of failed runs from `~/.attune/ops/runs/`.

3. **RR-2:** Combining “run histories and bulletin transitions” lacks a reconciliation contract. Records from `~/.attune/ops/runs/` and `~/.attune/bulletin/archive/` may describe the same invocation, but the draft defines neither identity keys nor deduplication, risking inflated support counts. PACK-3 also shows the bulletin archive is too sparse to assume it is authoritative.

4. **RR-3:** The confidence requirement is not reproducible or acceptance-testable. Define the formula or deterministic ordering, recency decay, missing-success handling, and exact classification rule for `ATTUNE_REC`; “steps containing `ATTUNE_REC`” is ambiguous against `src/attune/ops/runner.py` and `src/attune/curator/sources/recommendations.py`.

5. **RR-4:** PACK-3 establishes a shipped curator module, not a “curator UI.” The requirement invents an ungrounded presentation surface and leaves the actual integration contract unspecified. Name the source/provider interface under `src/attune/curator/sources/`, the recommendation payload, stable identity, and how acceptance is returned to the scaffolder.

6. **RR-5:** “Canonical YAML” is undefined relative to the original scaffolding design in PACK-2 and `docs/specs/pipeline-learner/requirements.md`. Specify the existing or new schema, naming and collision policy, required `evidence.json` provenance fields, atomic two-file creation, and idempotency key. As written, “idempotent” and “never modify files” do not determine behavior when an accepted candidate already exists under `docs/specs/pipelines/`.

7. **RR-6:** Registry validation and registry drift compliance are conflated. `_DEFAULT_WORKFLOW_NAMES` in `src/attune/workflows/__init__.py` can validate mined step names, but generated YAML artifacts do not inherently participate in workflow registry drift guards. State separately whether Pipeline Learner itself is a registered workflow; if so, require its registration and drift-guard updates.

8. **MISSING:** The refreshed requirements lack concrete acceptance criteria replacing those in `docs/specs/pipeline-learner/requirements.md`. Require fixtures proving the known seven-occurrence pair surfaces, sub-threshold noise is rejected, auto-only confidence ranks lower, duplicate cross-source events are not double-counted, rejected proposals write nothing, accepted proposals produce valid YAML plus evidence, and reruns are idempotent.

9. **MISSING:** Open Question 2 preserves an unsupported date-nested archive format even though PACK-3 establishes the current layout as `~/.attune/bulletin/archive/*.jsonl`. V1 should require the observed flat format; compatibility with an evidenced historical format can be added only with fixtures or actual corpus samples.

10. **MISSING:** No requirement defines malformed-record behavior, unreadable files, unknown workflows, clock skew, or partial corpus availability for the inputs identified in PACK-2 and probed in PACK-3. Since those inputs are local operational files under `~/.attune/ops/runs/` and `~/.attune/bulletin/archive/`, the learner needs deterministic skip/error reporting and must not convert corrupt or incomplete data into proposals.

VERDICT: needs-revision
```

### #6 — synthesis (moderator)

```text
status: failed
conditions: SEAT_ABSENT, LINT_DIRTY
staged: 0 | deferred_over_cap: 0

## Failures / degradations (receipts)
{"code": "SEAT_ABSENT", "run_id": "producing-pipeline-learner-v1-20260719", "thread": "producing-pipeline-learner-v1-20260719", "round": 1, "seat": "claude", "role": "drafter", "detail": "invocation failed after retry", "evidence": "Failed to authenticate. API Error: 401 OAuth access token has been revoked.\nPermission allow rule (../.claude/settings.json): Write(/Users/patrickroebuck/attune-ai/tests/unit/*) is not matched by file permission checks — only Edit(path) rules are. Use Edit(/Users/patrickroebuck/attune-ai/tests/unit/*) instead (Edit rules cover all file-editing tools)."}
{"code": "SEAT_ABSENT", "run_id": "producing-pipeline-learner-v1-20260719", "thread": "producing-pipeline-learner-v1-20260719", "round": 2, "seat": "claude", "role": "critic", "detail": "invocation failed after retry", "evidence": "Failed to authenticate. API Error: 401 OAuth access token has been revoked.\nPermission allow rule (../.claude/settings.json): Write(/Users/patrickroebuck/attune-ai/tests/unit/*) is not matched by file permission checks — only Edit(path) rules are. Use Edit(/Users/patrickroebuck/attune-ai/tests/unit/*) instead (Edit rules cover all file-editing tools)."}
{"code": "LINT_DIRTY", "run_id": "producing-pipeline-learner-v1-20260719", "thread": "producing-pipeline-learner-v1-20260719", "round": 3, "seat": "antigravity", "role": "drafter", "detail": "dirty after the one repair round", "evidence": "RR-1: missing convergence tag (agreed / 2-1 / contested)\nRR-2: missing convergence tag (agreed / 2-1 / contested)\nRR-3: missing convergence tag (agreed / 2-1 / contested)\nRR-4: missing convergence tag (agreed / 2-1 / contested)\nRR-5: missing convergence tag (agreed / 2-1 / contested)\nRR-6: missing convergence tag (agreed / 2-1 / contested)\nRR-7: missing convergence tag (agreed / 2-1 / contested)\nRR-8: missing convergence tag (agreed / 2-1 / contested)"}
```

## Thread `producing-usage-signals-refresh-20260719`

### #1 — question (moderator)

```text
# Grounding pack — producing run: usage-signals requirements refresh

Task: author REFRESHED requirements for the `usage-signals` spec.
The requirements.md froze at approval (2026-06-11); the spec's
decisions.md has since accumulated 13+ shipped decisions. The chair
will use the staged candidates to re-scope the spec honestly: what
is DONE (and should read as done), what genuinely remains, and what
the accumulated evidence says the remaining work actually is. Do
not restate shipped requirements as open work; do not invent new
scope beyond what the evidence supports.

## PACK-1 — The original requirements (approved 2026-06-11, condensed)

Problem: every feedback loop terminates at the chair; no visibility
into external usage (PyPI trends, marketplace installs, which
workflows external users run); plus internal watchdog gaps (the
buffered-writer bug silently lost ~10 days of telemetry; a CI
key-spend burned ~$1,200 in a night).

- R1 Phase 0 inventories what's free (pypistats, GitHub traffic,
  marketplace) with a baseline snapshot in decisions.md.
- R2 Privacy stance explicit and conservative; any instrumented
  ping opt-in, payload enumerated, auditable.
- R3 One surface: signals land on the existing ops dashboard.
- R4 Release ritual hook: baseline reach snapshot at tag time.
- R5 Telemetry watchdog: last-write age for usage.jsonl, >48h flag,
  freshness regression test.
- R6 Spend alarm: daily anomaly check with explicit flat-history
  rule.
- Done-when: Phase 0 recorded; dashboard shows reach + freshness +
  spend panels; one release ships a before/after reach pair; the
  opt-in ping question explicitly decided in decisions.md.

## PACK-2 — SHIPPED since approval (docs/specs/usage-signals/decisions.md, live probes 2026-07-19)

- D1 Phase 0 baseline COMPLETE (2026-06-11) with per-package
  pypistats tables and mirror-split addendum.
- D2 zero-instrumentation verdict recorded; D4 ping ruled BUILD.
- D3 R4 snapshot script shipped: `scripts/reach_snapshot.py`;
  `docs/specs/usage-signals/snapshots/` holds dated JSONs current
  through 2026-07-18.
- D5–D8 Phase 2 opt-in ping shipped END-TO-END and verified live
  (2026-06-20): `src/attune/telemetry/usage_ping.py` (default OFF;
  `DO_NOT_TRACK` and `ATTUNE_USAGE_PING` overrides; payload
  enumerated), website ingest chain with validate + rate-limit libs
  (`website/lib/usage/{validate,rate-limit}.ts`).
- D9/D11/D12 default stays OFF; first-run consent prompt shipped
  (8.6.1) on CLI and plugin/MCP channels as the opt-in lever.
- D13 R6 spend alarm SHIPPED (2026-06-20).
- D11 (second use — the decisions ledger has a duplicate D11
  number, a small hygiene defect worth a candidate noting):
  attune-rag download figure declared uninterpreted noise
  (2026-07-12).
- DEC-7 amendment (2026-07-17): 10.5.0 tagged mid-window as a
  deliberate probe; read scheduled with tag-date + external
  responses on 2026-07-27.

## PACK-3 — Live gaps and evidence (chair memory + receipts)

- **Ping signal ≈ 0.** The pipeline is done and exemplary, but
  opted-in external signal is approximately zero. The chair's
  recorded frame: the real remaining task is talking to ~5 real
  users, not more pipeline. "Hundreds of users" figures are pepy
  badge vanity, explicitly not evidence.
- **reach_snapshot rate-limit soft-fail** (receipt 2026-07-17,
  v10.5.0 close-out): the script EXITS 0 on pypistats rate-limit;
  three retries across ~90 min all captured 0/5 packages, each
  background task reporting "completed, exit 0" — the R4 tag-time
  before/after pair failed silently for that release. The 429
  penalty outlasted 50+ minutes; post-release retries are a
  tar-pit.
- **R5 freshness watchdog**: templates exist under
  `src/attune/ops/templates/` (telemetry.html, home.html) — the
  drafter should treat the watchdog as shipped-or-partial per
  PACK-2's dashboard surfaces, and any residual R5 claim must cite
  what is actually missing rather than restating the requirement.
- The original done-when is nearly satisfied EXCEPT the
  before/after reach pair failed at 10.5.0 (rate-limit) and the
  outcome question ("did anyone else use it") remains unanswered
  by data.

## PACK-4 — Citable sources

- docs/specs/usage-signals/requirements.md (frozen 2026-06-11)
- docs/specs/usage-signals/decisions.md (D1–D13 + DEC-7 amendment)
- docs/specs/usage-signals/phase2-design.md
- docs/specs/usage-signals/snapshots/ (dated JSONs → 2026-07-18)
- src/attune/telemetry/usage_ping.py
- scripts/reach_snapshot.py
- website/lib/usage/{validate,rate-limit}.ts
- src/attune/ops/templates/ (telemetry.html, home.html)
```

### #2 — event (moderator)

```text
scheduled-assignment
```

### #3 — position (antigravity)

```text
## Requirements

**RR-1 — Shipped Baseline, Opt-In Telemetry Pipeline, and Privacy Controls**

**Rationale**: Phase 0 package baseline inventory (D1) and the Phase 2 opt-in usage ping pipeline (`src/attune/telemetry/usage_ping.py`, `website/lib/usage/{validate,rate-limit}.ts`) are shipped end-to-end and verified live. Opt-in consent prompts (D9/D11/D12) have been deployed across CLI, plugin, and MCP channels. This infrastructure is considered complete and must be maintained without expanding payload scope.

- Maintain default-OFF telemetry stance with explicit `DO_NOT_TRACK` and `ATTUNE_USAGE_PING` environment overrides.
- Preserve strict schema validation and rate-limiting across ingest endpoints without adding unprompted payload attributes.

**RR-2 — Dashboard Operations Surface and Freshness Watchdog Integrity**

**Rationale**: The ops dashboard panels (`src/attune/ops/templates/telemetry.html`, `home.html`) and spend anomaly alarm (D13 / R6) are shipped. The telemetry freshness watchdog (R5) requires monitoring `usage.jsonl` last-write age (>48h flag) against existing templates rather than re-creating dashboard surfaces.

- Render reach, data freshness, and daily spend anomaly indicators on the primary ops dashboard using existing templates under `src/attune/ops/templates/`.
- Verify the >48h last-write freshness alarm for `usage.jsonl` with automated regression tests to prevent silent logging stalls.

**RR-3 — Reach Snapshot Error Handling and Rate-Limit Resilience**

**Rationale**: The snapshot tool `scripts/reach_snapshot.py` (D3) soft-failed during the v10.5.0 release tag ritual by returning exit code 0 when encountering pypistats HTTP 429 rate limits. This caused silent recording of 0/5 packages across retries and broke the required R4 tag-time before/after reach comparison pair.

- Update `scripts/reach_snapshot.py` to detect HTTP 429 rate-limit responses and fail with a non-zero exit code instead of writing zeroed package data.
- Ensure tag-time release rituals capture valid before/after reach snapshots in `docs/specs/usage-signals/snapshots/` or alert on rate-limit blockage.

**RR-4 — Direct User Outreach for Qualitative Adoption Discovery**

**Rationale**: Despite a fully operational telemetry pipeline, opted-in signal volume remains near zero. Building additional automated telemetry pipelines or relying on vanity metrics (such as Pepy download counts, declared as uninterpreted noise in D11) will not yield actionable insight. Grounded progress requires direct qualitative feedback from real users.

- Conduct qualitative interviews with at least 5 active external users to evaluate actual workflow usage and needs.
- Exclude Pepy download metrics and unvalidated third-party counters from adoption evaluations.

**RR-5 — DEC-7 Probe Evaluation and Decision Ledger Hygiene**

**Rationale**: The DEC-7 amendment tagged release v10.5.0 as a deliberate probe with evaluation scheduled for 2026-07-27. Additionally, `docs/specs/usage-signals/decisions.md` contains a duplicate "D11" entry that requires structural correction.

- Execute the scheduled read of the v10.5.0 release probe on 2026-07-27, evaluating tag-date baseline snapshots against external response signals.
- Renumber the duplicate D11 entry in `docs/specs/usage-signals/decisions.md` to maintain decision ledger integrity.

## Non-goals

- Adding mandatory, opt-out, or expanded payload instrumentation to any client surface.
- Developing additional automated ingestion pipelines prior to completing qualitative user interviews.
- Treating Pepy download counts or third-party badge metrics as evidence of real user engagement.
- Re-architecting shipped ops dashboard templates in `src/attune/ops/templates/`.

## Open questions

- If qualitative interviews with 5 real users demonstrate zero external adoption, should the opt-in ping telemetry infrastructure be formally deprecated or retained in a dormant state?
- How should the release tag ritual handle extended pypistats rate-limiting (>50 minutes) without stalling release publication pipelines?
```

### #4 — position (claude)

```text
6. **RR-1:** The bullets ("Maintain default-OFF…", "Preserve strict schema validation…") restate outcomes that PACK-2 records as SHIPPED (D1 baseline; D5–D8 opt-in ping end-to-end with payload enumerated; D9/D11/D12 default-OFF + consent) as though they were open requirements. The task's grounding pack directive is explicit: "do not restate shipped requirements as open work." This content belongs in a DONE/status framing (or is already covered by the Non-goals), not as active requirement bullets — as written it pads the open scope with completed work.

1. **RR-2:** PACK-3's R5 note explicitly instructs that "any residual R5 claim must cite what is actually missing rather than restating the requirement." RR-2 does the opposite — it demands "automated regression tests" for the >48h `usage.jsonl` alarm without first establishing whether that alarm and test already exist. Given `src/attune/ops/templates/{telemetry.html,home.html}` are shipped surfaces and the original R5 (PACK-1) already called for a "freshness regression test," the drafter needed to probe the current watchdog state and name the concrete missing piece (does the >48h flag fire? is there a regression test?) before writing it as open work. As written it risks re-scoping shipped work as open — the exact failure the task warns against.

2. **RR-2:** The rationale conflates two distinct R-items into one bullet — it asserts the spend alarm (D13/R6, PACK-2) is shipped (correct) but then treats freshness (R5) as unverified, all under one requirement. Split the DONE portion (spend + reach panels, per PACK-2 D13 and `src/attune/ops/templates/`) from the genuinely-open portion (freshness verification) so the chair can mark done-vs-remaining honestly per the task framing.

3. **RR-4:** The chair's recorded frame in PACK-3 is "talking to ~5 real users," but ping signal ≈ 0 (PACK-3) means the opted-in population is essentially unidentifiable — the requirement provides no recruitment/identification path. "Conduct qualitative interviews with at least 5 active external users" is unactionable when zero telemetry (`src/attune/telemetry/usage_ping.py` signal ≈ 0) exists to locate them; the requirement must name how those users are found (marketplace, GitHub, direct outreach) or it inherits the same tar-pit as the failed reach pair.

4. **RR-5:** Per PACK-3's reach_snapshot receipt (2026-07-17) the v10.5.0 tag-time before/after pair FAILED (0/5, rate-limited, `scripts/reach_snapshot.py`), yet RR-5 schedules the 2026-07-27 DEC-7 read to evaluate "tag-date baseline snapshots against external response signals." The snapshot data that read depends on (`docs/specs/usage-signals/snapshots/`) is compromised for 10.5.0. RR-5 must either sequence the RR-3 fix as a prerequisite or acknowledge the 10.5.0 baseline is a hole — otherwise the scheduled read evaluates against zeroed data.

5. **MISSING:** No refreshed Done-when / acceptance section. PACK-1's done-when and PACK-3's closing note ("original done-when is nearly satisfied EXCEPT the before/after reach pair failed at 10.5.0 and the outcome question remains unanswered by data") are the crux of this refresh — the spec should restate the done-when as: reach + freshness + spend panels shipped (done), opt-in question decided (done), and the ONLY two open conditions being (a) a successful before/after reach pair and (b) a data-or-qualitative answer to "did anyone else use it." Without this the reader can't tell the spec is ~80% done.

7. **RR-5:** The duplicate-D11 renumbering is grounded (PACK-2 flags the duplicate D11 as "a small hygiene defect worth a candidate noting"), but renumbering a historical ledger entry in `docs/specs/usage-signals/decisions.md` can break existing cross-references to "D11" (e.g. the attune-rag-noise decision). A note/annotation is what the pack asked for ("worth noting"), not necessarily a renumber. Downgrade to annotating the collision rather than mutating shipped decision IDs.

VERDICT: needs-revision
```

### #5 — position (codex)

```text
1. **RR-1:** This is labeled as a requirement but describes completed work without an explicit `DONE` status. Separate shipped facts from residual obligations and cite the verifying decisions individually; `docs/specs/usage-signals/decisions.md` D1 and D5–D12 support completion, while `src/attune/telemetry/usage_ping.py` supports the current privacy behavior.

2. **RR-1:** “Must be maintained without expanding payload scope” creates an indefinite maintenance requirement not established by PACK-2. The supported constraint is that payload expansion requires an explicit privacy decision and audit, not that expansion is permanently prohibited; see PACK-1 R2 and `docs/specs/usage-signals/phase2-design.md`.

3. **RR-2:** The rationale says the dashboard panels are shipped, but the first acceptance bullet requires rendering those panels. This restates potentially completed scope as open work. PACK-3 explicitly requires classifying R5 as shipped-or-partial only after identifying the concrete missing behavior in `src/attune/ops/templates/telemetry.html` and `src/attune/ops/templates/home.html`.

4. **RR-2:** “Verify” is not a sufficiently testable residual requirement. Name the existing implementation and missing test path, or mark R5 `DONE` if the >48-hour behavior and regression test already exist. PACK-3 forbids merely restating the original watchdog requirement without evidence of what remains missing.

5. **RR-3:** The requirement over-specifies HTTP 429 handling while under-specifying the actual safety invariant. `scripts/reach_snapshot.py` must return nonzero for any incomplete required-package snapshot, avoid publishing a misleading artifact, and report which packages failed; otherwise non-429 failures can reproduce the same silent 0/5 outcome documented in PACK-3.

6. **RR-3:** “Capture valid before/after snapshots or alert” is ambiguous about release behavior and validity. Define whether release publication proceeds, what constitutes a valid snapshot, and how a blocked comparison is recorded after extended rate limiting. PACK-3 says repeated post-release retries became a tar-pit, so retrying until success cannot be the implicit criterion.

7. **RR-4:** “At least 5 active external users” lacks a recruitment definition, evidence artifact, and completion criterion. Specify how “external” and “active” are established, where interview findings are recorded, and what synthesized output answers the usage question; PACK-3 supports talking to approximately five real users, not merely counting interviews.

8. **RR-4:** The requirement drifts from discovering “which workflows external users run” into broadly evaluating “usage and needs.” Constrain the interview protocol to the unresolved adoption and workflow-use questions from PACK-1 and PACK-3 to avoid inventing product-research scope.

9. **RR-5:** The scheduled probe comparison is internally impossible as written because PACK-3 states the v10.5.0 tag-time before/after pair failed. The 2026-07-27 read should explicitly record the missing quantitative evidence, evaluate whatever external responses actually exist, and avoid presenting a non-comparable snapshot as a baseline; cite the DEC-7 amendment in `docs/specs/usage-signals/decisions.md`.

10. **RR-5:** Blindly renumbering the duplicate D11 can invalidate existing references. Require a unique corrective identifier or an explicit renumbering map while preserving historical traceability in `docs/specs/usage-signals/decisions.md`.

11. **MISSING:** The refresh needs an explicit status taxonomy such as `DONE`, `PARTIAL`, and `OPEN`. Without it, RR-1 and RR-2 continue mixing shipped reality with remaining work, contrary to the grounding pack’s central instruction and PACK-2’s D1–D13 evidence.

12. **MISSING:** There is no refreshed done-when section. It should cover the concrete residual outcomes: snapshot failures become visible and non-misleading, R5’s actual residual is verified or closed, the DEC-7 read is recorded, and five-user findings answer the external-use question. The original done-when in PACK-1 is no longer an honest acceptance boundary.

VERDICT: needs-revision
```

### #6 — synthesis (moderator)

```text
status: failed
conditions: LINT_DIRTY
staged: 0 | deferred_over_cap: 0

## Failures / degradations (receipts)
{"code": "LINT_DIRTY", "run_id": "producing-usage-signals-refresh-20260719", "thread": "producing-usage-signals-refresh-20260719", "round": 3, "seat": "antigravity", "role": "drafter", "detail": "dirty after the one repair round", "evidence": "RR-1: missing convergence tag (agreed / 2-1 / contested)\nRR-2: missing convergence tag (agreed / 2-1 / contested)\nRR-3: missing convergence tag (agreed / 2-1 / contested)\nRR-4: missing convergence tag (agreed / 2-1 / contested)\nRR-5: missing convergence tag (agreed / 2-1 / contested)"}
```
