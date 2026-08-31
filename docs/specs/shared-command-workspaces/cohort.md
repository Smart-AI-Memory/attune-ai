# Shared Command Workspace Cohort Ledger

**Selection basis:** receipts from Roundtable, Spec, `/release-prep`, and
`/bug-predict`; ordered under the chair's persisted `auto_run=true` ruling.
The order prioritizes semantic risk and contract pressure, not implementation
cost. Roundtable and Spec are pilots; the numbered cohort below is the next ten
examples requested by the chair.

## Selection evidence from pilots and leading cohort adapters

| Adapter | Semantic cells covered | Failure-sensitive receipt |
| --- | --- | --- |
| Roundtable | nested rounds, progress vs authority, fixed roster, bounded pagination, per-item rulings | nine accepted seat receipts, synthesis id, seven one-item ruling pages, stale nested action rejection, terminal board receipt |
| Spec | tree-derived intake, artifact creation, redo/approve/resume, lifecycle/task gates, persisted recovery | exact artifact paths and probes, seven parsed task ids, BLOCKED/CHAIR_REQUIRED rejection tests, state save payload |
| `/release-prep` | repeated fail-closed gatekeepers, warning acceptance, separate final approval | four named real-probe receipts, missing/error blocker tests, four bound accepts, confirmed terminal approval |
| `/bug-predict` | immediate read-only execution, progress-only publication, truthful success/failure terminal | zero initial actions/nonce, terminal finding receipt, explicit “did not complete” failure fixture |

## Chair-approved ordered cohort

| # | Command | Missing semantic axis | Failure-sensitive live receipt | Slice rollback boundary |
| ---: | --- | --- | --- | --- |
| 1 | `/release-prep` | repeated multi-gate authority | four named gate probes plus separately confirmed terminal approval; missing/error gatekeepers remain blockers | release-prep adapter, registration, skill projection, tests |
| 2 | `/bug-predict` | read-only work without synthetic confirmation | validated target, zero initial actions, truthful success or “did not complete” terminal | bug-predict adapter, registration, skill projection, tests |
| 3 | `/bulk` | asynchronous external submission and later reconnect | exact accepted task count plus provider batch id; rejection/timeout must never render “submitted” | bulk adapter, registration, skill projection, tests |
| 4 | `/memory-and-context` | durable external state, privacy classification, destructive forget | store→retrieve evidence for the same classified key; forget requires a separately bound confirmation and a post-delete miss | memory adapter, registration, skill projection, tests |
| 5 | `/smart-test` | authority escalation from read-only audit to generated file writes and validation | proposed paths before approval, exact written-file hashes, actual test exit/result; generator failure cannot claim tests were created | smart-test adapter, registration, skill projection, tests |
| 6 | `/doc-gen` | previewable artifact mutation with import/reality validation | proposed doc targets, confirmed apply, exact changed paths/hashes, doc-import probe; partial write is a failed receipt | doc-gen adapter, registration, skill projection, tests |
| 7 | `/workflow-orchestration` | fan-out/fan-in with mixed child outcomes | one receipt per requested child in stable order; aggregate cannot be clean while a child is missing/error | orchestration adapter, registration, skill projection, tests |
| 8 | `/image-analysis` | validated multimodal input and provider boundary | canonical image path, MIME/dimensions/hash, provider success/error; decode/provider failure cannot render an empty successful analysis | image-analysis adapter, registration, skill projection, tests |
| 9 | `/verify` | deterministic per-claim evidence chain and hard-gate option | claim, severity, evidence, and location per finding; any error keeps the hard gate failed | verify adapter, registration, skill projection, tests |
| 10 | `/security-audit` | severity-triggered remediation handoff without implicit mutation | files-scanned count and categorized findings, explicit incomplete-scan failure, separate bound handoff to Fix | security-audit adapter, registration, skill projection, tests |

## Cohort execution rule

Rows 1–2 shipped under Task 5; rows 3–10 are the separately gated Task 7
slices in this exact order. Every adapter must
record: lifecycle execution and verification gates, at least 90% changed-code
coverage, widget and Markdown/text fallback parity, a live terminal receipt,
any shared-core change, and the exact rollback boundary above. A failed slice
stops before the next row even under auto-run. The adapter interface remains
provisional until receipt 10 is complete.

Task 6 introduces no production change and no shared-core change.

## Cohort receipts

