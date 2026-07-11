# Spec: Fable Premium Tier (attune-ai)

> Companion spec to the attune workspace's
> [specs/fable-model-tiers/](https://github.com/Smart-AI-Memory/attune/tree/main/specs/fable-model-tiers)
> (approved 2026-07-09; tasks 1–10 shipped in attune-rag 0.8.0 and
> attune-author 0.24.0/0.25.0). This spec covers the same decision —
> premium tier moves from `claude-opus-4-8` to `claude-fable-5` — applied
> to the attune-ai plugin, which has its own tier system, its own direct
> Anthropic call paths, and a Batch API surface the workspace packages
> mostly don't have.

---

## Phase 1: Requirements

**Status**: draft

### Problem statement

The attune workspace made Fable 5 the premium tier everywhere
(judge, polish, doc-gen) via `resolve_model("premium")` +
`fable_extras()` + `ModelRefusalError`. The attune-ai plugin still pins
premium to `claude-opus-4-8` across at least a dozen call sites and five
independent `ModelTier` enums. Until the plugin follows, "premium" means
different models in different layers of the same product, and plugin
users don't get Fable's capability gains on complexity-routed work.

Fable also brings three behaviors opus never had, each needing a
plugin-specific answer:

1. **Refusals** — safety classifiers can return HTTP 200 with
   `stop_reason: "refusal"`; content may be empty. Callers must check
   before reading `response.content`.
2. **Server-side fallback is beta-namespace + `extra_body` only** —
   `client.beta.messages.create(..., betas=["server-side-fallback-2026-06-01"],
   extra_body={"fallbacks": [{"model": "claude-opus-4-8"}]})`. The SDK
   (≤0.96 verified) rejects `fallbacks` as a named kwarg.
3. **The Batch API rejects `fallbacks` entirely** — the plugin's bulk
   paths (`analyze_batch`, batch workflows) cannot use server-side
   fallback at all and need their own refusal story.

Plus an operational constraint: fable-5 is **$10/$50 per MTok** vs
opus-4-8's $5/$25, and requires **30-day org data retention** (ZDR orgs
get a 400 on every request).

### Scope

**In scope:**

- Premium-tier default swap `claude-opus-4-8` → `claude-fable-5` at the
  known sites (audited 2026-07-10 against `src/attune`):
  - `config/agent_config.py:153` — `ModelTier.PREMIUM` default map
  - `config/sections/routing.py:37,71` — `premium_model` default
  - `config/xml_config.py:61` — `"very_complex"` complexity routing
  - `agent_factory/base.py:305` — agent factory premium default
  - `template_defs_basic.py:30,86`, `template_defs_web.py:29,203` —
    template model maps
  - `models/registry.py:151` — premium `ModelInfo` (id **and** pricing:
    $10/$50, not the current ~$5/M note)
  - `workflows/config.py:564,577` — YAML defaults/docs
  - `workflows/progressive/workflow.py:54` — progressive-depth premium
  - `curator/core.py:46` — `_CURATOR_MODEL`
  - `workflows/escalation/chain.py:69` — escalation chain top rung
  - `llm/providers/anthropic.py:406` — pricing table gains a
    `claude-fable-5` entry ($10/$50); opus entry stays (it remains the
    fallback target and batch premium)
- A `fable_extras()`-equivalent choke point for the plugin's direct
  (non-batch) Anthropic call paths: beta namespace + betas header +
  `extra_body` fallbacks + refusal check. Mirror the semantics of
  `attune_rag.model_tiers` (canonical copy) without importing it —
  attune-rag is not a plugin dependency.
- Refusal handling: `stop_reason == "refusal"` surfaces as a typed error
  (align naming with `ModelRefusalError` in attune-rag/author), never a
  silent empty result.
- **Batch premium story** (Decision required — see Edge cases): default
  proposal is to mirror attune-author's `_batch_polish_model()`
  precedent — batch submissions resolve premium and swap
  fable → `claude-opus-4-8`, so batch runs on the fallback target
  directly with no refusal-retry machinery.
- Env-override unification: `workflows/progressive/workflow.py:76`
  already reads `ATTUNE_MODEL_PREMIUM`; `workflows/config.py:658`
  documents legacy `EMPATHY_MODEL_PREMIUM`. Decide one canonical var
  (proposal: `ATTUNE_MODEL_PREMIUM`, matching the workspace) with the
  legacy var honored as a deprecated alias.
- Rollback lever: env pin `ATTUNE_MODEL_PREMIUM=claude-opus-4-8` must
  restore prior behavior at every swapped site without a release.

**Out of scope:**

- `cost_tracker.py:68` `BASELINE_MODEL = "claude-opus-4-8"` — the file's
  own comment says changing it mis-prices history. Stays.
- Cheap and capable tiers (haiku-4-5 / sonnet-5) — unchanged.
- attune-rag / attune-author changes — shipped under the workspace spec.
- Consolidating the five duplicate `ModelTier` enums
  (`config/agent_config.py`, `workflows/compat.py`,
  `models/registry.py`, `telemetry/feedback_models.py`,
  `routing/model_router.py`) into one — a real refactor, but a separate
  spec. This spec only requires the **default-model values** they carry
  to move together (see Edge cases).

### User stories

