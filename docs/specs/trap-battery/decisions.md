# Decisions — trap-battery

## 2026-07-08 — Spec originated; pilot scale ratified

- **Origin:** next-session-starter queue item 3 ("the real next
  milestone"), after items 1–2 verified shipped and the README
  badge guard (2c) was found ALREADY BUILT (#659) — see
  `project_guardrail_candidates` memory for that closure.
- **Pilot scale (Patrick, via AskUserQuestion):** 3 classes ×
  2 arms × 5 repeats (~30 sessions, ~$30–60 est.), then scale.
  Chosen over 20/cell-from-the-start (pays full price for trap
  designs that may not discriminate) and 3/cell smoke (no rates
  at all). Discrimination gate (each trap fires ≥2/5 OFF-arm)
  decides which classes graduate to the 20+/cell rate run.
- **Deterministic scoring only in phase 1** — no LLM judge.
  Aligns with the guardrails-as-code receipt discipline; a trap
  whose failure cannot be machine-checked is redesigned.
- **question-shape flagged weakest scorer** at requirements time;
  pre-approved swap candidate is `zsh-status-readonly` (measured
  exposure; JIT-fired in the originating session itself).

## 2026-07-12 — Phase 1 pilot APPROVED (Patrick)

- Approved via the freeze-week plan (product-direction-review,
  Block 4) — a decision, not a design pass, per the third
  assessment's ledger item 9.
- Scope unchanged from the ratified pilot: 3 classes × 2 arms ×
  5 repeats, deterministic scoring only, discrimination gate
  before any scale-up.
- Sequencing: build/run AFTER freeze-week Block 0 lands
  (`ANTHROPIC_ADMIN_API_KEY` + Console spend cap), so the
  ~$30–60 pilot spend runs under live enforcement. The run
  itself still gets a stated-cost go at execution time per the
  spend gate.
- DEC-1 note: existing spec directory — freeze-compatible.
