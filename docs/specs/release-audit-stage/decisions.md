# Release Audit Stage — Decisions

Append-only. Chair rules; the lead records.

## D1 — Stage inside /release (RATIFIED chair 2026-08-22)

Not a separate command, not a headless routine. One surface; the
audit runs where the release already runs. (Roundtable
`q-release-audit-roundtable-stage-001` intake form.)

## D2 — The table sits every release (RATIFIED chair 2026-08-22)

Not gated on residual size. The register makes an empty residual
nearly impossible (15/26 classes ungated or open), and the moderator's
"only when non-empty" gate would have fired every release anyway —
same rule, less machinery. Payability comes from the near-zero cost
floor of an empty-residual sitting (R3), not from skipping.

## D3 — Seat roles (RATIFIED chair 2026-08-22)

(a) advise ship/hold per residual item: IN. (c) rank which
ungated/open classes need a gate before this release: IN. (d) detect
defects in the diff: OUT — settled by measurement (attune-forms: the
single reviewer found all 23 defects; batch 2: 450k tokens for 8
instances of one class). (b) name a NEW class from a diff summary:
HELD, not promoted — 2 seats no, 1 qualified yes; may return only in
the instrumented form (candidate + confirm recipe, never blocking,
tallied candidates-named vs candidates-confirmed so the role retires
itself by evidence).

## D4 — Teeth (RATIFIED chair 2026-08-22)

`gate-before-ship` HAS TEETH: the stage may hold a release until a
fixed-but-ungated class re-exposed by the diff gets its gate.
Advisory-only rejected — an advisory stage reports a growing set
while nothing forces it to shrink. (Both external seats independently
asked this exact question, blind to each other — msgs 5 and 6.)

## D5 — Trigger: hit blocks, exposure warns (RATIFIED chair 2026-08-22)

A calibrated rule HIT blocks. Surface EXPOSURE warns via the packet's
§3 boolean matrix only — never warning-severity rows competing with
hits for the packet's cap (a noisy gate gets allowlisted into
uselessness). Chair confirmed the moderator's narrowing with the
round-2 triage batch (former OQ2).

## D6 — Escape: DEFER with owner and expiry (RATIFIED chair 2026-08-22)

Chair overruled the moderator's lighter one-line record toward more
rigor. The expiry is not a reminder — at expiry the block RESUMES,
which is the convergence mechanism D4 reaches for. Schema and
tracked-file location in R5 (round-2 convergent critique, Codex#11 +
Agy#5).

## D7 — Round-2 critique triage (RATIFIED chair 2026-08-22, batch)

Claude drafted; Codex and Antigravity critiqued (both lint-clean;
Codex `needs-revision` with 16 items, Antigravity `ready-with-edits`
with 8). Triage: 21 ACCEPTED (6 convergent-pair defects among them),
2 ACCEPTED-MODIFIED (Codex#9 split semantics — partition re-runs
accepted, auto-partition proposer declined; Codex#2 path semantics —
folded into R1 acceptance), 1 DECLINED with reason (Agy#1 perfect-
recall calibration bar — see the dissent register in
requirements.md). OQ1 resolved to release-count expiry on convergent
critic recommendation.

## D8 — Phase order (RATIFIED chair 2026-08-22)

Item 1 (the stage) carries item 4 (derived status column) as its
Phase 0 — the stage's steps 1–3 read artifacts that are machine-local
scratch today, so the rule-pack promotion is the critical path, not a
side finding. Item 3 (class M by receipt declaration) is Phase X:
independent, may ship first.

## D9 — The sitting instruments itself (RATIFIED chair 2026-08-22)

From the post-spec feedback review: roles (a)/(c) had no instrument
while role (b) did. The manifest's `sitting_delta` field records, per
release, whether the sitting changed any disposition from the §7
pre-filled defaults. Zero deltas across ~6 releases puts D2 (the
every-release sitting) up for review by measurement rather than
argument — the same retire-by-evidence mechanism ruled for role (b).

## D10 — The sweep is package-scoped (RATIFIED chair 2026-08-22)

The per-release sweep scans `src/` only. Amends R1's scan-path
semantics, which named no root.

**Why.** The rule pack's calibration receipts were measured against
PACKAGE sites — the R7 receipt is "11 confirmed sites fixed in PR #2121"
in `src/attune`. Running those rules over `tests/` is
out-of-distribution: the recorded recall/precision does not transfer,
and a test that does `data = json.loads(fixture); data["k"]` is
controlled input, not the malformed-input class the rule targets.

**The measurement that forced it.** The stage's first live run, on the
real `v13.0.2..HEAD` release diff, produced **8/8 blocking hits, all in
test files**. Under D5 that would have held 14.0.0 on eight false
positives — precisely the failure D5 names, "a noisy gate gets
allowlisted into uselessness". Rescanning scoped: 53 changed files, 20
swept, **0 blocking**, and §0 still names all nine removed public
symbols. The breaking change stays visible; the noise goes.

**Scope of this ruling — narrow, deliberately.** It governs the
per-release SWEEP only. Continuous gates keep scanning the whole tree,
and narrowing THEM is the opposite call. Evidence from the same
session: the `ast.parse` null-byte gate was scoped to `src/attune` and
therefore never saw ITSELF; widening it surfaced 14 ValueError-blind
sites, 12 of them long-standing, four in gates or CI scripts. A
scope exclusion makes a gate blind in a way that looks like health.

**The counter-position, recorded.** The lead argued against scoping by
path at all, proposing instead that a hit BLOCKS only where the rule's
calibration matches the surface it was measured on, while everything
scanned stays visible as an advisory §2 row — same clearing of 14.0.0,
without buying it by not looking. The chair chose the simpler path
scope. Consequence accepted: defect shapes in `tests/` and `scripts/`
are outside the per-release audit and rely on continuous gates instead.

**Anti-blindness requirement.** Because a narrowed sweep must not read
like a clean one, the packet's §0 reports `files_changed`,
`files_swept`, `files_not_swept`, and `sweep_scope`. An empty residual
is never ambiguous between "no defects here" and "did not look here".
