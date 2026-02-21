# Ultra Tier: Opus 4.6 with 1M Context Window

**Created:** 2026-02-21
**Source:** /brainstorm session
**Status:** Experimental (beta API feature)

## Problem

Attune's 3-tier routing (cheap/capable/premium) maxes out
at 200K context. Some tasks -- whole-repo review,
cross-module bug hunting, full-codebase refactoring --
need both more context AND the best reasoning capability.
There is no way to leverage Opus 4.6's 1M context beta.

## Goals

- Cost protection: ultra only fires when genuinely needed
  (must-have)
- New capabilities: unlock task types impossible at other
  tiers (must-have)
- Seamless routing: system detects when context exceeds
  premium's window (must-have)
- Experimental flag: clearly marked as beta (must-have)
- Graceful fallback if the beta API changes (nice-to-have)

## End State

A fourth "ultra" tier in the routing system that:

1. Uses `claude-opus-4-6` with the
   `anthropic-beta: context-1m-2025-08-07` header
2. Routes new task types: `whole_repo_review`,
   `cross_module_analysis`, `full_codebase_refactor`,
   `deep_context_reasoning`
3. Uses long-context pricing: $10/MTok input,
   $37.50/MTok output
4. Auto-escalates from premium when estimated input
   tokens exceed 200K
5. Marked as experimental throughout

**Demo moment:** Run a whole-repo code review on the
Attune codebase itself in a single pass.

## Approach

Six implementation tasks using XML-enhanced prompts.

---

```xml
<task id="1" name="model-registry-ultra">
  <objective>
    Add ULTRA tier to ModelTier enum, extend ModelInfo
    with beta_headers and context_window fields, and
    register the ultra model in MODEL_REGISTRY.
  </objective>

  <context>
    <existing-code path="src/attune/models/registry.py">
      ModelTier enum has CHEAP, CAPABLE, PREMIUM.
      ModelInfo is a frozen dataclass with id, provider,
      tier, costs, max_tokens, supports_vision,
      supports_tools. MODEL_REGISTRY maps
      provider -> tier -> ModelInfo.
      TIER_PRICING dict has cheap/capable/premium entries.
      _build_caches iterates ModelTier enum values.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/models/registry.py">
      <change location="ModelTier enum (line 20-30)">
        BEFORE:
        class ModelTier(Enum):
            CHEAP = "cheap"
            CAPABLE = "capable"
            PREMIUM = "premium"

        AFTER:
        class ModelTier(Enum):
            CHEAP = "cheap"
            CAPABLE = "capable"
            PREMIUM = "premium"
            ULTRA = "ultra"
      </change>

      <change location="ModelInfo dataclass (line 39-66)">
        Add two optional fields:
        - beta_headers: dict[str, str] | None = None
        - context_window: int = 200_000
        These must be keyword-only to preserve frozen
        dataclass compatibility.
      </change>

      <change location="MODEL_REGISTRY (line 125-162)">
        Add "ultra" entry under "anthropic":
        ModelInfo(
            id="claude-opus-4-6",
            provider="anthropic",
            tier="ultra",
            input_cost_per_million=10.00,
            output_cost_per_million=37.50,
            max_tokens=128_000,
            supports_vision=True,
            supports_tools=True,
            beta_headers={
                "anthropic-beta":
                "context-1m-2025-08-07"
            },
            context_window=1_000_000,
        )
      </change>

      <change location="TIER_PRICING (line 464-468)">
        Add ultra pricing entry:
        "ultra": {
            "input": 10.00,
            "output": 37.50
        }
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      ModelTier.ULTRA.value == "ultra"
    </check>
    <check>
      MODEL_REGISTRY["anthropic"]["ultra"].id
      == "claude-opus-4-6"
    </check>
    <check>
      MODEL_REGISTRY["anthropic"]["ultra"].beta_headers
      is not None
    </check>
    <check>
      MODEL_REGISTRY["anthropic"]["ultra"].context_window
      == 1_000_000
    </check>
    <check>
      ModelRegistry().list_tiers() includes "ultra"
    </check>
  </validation>

  <risks>
    <risk severity="low">
      Same model ID as premium -- ensure
      get_model_by_id returns both entries or handles
      the collision. May need to use tier-qualified
      lookups instead.
    </risk>
  </risks>
</task>
```

---

