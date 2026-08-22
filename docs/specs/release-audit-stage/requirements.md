# Release Audit Stage — Requirements

**Status:** approved (chair, 2026-08-22) — triage of 24 critique
items ratified in session; D1–D6 ratified; OQ1 resolved (releases);
OQ2–OQ3 folded into R2/R5.
**Slug:** `release-audit-stage`
**Provenance:** roundtable `q-release-audit-roundtable-stage-001`
(2026-08-22, 3/3 seats, round-1 convergence halt; round-2
draft+critique loop: Claude drafter, Codex + Antigravity critics,
both lint-clean, 24 items triaged — 21 accepted, 2
accepted-modified, 1 declined-with-reason). Curated stub:
[docs/reports/roundtable/q-release-audit-roundtable-stage-001.md](../../reports/roundtable/q-release-audit-roundtable-stage-001.md).
Full transcript machine-local at `~/.attune/reports/roundtable/`.

## Problem

Three release surfaces exist and none of them looks at the diff:

| Surface | Covers |
|---|---|
| `attune workflow run release-gate` | bandit / ruff / pytest vs hard thresholds — hygiene |
| `attune-release-check` skill | version not on PyPI, clean tree, CI green, changelog — hygiene |
| `release-execute` skill | publish mechanics with per-step postconditions |
| `release_notes` MCP tool | advisory go/no-go with no evidence about this diff |

Nothing asks **what class of defect this release could have
introduced.** The library review answered that for the tree as of
2026-08-20 and produced a 26-class register — but a register is a
snapshot, and 15 of its 26 classes have no tree-scanning gate:

- **7 fixed-but-ungated** (H1, G1, G2, I-4, I-3, H2, H5) — confirmed
  and fixed with executed receipts; nothing prevents the same shape
  re-entering on a new diff.
- **8 open** — confirmed, unmechanized.

That certain-and-invisible risk is what this spec catches. The
register's measured premise governs the design:

> Review is the right tool for FINDING A CLASS and the wrong tool for
> ENUMERATING ITS INSTANCES. Only the gate is permanent.

Evidence: the attune-forms review (3-seat table designed the funnel;
a SINGLE reviewer found all 23 confirmed defects) and attune-ai batch
2 (3 reviewers, ~450k tokens, 8 instances of one class; mechanizing
that class took ~20 minutes and found 84 more at zero false
positives).

## Goal

Every release carries a receipt about its own diff's class exposure,
produced mostly mechanically, with a bounded deliberative sitting on
the residual — and the fixed-but-ungated set **shrinks** over
releases rather than accumulating.

## Blocking prerequisite

`sweep_suite_v2_r7.py` (157 lines) and `CLASS-REGISTER.md` are
machine-local scratch under `~/.attune/reports/attune-ai-review/`.
Stage steps 1–3 read both. Phase 0 is not a follow-on — nothing else
here is buildable until it lands.

## Requirements

### R1 — The rule pack is tracked code

A rule pack under `src/attune/classes/`; each rule a callable plus
metadata `{id, invariant, calibration, fixtures}`.

- **Calibration receipt schema** (Codex#1 + Agy#1, convergent):
  `{repo, recall, precision, date, fixture_hash}`. A rule is
  `calibrated-here` only when its repo field matches the current
  repo's canonical identity (normalized `origin` slug, directory-name
  fallback — the session-start-integrity D1 convention) AND its
  pinned fixtures pass. Corpus recall/precision are **recorded
  honestly, not thresholded** — the register's own shipped standard
  is 8/11 recall, and pretending to 1.0 would be fiction (Agy#1
  declined on this point, ledgered).
- Any populated-but-non-matching calibration object is
  `uncalibrated-here`: advisory, never blocks, never clears.
- **Scan path semantics** (Codex#2, accepted-modified into
  acceptance): `attune classes scan --paths <changed>` takes
  normalized repo-relative paths; deleted files are skipped, renames
  scan the new path, binary/generated files are excluded by the same
  filters the sweep suite used.
