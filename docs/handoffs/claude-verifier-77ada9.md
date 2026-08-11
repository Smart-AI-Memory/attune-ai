# Handoff — claude/verifier-77ada9 (mcv T3 re-probe)

**Branch:** `claude/verifier-77ada9` · **Spec:**
docs/specs/memory-claim-verification · **Task:** T3 (metric — gates
P1). Delete this file when the branch merges.

## What was actually done (evidence, not claims)

- Recovered D8's exact 40-transcript set from the machine-local raw
  log (`~/.attune/reports/memory-claim-verification/
  rider-c-probe-raw.txt`); all 40 resolved on disk; list pinned at
  `~/.attune/reports/memory-claim-verification/d8-transcripts.txt`.
- Rewrote `scripts/probe_ref_binding.py` into the D-5 two-arm
  harness: imports the REAL hook extraction + REAL T2 binder
  (`_bind_findings`) — retired fuzzy matcher deleted; no test
  references the script (grepped). Pinned black + ruff pre-flighted
  clean.
- Built 6 salted transcript copies (machine-local,
  `~/.attune/tmp/mcv-salted/` + manifest); salt verified present in
  BOTH the extractor tail and the binder universe on all 6 before
  the run.
- Full run (exit 0, output verified non-empty): 40 transcripts ×
  both arms + 6 salted, local llama3.1:8b, zero API spend. Raw:
  `re-probe-v2-raw.txt`, rows: `re-probe-v2-rows.jsonl`.
- Aboutness audit judged in-session (single authoring judge —
  second-judge overlap owed if a non-authoring seat appears):
  24/30 = 80.0% about-correct, Wilson [62.7%, 90.5%]; false-unbound
  4/15 (each named PR verified in-universe via
  `_derive_session_refs` before the call was recorded).
- Recorded as **D11** in the spec's decisions.md (tasks.md said
  "as D10"; the approval ruling consumed D10 — drift noted in the
  entry). T3 heading in tasks.md annotated DONE.

## Headline numbers (full tables in decisions.md D11)

- v2 bind rate: 20.3% primary / 19.6% all-in (D8 fuzzy: 22.9%).
- **Membership-rejection 32.8% → the pre-registered 20% D-1
  inventory-IDs trigger FIRES.** Anchors trigger does not fire.
- Salt uptake 1/30 — the hit is a manufactured finding about the
  salt (provenance failure), not a convenience ref.
- Extraction-quality regression: findings/transcript −8.4%, mean
  length −14.8% under the v2 prompt.

## Next action

T4 — chair threshold ruling + P1 go/no-go with a form (thresholds,
escalation vs the fired trigger, `ATTUNE_MEMORY_REFS_V2` flip).
Present D11's numbers; do NOT smooth the exactly-80.0% aboutness
point or the fired trigger.

## Unresolved risks

- Single-judge aboutness; CI is wide.
- Cross-repo bare-number PR collisions observed live (B13/B21
  class) — a real P1 design input.
- v1/v2 quality deltas include sampling noise (no paired blind
  comparison).