1. As a plugin user routing a `very_complex` task, I want premium to be
   Fable 5 so the hardest work gets the most capable model.
2. As a plugin user on a $20/month budget, I want `ATTUNE_MODEL_PREMIUM`
   to pin premium back to opus/sonnet so the 2× price jump is opt-out
   without a release.
3. As a bulk-skill user, I want batch premium jobs to keep succeeding
   (no `fallbacks`-rejection errors, no silently-refused items) even
   though the Batch API can't do server-side fallback.
4. As a maintainer, I want one choke point for fable request shaping so
   the beta header / extra_body rules aren't re-implemented per call
   site (the workspace spec's lesson).

### Affected components

- [x] Plugin config (`plugin.json`) — version bump on release
- [x] PyPI package (`pyproject.toml`, release pipeline)
- [x] Core `src/attune` modules (config, routing, agent factory,
  templates, registry, workflows, curator, providers)
- [ ] Skills (`plugin/skills/`) — bulk skill docs mention the batch
  premium behavior; no interface change expected
- [ ] Agents (`plugin/agents/`) — inherit via agent factory defaults
- [ ] Help templates — regenerate after the swap (staleness detection
  will flag them)

### Invocation & triggers

No new user-facing invocation. Existing surfaces change behavior:
complexity routing (`very_complex`), agent factory `premium` tier,
`/bulk` batch processing at `model_tier: "premium"`, curator, and the
escalation chain.

### Tool scope

N/A — this is a library/config change, not a new skill or agent.

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Above; site audit dated 2026-07-10 |
| **Skill/agent contracts** | addressed | No SKILL.md interface changes; bulk skill docs note batch-premium = opus |
| **User interaction** | addressed | Behavior change only; refusals surface as typed errors with the stop_details category |
| **Edge cases** | addressed | See table below (batch, refusal, retention, pricing, enum drift) |
| **Plugin compatibility** | addressed | Explicit model args and env pins unchanged; `BASELINE_MODEL` untouched |
| **Error handling** | addressed | Refusal → typed error; retention 400 → hint appended (mirror workspace wording) |
| **Tradeoffs & alternatives** | addressed | See table below |
| **Rollback strategy** | addressed | Env pin (no deploy) → revert defaults (code) → PyPI version pin (release) |

### Edge cases & open questions

| Question / Edge case | Resolution |
|----------------------|------------|
| **Batch API rejects `fallbacks` — what's batch premium?** | **DECISION REQUIRED.** Option A (proposed): swap fable→opus-4-8 at batch-submission time, mirroring attune-author `_batch_polish_model()`. Option B: submit fable, detect per-item `stop_reason: "refusal"` in results, re-queue refused items on opus client-side. A is one line and proven; B preserves fable quality for the non-refused majority at the cost of result-processing machinery and a second batch round-trip. Propose A now; B can be a follow-up if refusal rates prove negligible. |
| Refusal after the whole fallback chain declines (direct calls) | Typed error with `stop_details.category`/`explanation`; workflows record the item as errored, never silently skipped (same rule as the workspace spec). |
| Org without 30-day retention → 400 on every fable call | Re-raise with the retention hint (same wording as attune-rag) so users don't debug payloads. |
| Cost/pricing drift | `models/registry.py` premium pricing and `llm/providers/anthropic.py` table must both gain fable-5 at $10/$50; cost dashboards re-baseline. `BASELINE_MODEL` stays opus. |
| Five `ModelTier` enums / many default maps drift after the swap | Add a unit test asserting every premium default site resolves to the same model ID (grep-driven list), so a future partial edit fails CI. Full enum consolidation deferred. |
| Batch + `betas` header | The batch path must NOT send the server-side-fallback beta or `extra_body` fallbacks (rejected); the choke point must distinguish batch from direct calls. |
| `EMPATHY_MODEL_PREMIUM` legacy env var | Honor as deprecated alias if set and `ATTUNE_MODEL_PREMIUM` unset; warn once. Confirm no other consumer depends on it. |
| Anthropic SDK floor | `extra_body` works on every SDK version; no floor bump needed for the fallback shape. Verify the installed floor supports `stop_details` fields (present since the 4.7-era SDKs). |

### Gaps (if any)

- Phase 1 drafted from the workspace spec's decisions plus a code audit;
  Patrick has not yet been interviewed on the plugin-specific choices
  (batch Option A vs B, env-var alias policy). Status stays `draft`
  until those are confirmed.
- Refusal-rate telemetry doesn't exist yet — the A-vs-B batch decision
  is being made without data. Acceptable: A is reversible.

---

## Phase 2: Design

> To be created at `specs/fable-premium-tier/design.md` after
> requirements approval. Key design inputs: the canonical
> `attune_rag/model_tiers.py` (attune-rag 0.8.0) for `fable_extras`
> semantics, and attune-author's `_batch_polish_model()` for the batch
> swap precedent. Note both mirrored modules are stdlib-`logging`-only —
> attune-ai uses structlog, so its copy may use structlog but must not
> be byte-shared with the author mirror.

## Phase 3: Tasks

> To be created at `specs/fable-premium-tier/tasks.md` after design
> approval.

## Phase 4: Implementation

> Tracked via the tasks table once Phase 3 is approved.
