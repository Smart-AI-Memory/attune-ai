# fable-premium-tier — decisions

## 2026-09-03 — Premium tier retargeted to Claude Fable 5.1 (Patrick, in-session)

**Ruling:** the PREMIUM tier default is `claude-fable-5-1`. Same
$10/$50 per MTok as Fable 5, same 1M context / 128K output, same
adaptive-only thinking, same server-side `fallbacks` opt-in via the
beta namespace (`claude-opus-4-8` stays the fallback target). `fable_extras`
keeps its `claude-fable` prefix test, so both generations ride the same
call path; `claude-fable-5` stays a known `ATTUNE_MODEL_PREMIUM`
override and is priced by id in `ADDITIONAL_MODELS` (still served,
and pre-5.1 telemetry records reference it).

**What 5.1 changes that this codebase had to absorb:**

- **Forced `tool_choice` is a 400** on 5.1 (`type "tool" and "any" are
  not supported for this model`). The curator was the only raw-SDK
  forced-tool call on the premium path; it now uses `tool_choice: auto`
  plus `strict: true` (schema objects gained `additionalProperties:
  false`) for fable models, and keeps the forced call for every other
  pin. Pinned by `tests/unit/curator/test_run_curator.py`.
- **Cache reads are $0.25/MTok** (0.025x input, versus the 0.1x every
  other model derives). `AnthropicProvider.get_model_info` carries an
  explicit `cost_per_1m_cache_read` on the 5.1 row and
  `calculate_actual_cost` honors it; rows without the key keep the 0.1x
  derivation. Pinned by `tests/unit/models/test_fable_pricing_consistency.py`.
- **Thinking blocks are bound to the producing model and to the
  conversation prefix.** Inferred, not live-verified: no attune-ai call
  site replays prior assistant turns with thinking blocks to the raw
  SDK (the provider extracts text only; escalation/retry builds fresh
  prompts; agent-factory adapters carry plain-text assistant turns), so
  neither check bites. Revisit if a multi-turn raw-SDK path is added.
- **Retention hint** in `attune.llm.fable_call` now reads
  `claude-fable-* models require >=30-day org data retention` — the
  requirement is unchanged on 5.1.

**Mirror contract:** `attune.model_tiers` is a byte-mirror of
`attune_rag.model_tiers` and CI installs attune-rag from PyPI for the
drift guard (`tests/unit/test_model_tiers_drift.py`). The same
`_DEFAULTS` / `_KNOWN_MODELS` change is carried to attune-rag in step;
this repo's drift lane is red until that attune-rag release is on
PyPI, by design — the guard is doing its job.

**Not adopted (follow-ups, chair-callable):** `fallbacks: "default"`
(the newer category-routed form under `server-side-fallback-2026-07-01`)
— the array form still works on 5.1 and keeps the fallback target
explicit for telemetry; per-message effort and turn-scoped system
messages (no agent loop here builds long `messages` arrays);
`thinking.display: "updates"` (no user watches a long tool-calling
turn through the provider).

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
