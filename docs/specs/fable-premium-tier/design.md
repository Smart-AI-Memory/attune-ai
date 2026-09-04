# Design: Fable Premium Tier (attune-ai)

> Phase 2 of [requirements.md](requirements.md) (approved 2026-07-10,
> Batch question decided: Option A). Companion to the workspace spec
> `specs/fable-model-tiers/` (attune repo, approved 2026-07-09), whose
> design this mirrors where the plugin's architecture allows.

**Status**: approved (2026-07-10 — Patrick, via PR #1303 review)

## Architecture

### Starting point (what the explore pass found)

Unlike attune-rag/attune-author — which each had one LLM chokepoint —
attune-ai has **no** central model-tier module and **no** single client
wrapper. `"claude-opus-4-8"` is hardcoded as the premium model at ~12
live routing sites, and Anthropic clients are constructed at 12+
independent call sites. The design therefore has two halves:

1. **Tier resolution** — introduce the canonical `model_tiers.py`
   contract (third mirror) and route every premium literal through it.
2. **Fable request handling** — wire betas/fallbacks/refusal handling
   into the two providers that carry premium traffic, plus a small
   shared helper for the scattered direct call sites.

### 1. Tier resolution — `src/attune/model_tiers.py` (new)

> **Correction 2026-09-04.** The "attune-ai does not depend on
> attune-rag" premise below was already false at approval: attune-rag
> has been a core dependency since 2026-04-30 (`c2ab06e40`). The mirror,
> drift test, and CI install step are retired; `attune.model_tiers` is
> now a re-export of `attune_rag.model_tiers` with a `>=1.2.0` floor.
> The rest of §1 is kept as the historical design.

Byte-for-byte mirror of the canonical `attune_rag/model_tiers.py`
resolution contract (same as `attune_author/model_tiers.py`):

- Exports: `resolve_model(tier)`, `fable_extras(model)`,
  `ModelRefusalError`, constants `_DEFAULTS`, `_ENV`, `_KNOWN_MODELS`,
  `_FABLE_BETAS`, `_FABLE_FALLBACKS`.
- `_DEFAULTS = {"premium": "claude-fable-5", "capable":
  "claude-sonnet-5", "cheap": "claude-haiku-4-5"}`.
- Stdlib-only (`logging` + `os`), no anthropic import, no I/O at
  import time. Resolution is per-call (`os.getenv` on each call), so
  tests/CI flip tiers with `monkeypatch.setenv`.
- **Drift test**: port `attune-author/tests/test_model_tiers_drift.py`.
  attune-ai does not depend on attune-rag, so the drift test is
  `pytest.importorskip("attune_rag")`-guarded, and a dedicated CI step
  installs `attune-rag>=0.8` from PyPI (the version that ships
  `model_tiers`) in the test job before running it. This keeps the
  lesson from the sibling-hooks drift problem: duplication only with an
  automated alarm.

### 2. Env vs config precedence (decides the requirements open question)

**Env wins over config; config wins over the built-in default.** This
matches both the platform packages (`resolve_model` is env-first) and
the plugin's own shipped behavior — `workflows/config.py:284-290` and
`workflows/progressive/workflow.py:67-76` already apply
`ATTUNE_MODEL_PREMIUM` at highest priority over `routing.premium_model`.
Changing to config-authoritative would be a behavior regression for
existing users. User story 3 is still satisfied: an explicit
`premium_model` in routing config beats the new fable **default**;
only an explicit env var beats the config.

Resolution order for the premium tier, everywhere:

```
ATTUNE_MODEL_PREMIUM (env)  >  routing.premium_model (user config)  >  resolve_model default (claude-fable-5)
```

Implementation: `RoutingConfig` keeps its dataclass shape but its
defaults defer to the tier module —
`premium_model: str = field(default_factory=lambda: resolve_model("premium"))`
(and the same expression as the `from_dict` fallback). Because
`resolve_model` is env-aware, a config object constructed with no
explicit value already reflects the env override; call sites that today
read `os.getenv("ATTUNE_MODEL_PREMIUM", config_value)` keep working
unchanged.

### 3. Tier-surface changes (all → `resolve_model("premium")`)

Every live premium routing literal is replaced by a call through the
tier module, so the *next* model change is a one-line diff:

| Surface | Today | Change |
|---|---|---|
| `config/agent_config.py:153` | `ModelTier.PREMIUM: "claude-opus-4-8"` in `get_model_id()` | `resolve_model("premium")` |
| `config/sections/routing.py:37,71` | dataclass + `from_dict` defaults | `default_factory` per §2 |
| `agent_factory/base.py:305` | ImportError-fallback tier map | `resolve_model("premium")` |
| `config/xml_config.py:61` | `"very_complex": "claude-opus-4-8"` | `resolve_model("premium")` (in `default_factory`) |
| `workflows/config.py:564,577` | embedded default YAML | literal → `claude-fable-5` (data, not code) with comment pointing at `model_tiers` |
| `workflows/progressive/workflow.py:54` | defaults map | `resolve_model("premium")` |
| `workflows/escalation/chain.py:69` | escalation final model | `resolve_model("premium")` |
| `curator/core.py:46` | `_CURATOR_MODEL` constant | resolve per-call (constant becomes a function or is resolved at use) |
| `agents/release/release_models.py:50` | `MODEL_CONFIG["premium"]` | `resolve_model("premium")` |
| `models/adaptive_routing.py:159` | tier map | `resolve_model("premium")` |
| `routing/model_router.py:185` | premium routing target | `resolve_model("premium")` |
| `template_defs_basic.py:30,86`, `template_defs_web.py:29,203` | YAML-in-string agent template defaults | literal → `claude-fable-5` (generated agent configs; the runtime honors explicit overrides as today) |

**Not changed** (data/telemetry, opus remains real and priced):
`models/registry.py` keeps its opus-4-8 entry and **gains** a
`claude-fable-5` entry ($10/$50 per MTok, 1M context, 128K output);
`llm/providers/anthropic.py:406` pricing table gains a fable row;
telemetry filters unchanged.

> **Amendment (2026-07-10, Patrick, during execution):** the original
> design kept `BASELINE_MODEL = "claude-opus-4-8"`. Amended:
> `BASELINE_MODEL` moves to `claude-fable-5`. With fable premium at 2×
> opus pricing, an opus baseline makes every premium call report
> *negative* savings — "routing lost money" when the user deliberately
> upgraded. The historical-continuity concern that motivated the
> original choice was verified moot: `baseline_cost` is computed at
> log time and stored per record (`cost_tracker.py:383-394`), so old
> records keep opus math and only post-switch records use fable. The
> hardcoded report label `"Baseline (Opus)"` (`cost_tracker.py:521`)
> becomes dynamic in the same change (task 7).

### 4. Fable request handling — providers + one helper

Fable calls differ in four ways: beta namespace + fallback opt-in,
no explicit `thinking`/sampling params, `stop_reason: "refusal"`
handling, and the ≥30-day-retention 400. attune-ai wires this at three
places:

**(a) `llm/providers/anthropic.py` (central async provider — the main
interactive path).** In `generate()` around the `:212` call:

```python
extras = fable_extras(model)          # {} for non-fable
if extras:
    response = await self.client.beta.messages.create(
        **api_kwargs, betas=extras["betas"],
        extra_body=extras["extra_body"],   # fallbacks ride here; SDK ≤0.96 has no typed param
    )
else:
    response = await self.client.messages.create(**api_kwargs)
if response.stop_reason == "refusal":
    raise ModelRefusalError(...)      # category/explanation from stop_details
```

Retention hint: a non-retryable 400 on a fable call is re-raised with
the platform packages' hint appended (*"claude-fable-5 requires ≥30-day
org data retention — check the org's retention configuration before
debugging the payload"*).

Param stripping: `_normalize_api_kwargs_for_model` currently strips
sampling params via `_OPUS_NO_SAMPLING_RE` (matches opus-4.7+ only).
Extend it: for `claude-fable*` models strip `temperature`/`top_p`/
`top_k` **and** any explicit `thinking` config (fable rejects
`{"type": "disabled"}` and `budget_tokens`; adaptive-by-default means
omission is correct), each with a logged warning — consistent with the
existing opus behavior and the attune-rag judge precedent. **Decision
from requirements' open question: strip + warn, don't raise.**

**(b) `llm/providers/anthropic_batch.py` (the bulk-skill path) —
Option A.** The Batch API rejects `fallbacks`, so batch premium work
never targets fable. Mirror attune-author's `_batch_polish_model()`:

```python
def _batch_premium_model() -> str:
    model = resolve_model("premium")
    return "claude-opus-4-8" if fable_extras(model) else model
```

Any batch request whose resolved model is fable is downgraded to
opus-4-8 at request-build time (`:118-123` normalization site). The
bulk skill docs state the policy: *interactive premium = fable-5 (with
server-side opus fallback); batch premium = opus-4-8*. Follow-up
telemetry (below) feeds a future Option B revisit.

**(c) Scattered direct call sites.** `curator/core.py`,
`workflows/escalation/chain.py`, `agents/release/base_agent.py`,
`meta_workflows/llm_execution.py` construct their own clients and can
now receive a fable model from `resolve_model("premium")`. A new thin
helper `src/attune/llm/fable_call.py` (~40 lines, sync + async
variants) wraps the namespace switch + refusal check + retention hint
so no call site hand-rolls it:

```python
msg = create_with_fable(client, model=model, **kwargs)   # sync
msg = await acreate_with_fable(client, model=model, **kwargs)
```

Call sites swap `client.messages.create(...)` for the helper. Sites
that only ever run cheap/capable models are untouched. LangChain/
LangGraph adapters are **out of scope for v1**: they pass model IDs to
`ChatAnthropic`, which handles fable without the fallback opt-in; a
refusal there surfaces as an empty/failed generation — documented
limitation, revisit if adapter usage grows.

### 5. Refusal telemetry (feeds the Option B revisit)

`ModelRefusalError` handling in the workflow layer records a
`fable_refusal` telemetry event (existing telemetry plumbing —
`models/telemetry/`) with the category from `stop_details`. Reaching
this means the *whole* fable→opus chain refused; the item errors,
never silently skips. Once a real refusal rate is known, requirements'
Option B (batch re-queue) can be costed.

## API changes

No MCP tool or skill interface changes. Python-surface changes:

| Surface | Change |
|---|---|
| `attune.model_tiers` (new) | mirrored contract: `resolve_model`, `fable_extras`, `ModelRefusalError` |
| `attune.llm.fable_call` (new) | `create_with_fable` / `acreate_with_fable` helpers |
| `AnthropicProvider.generate()` | beta-namespace switch, refusal → typed error, retention hint, fable param stripping |
| `anthropic_batch` | `_batch_premium_model()` downgrade (Option A) |
| `RoutingConfig` | defaults defer to `resolve_model`; explicit user values still win |
| bulk skill SKILL.md | documents the batch-premium-stays-opus policy |

Backward compatibility: every changed surface keeps its explicit
`model:`/`premium_model:` parameter — callers pinning a literal model
ID see no behavior change. No anthropic SDK floor bump (`fallbacks`
rides in `extra_body`, verified through 0.96 —
`~/.claude/.../memory: project_fable_fallbacks_extra_body`).

## Data model changes

None. Operational notes:

- **Tokenizer**: fable-5 uses the Opus 4.8 tokenizer — counts roughly
  unchanged vs opus-4-8, so no `max_tokens` audit needed for the
  premium switch itself.
- **Pricing**: premium moves $5/$25 → $10/$50 per MTok (prompt cache:
  $12.50/MTok write, $1/MTok read — confirmed against the live pricing
  page 2026-07-10). Cost-tracker gains the fable row;
  `BASELINE_MODEL` moves to `claude-fable-5` per the §3 amendment
  (log-time storage keeps historical records priced at opus math).
  Release notes call out the premium price change prominently.

## UI/UX

N/A — no UI. CLI/config help text updated to name the new premium
default and the three-level precedence (env > config > default).
Refusals surface as a typed, per-item error in workflow output with
the category and a one-line remediation hint.

## Cross-layer impact

- attune-rag / attune-author: **no changes** (shipped, PRs #188/#87).
- attune-ai is self-contained; it mirrors the contract, it does not
  import it. CI installs `attune-rag` from PyPI only for the drift
  test.
- Release: single attune-ai release (version bump in pyproject.toml +
  plugin.json + uv.lock together, per the three-file rule); plugin
  users pick up the new default on upgrade; rollback is a config pin.

## Tradeoffs & alternatives

| Option | Pros | Cons | Chosen? |
|---|---|---|---|
| Third mirrored `model_tiers.py` + PyPI-installed drift test | Consistent contract across all 3 packages; no new runtime dep | Third copy to keep in sync (alarmed) | ✅ |
| Depend on attune-rag for tiers | Single source | New runtime dep for 3 constants; plugin install footprint grows | ❌ |
| Flip literals in place (no tier module) | Smallest diff | 12 sites to find again next model change; no env parity | ❌ |
| Batch Option A (opus for batch premium) | Zero new failure modes; predictable 50% discount economics; matches author precedent | "Premium" differs batch vs interactive (documented) | ✅ (decided in Phase 1) |
| Batch Option B (fable + re-queue refusals) | Fable quality in batch | Re-queue machinery; refusal rate unknown | Deferred until telemetry |
| Raise on explicit thinking/sampling params | Fail-loud | Breaks existing callers that pass temperature everywhere | ❌ (strip + warn) |

## Testing strategy (summary — expanded in tasks.md)

- Unit (mirroring author's suites): `resolve_model` precedence
  (env > config default), `fable_extras` gating, refusal →
  `ModelRefusalError` (mocked `stop_reason: "refusal"`), retention-hint
  wrapping on 400, fable param stripping, `_batch_premium_model()`
  downgrade.
- Drift: `_DEFAULTS`/`_ENV`/`_KNOWN_MODELS`/`_FABLE_*` equality vs
  `attune_rag.model_tiers` (importorskip-guarded; CI installs
  attune-rag>=0.8 in a dedicated step).
- Update the 4 breaking assertions found in the explore pass:
  `tests/agent_factory/test_agent_factory.py:393`,
  `tests/unit/config/test_config_validation.py:283,290`,
  `tests/unit/agents/release/test_release_models.py:392`,
  `tests/unit/workflows/escalation/test_chain.py:75`.
- All per testing-conventions.md: autouse key-strip fixture, patch at
  the `anthropic.Anthropic`/`AsyncAnthropic` import boundary, no live
  calls.

## Rollback

- **No-deploy**: `premium_model: claude-opus-4-8` in routing config, or
  `ATTUNE_MODEL_PREMIUM=claude-opus-4-8` in the environment.
- **Code-level**: revert `_DEFAULTS` in `attune.model_tiers` (drift
  test will flag divergence from the platform packages — intentional
  until they revert too).
- **Hard**: pin the previous attune-ai version from PyPI.