| # | Status | Adapter LOC | Core change | Coverage | Fallback/live receipt | Failures and rollback |
| ---: | --- | ---: | --- | ---: | --- | --- |
| 1 `/release-prep` | verified | 441 | none | 97.56% branch | four named real-probe gate receipts, four separately bound accepts, and final confirmed approval reached widget + Markdown terminal through the real host | missing/error critical gatekeepers remain blockers; rollback is `release_prep.py`, registration/exports, skill projection, tests, and this row |
| 2 `/bug-predict` | verified | 316 | none | 99.08% branch | validated real repository path opened read-only with zero initial actions; success and explicit “did not complete” paths reached widget + Markdown terminal with no model spend | malformed/incomplete producer results fail closed; rollback is `bug_predict.py`, registration/exports, skill projection, tests, and this row |
| 3 `/bulk` | verified | 345 | none | 99.22% branch | widget + Markdown submission and pending reconnect receipts reached terminal through the real host; deterministic provider fixture used, no paid API call | rejection/timeout and partial-success claims fail closed; rollback is `bulk.py`, registration/exports, skill projection, tests, and this row |
| 4 `/memory-and-context` | verified | 400 | none | 90.51% branch | real host + ephemeral live backend stored/retrieved the same classified value by digest, then confirmed forget and post-delete miss; no durable user memory changed | mismatched value/classification, backend error, and still-present deletion fail closed; rollback is `memory_context.py`, registration/exports, skill projection, tests, and this row |
| 5 `/smart-test` | verified | 412 | none | 92.96% branch | real host consumed audit then confirmed generation; real disk hash and actual 14-test green probe reached widget + Markdown terminal; existing test file was a non-mutating write-boundary fixture | generator/test failure retains exact written paths and cannot claim success; rollback is `smart_test.py`, registration/exports, skill projection, tests, and this row |
| 6 `/doc-gen` | verified | 354 | none | 90.28% branch | real host consumed audit then confirmed apply; real cohort-ledger disk hash and executed heading-reality probe reached widget + Markdown terminal; existing changed doc was a non-mutating artifact fixture | partial writes/reality failure retain exact hashes and cannot claim success; rollback is `doc_gen.py`, registration/exports, skill projection, tests, and this row |
| 7 `/workflow-orchestration` | verified | 312 | none | 98.01% branch | real host collected exact already-executed security/test/docs probes out of order, then rendered stable requested order in widget + Markdown terminal; no paid children invoked | WARNING is degraded; FAIL/ERROR/MISSING blocks clean aggregate; rollback is `workflow_orchestration.py`, registration/exports, skill projection, tests, and this row |
| 8 `/image-analysis` | verified | 310 | none | 98.42% branch | real MCP server decoded real `og.png` as 1200×630 PNG with byte count/SHA-256, then actual no-key provider failure rendered “did not complete”; no network/model spend | invalid magic, extension mismatch, size/dimension error, empty success, and provider mismatch fail closed; rollback is `image_analysis.py`, registration/exports, skill projection, tests, and this row |
| 9 `/verify` | verified | 341 | none | 93.18% branch | real `attune_verify` checked imports/flags/links/counts on the cohort ledger and its exact clean result plus explicit empty ambient cross-check reached a hard-gate-passed widget + Markdown terminal | checker/cross-check failure is incomplete; deterministic errors alone control hard gate; rollback is `verify.py`, registration/exports, skill projection, tests, and this row |
| 10 `/security-audit` | verified | 366 | none | 96.15% branch | actual MCP execution without credentials returned the real SDK/CLI login failure, which the shared host rendered as an incomplete terminal receipt with no health score or clean claim; no model spend | failed/incomplete scans cannot report clean or a score; high/critical findings require a separately bound handoff action; rollback is `security_audit.py`, registration/exports, skill projection, tests, and this row |

Image boundary discovery: `docs/assets/images/empathy-brain-logo.png` has JPEG
bytes despite its `.png` extension (`file` and the adapter agree). The adapter
rejected it before provider execution. The asset itself is outside this
slice's rollback boundary and was not modified.

Verify boundary discovery: the first live probe showed `result.checked` is an
ordered category list, not an integer count. The adapter was corrected before
promotion and now preserves the exact `attune_verify` shape.

## Cohort promotion

All ten cohort adapters are registered in the chair-approved order. The
adapter interface is now stable at version 1: `create`, `project`, `apply`,
and the optional progress-only `publish` capability. No Task 7 slice changed
the shared core; future domain behavior remains adapter-owned.
