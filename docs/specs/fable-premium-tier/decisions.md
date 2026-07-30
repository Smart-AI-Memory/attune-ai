# fable-premium-tier — decisions

## 2026-07-29 — Editing model split from the premium tier (Patrick, in-session)

**Ruling:** writing tasks draft on the CAPABLE tier
(`claude-sonnet-5`); editing/polish passes run on a dedicated
**editing model**, default `claude-opus-5`, env-overridable via
`ATTUNE_MODEL_EDITING`. The PREMIUM tier stays `claude-fable-5`
per this spec — the editing model is deliberately NOT a tier,
because `attune.model_tiers` is a byte-mirrored contract owned by
attune-rag and must not grow attune-ai-local keys.

**What moved:**

- `attune.authoring.polish._polish_model()`: premium tier
  (Fable 5, $10/$50) → editing model (Opus 5, $5/$25) — halves
  polish cost while keeping Opus-tier editing judgment.
- `attune.help.polish`: hardcoded `claude-sonnet-5` → editing
  model (editing pass upgraded from the drafting model).
- `claude-opus-5` added to `ADDITIONAL_MODELS` ($5/$25, 128K
  output) so cost tracking prices editing calls; not tier-routed.

**Enforcers:** `tests/unit/models/test_editing_model.py` (default,
override, blank-override, priced-in-registry) and
`tests/unit/authoring/test_polish_smoke.py` (wire-level sentinel,
now pinned to the editing default).

**Rationale (from the model comparison read the same evening):**
quality differences between Sonnet and Opus show up most in
editing — what to cut, what a reader needs — while drafting
quality is near-parity at 3/5 the price; mechanical verification
gates (doc-import, claim-drift, /verify) already floor the
drafting quality risk.