```xml
<task id="2" name="task-types-ultra">
  <objective>
    Add ultra-tier task types to TaskType enum and
    create ULTRA_TASKS frozenset with tier mappings.
  </objective>

  <context>
    <existing-code path="src/attune/models/tasks.py">
      TaskType enum with CHEAP/CAPABLE/PREMIUM sections.
      CHEAP_TASKS, CAPABLE_TASKS, PREMIUM_TASKS
      frozensets. TASK_TIER_MAP combines all three.
      get_tier_for_task() defaults to CAPABLE.
      get_tasks_for_tier() and get_all_tasks() return
      task lists by tier.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/models/tasks.py">
      <change location="TaskType enum (after PREMIUM section)">
        Add ULTRA section:
        # ULTRA TIER TASKS (~$10/M input, 1M context)
        # Experimental: requires beta API access
        WHOLE_REPO_REVIEW = "whole_repo_review"
        CROSS_MODULE_ANALYSIS = "cross_module_analysis"
        FULL_CODEBASE_REFACTOR = "full_codebase_refactor"
        DEEP_CONTEXT_REASONING = "deep_context_reasoning"
      </change>

      <change location="After PREMIUM_TASKS frozenset">
        Add ULTRA_TASKS frozenset with the four new
        task types.
      </change>

      <change location="TASK_TIER_MAP (line 133-137)">
        Add ultra tasks to the mapping:
        **dict.fromkeys(ULTRA_TASKS, ModelTier.ULTRA),
      </change>

      <change location="get_tasks_for_tier (line 248-264)">
        Add ULTRA case returning list(ULTRA_TASKS).
      </change>

      <change location="get_all_tasks (line 267-278)">
        Add "ultra": list(ULTRA_TASKS) to return dict.
      </change>

      <change location="TASK_INFO (line 300-359)">
        Add TaskInfo entries for the four new tasks.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      get_tier_for_task("whole_repo_review")
      == ModelTier.ULTRA
    </check>
    <check>
      "ultra" in get_all_tasks()
    </check>
    <check>
      len(ULTRA_TASKS) == 4
    </check>
  </validation>
</task>
```

---

```xml
<task id="3" name="routing-config-fallback">
  <objective>
    Add ultra tier to RoutingConfig dataclass and
    TierFallbackHelper progression chain.
  </objective>

  <context>
    <existing-code
      path="src/attune/config/sections/routing.py">
      RoutingConfig has default_tier Literal with
      cheap/capable/premium, model fields for each tier,
      max_tokens fields. to_dict() and from_dict()
      serialize all fields.
    </existing-code>
    <existing-code
      path="src/attune/models/tier_helper.py">
      TIER_PROGRESSION maps cheap->capable,
      capable->premium, premium->None.
      should_fallback() blocks fallback from premium.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/config/sections/routing.py">
      <change location="RoutingConfig dataclass">
        - Add "ultra" to default_tier Literal type
        - Add ultra_model: str = "claude-opus-4-6"
        - Add max_tokens_ultra: int = 128_000
        - Add ultra_enabled: bool = False
          (opt-in experimental)
        - Add ultra_beta_header: str =
          "context-1m-2025-08-07"
        - Update to_dict() and from_dict()
      </change>
    </file>

    <file path="src/attune/models/tier_helper.py">
      <change location="TIER_PROGRESSION dict">
        BEFORE:
        "premium": None

        AFTER:
        "premium": "ultra"
        "ultra": None
      </change>

      <change location="should_fallback method">
        BEFORE: blocks fallback from "premium"
        AFTER: blocks fallback from "ultra"
        (premium can now fall UP to ultra)
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      TierFallbackHelper.get_next_tier("premium")
      == "ultra"
    </check>
    <check>
      TierFallbackHelper.get_next_tier("ultra") is None
    </check>
    <check>
      TierFallbackHelper.should_fallback(
          TimeoutError(), "ultra") is False
    </check>
    <check>
      TierFallbackHelper.should_fallback(
          TimeoutError(), "premium") is True
    </check>
  </validation>
</task>
```

---

