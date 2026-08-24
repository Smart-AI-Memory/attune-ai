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

## D11 — Manifest durability: release asset primary, tracked history optional (RATIFIED chair 2026-08-22)

**Basis, stated so a later reader can weigh it.** The chair asked where
the manifest should live after the lead flagged that `.attune/` is
gitignored; the lead recommended the shape below; the chair directed it
be written up as a decision. The chair has NOT yet ruled on the optional
tracked-history half — that is marked OPEN at the foot of this entry.

**The problem.** R7 puts the manifest at
`.attune/release-manifests/<tag>.json`, and `.gitignore` carries
`.attune/*` with explicit negations for `!.attune/defers/` and
`!.attune/class-dispositions.yaml`. The manifest matches neither, so it
is machine-local. Consequences: the receipt cannot be verified by anyone
who was not at the keyboard, a release cut from CI or a second machine
finds no manifest and `require_manifest` refuses, and the artifact that
records WHY a release was authorized does not survive the machine that
produced it. For something whose stated job is connecting the audit to
deployment, that is thinner than it reads.

**Why the obvious fix does not work.** Adding
`!.attune/release-manifests/` is one line and matches how defers are
already treated (D6 tracks defers precisely because an escape hatch must
be auditable). But the manifest is SHA-BOUND, and committing it changes
the SHA:

    audit SHA X  ->  manifest records head_sha = X
    commit the manifest  ->  creates SHA Y
    tag Y  ->  require_manifest(Y) REFUSES: the ruling names X

Tracking it naively breaks the binding that gives it its value. Noted
because it is the kind of thing that looks like a one-line change right
up until the gate refuses the release it was meant to authorize.

**Ruled.**

1. **Primary durability is a GitHub Release asset.** The manifest is
   attached to the release it authorized. No circularity — the release
   is created after the tag, so the artifact lands on the thing it
   ruled on. It is publicly verifiable, immutable by virtue of the
   release, and readable without access to the producing machine.
2. **The local file stays the gate's input.** `require_manifest` reads
   `.attune/release-manifests/<tag>.json` pre-tag, which is the only
   moment it needs to exist locally. No change to the gate's read path.
3. **Binding to the tree instead of the commit is REJECTED.** It would
   dodge the circularity, but a tree hash does not say which release it
   authorized, and "a ruling on an earlier commit does not authorize
   this tag" is the property the binding exists to enforce.

**OPEN — for the chair, not settled here.** Whether to ALSO track a
post-tag history under `.attune/release-manifests/` (`git log` over past
rulings). It requires one substantive change: `require_manifest` would
have to accept a manifest whose `head_sha` is an ANCESTOR of the tag
rather than strictly equal, or the post-tag commit invalidates it for
later re-verification. Loosening a binding to gain a convenience is
exactly the trade that deserves a chair read rather than a lead's
judgement, so it is left open.

*Recorded 2026-08-22: the chair stated a LEAN toward adopting it
("I'm leaning toward your suggestion"). Recorded as a lean and not
promoted to a ruling — the ancestor-binding change weakens a security
property, and a lean stated in passing is not the read that trade
deserves. It stays OPEN until ruled explicitly.*

**Not yet implemented.** 14.0.0 ships R7 as written (local file, gate
reads it). The release-asset upload is follow-on work.

## Record — C10 (phantom read) registered (2026-08-24, lead records)

Executed against the 14.1.0-retro chair GO ("class-register entry:
the phantom-read class"). The entry is in the canonical register
corpus (`~/.attune/reports/attune-ai-review/CLASS-REGISTER.md`,
machine-local per the local-first reports carve): **C10 — the
consumer reads a key/field/name no producer emits (or whose meaning
differs); the read defaults clean, so the defect renders healthy.**
Seven confirmed instances 2026-08-23/24 (secure-release phantom keys
#2222, doc-orchestrator context keys #2223, MCP test-gen handler
keys #2213→#2250, three probe misreads incl. the #2221 false alarm,
and the entry-point group split fixed in #2259 — instance 7
generalizes the "key" to any producer/consumer channel identity).
Status REGISTERED, unmechanized: per the register pipeline the next
step is a calibratable narrow rule (result-key contract scan over
the known workflow producer/consumer pairing; channel-identity scan
for entry-point groups), never an uncalibratable general dataflow
rule. Not a chair ruling — a record of executing one.
