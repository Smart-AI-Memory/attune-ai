# memory-claim-verification — Design (post-D9)

**Status:** draft (2026-08-10) — awaiting chair review. Authored
under D9's authorization ("design phase — extractor refs field +
binder + re-probe"); implementation authority begins at this gate,
and P1 implementation is additionally gated on the D-5 re-probe.
**Rulings this design executes:** D7 (per-finding matching, riders
a–c), D8 (22.9% measured — fuzzy matching retired), D9 (C-hardened:
propose-at-extraction, validate-at-binding; settled core mandated;
cheapest shape first; adversarial subset).

## Code reality (verified 2026-08-10)

- Extraction: `plugin/hooks/session_stash.py::_extract_via_ollama`
  builds the prompt inline and parses via `_parse_typed_findings`
  (R5#2 strict typed-schema parse: discard-on-mismatch, never
  coerce; `source_ref` today is a SINGLE optional short locator
  with length caps and injection-machinery rejection).
- Universe derivation: `scripts/probe_ref_binding.py::derive_refs`
  already walks a transcript's `tool_use` records into
  `{pr, sha, file, spec}` sets — the binder's seed.
- Storage: `_stash_findings` writes typed findings to the resolved
  memory backend; no schema-version field exists today.

## D-1 — Cheapest shape first, with named escalation triggers

Ship antigravity's round-3 shape: a plain `refs` list of
`kind:value` strings, strict negative prompting, exact-membership
binding. The two heavier shapes are NOT built now; each has a
mechanical re-entry trigger measured by the D-5 re-probe:

| Escalation | Trigger (from re-probe numbers) |
| --- | --- |
| claude's anchored refs | aboutness-precision audit fails the chair's threshold while membership-rejection is LOW (selection-confabulation dominates — needs the demotion observable) |
| codex's inventory-IDs | membership-rejection rate stays HIGH (invention persists despite negative prompting — the model must be denied value-authoring) |

Both triggers firing → inventory first (it removes the failure at
the source), anchors only if the audit still fails after it.

## D-2 — Refs schema v2

```json
{"type": "...", "content": "...", "confidence": 0.9,
 "refs": ["file:src/attune/x.py", "pr:2041"]}
```

- Kinds: `file | pr | spec | command`. **sha is dropped** —
  deliberate, D8 measured ZERO sha binds across 192 findings;
  re-entry trigger: a re-probe arm showing findings that quote
  SHAs.
- Cardinality 0–3 (codex); more than three → the three strongest.
- `refs: []` is EXPLICITLY-UNBOUND — a first-class, preferred
  success state ("a convenience reference is a defect").
- `source_ref` is deprecated in v2: the prompt stops requesting
  it; the parser still accepts it on v1 rows, never rewrites them.
- The refs list inherits the FULL R5#2 discipline in
  `_parse_typed_findings`: non-list refs, non-string items,
  over-long items (same cap as source_ref), or injection-shaped
  items drop the ITEM; a refs field whose every item drops yields
  `refs: []`, not a dropped finding (an over-eager ref must not
  cost a good finding — mirrors codex's reject-the-entry rule).

**Prompt delta** (appended constraint language, shipped verbatim —
synthesis of the three seats' round-3 texts):

```text
- refs: 0-3 entries "kind:value" (kinds: file:<path>, pr:<number>,
  spec:<slug>, command:<exact command>). Attach a ref ONLY if the
  finding is ABOUT that artifact — if removing the ref would make
  the finding unverifiable. Artifacts that merely appeared in the
  session do not qualify; a convenience reference is a defect.
  refs: [] is a correct and common answer. Write the finding
  first, refs second — never let refs shorten the finding.
```

## D-3 — Binder: at stash time, deterministic, reason-coded

Placement: inside the Stop-hook stash pipeline, after
`_parse_typed_findings` — the `tool_use` universe is only reliably
available while the transcript path is at hand. The universe
builder is `derive_refs()` promoted out of the probe script into
the hook (or a shared module the hook and probe both import — one
source, the probe becomes the binder's test harness).

Rules, in order (no LLM, no fuzzy matching anywhere):

1. Parse `kind:value`; unknown kind → item `rejected:bad_kind`.
2. Normalize (path absolutized against cwd; command
   whitespace-collapsed; pr digits; spec slug lowered).
3. Exact membership in the derived universe → `bound`;
   miss → `rejected:not_in_session`.
4. Finding status: `bound` iff ≥1 ref bound; `unbound_explicit`
   when `refs: []` was proposed; `unbound_all_rejected` when every
   proposed ref rejected. v1 rows are `unbound_legacy` and NEVER
   pass through the binder.
5. Rejected items are STORED with their reason codes (codex —
   the evaluation surface), never rendered as bound.

## D-4 — Corpus versioning

New extractions carry `schema_version: 2` plus
`extractor_prompt_version` in finding metadata. v1 rows: never
backfilled, never binder-processed, never rewritten to `refs: []`
("not collected" ≠ "explicitly unbound" — codex). Metrics segment
by version; no blended series. A v1 finding re-extracted from a
retained transcript yields a NEW v2 finding; the v1 row is not
mutated.

## D-5 — Re-probe protocol (gates P1 implementation)

Extend `scripts/probe_ref_binding.py` with a v2 arm; run BOTH arms
(shipped prompt vs v2 prompt+binder) on the SAME 40 transcripts as
D8, plus the **chair-adopted adversarial salted subset**: ≥5
transcripts salted with highly salient but unrelated artifacts
(incl. cross-repo), reported separately, never blended.

Report (bind-rate movement is meaningless alone — all mandated):

- bind rate, dual denominators: primary excluding zero-universe
  sessions (`no_ref_universe`), secondary all-in (comparable to
  D8's 22.9%);
- membership-rejection rate (invention proxy) and refs-per-finding
  distribution (attachment-pressure signal);
- extraction-quality regression guard: findings-per-transcript,
  mean content length, dedup rate vs the shipped-prompt arm;
- aboutness-precision audit: 30 bound findings, stratified by
  kind, one judge, binary "is the finding ABOUT this artifact?",
  Wilson 95% interval; plus 15 unbound findings checked for
  false-unbound. (Second-judge overlap subset if a non-authoring
  seat is available.)

Thresholds are the CHAIR's, set after these numbers exist (ruled
2026-08-10). The refs are described everywhere as
"extractor-proposed, inventory-validated" — never verified
evidence.

## D-6 — Explicitly out (with re-entry triggers)

- Anchors / inventory-IDs — D-1 triggers.
- Demoted-state machinery and its visibility question —
  anchor-specific; enters only with anchors.
- `ref_rejected` → UsageTracker telemetry — unmandated (chair
  triage 2026-08-10); re-entry: the re-probe shows rejection rates
  worth tracking longitudinally.
- Recall-time re-binding, cross-session binding, curated-tier
  verification — out of this phase entirely.
