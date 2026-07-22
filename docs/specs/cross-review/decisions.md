# Cross Review — Decisions

Dated chair rulings. Newest last.

## 2026-07-22 — Feature ratified (roundtable amendment)

Roundtable `q-multi-llm-obvious-win-001`: `cross_review` proposed by
the claude seat as its lead pick. Initial chair ruling recorded it
as a second-pick candidate gated on the 07-27 usage read; same-day
chair amendment RATIFIED it as the second committed multi-LLM
feature — the usage read now informs sequencing/design only.
Binding posture from the amendment: board-only advisory, never a
merge gate until dogfooded finding-quality earns it. Report:
`docs/reports/roundtable/q-multi-llm-obvious-win-001.md` (#1600).
Tracking issue: #1602.

## 2026-07-22 — Scheduling amendment (chair)

Spec AUTHORING pre-07-27; IMPLEMENTATION post-lift, SECOND after
cross-provider-session-handoff. Note: the second position is a
chair sequencing ruling, not a code dependency — the mechanism
reuses the shipped roundtable core only.

## 2026-07-22 — Requirements APPROVED (chair)

R1–R6 + non-goals as drafted; binding posture is a requirement
(blocking-path wiring violates the spec). OPEN-1 (default seat),
OPEN-2 (cadence surface), OPEN-3 (diff budget) explicitly held for
the 07-27 usage-signal read.

## 2026-07-22 — Design RATIFIED + tasks APPROVED (chair, one ruling)

D1 roundtable-primitive composition (`attune.roundtable.review`);
D2 read-only diff gathering with everywhere-visible truncation
manifest; D3 mandatory reply format + `lint_review()`,
noncompliance flagged never repaired; D4 advisory rendering, no
exit-code coupling; D5 per-run ledger append to receipts.md
(D7-honest); D6 knobs named, values land with OPEN-1..3.
Tasks T1 (module) → T2 (skill + mirrors) → T3 (five-run dogfood
ledger across ≥2 seats; low quality is a valid, posture-fixing
result) → T4 (docs + OPEN closure citing usage-read data). Spec is
now fully authored 2026-07-22; implementation staged post-07-27.
