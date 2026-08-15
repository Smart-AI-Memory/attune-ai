# Confirm Construct — decisions

Decision log for [requirements.md](requirements.md). Append-only;
newest at the bottom.

## D1 — Intake rulings (form-accepted, 2026-08-14)

**Date:** 2026-08-14 · **Status:** decided (Patrick — chair accepted
the intake form as prefilled: "proceed as indicated by my form
submissions"; validated receipt `resp-20260814-212130`).

Provenance chain: round table `q-forms-grammar-expansion-001` — the
claude seat ("confirm construct — action preview with explicit
consequences list, approve/abort, degrading to boolean with the
receipt in description") and the codex seat ("confirmation of
consequences: compact summary plus explicit acknowledgement for
destructive, costly, or externally visible actions") converged
independently; chair ruled it "spec next" via the live
deliberation+triage widget (receipt `resp-20260814-211025`).

1. **Answer shape = two-way** (approve/abort; exactly two
   author-nameable labels). Three-way and typed-acknowledgment lanes
   declined for v1; typed-ack named as a possible v2 needing its own
   ruling and a flat-surface answer.
2. **Consequences = structured items** `{label, severity?, detail?}`
   — the `triage_items` shape; severity a free tag with a conventional
   vocabulary named in docs, not enforced.
3. **Slug = `confirm-construct`**, spec home attune-ai `docs/specs/`
   (attune-forms carries no specs tree — extraction-era precedent).
4. **Done-when** recorded verbatim in requirements.

## D2 — Lead-proposed rule flagged for ratification: no pre-selected approval (2026-08-14)

**Date:** 2026-08-14 · **Status:** RATIFIED — chair approved the
requirements ("requirements approved") immediately after the lead's
explicit disclosure of this rule and the R5a collision in response to
"any pushback?". The approval covers the amended text carrying both;
the rule stands as written (no `default`, no `recommended` on a
confirm).

R1 forbids `default` and `recommended` on a confirm: a pre-selected or
pre-badged approval defeats the gate. This was added by the lead
beyond the intake forks. When the chair asked "any pushback?", the
lead disclosed it rather than letting it ride (the widget-kernel-family
D2 counter-case discipline: lead-added rulings must be traceable and
chair-ratified, never laundered into a spec the chair already
skimmed). Also disclosed at the same time: the skill-text collision
now recorded as R5a (bare confirmations stay conversational; the
construct is reserved for consequence-bearing actions).

Chair options: ratify as written / strike (allow recommended) /
narrow (allow default=abort only). Recorded here when ruled.

## D3 — AC-3 live receipt + ship approval (chair via confirm card, 2026-08-14)

**Date:** 2026-08-14 · **Status:** decided.

The construct's first human-validated round-trip was its own ship
gate: a live `confirm` card ("Push claude/confirm-construct and open
the PR?") with three severity-tagged consequences, rendered from the
working tree, answered **Approve** by the chair, validated through
`collect_form_response` — receipt `resp-20260814-213355` (AC-3
satisfied by construction). During execution the widget CSS family was
renamed `.ae-gate-*` after a semantic collision with the BASE
fully-inferred banner class `.ae-confirm` (same name, different rule)
— caught by eyeball, not by the class-coverage guard, which only
detects unstyled classes. Theme lands at 8,158 B, under the 8 KB cap.
