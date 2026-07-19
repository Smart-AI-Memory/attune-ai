# Grounding pack — spec-lifecycle-gates (producing-run input)

**Subject:** Intelligent progress/quality gates for the spec-driven
development lifecycle, runnable autonomously or chair-gated.
**Provenance:** round-table thread `q-spec-gates-001` (2026-07-19,
promoted to `docs/reports/roundtable/q-spec-gates-001.md`).
**Drafter:** claude (owed per rotation ledger). **Arming:** per-spec
(chair queues this pack; no standing cadence).

## The composed frame the table converged on (seed, not contract)

- Gates sit at the five lifecycle boundaries (brainstorm →
  requirements → design → tasks → execution → verification) plus a
  continuous drift/self-truthing sweep.
- Autonomy split (unanimous): autonomous gates may BLOCK / REVISE /
  REPORT with exact shortfalls; only the chair APPROVES scope,
  irreversible choices, waivers, promotion. Never-auto-promote
  generalizes to never-auto-advance-on-judgment.
- Container (codex): a shared gate protocol — machine-readable
  findings, evidence references, proposed disposition, four states:
  `PASS / REVISE / CHAIR_REQUIRED / BLOCKED`.
- Build path (claude): map each gate onto a SHIPPED mechanism —
  compiler-lint seam (TR-4), corpus-readiness refuse-with-shortfall
  shape (RR-1), doc-import-gate + `[[?slug]]` hatch, producing-run
  caps, central receipt re-run (delegation receipts), curator
  sources for triage, starter-reconciler-style self-truthing.
- Escalation policy (antigravity): blast radius — additive/isolated
  auto-passes; public API, shared schema, security primitives,
  migrations always chair.
- Shared named risk: ceremony inflation / Goodhart on lintable
  formats. Shared mitigation: risk-tiered activation — a small
  mandatory baseline (the fully-mechanical gates) with the full
  ladder only for spec-tier / irreversible work.

## Chair rulings already made (constraints on the draft)

See `decisions.md` in this directory — verdict-ledger location,
flaky-live-fire override path, and fixed-vs-dynamic gate policy are
ruled; the draft must conform, not re-litigate.

## Live probes the drafter must run (PACK discipline)

- Verify each claimed building block exists and name its import
  path/entry point (compiler lints, producing module, readiness
  gate, drift-guard examples, curator sources contract, receipts
  taxonomy source).
- Grep for existing enforcers before proposing any new gate — the
  twice-earned lesson: several "new" gates may already have partial
  tests (e.g. rules-residency budget, doc-import audit, complexity
  ratchet, lessons golden-smoke).
- Count the real chair-interaction cost: how many decisions.md
  rulings per week the current process already generates, so the
  gate ladder's CHAIR_REQUIRED volume is designed against measured
  decision fatigue, not guessed.

## Non-goals to carry into the draft

- No second telemetry pipeline; verdict storage follows the ruled
  ledger location.
- No gate fires on sub-spec-tier work beyond the mandatory baseline
  (the xml-enhanced-prompts "Do NOT use" list is the tier boundary).
- The chair's per-item ruling surface stays decisions.md — gates
  produce candidates and evidence, never rulings.
