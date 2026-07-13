# Tasks: Fable Premium Tier (attune-ai)

> Phase 3 of [requirements.md](requirements.md) /
> [design.md](design.md) (both approved 2026-07-10).
> Execution plan for Claude Code:
> [.claude/plans/fable-premium-tier.md](../../../.claude/plans/fable-premium-tier.md).

**Status**: approved (2026-07-10 — Patrick: "GO" in session; execution
started same day. Amendment ratified during task 1: `BASELINE_MODEL`
moves to `claude-fable-5` — see task 7 note and design.md §3
amendment.)

## Implementation order

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Add `src/attune/model_tiers.py` — mirror of the canonical attune-rag contract (`resolve_model`, `fable_extras`, `ModelRefusalError`, constants) + unit tests | attune-ai | done | Stdlib-only; per-call env resolution. Copied from `attune_author/model_tiers.py` (docstring adapted to attune-ai's no-rag-dependency situation; logic byte-identical). 26 tests pass; ruff clean; import-clean verified. Commit `cd8ffe917`. |
| 2 | Drift test vs `attune_rag.model_tiers` (`pytest.importorskip`-guarded) + CI step installing `attune-rag>=0.8` in the test job | attune-ai | done | Ported from `attune-author/tests/test_model_tiers_drift.py`. Verified both paths: skip (venv's rag 0.7.0 predates model_tiers → 1 skipped) and pass (5/5 vs sibling checkout source). tests.yml gains the install step in the matrix test job; YAML parse-checked. |
| 3 | Add `src/attune/llm/fable_call.py` — `create_with_fable` / `acreate_with_fable` (beta-namespace switch, `extra_body` fallbacks, refusal → `ModelRefusalError`, retention hint on 400) + tests | attune-ai | done | Mirrors attune-author's proven `call_anthropic` fable handling (thin: no retry loop — that stays at call sites/provider). Retention hint re-raises same exception type when rebuildable from a message, else RuntimeError, original chained as `__cause__`. Docstring carries the first-TEXT-block gotcha for consumers. 13 mock-only tests. |
| 4 | Wire the central async provider (`llm/providers/anthropic.py`): fable extras + refusal + retention hint in `generate()`; extend `_normalize_api_kwargs_for_model` to strip `thinking`/sampling for `claude-fable*` with logged warnings | attune-ai | pending | Fable rejects explicit `thinking` config; strip + warn, don't raise (design §4a). |
| 5 | Batch provider Option A: `_batch_premium_model()` in `anthropic_batch.py` (fable → opus-4-8 at request build) + tests; document the policy in the bulk skill's SKILL.md | attune-ai | pending | Batch API rejects `fallbacks`. Mirrors author's `_batch_polish_model()`. |
| 6 | Route all premium literals through `resolve_model("premium")` — the 12-surface table in design §3 (incl. `RoutingConfig` `default_factory`, template_defs literals → `claude-fable-5`) | attune-ai | pending | Update the 4 breaking test assertions (design §Testing). |
| 7 | Registry + pricing: `claude-fable-5` entries in `models/registry.py`, provider pricing table, `cost_tracker` ($10/$50 per MTok; cache write $12.50 / read $1) + tests. **AMENDED 2026-07-10 (Patrick):** `BASELINE_MODEL` moves to `claude-fable-5` — with fable premium at 2× opus pricing, an opus baseline yields negative savings on every premium call ("routing lost money" when the user deliberately upgraded). Safe because `baseline_cost` is computed at log time and stored per record (`cost_tracker.py:383-394`) — history stays frozen at opus math; only new records use fable. Also make the report label at `cost_tracker.py:521` (`"Baseline (Opus)"`) dynamic. | attune-ai | pending | Supersedes design §3 "BASELINE_MODEL stays opus-4-8"; design.md carries the matching amendment note. |
| 8 | Scattered premium call sites adopt the `fable_call` helper: `curator/core.py`, `workflows/escalation/chain.py`, `agents/release/base_agent.py`, `meta_workflows/llm_execution.py`; add `fable_refusal` telemetry event in workflow error handling | attune-ai | pending | LangChain/LangGraph adapters out of scope v1 (design §4c). |
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
