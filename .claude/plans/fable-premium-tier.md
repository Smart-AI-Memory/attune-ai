# Execution plan: fable-premium-tier

Generated from [docs/specs/fable-premium-tier/tasks.md](../../docs/specs/fable-premium-tier/tasks.md).
Each task block is self-contained — a fresh Claude Code session can pick
up any task without prior conversation context. Run tasks in order;
dependencies are noted explicitly.

```xml
<plan>
  <feature>fable-premium-tier</feature>
  <spec>docs/specs/fable-premium-tier/tasks.md</spec>

  <task id="1">
    <title>Add src/attune/model_tiers.py (mirrored tier contract) + unit tests</title>
    <context>
      Read docs/specs/fable-premium-tier/design.md §1. The canonical
      module is attune_rag/model_tiers.py; attune_author/model_tiers.py
      is a byte-for-byte mirror of the resolution logic. Copy the
      mirror pattern: exports resolve_model(tier), fable_extras(model),
      ModelRefusalError, constants _DEFAULTS/_ENV/_KNOWN_MODELS/
      _FABLE_BETAS/_FABLE_FALLBACKS. Stdlib-only (logging + os) — no
      anthropic import, no I/O at import time. resolve_model reads
      os.getenv per call (not import time). Reference source if
      available locally: ~/attune/attune-author/src/attune_author/model_tiers.py.
    </context>
    <scope>
      New file src/attune/model_tiers.py. New test file
      tests/unit/test_model_tiers.py covering: env-override precedence,
      blank-override fallthrough, unknown-override warning, unknown
      tier ValueError, fable_extras gating (empty for non-fable, betas +
      extra_body shape for claude-fable*), fresh-dict semantics.
      Do NOT wire any call sites yet.
    </scope>
    <acceptance>
      pytest tests/unit/test_model_tiers.py passes; ruff clean;
      python -c "import attune.model_tiers" makes no network calls and
      succeeds without anthropic installed being exercised.
    </acceptance>
  </task>

  <task id="2">
    <title>Drift test vs attune_rag.model_tiers + CI install step</title>
    <context>
      Design §1 (drift alarm). attune-ai does not depend on attune-rag;
      the drift test must skip cleanly when attune_rag is absent and run
      in CI where a dedicated step installs attune-rag>=0.8 from PyPI.
      Port the shape of attune-author/tests/test_model_tiers_drift.py
      (asserts _DEFAULTS/_ENV/_KNOWN_MODELS/_FABLE_* equality and
      resolution parity).
    </context>
    <scope>
      New tests/unit/test_model_tiers_drift.py with
      pytest.importorskip("attune_rag"). Edit the tests workflow
      (.github/workflows/*.yml test job) to add a step:
      pip install "attune-rag>=0.8" before pytest. Do not add attune-rag
      to pyproject dependencies.
    </scope>
    <acceptance>
      Locally without attune-rag: test reports skipped. With
      "pip install attune-rag>=0.8" in a scratch venv: test passes.
      CI workflow YAML parses (yamllint or python -c yaml.safe_load).
    </acceptance>
  </task>

  <task id="3">
    <title>Add src/attune/llm/fable_call.py helper + tests</title>
    <context>
      Design §4c. Depends on task 1. Sync + async functions
      create_with_fable(client, *, model, **kwargs) /
      acreate_with_fable(...): if fable_extras(model) is non-empty,
      call client.beta.messages.create(..., betas=extras["betas"],
      extra_body=extras["extra_body"]) — fallbacks MUST ride in
      extra_body, the SDK (≤0.96) rejects a typed fallbacks kwarg.
      Otherwise client.messages.create(...). After the call: if
      response.stop_reason == "refusal", raise ModelRefusalError with
      category/explanation read from stop_details (guard for None).
      Wrap non-retryable 400s on fable calls with the retention hint
      string used in attune_author/src/attune_author/doc_gen/_anthropic.py.
    </context>
    <scope>
      New file src/attune/llm/fable_call.py. New test file
      tests/unit/llm/test_fable_call.py using MagicMock clients (no
      network): namespace switch, refusal raise, retention-hint 400
      wrapping, passthrough for non-fable models.
    </scope>
    <acceptance>
      pytest tests/unit/llm/test_fable_call.py passes; ruff clean.
    </acceptance>
  </task>

  <task id="4">
    <title>Wire the central async provider for fable</title>
    <context>
      Design §4a. Depends on tasks 1+3. In
      src/attune/llm/providers/anthropic.py: generate() (call site
      ~line 212) adopts the fable path (use acreate_with_fable or
      inline the same logic). Extend _normalize_api_kwargs_for_model:
      today _OPUS_NO_SAMPLING_RE (lines ~18-21) strips sampling for
      opus-4.7+; add a claude-fable* branch that strips temperature/
      top_p/top_k AND any explicit thinking config, each with a logged
      warning (fable rejects explicit thinking; adaptive-by-default
      means omission is correct). Decision recorded in design: strip +
      warn, never raise.
    </context>
    <scope>
      src/attune/llm/providers/anthropic.py only, plus its test module
      (tests/unit/llm/providers/test_anthropic*.py — extend, don't
      rewrite). Patch AsyncAnthropic at the import boundary per
      testing-conventions.md.
    </scope>
    <acceptance>
      New tests: fable model → beta.messages.create called with betas +
      extra_body; refusal → ModelRefusalError; thinking/sampling params
      stripped with warning for fable, preserved for sonnet. Full
      provider test module passes.
    </acceptance>
  </task>

  <task id="5">
    <title>Batch Option A + bulk skill docs</title>
    <context>
      Design §4b; requirements decision table (Patrick chose Option A,
      2026-07-10). The Batch API rejects the fallbacks param, so batch
      premium work never targets fable. Mirror
      attune-author/src/attune_author/maintenance_batch.py
      _batch_polish_model() (lines ~334-351): resolve premium; if
      fable_extras(model) is truthy return "claude-opus-4-8"; else the
      resolved model (honors env/config pins).
    </context>
    <scope>
      src/attune/llm/providers/anthropic_batch.py: add
      _batch_premium_model() and apply it where premium-tier requests
      are built (normalization site ~lines 118-123). Bulk skill
      documentation (plugin/skills/bulk*/SKILL.md): add a short
      "Model policy" note — interactive premium = fable-5 with
      server-side opus fallback; batch premium = opus-4-8.
    </scope>
    <acceptance>
      Unit test: with default env, _batch_premium_model() ==
      "claude-opus-4-8"; with ATTUNE_MODEL_PREMIUM=claude-sonnet-5,
      returns claude-sonnet-5. Batch request built for a premium job
      carries no fable model and no betas/fallbacks. SKILL.md note
      present.
    </acceptance>
  </task>

  <task id="6">
    <title>Route all premium literals through resolve_model("premium")</title>
    <context>
      Design §3 table — 12 surfaces with file:line. RoutingConfig
      (config/sections/routing.py:37,71) moves to
      field(default_factory=lambda: resolve_model("premium")) and the
      same expression as the from_dict fallback. template_defs_basic.py
      (:30,:86) and template_defs_web.py (:29,:203) are YAML-in-string
      literals: flip "claude-opus-4-8" → "claude-fable-5".
      workflows/config.py embedded YAML (:564,:577) likewise literal.
      All other rows call resolve_model("premium").
    </context>
    <scope>
      Exactly the files in the design §3 table. Also update the 4
      breaking assertions: tests/agent_factory/test_agent_factory.py:393
      ("opus" in premium → fable), tests/unit/config/
      test_config_validation.py:283,290, tests/unit/agents/release/
      test_release_models.py:392, tests/unit/workflows/escalation/
      test_chain.py:75. Do NOT touch models/registry.py,
      cost_tracker.py, or telemetry (task 7 handles registry/pricing).
    </scope>
    <acceptance>
      Full test suite passes. grep -rn "claude-opus-4-8" src/ shows
      only: registry/pricing/telemetry data sites, the batch downgrade
      target, and _FABLE_FALLBACKS. ATTUNE_MODEL_PREMIUM=claude-sonnet-5
      env flips every routed surface (spot-check via a unit test on
      2-3 surfaces).
    </acceptance>
  </task>

  <task id="7">
    <title>Registry + pricing entries for claude-fable-5</title>
    <context>
      Design §3 "Not changed" note and §Data model. Fable-5: $10/$50
      per MTok, 1M context window, 128K max output, same tokenizer as
      opus-4-8. BASELINE_MODEL in cost_tracker.py stays opus-4-8.
    </context>
    <scope>
      models/registry.py (new entry), llm/providers/anthropic.py
      pricing/capability table (~line 406), cost_tracker.py pricing
      map. Extend existing registry/pricing tests with fable rows.
    </scope>
    <acceptance>
      Registry lookup for claude-fable-5 returns the entry; cost
      estimation for a fable call uses $10/$50; existing opus tests
      unchanged and green.
    </acceptance>
  </task>

  <task id="8">
    <title>Scattered premium call sites adopt fable_call + refusal telemetry</title>
    <context>
      Design §4c and §5. Depends on tasks 3+6. After task 6 these
      sites can receive a fable model: curator/core.py (client :342,
      call :249), workflows/escalation/chain.py, agents/release/
      base_agent.py (client :114, call :181),
      meta_workflows/llm_execution.py (:253,:256). Swap direct
      messages.create calls for create_with_fable/acreate_with_fable.
      Telemetry: where workflows catch per-item errors, record a
      "fable_refusal" event (existing telemetry plumbing under
      models/telemetry/) carrying stop_details.category; the item
      errors, never silently skips.
    </context>
    <scope>
      The four call-site files + the workflow error-handling location
      that owns per-item error recording. Tests per site (mocked
      client): fable model routes through the beta namespace; refusal
      produces the telemetry event and a per-item error.
    </scope>
    <acceptance>
      New unit tests pass; full suite green; no direct
      client.messages.create remains in the four files for
      premium-capable paths (grep check).
    </acceptance>
  </task>

  <task id="9">
    <title>Docs, changelog, version bump, release</title>
    <context>
      Design §Cross-layer. Depends on all prior tasks. Version bump
      must touch pyproject.toml + plugin.json + uv.lock together
      (pre-commit fails on lockfile drift). CHANGELOG entry must call
      out the premium price change ($5/$25 → $10/$50 per MTok) and the
      no-deploy rollback (premium_model config pin /
      ATTUNE_MODEL_PREMIUM env).
    </context>
    <scope>
      plugin/help/generated/ tier docs regeneration (repo's standard
      regen tooling), CHANGELOG.md, pyproject.toml, plugin.json,
      uv.lock. Release itself follows the standard publish flow
      (GitHub Release → OIDC → PyPI env approval gate) — stop at the
      approval gate and provide the Actions run URL.
    </scope>
    <acceptance>
      Pre-commit green (lockfile consistent); CHANGELOG entry present;
      release PR merged; publish run paused at the approval gate with
      URL delivered.
    </acceptance>
  </task>
</plan>
```
