# Round table — q-forms-grammar-expansion-001 (curated stub)

**Question (chair, 2026-08-14):** which new form/widget constructs and
surfaces should attune-forms add for users across Claude, Antigravity,
and Codex hosts? Seeds: deliberation construct, triage construct,
portable markdown surface.

One round, all three seats present (claude 36s, antigravity 47s,
codex 25s); halted on convergence. Full transcript (moderator
development data, never tracked):
`~/.attune/reports/roundtable/q-forms-grammar-expansion-001.md`.

## Promoted content (chair-approved: board msgs 2, 3, 4, 8)

- **3/3:** the markdown surface ships first and is only real with a
  specified return path (wire-format + validation loop). Shipped in the
  attune-forms grammar-expansion PR as the sentinel-marked JSON answer
  skeleton emitted by `form_to_markdown`.
- **3/3:** triage is the strongest new construct. Amendment applied:
  answers key on stable per-item ids (label fallback), not labels.
- **Split on deliberation:** fold into decision (claude) / keep with
  strict summary degradation (antigravity) / defer for a consumer
  (codex). The strict degradation and the synthesis-pick-is-not-the-
  answer separation were applied regardless.
- **Member-originated candidates:** confirm construct (claude + codex
  independently), tolerant markdown ingestion (all three seats' shared
  parser concern), ranking (codex), hunk_review (antigravity),
  assumption-review (codex), surface capability contract (codex).

## Chair rulings (form receipt resp-20260814-211025)

Collected through the live deliberation + triage widget rendered by the
constructs under ruling — their first human-validated round-trip.

1. **Deliberation: KEEP as its own construct** as built (pushback
   precedent: a distinct communicative act earns a construct even when
   the answer path is decision-shaped).
2. **confirm construct → spec next. tolerant markdown ingestion → spec
   next.** ranking / hunk_review / assumption-review / capability
   contract → backlog. Nothing declined.
3. Digest promoted to this stub; rulings recorded here.
