# memory-claim-verification — decisions

**Status:** active (2026-08-10) — D1–D9 ruled. The ref-binding
table ran all three rounds (thread `q-ref-binding-001`): D7
per-finding matching, D8 probe FAILED the gate (22.9%), D9 adopts
C-hardened (propose-at-extraction, validate-at-binding). Next:
design phase — extractor refs field + binder + re-probe (with the
chair-adopted adversarial salted subset); the inventory-vs-anchor
fork settles empirically.

## D1 (2026-07-26): the extraction prompt is NOT the control

**Ruled.** The prompt already carries a PROVENANCE rule instructing the
model to record only what the session concluded. Both bad findings on
2026-07-25 violated it anyway.

Tightening the prompt, or making `/recall review` mandatory, were both
considered and REJECTED as patches:

- Prompt-tightening leaves an 8B model writing unverified assertions,
  just fewer of them. The failing component cannot be its own control.
- Mandatory review adds friction to every session to catch a minority of
  bad records — and `/recall review` already exists and is not run, which
  is the empirical answer to whether more optional review works.

Verification must live **outside** the model, in code that resolves
entities against ground truth.

## D2 (2026-07-26): apply the claim-drift architecture, don't invent one

**Ruled.** The claim-drift gate and the capability projector both refuse
to trust a written value and derive it from a live source. Both caught
real drift on 2026-07-25. The memory store is the last surface in the
repo still trusting written prose about mutable state.

This spec is therefore **not a new technique** — it is the existing
derive-don't-store discipline applied to `session_stash`. Design reviews
should check consistency with those two mechanisms before adding
machinery.

## D3 (2026-07-26): read-time annotation ships first and alone

**Ruled.** P1 (refs + read-time re-resolution) is independently
shippable, carries no write-path risk, requires no model change, and
catches the motivating failure. Seeing `⟨pr:1666 → MERGED⟩` beside "open
for reviewing" defeats the bad finding **without any natural-language
understanding**.

Write-time rejection (P2) is strictly more invasive and depends on OQ1.
Do not bundle them.

## D4 (2026-07-26): unreachable is never contradicted

**Ruled.** A resolver that cannot reach `gh`, git, or the filesystem must
store the finding ungrounded, never reject it. The memory layer degrades
silently and never blocks a session — this is existing contract, restated
here because a verification step is exactly where it would be broken.

## D5 (2026-07-26): the golden set pins BOTH directions

**Ruled.** The acceptance test replays all four real 2026-07-25 findings
and requires the two bad ones to be caught **and the two good ones to
survive**. A change that rejects everything is as wrong as one that
accepts everything.

Same discipline as `tests/unit/ci/test_platform_compat_scanner.py`, where
each false-positive class is pinned to its true positive so a later
re-broadening fails loudly instead of silently refilling the store.

---

## Open, for the chair

- **OQ1 — MEASURED 2026-07-26. Answer: NO, and neither does the
  fallback.** See "OQ1 measurement" below. Awaiting a chair ruling on
  the mechanism.
- **OQ2** — on contradiction, reject or demote? Proposal: demote to
  `interpretation` with the contradiction recorded.
- **OQ3** — should a grounded finding outlive the 30-day TTL? Changes the
  store's character from working-memory to durable.

---

## OQ1 measurement — 2026-07-26

Harness: `scripts/measure_stash_refs.py`. Replays real session
transcripts through the REAL tail extractor
(`plugin/hooks/session_stash.py::_read_transcript_tail`) and the REAL
Ollama call, with the shipped prompt plus a minimal `refs` clause —
measuring the model, not prompt craft.

| Metric | n=18 (>20 KB) | n=12 (>200 KB) |
|---|---|---|
| JSON parse ok | 100% | 100% |
| findings WITH refs | 79.7% | 85.1% |
| refs well-formed | 81.2% | **56.4%** |
| refs **grounded in the tail** | **28.1%** | **21.8%** |
| findings heuristic-backfillable | 10.1% | 8.5% |

"Grounded" = the ref's value literally appears in the transcript the
model was shown. Ungrounded means fabricated. The check is generous
(a bare `pr:1666` scores grounded if `1666` appears anywhere).

### Two findings, both decisive

**1. The model emits refs enthusiastically and gets them wrong.**
~80–85% of findings carry refs, but only ~22–28% of those refs appear
in the source at all. Restricting to substantial transcripts made it
WORSE, not better — well-formedness fell to 56%. This is the worst
possible shape for R3: confident, structured, and fabricated. Verifying
such claims would mostly verify inventions.

**2. Heuristic back-fill is not a fallback either.** Only ~10% of
findings contain an entity a regex over `content` could recover. The
requirements assumed back-fill was the safety net if the model failed.
It is not — it is a narrow supplement.

