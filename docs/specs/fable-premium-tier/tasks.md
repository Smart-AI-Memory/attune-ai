# Tasks: Fable Premium Tier (attune-ai)

> Phase 3 of [requirements.md](requirements.md) /
> [design.md](design.md) (both approved 2026-07-10).
> Execution plan for Claude Code:
> [.claude/plans/fable-premium-tier.md](../../../.claude/plans/fable-premium-tier.md).

**Status**: in-progress (2026-07-13) — approved 2026-07-10 (Patrick:
"GO"); tasks 1–8 done on feat/fable-premium-tier (PR #1361); task 9
(release) parked ≥07-28. Amendment ratified during task 1:
`BASELINE_MODEL` moves to `claude-fable-5` — see task 7 note and
design.md §3 amendment.

## Implementation order

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Add `src/attune/model_tiers.py` — mirror of the canonical attune-rag contract (`resolve_model`, `fable_extras`, `ModelRefusalError`, constants) + unit tests | attune-ai | done | Stdlib-only; per-call env resolution. Copied from `attune_author/model_tiers.py` (docstring adapted to attune-ai's no-rag-dependency situation; logic byte-identical). 26 tests pass; ruff clean; import-clean verified. Commit `cd8ffe917`. |
| 2 | Drift test vs `attune_rag.model_tiers` (`pytest.importorskip`-guarded) + CI step installing `attune-rag>=0.8` in the test job | attune-ai | done | Ported from `attune-author/tests/test_model_tiers_drift.py`. Verified both paths: skip (venv's rag 0.7.0 predates model_tiers → 1 skipped) and pass (5/5 vs sibling checkout source). tests.yml gains the install step in the matrix test job; YAML parse-checked. |
| 3 | Add `src/attune/llm/fable_call.py` — `create_with_fable` / `acreate_with_fable` (beta-namespace switch, `extra_body` fallbacks, refusal → `ModelRefusalError`, retention hint on 400) + tests | attune-ai | done | Mirrors attune-author's proven `call_anthropic` fable handling (thin: no retry loop — that stays at call sites/provider). Retention hint re-raises same exception type when rebuildable from a message, else RuntimeError, original chained as `__cause__`. Docstring carries the first-TEXT-block gotcha for consumers. 13 mock-only tests. |
| 4 | Wire the central async provider (`llm/providers/anthropic.py`): fable extras + refusal + retention hint in `generate()`; extend `_normalize_api_kwargs_for_model` to strip `thinking`/sampling for `claude-fable*` with logged warnings | attune-ai | done | `generate()` routes through `acreate_with_fable` (beta namespace + fallbacks; refusal → `ModelRefusalError`; retention-hint 400, original chained). `_normalize` strips sampling AND whole `thinking` key for `claude-fable*` with per-param warnings (design §4a: strip + warn, don't raise); opus-4.7+ behavior untouched. 6 mock-only tests (`tests/llm/test_anthropic_provider_fable.py`); unit+llm suites green — 17,117 passed, 14 pre-existing env failures identical on stashed baseline. |
| 5 | Batch provider Option A: `_batch_premium_model()` in `anthropic_batch.py` (fable → opus-4-8 at request build) + tests; document the policy in the bulk skill's SKILL.md | attune-ai | done | `_batch_premium_model()` mirrors author's `_batch_polish_model()`; `create_batch` additionally downgrades ANY fable-model request at build time (downgrade BEFORE normalize, so opus rules strip sampling), logged per request. Policy line in bulk SKILL.md (+ `.agents` mirror via sync_agents_skills.py). 5 mock tests; provider fable tests migrated off `patch.dict(sys.modules)` to the `fake_module` fixture per the repo guard. Suite: 17,141 passed, 1 pre-existing env failure (live-Ollama). |
| 6 | Route all premium literals through `resolve_model("premium")` — the 12-surface table in design §3 (incl. `RoutingConfig` `default_factory`, template_defs literals → `claude-fable-5`) | attune-ai | done | All 12 surfaces routed: curator `_CURATOR_MODEL` → `_curator_model()` (per-call), escalation ladder built per instance (class attr removed), release `MODEL_CONFIG` resolves at import (comment notes it), YAML-in-string surfaces → literal `claude-fable-5`. Deviations: `model_router.py` has NO live literal (tier map is registry-sourced — task 7); docstring example updated. `test_agent_factory.py:393` left asserting opus — it exercises the registry-backed router path, which flips in task 7. 6 test files updated. Suite: 17,613 passed, 1 pre-existing live-Ollama failure. |
| 7 | Registry + pricing: `claude-fable-5` entries in `models/registry.py`, provider pricing table, `cost_tracker` ($10/$50 per MTok; cache write $12.50 / read $1) + tests. **AMENDED 2026-07-10 (Patrick):** `BASELINE_MODEL` moves to `claude-fable-5` — with fable premium at 2× opus pricing, an opus baseline yields negative savings on every premium call ("routing lost money" when the user deliberately upgraded). Safe because `baseline_cost` is computed at log time and stored per record (`cost_tracker.py:383-394`) — history stays frozen at opus math; only new records use fable. Also make the report label at `cost_tracker.py:521` (`"Baseline (Opus)"`) dynamic. | attune-ai | done | Supersedes design §3 "BASELINE_MODEL stays opus-4-8"; design.md carries the matching amendment note. Done: premium tier entry → fable-5 ($10/$50, 128K out); opus-4-8 kept by-id via ADDITIONAL_MODELS (batch target + history); TIER_PRICING/provider table/analytics baseline all consistent (analytics now registry-sourced); BASELINE_MODEL → fable-5 with dynamic report label; `_get_tier` knows fable; drift-guard suite `tests/unit/models/test_fable_pricing_consistency.py`. |
| 8 | Scattered premium call sites adopt the `fable_call` helper: `curator/core.py`, `workflows/escalation/chain.py`, `agents/release/base_agent.py`, `meta_workflows/llm_execution.py`; add `fable_refusal` telemetry event in workflow error handling | attune-ai | done | curator/base_agent/llm_execution swap `messages.create` → `(a)create_with_fable` (escalation chain already rides the fable-wired provider — no own client; it now RE-RAISES `ModelRefusalError` instead of retrying). base_agent + llm_execution fixed to read the first TEXT block, not `content[0]`. New `log_fable_refusal` helper (models/telemetry) emits the event wherever the refusal stops propagating: execution_mixin, curator degrade, agent fallback, meta_workflow failure dict. LangChain/LangGraph adapters out of scope v1 (design §4c). Mock-only tests via `fake_module`. |
| 9 | Docs + release: regenerate `plugin/help/generated/` tier docs, CHANGELOG entry with prominent premium price callout, version bump (pyproject.toml + plugin.json + uv.lock together), release | attune-ai | pending | Release via the standard publish flow (approval-gated). |

## Testing strategy

- Unit suites per task (mirroring attune-author's): tier resolution
  precedence, `fable_extras` gating, refusal handling, retention hint,
  param stripping, batch downgrade.
- Drift test with attune-rag installed from PyPI (CI-only extra step).
- LLM-test discipline per testing-conventions.md: autouse
  `ANTHROPIC_API_KEY`-strip fixture, patch at the
  `anthropic.Anthropic`/`AsyncAnthropic` import boundary, no live
  calls, no `live` marker needed (no new live tests).
- Full suite + lint green before each task's commit.

## Rollback plan

- Config pin `premium_model: claude-opus-4-8` or
  `ATTUNE_MODEL_PREMIUM=claude-opus-4-8` — no-deploy rollback.
- `git revert` per task commit (tasks are independent, ordered so
  earlier tasks don't depend on later ones).
- PyPI version pin as the hard rollback after release.
