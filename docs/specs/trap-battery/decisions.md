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