Both mechanisms the spec named therefore fail. The premise of OQ1 —
"if not the model, then heuristics" — was a false dichotomy.

### A third mechanism the spec did not consider

Refs need not come from the model OR from the finding text. The
transcript's `tool_use` records already contain the session's real
entities, deterministically extractable. Probed on the newest
transcript (148 tool_use blocks):

- PR numbers recovered from commands: `1578 1605 1607 1666 1667 1668`
  — exactly the PRs that session touched, no fabrications
- the real merge SHA `1f6553edc24d3cf7e8adebb5a853132fa1e332ef`
- 10 distinct file paths, from `file_path` inputs

These are facts about what the session DID, not prose about what a
model thinks it did. The hook currently DISCARDS them: `_text_of`
replaces every `tool_use`/`tool_result` block with
`[tool output omitted]` (correct for R1 provenance — tool output is not
speech — but it means the structured facts are thrown away before
extraction).

**Implication:** derive the session's ref-set deterministically from
`tool_use` blocks, then attach refs to findings by matching, rather than
asking the model to author them. This is the same derive-don't-store
discipline as D2, applied one layer earlier than the spec proposed.

Recommendation to the chair: R3 as written is not viable; replace the
model-authored `refs` requirement with session-derived refs. The table
should deliberate HOW findings bind to the derived ref-set, which is a
real design fork with defensible alternatives.

## D6 (2026-07-26): the ref-binding question waits for the table, after the fire

**Ruled (chair).** OQ1's measurement retires R3-as-written but does not
settle its replacement. The open fork — given refs are deterministically
derivable from `tool_use` records, how does a finding BIND to them —
goes to the round table, convened **after** the 07-27 06:00 roundtable
fire, not before.

Reasons: the fire is the north-star receipt for `agent-round-table` and
should not share an evening with an exploratory run; the binding question
blocks nothing until P1 is built; and the table briefs better with a
clean run to point at, plus the measured numbers already in this file.

The three candidate bindings to put to the table:

1. **Session ref-set on every finding** — cheap, deterministic,
   imprecise (a finding inherits entities it is not about).
2. **Per-finding matching** against the derived set — precise, lossy
   (a finding that names nothing matchable stays ungrounded).
3. **The SESSION is the grounded unit**, not the finding — sidesteps
   binding entirely; changes what `grounding` in R4 means.

No implementation starts before that ruling.

## D7 (2026-08-10): ref-binding = per-finding matching, with three riders (table unanimous, chair adopted)

