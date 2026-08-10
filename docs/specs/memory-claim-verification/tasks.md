# memory-claim-verification — Tasks (post-D9 design phase)

**Status:** draft (2026-08-10) — awaiting chair approval of
[design.md](design.md). T1–T2 implementation authority begins at
that gate; T4+ (P1) is ADDITIONALLY gated on T3's numbers plus the
chair's threshold ruling.

## T1 — Extractor v2: refs field (impl)

`plugin/hooks/session_stash.py`: append the D-2 prompt delta
(BEHIND `ATTUNE_MEMORY_REFS_V2`, default off — production prompt
unchanged until T4); extend `_parse_typed_findings` with the
refs-list parse under the full R5#2 discipline (item-level drop,
finding survives; SYNTAX-ONLY — kind validation is the binder's,
per D-2/D-3; length caps shared with source_ref); stamp
`schema_version: 2` + `extractor_prompt_version` in finding
metadata; stop requesting `source_ref` (v1 rows untouched).

**Receipt (suite):** `tests/unit/hooks/` stash tests SERIAL, exact
tail; new R5#2-style security tests (injection-shaped ref,
over-long ref, non-list refs, all-items-dropped → `refs: []`).

## T2 — Binder module (impl)

Promote `derive_refs()` from `scripts/probe_ref_binding.py` into a
shared module imported by both the hook and the probe; implement
the D-3 rule chain with reason-coded rejections (including
`rejected:bad_kind` for kinds the parser passed through) and the
four finding statuses; wire into the stash pipeline after the
typed parse BEHIND the same default-off flag — T4's go flips it,
never this task. No LLM, no fuzzy matching — a drift-guard test greps the
binder module for the retired fuzzy constructs (substring/basename
matching against prose).

**Receipt (suite + behavioral):** binder unit tests per rule
(bad_kind, not_in_session, normalization cases, empty-universe,
v1-bypass); a golden transcript fixture round-trip
(extract → bind → stored statuses byte-compared).

## T3 — Re-probe, both arms + salted subset (metric — gates P1)

Extend the probe script per D-5; build the salted subset (≥5
transcripts, cross-repo salience); run both arms on D8's 40
transcripts; run the 30+15 aboutness audit; record everything in
decisions.md as D10 with the full metric table. Machine-local raw
data per local-first-reports.

**Receipt (metric):** the D-5 report, full stream, dual
denominators, regression guard, Wilson interval — bind-rate
movement never reported alone. Escalation triggers (D-1 table)
evaluated explicitly in the entry.

## T4 — Chair threshold ruling + P1 go/no-go (gate)

Present T3's numbers with a form: thresholds, escalation (none /
inventory / anchors — evaluated against D-1's PRE-REGISTERED 20%/
80% trigger levels), P1 authorization, and the
`ATTUNE_MEMORY_REFS_V2` default flip. Recorded as D11.

## T5 — Record and close the phase (release-notes)

decisions.md phase record; CHANGELOG under Unreleased when the
extractor change ships to users; spec headers status-truthed.

## Explicitly deferred

Everything in design.md D-6, each with its named re-entry trigger.