- **Fail closed** (Agy#7): a rule callable crash or timeout marks the
  class `SCAN-ERROR`, lands in packet §2, and aborts the stage unless
  the chair explicitly waives — a failed gatekeeper fails the gate
  (contract §7).
- Acceptance: scan runs in CI on this repo; the 2026-08-20
  calibration fixtures pass as pinned tests; a deliberately-crashing
  fixture rule produces `SCAN-ERROR` and a non-zero exit.

### R2 — The status column is DERIVED, never authored

`attune classes register` computes each class's status:

| gate present + passing? | full-repo hits | active DEFER? | derived status |
|---|---|---|---|
| yes | 0 | — | CLOSED |
| no | 0 | no | FIXED BUT UNGATED |
| no | >0 | no | OPEN |
| no | any | yes, unexpired | DEFERRED |
| yes | >0 | — | **BROKEN GATE — loud** |

- **Full-repo hits, never the changed-file sweep** (Codex#4): status
  derives from a whole-tree scan; changed-file hits are reserved for
  release exposure analysis. Deriving from a partial scan would
  falsely report CLOSED.
- **Gate mapping is identity, not existence** (Codex#3): the mapping
  references stable test node IDs plus the asserted class id, and the
  drift guard checks both existence and identity — a renamed or
  reassigned gate must not preserve CLOSED.
- **CLOSED requires the gate PASSING** (Agy#2), confirmed at
  reconcile time — presence on disk is not a gate.
- **DEFERRED state** (Agy#2): an unexpired DEFER record renders as
  its own status, so the register and the stage evaluator agree.
- Acceptance: derived output matches the 2026-08-20 hand-maintained
  register on hand-check; a renamed gate test in a fixture repo trips
  the drift guard; a fixture DEFER renders DEFERRED and flips back at
  expiry.

### R3 — The six-step stage inside /release

```text
0  baseline    merge-base diff vs last release tag
1  reconcile   CLOSED gates green in CI (bound receipt)
2  diff sweep  rules over changed files, weighted to fixed-but-ungated
3  residual    hits + ungated exposure + new-boundary inventory
4  sitting     one round, three seats, no rebuttal loop
5  chair       rules per item; manifest written
```

- **Baseline definition** (Codex#5 + Agy#3, convergent):
  `git diff $(git merge-base <last-release-tag> HEAD)..HEAD`, with a
  `--baseline <ref>` override. The resolved baseline SHA is recorded
  in the manifest. No valid baseline (no tag, shallow clone) fails
  closed with a preflight error — never a guessed range.
- **Reconcile receipt binding** (Codex#6): the receipt names an
  allowlisted workflow, the repository, the HEAD SHA, and a
  successful conclusion. A green run for an earlier commit does not
  authorize.
- **Disposition vocabulary + completion invariant** (Codex#7): chair
  dispositions are exactly `SHIP | HOLD | GATE-FIRST | DEFER`; the
  stage is complete only when every residual item id carries exactly
  one ruling — missing or duplicate rulings reject the manifest.
- Reconcile red at step 1 aborts before any sitting. An empty
  residual still sits (one-page packet, minutes) — the near-zero cost
  floor is what makes the every-release ruling payable.
- Acceptance: one full dry run on a real release diff produces a
  valid manifest; a no-tag fixture repo fails preflight closed.

### R4 — The residual packet (versioned schema v1)

Hard caps: ≤1500 words, ≤12 residual items, ≤20 sweep rows, zero diff
hunks, no file contents. The schema below is normative (Codex#8 +
Agy#4, convergent — no reference-only sections):

| § | Content | Required fields |
|---|---|---|
| 0 | Header | tag range, baseline SHA, files changed, packages touched, public symbols added/removed |
| 1 | Reconcile receipt | CI run id, workflow name, HEAD SHA, conclusion |
| 2 | Sweep hits | class id, `file:line`, one-line excerpt, rule recall/precision, any `SCAN-ERROR` |
| 3 | Ungated exposure | per fixed-but-ungated class: boolean over changed surface + file (matrix only — never warning-severity rows competing with hits; OQ2 resolved) |
| 4 | New-boundary inventory | boundary kind + two program points each |
| 5 | Open-class exposure | class id + file |
| 6 | Explicit NULL section | what the diff does NOT introduce |
| 7 | Default dispositions | one pre-filled disposition per item |

- **Over-cap refusal** (Agy#4): exit code 2 with structured JSON
  diagnostics — the chair splits the release; the builder never
  truncates.
- **Split semantics** (Codex#9, accepted-modified): each chair-chosen
  partition re-runs baseline → sweep → exposure independently; the
  auto-partition proposer is declined — the chair splits, the tool
  re-runs.
- §7 is the anti-mush mechanism: seats AMEND pre-filled dispositions
  per item number, one closing paragraph maximum — they never compose
  from a dump.
- Acceptance: builder emits all 8 sections from a real diff; an
  over-cap diff exits 2 with the split diagnostic, untruncated.

### R5 — Teeth

- A calibrated rule HIT on a fixed-but-ungated class **re-exposed by
  the diff** blocks the release until the class gets its gate.
  Exposure warns via §3 only.
- **Re-exposure operationally defined** (Codex#10): a finding present
  at HEAD and absent at baseline, compared by stable finding identity
  (class id + normalized path + structural anchor, rename-tracked).
  Pre-existing findings are register debt, not release blocks.
- **DEFER record** (Codex#11 + Agy#5, convergent): tracked YAML at
  `.attune/defers/<class_id>.yaml` —
  `{class_id, finding_identity, owner, reason, approved_at,
  created_sha, expires_after_releases, chair_receipt}`. Validated by
  `attune classes register`; a record missing chair_receipt or scoped
  wider than one class is rejected.
- **Expiry unit: releases** (OQ1 RESOLVED — both critics converged on
  release count): at expiry the block resumes automatically. The
  block resuming IS the convergence mechanism.
- **Arming gate** (Codex#16): Phase 2 arms only on a chair-recorded
  promotion naming the validated rule-pack version, after Phase 1 has
  produced at least one clean dry-run manifest.
- Acceptance: a deliberately re-exposed fixture class blocks; an
  expired DEFER re-blocks; boundary tests pin the exact expiration
  transition.

### R6 — Class M by receipt-type declaration

- **Receipt-type enum** (Codex#14): `suite | behavioral | live-fire |
  metric | evidence-chain` — the decision-routine taxonomy verbatim.
  Admissibility: a boundary-class fix requires `behavioral` or
  `live-fire`.
- **Metadata schema, fail closed** (Codex#13): the check reads a
  validated declaration naming the class id; a changed fix touching a
  boundary class with no declaration fails the check — absence is not
  a pass.
- **Survives squash** (Agy#6): enforcement is at PR CI, and the
  release-stage sweep re-verifies commit trailers
  (`Receipt-Type:`, `Evidence:`) across the release baseline for all
  commits touching boundary classes — PR metadata detaches on squash;
  trailers do not.
- Attestations carry an evidence pointer and receipt type, never a
  bare yes.
- Three AST shapes seed a detector **worklist, never a verdict**:
  mock-only-assertion patched call sites; test-local literals fed to
  a deserializer whose paired writer exists (I-4 mirrored into
  tests); "cannot write" tests that patch instead of chmod.
- Independent of R1–R5; may ship first.
- Acceptance: metadata check fires on a fixture PR declaring `suite`
  for a boundary-class fix; trailer re-verification catches a
  squashed fixture commit; worklist detector emits its three shapes
  on pinned fixtures.

### R7 — The chair manifest (Codex#15 + Agy#8, convergent)

`.attune/release-manifests/<tag>.json`, schema-versioned:
`{tag, head_sha, baseline_sha, packet_hash, reconcile_receipt,
per_item_dispositions, defer_refs, sitting_delta, chair_receipt}`.

- Immutable once written; a re-run writes a new manifest.
- **`sitting_delta` — the sitting instruments itself** (D9): a
  boolean per residual item recording whether any seat amendment
  changed the chair's final disposition from the packet's §7
  pre-filled default, plus the release-over-release tally. The same
  retire-by-evidence instrument ruled for role (b): if the sitting
  changes no disposition across ~6 releases, the every-release
  ruling (D2) has earned its own review — by measurement, not
  argument.
- **Required input to `release-execute`** — the publish path verifies
  a valid manifest exists for the tag being cut, connecting the stage
  to deployment instead of leaving it advisory-by-accident.
- Acceptance: `release-execute` refuses a tag with no manifest;
  manifest validation rejects missing/duplicate item rulings (R3);
  `sitting_delta` is required — a manifest without it is invalid.

## Phases

| Phase | Scope | Gate |
|---|---|---|
| **0** | R1 + R2 | scan + register in CI; derived status matches 2026-08-20 register; SCAN-ERROR fixture fails closed |
| **1** | R3 + R4 + R7 | one clean dry-run manifest on a real release diff |
| **2** | R5 armed | chair-recorded promotion naming rule-pack version (Codex#16) |
| **X** | R6 | independent; may ship first |

## Non-goals

- Seats do not detect defects in the diff (ruled out on measured
  evidence: 450k tokens → 8 instances of one class).
- Seats do not name new defect classes this cycle (held; only the
  instrumented candidate form may return — see the curated stub).
- The stage does not replace `release-gate`, `attune-release-check`,
  or `release-execute`; it covers the diff-risk gap they leave.
- No auto-partition proposer for over-cap releases (declined,
  Codex#9-as-filed): the chair splits, the tool re-runs.

## Dissent register

- **Agy#1 (calibration bar `recall == 1.0`): DECLINED.** Seat's
  claim: calibrated status should require perfect recall on
  repo-pinned positive fixtures. Lead's reason: conflates
  fixture-pinning (which must pass) with corpus recall (which is
  recorded, not thresholded) — the register's own shipped calibration
  standard is 8/11 recall, honestly stated; a 1.0 bar would either
  block every real rule or invite fixture-shrinking to meet it.
  Fixture passage is required; corpus metrics are receipts, not
  gates.

## Resolved questions

- **OQ1 — expiry unit: RELEASES** (both critics convergent; ratified
  with the triage).
- **OQ2 — exposure rendering: §3 boolean matrix only** (folded into
  R4; ratified with the triage batch).
- **OQ3 — rule→gate mapping drift: folded into R2** (identity-checked
  mapping + drift guard; Codex#3).