**Ruled (chair, via the promotion form + "go with the
recommendations of the roundtable").** The D6 table sat 2026-08-10
(thread `q-ref-binding-001`, halted after round 1 of 3 on
unanimous convergence; full transcript machine-local at
`~/.attune/reports/roundtable/q-ref-binding-001.md`). All three
seats (claude, antigravity, codex) independently picked candidate
2 and rejected 1 (inherited refs produce false verification
outcomes) and 3 (verification consumes findings, not sessions).

The binding model: a finding binds only to refs deterministically
matched between its own text/payload and the session-derived ref
set — closed-set exact/basename/symbol matching, no LLM in the
raw-tier binding path. Riders, adopted with the ruling:

- **(a) Unbound is first-class.** A finding matching nothing is
  stored ungrounded/unbound — honest state, never presented as
  grounded, never papered over. Verification distinguishes
  `bound` / `unbound` / `stale-missing-ref`.
- **(b) Session provenance, not session binding.** Every finding
  carries its session-id; the session ref-set stays derivable as
  an explicitly-labeled WEAKER view (candidate 1 as a lens, never
  a stored binding). Later deterministic evidence may promote
  `unbound` → `bound` with the original finding unchanged and
  binding provenance recorded (codex follow-up, admitted).
- **(c) Measure before building.** An OQ1-style probe on the
  existing stashed corpus runs BEFORE the P1 matcher build: what
  fraction of real raw-tier findings textually name at least one
  ref derivable from their session's tool_use records? A low hit
  rate (<50%) reopens the design conversation (2-with-fallback vs
  3) before the build cost is paid — the vacuous-verification-layer
  risk all three seats flagged.

Seat risk register, preserved: matchability as a hidden quality
gate biasing recall toward easily-named entities (codex); matcher
recall on prose findings + over-matching on short/common tokens
(claude); abstract findings staying ungrounded and going stale
undetected (antigravity).
## D8 (2026-08-10): rider-(c) probe MEASURED — 22.9% bind rate, design conversation REOPENED

**Measured, same day as D7** (`scripts/probe_ref_binding.py
--samples 40`; full data machine-local at
`~/.attune/reports/memory-claim-verification/rider-c-probe.md`).
Real shipped extractor (session_stash._extract_via_ollama,
llama3.1:8b), ref-sets derived from each session's tool_use
records, matching purely deterministic (exact path / basename /
pr-number / sha-prefix / spec-slug, stoplist + min-basename
guards).

| Metric | Value |
|---|---|
| transcripts scored | 40 |
| findings extracted | 192 |
| findings bound (>=1 derived ref) | 44 (**22.9%**) |
| by kind | pr=21, sha=0, file=43, spec=4 |
| D7 gate (50%) | **FAILED — reopen design** |

The over-match spot-check LOWERS true precision further: among
the 44 are a generic security-posture finding bound to
`ops/security.py` by the word "security", a bare repo-directory
ref, and a 2-char `spec:v1` slug bind. The number is consistent
with OQ1's 28.1% grounded — prose findings summarize decisions,
they do not name artifacts. The vacuity risk all three D7 seats
flagged is measured fact, not speculation.

**Consequence (mechanical, per D7 rider c):** the P1 matcher
build does NOT proceed. The reopened fork — candidate
2-with-fallback (findings mostly consumed through rider-(b)'s
weaker session-view lens) vs candidate 3 (session as the grounded
unit, redefining R4) — awaits a chair ruling; re-convening the
table with these numbers is the moderator-recommended path, since
the seats deliberated without them.

Honest limits recorded in the local report: basename multi-bind
(SKILL.md class), symbol-kind underivation (unmeasured), spec-slug
min-length gap, Ollama run-to-run nondeterminism (noise dwarfed by
the 22.9-vs-50 margin), zero sha binds.

## D9 (2026-08-10): C-hardened ADOPTED — propose-at-extraction, validate-at-binding; rounds 2-3 of the table

**Ruled (chair, final-ruling form: "Adopt; design phase settles
inventory-vs-anchor via re-probe"; follow-up triage delivered in
chat after a widget multi-select fault).** After D8 failed the
gate, the chair directed rounds 2 and 3 on thread
`q-ref-binding-001` (D3 ceiling reached; transcript
machine-local). Round 2: all three seats independently converged
on option C. Round 3 (attack-then-harden, chair-directed before
ruling): C SURVIVED 3/3 under adversarial pressure, each seat
emitting a build-ready hardened design.

**The settled core (mandated verbatim, all three seats agree):**

- Refs are PROPOSED at extraction (structured field, chosen from
  the session's artifacts) and VALIDATED at binding —
  deterministic set-membership/exact only; fuzzy prose matching
  stays retired (D8 showed it caused both failure modes).
- Empty refs is a PREFERRED, first-class success state; "a
  convenience reference is a defect"; prompts instruct
  refs-last-finding-first so the field cannot displace finding
  quality.
- Corpus is versioned: legacy v1 "not collected" is DISTINCT from
  v2 "explicitly unbound"; no backfill, no mutation, no blended
  metrics across versions.
- The re-probe (same 40 transcripts as D8) reports bind rate ONLY
  alongside (i) an extraction-quality regression guard
  (findings-per-transcript, length, dedup; blind paired
  comparison) and (ii) a MANUAL aboutness-precision audit
  (stratified sample, independent judges). Thresholds stay the
  chair's, set AFTER numbers (ruled on the round-2 form: "Decide
  after re-probe numbers").
- **Adversarial subset (chair-adopted, codex follow-up):** the
  re-probe includes a salted subset — transcripts carrying highly
  salient but unrelated artifacts (incl. cross-repo) — reported
  separately.
- Refs are forever described as "extractor-proposed,
  inventory-validated" — never fully-verified evidence.

**The one open fork, sent to the design phase with the re-probe as
the deciding instrument (cheapest shape first):** codex's opaque
inventory-ID selection vs claude's anchored refs (verbatim
transcript anchor, locality-checked, demotion-rate observable) vs
antigravity's plain strict-prompting + exact membership. The
designs compose; each addition costs tokens and failure surface.

**Not adopted now (design-phase options, unmandated):**
demoted-ref visibility handling in session view; `ref_rejected`
events into UsageTracker telemetry.

**Risk register (round 3, per seat, preserved):** human precision
review cannot mechanically prove aboutness (codex);
anchor-locality over-rejection creating pressure to loosen — fuzzy
matching's back door (claude); prompt-compliance variance across
model families (antigravity).

## D10 (2026-08-10): design + tasks APPROVED — the read #2043's merge outran

Chair message: "approve task for 2043". Context: PR #2043 carried
design.md + tasks.md chair-read, but the Class-1 auto-merge lane
took it ~1.7h before the read (the lane had no mechanical notion
of chair-read; fixed same day in PR #2044 — "(chair-read)" title
or `chair-read` label now skips Class 1, drift-guarded). This
ruling completes the read after the fact: design.md and tasks.md
statuses flip to approved, T1–T2 implementation authority is
granted (T1+T2 had already shipped in PR #2045 under the chair's
explicit merge authorization, so no unauthorized code landed), and
T4+ (P1) stays gated on T3's re-probe numbers plus the chair's
threshold ruling, per the tasks doc.

Scope confirmed by the chair via pushback form (2026-08-10,
D11d COUNTER-CASE raised by the lead): "approve task for 2043"
covers BOTH design.md and tasks.md — not tasks-only. The chair
also confirmed the standing policy that recordings of explicit
in-session chair rulings merge unmarked (transcription, not new
governance text); interpretive doubt is handled by draft-holds,
as was done with this PR.

## D11 (2026-08-10): T3 re-probe MEASURED — rejection trigger FIRES (32.8%), aboutness at the 80% boundary

**Measured** (tasks.md said "record as D10"; that number was
consumed by the approval ruling above — numbering drift noted, not
re-litigated). Both arms on the SAME 40 transcripts as D8
(recovered from the D8 raw log, all 40 resolved on disk), plus the
chair-adopted salted adversarial subset (6 transcripts, cross-repo
salience, both channels: prose in the extractor tail AND tool_use
records in the binder universe). REAL shipped extractor + REAL T2
binder via `ATTUNE_MEMORY_REFS_V2`; zero API spend (local
llama3.1:8b). Full data machine-local per local-first-reports at
`~/.attune/reports/memory-claim-verification/re-probe-v2.md`
(+ `-raw.txt`, `-rows.jsonl`, `d8-transcripts.txt`).

### Main arm (40 transcripts; both arms scored 40/40)

| Metric | v1 (shipped) | v2 (refs+binder) |
|---|---|---|
| findings extracted | 195 | 179 |
| findings/transcript | 4.88 | 4.47 (−8.4%) |
| mean content length | 106.3 | 90.6 (−14.8%) |
| dedup rate | 0.0% | 0.0% |

| v2 metric | Value |
|---|---|
| statuses | bound 35 · unbound_explicit 115 · all_rejected 22 · no_ref_universe 7 |
| bind rate PRIMARY (excl. no_ref_universe) | **35/172 = 20.3%** |
| bind rate SECONDARY (all-in; D8 fuzzy was 22.9%) | 35/179 = 19.6% |
| ref items proposed / checked | 76 / 67 |
| bound items (pr/file/spec) | 39 (25 / 14 / 0) |
| **membership-rejection rate** | **22/67 = 32.8%** |
| rejected bad_kind | 6 |
| refs-per-finding 0/1/2/3 | 115 / 53 / 10 / 1 |

Comparability caveat: D8's 22.9% was FUZZY matching over v1
findings; v2's 19.6% is validated exact-membership over proposed
refs — same magnitude, different epistemics (every v2 bind is
inventory-checked, every unbound is honest).

### Salted subset (separate — never blended)

30 findings: bound 8, rejection 2/10 = 20.0%. **Salt uptake: 1/30
proposed AND bound a salt ref** — and the failure shape is
upstream of aboutness: the extractor MANUFACTURED a finding about
the salt ("The production-outage postmortem is being worked on as
PR #5151") despite the prose framing it as unrelated. Provenance
failure, not just a convenience ref.

### Aboutness audit (30 bound stratified + 15 unbound; one judge)

- **24/30 about-correct = 80.0%, Wilson 95% CI [62.7%, 90.5%]**.
  file stratum 11/11; pr stratum 13/19 — all six failures are
  session-context PR numbers attached to findings about something
  else (incl. two cross-repo bare-number collisions).
- False-unbound: **4/15 clear** — findings that NAME a PR verified
  in-universe yet returned `refs: []` (#1725, #210, #1314, #2001).
  Strict negative prompting under-attaches as well as
  over-suppresses.
- Judge is the authoring seat (no non-authoring seat available);
  the design's second-judge overlap subset is owed if one becomes
  available before T4.

### D-1 pre-registered triggers (evaluated explicitly)

| Trigger | Level | Measured | Verdict |
|---|---|---|---|
| codex inventory-IDs | rejection > 20% | 32.8% | **FIRES** |
| claude anchored refs | aboutness < 80% AND rejection ≤ 20% | 80.0% / 32.8% | does not fire |

Only the inventory trigger fires → per D-1, inventory-IDs first
(deny value-authoring at the source) is the indicated escalation.
The aboutness point estimate sits exactly AT the 80% boundary with
a wide interval — flagged for the chair rather than smoothed either
way. Thresholds for P1 go/no-go remain the chair's, set at T4
against these numbers; an override of the fired trigger is visible
against the pre-registered 20% level.