```xml
<task id="4" name="model-router-ultra">
  <objective>
    Update ModelRouter to handle ultra tier in routing,
    cost comparison, and savings calculation. Update
    workflow routing strategies to support ultra.
  </objective>

  <context>
    <existing-code
      path="src/attune/routing/model_router.py">
      Local ModelTier enum duplicates registry enum.
      ModelRouter.MODELS loaded from MODEL_REGISTRY.
      route() returns model_id.
      compare_costs() iterates cheap/capable/premium.
      get_all_tasks() returns 3 tiers.
    </existing-code>
    <existing-code
      path="src/attune/workflows/routing.py">
      CostOptimizedRouting, PerformanceOptimizedRouting,
      BalancedRouting. RoutingContext has input_size.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/routing/model_router.py">
      <change location="ModelTier enum (line 35-45)">
        Add ULTRA = "ultra"
      </change>

      <change location="compare_costs (line 271)">
        Add "ultra" to the tier iteration list.
      </change>

      <change location="get_all_tasks (line 319-325)">
        Import ULTRA_TASKS and add to return dict.
      </change>
    </file>

    <file path="src/attune/workflows/routing.py">
      <change location="RoutingContext dataclass">
        Existing input_size field is sufficient for
        context-based routing. No structural change
        needed.
      </change>

      <change location="CostOptimizedRouting.route()">
        Add ultra routing: if input_size > 200_000,
        route to ULTRA (context requires it).
      </change>

      <change location="PerformanceOptimizedRouting">
        Add ultra for complex + large context tasks.
      </change>

      <change location="BalancedRouting.route()">
        Add ultra routing when input_size > 200_000
        and budget allows.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      ModelRouter().route("whole_repo_review")
      == "claude-opus-4-6"
    </check>
    <check>
      "ultra" in ModelRouter().compare_costs(
          "whole_repo_review", 500000, 10000)
    </check>
    <check>
      CostOptimizedRouting routes to ULTRA when
      input_size > 200_000
    </check>
  </validation>
</task>
```

---

```xml
<task id="5" name="beta-header-injection">
  <objective>
    Modify AnthropicProvider to inject beta headers from
    ModelInfo when making API calls for the ultra tier.
  </objective>

  <context>
    <existing-code
      path="src/attune/llm/providers/anthropic.py">
      AnthropicProvider.generate() builds api_kwargs
      dict and calls client.messages.create(**api_kwargs).
      No extra_headers currently set.
      generate_stream() has similar pattern.
    </existing-code>
    <existing-code
      path="src/attune/llm/providers/base.py">
      BaseLLMProvider.generate() signature accepts
      **kwargs for extensibility.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/llm/providers/anthropic.py">
      <change location="generate() method">
        Accept optional beta_headers parameter via
        **kwargs. If present, add extra_headers to
        api_kwargs before calling messages.create():

        beta_headers = kwargs.get("beta_headers")
        if beta_headers:
            api_kwargs["extra_headers"] = beta_headers
      </change>

      <change location="generate_stream() method">
        Same pattern: extract beta_headers from kwargs
        and pass as extra_headers.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>
      AnthropicProvider.generate() passes
      extra_headers when beta_headers kwarg is set
    </check>
    <check>
      AnthropicProvider.generate() works without
      beta_headers (backward compatible)
    </check>
  </validation>

  <risks>
    <risk severity="medium">
      Multiple call sites exist (release agent,
      SDK agent, meta-workflows). This task only
      covers the primary AnthropicProvider. Other
      call sites can be updated incrementally.
    </risk>
    <risk severity="low">
      Beta header format may change. The header
      value is stored in RoutingConfig for easy
      updates.
    </risk>
  </risks>
</task>
```

---

```xml
<task id="6" name="tests-ultra-tier">
  <objective>
    Add unit tests for ultra tier across all modified
    modules: registry, tasks, routing, config, fallback,
    and header injection.
  </objective>

  <context>
    <existing-code path="tests/">
      Existing test structure with unit/ directory.
      Tests use pytest with standard patterns.
    </existing-code>
  </context>

  <files-to-create>
    <file path="tests/unit/test_ultra_tier.py">
      Test cases:
      1. ModelTier.ULTRA exists with value "ultra"
      2. MODEL_REGISTRY has ultra entry with correct
         pricing and beta_headers
      3. Ultra tasks route to ModelTier.ULTRA
      4. get_all_tasks() includes "ultra" key
      5. TierFallbackHelper progresses premium->ultra
      6. TierFallbackHelper blocks fallback from ultra
      7. RoutingConfig includes ultra fields
      8. ModelRouter routes ultra tasks correctly
      9. ModelRouter.compare_costs includes ultra
      10. CostOptimizedRouting escalates to ultra for
          large input_size
      11. Beta headers are present on ultra ModelInfo
      12. Ultra tier is marked experimental
    </file>
  </files-to-create>

  <validation>
    <check>All tests pass: pytest tests/unit/test_ultra_tier.py</check>
    <check>No regressions: pytest tests/unit/</check>
  </validation>
</task>
```

---

## Next Steps

- [ ] Implement all 6 tasks
- [ ] Run full test suite
- [ ] Update CHANGELOG.md (when ready for release)
- [ ] Monitor Anthropic beta status for GA transition

## Open Questions

- Should ultra tier be available in batch API?
  (Beta header + batch may have quirks)
- Should we add a CLI command to check ultra tier
  eligibility (tier 4 access)?
- When the beta goes GA, how to migrate smoothly?
  (Remove beta_headers field, adjust pricing)
