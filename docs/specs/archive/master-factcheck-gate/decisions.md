# Master Fact-Check — Decisions

**Status:** superseded (2026-06-30) — by attune-author-consolidation (#1192 D4, fact-check absorbed #1193); reconciled at 2026-07-14 triage (was: draft)
[requirements.md](requirements.md) / [design.md](design.md).

## D1 — Fix resolution attune-ai-side; don't re-engineer `attune_author` first

**Decided.** The false positive is the editable-install mapping; the cure
is the authoritative repo-`src`-on-`sys.path` resolver that
`audit_doc_imports.py` already implements in attune-ai. Extract that
resolver and have `project_features.py` call it, rather than reaching into
the sibling `attune_author.check_python_refs`. Keeps the blast radius in
one repo and reuses proven, already-required machinery. A sibling change
is a fallback only if R1/R2 genuinely can't be met attune-ai-side.

## D2 — Gate only measured-reliable checks; deep checks stay advisory

**Decided.** The doc-import-gate deliberately scoped to import resolution
because deeper checking (method calls, claim accuracy) is high-false-
positive. This spec holds that line: a check becomes blocking only with a
measured near-zero false-positive rate on the 27-master corpus. An
LLM-grounded fact-checker never blocks merge on its own authority.

## D3 — This spec is partly investigative; let the corpus decide

**Decided.** Whether anything `check_python_refs` does beyond imports is
worth gating is **unknown** until measured against the real masters (Step
2). The spec does not pre-commit to "add a gate." Pre-committing would
repeat the exact mistake the premise-verification just caught — asserting
a gap that the evidence might not support.

## D4 — "Retire the duplicate" is a valid — even preferred — outcome

**Decided.** If the measurement shows the projector's check adds no
reliable coverage beyond the required gate, the right move is to *remove*
the redundant/flaky check, not to harden it. The single-source program's
own value is fewer trustworthy surfaces, not more machinery. A spec that
can conclude "delete code" is healthier than one that must ship a feature.

## Context: why the premise was only *partly* right

The insights discussion framed the verification half as "advisory and
backwards." Verification found that the *import* half is in fact already
authoritative and **required** (doc-import-audit + wiring-audit were
promoted into branch protection). The genuinely-weak surface is narrower:
a redundant warn-only checker that false-positives. Recording this so the
spec is not read as "the masters are unverified" — they are; the gap is a
trust bug in a secondary checker, not a missing gate.

## Open

- **`source_globs` → drift-propose (the bigger prize).** The richer
  follow-on remains: when globbed code moves, *propose* the diff to the
  master's API tables — the staleness-aware-mirror vision. Strictly out of
  scope here; this spec is about making the *existing* verification
  trustworthy, which is the prerequisite for trusting an auto-proposer
  later.
