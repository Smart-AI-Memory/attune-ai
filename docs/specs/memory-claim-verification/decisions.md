# memory-claim-verification — decisions

**Status:** active (2026-08-10) — D1–D7 ruled; the ref-binding
table sat 2026-08-10 (thread `q-ref-binding-001`) and D7 resolves
the fork. Next: the D7 rider-(c) measurement probe, then P1.

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
