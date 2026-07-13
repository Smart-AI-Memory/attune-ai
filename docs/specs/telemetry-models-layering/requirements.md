# Telemetry / Models Layering + Pricing Single-Source — requirements

**Status:** parked (2026-07-13) — no phase shipped; #1167/#1168 are the origin PRs that deferred this scope here, not implementers; remaining: Phases 1–4 (pricing single-source, layering, SRP splits, typed schemas) · **Owner:** Patrick + agent

Consolidates the **architectural** findings deferred from two code-review
fix PRs — #1167 (`usage_tracker`) and #1168 (`auth_strategy`, `registry`,
`usage_ping`, `feedback`). Those PRs landed the low-risk correctness /
security / perf fixes; this spec owns the larger refactors that break
callers and need design + careful test migration, so they were not
bundled.

Three themes recur across all five files: (1) **pricing duplicated across
≥4 sites**, (2) **upward / leaky coupling** (low-level modules importing
higher-level ones), and (3) **god-modules** mixing 5–7 responsibilities.
The work is phased so the highest-leverage, lowest-blast-radius change
(pricing single-source) lands first and the risky SRP splits land last
behind back-compat facades.

## Grounding (verified against code, not docstrings)

- **Pricing has ≥4 sources of truth.** `MODEL_REGISTRY` (`registry.py`)
  is the canonical table, but `TIER_PRICING` (`registry.py:464`) is a
  hand-maintained duplicate; `AuthStrategy.estimate_cost`
  (`auth_strategy.py:153`) hard-codes `$0.25/$3/$15` per-M rates; and
  `attune.llm.providers.anthropic` carries its own. This is the standing
  `project_model_pricing_three_sites` issue — now confirmed a 4th site
  (auth_strategy). The 1000× cost bug fixed in #1168 was a direct symptom
  of hand-maintained pricing constants.
- **`usage_tracker.py` is a 7-responsibility god-class** (write/buffer,
  rotation, summary-cache, read/query, savings/cache analytics, id
  hashing, process-lifecycle wiring) with a class-level singleton
  (`get_instance`) and two `atexit.register` calls fired from inside a
  library (`usage_tracker.py:120`).
- **`usage_ping.py` (≈580 LOC) imports UPWARD** into `attune.config`
  (`ConfigLoader`, `UnifiedConfig`) and `attune.__version__` — a
  circular-import landmine the moment `attune.config` imports telemetry.
- **`auth_strategy.py` mixes 4 concerns** (dataclass+enums, JSON
  persistence, interactive CLI wizard with 16 `print`/2 `input`, and an
  unrelated `count_lines_of_code` LOC utility), behind a disk-reading
  `get_auth_strategy()` singleton with no injection point. Two threshold
  sources of truth: `AuthStrategy.{small,medium}_module_threshold` vs the
  hard-coded `500/2000` in `get_module_size_category` (`:457`).
- **`feedback.py` mixes 5 concerns** (feedback persistence, usage-weight
  derivation, tag search, workflow-chain prediction, precursor warnings)
  and reaches through `_private` symbols from `templates.py` six times.
- **No typed record/schema** anywhere: `UsageRecord` is an implicit dict
  read via `entry.get()` at 7+ sites; `AuthStrategy.to_dict/from_dict`
  has no `schema_version` so old configs can't be migrated.
- **Latent concurrency bug (from #1167):** `UsageTracker.flush()` writes
  outside the lock and `json.dump` streams an entry over multiple
  `write()` calls, so concurrent flushes interleave and corrupt JSONL
  lines (silently dropped on read). Low severity (telemetry is
  best-effort) but real.

## Functional requirements

### Phase 1 — Pricing single-source (highest leverage, contained)

- **FR-1.1** `TIER_PRICING` is DERIVED from `MODEL_REGISTRY` at import
  time, not hand-maintained. A test asserts they cannot diverge.
- **FR-1.2** `AuthStrategy.estimate_cost` sources per-tier $/M rates from
  the registry (via a small pricing accessor), not local literals. The
  ~$0.197/module figure must be reproduced from registry data.
- **FR-1.3** Document the one remaining intentional copy (the
  `anthropic` provider table) or fold it in; a drift guard covers every
  site that claims a price.

### Phase 2 — Layering / dependency inversion

- **FR-2.1** `usage_ping` no longer imports `attune.config` or
  `attune.__version__`; the CLI/atexit registrar loads those and passes
  primitives (`install_id`, `telemetry_dir`, `enabled`, `version`) into a
  pure `run_sync`.
- **FR-2.2** `usage_tracker` no longer imports `attune.models.registry`
  or `attune.config.env_compat` at call time; pricing lookup + HMAC
  secret are injected (constructor params / a `PricingLookup` protocol).
- **FR-2.3** `feedback.get_usage_weights` takes an injected tracker
  rather than importing `UsageTracker` inline.

### Phase 3 — God-module SRP splits (behind back-compat facades)

- **FR-3.1** `usage_tracker` → `UsageStore` (write/rotate),
  `DailySummaryCache`, `UsageQuery`, `SavingsAnalytics`/`CacheAnalytics`,
  `UserIdHasher`, with a thin `UsageTracker` facade preserving today's
  public API.
- **FR-3.2** `auth_strategy` → `models/auth_strategy.py` (dataclass+enums
  only), `auth_strategy_repo.py` (I/O), `cli/auth_setup.py` (wizard with
  an `IOAdapter`), `utils/loc.py` (LOC counter). Single threshold source.
- **FR-3.3** `usage_ping` → a `telemetry/usage_ping/` package
  (policy / payload / transport / store / consent / runner).
- **FR-3.4** `registry` drops the dead `to_router_config` /
  `to_workflow_config` / `to_cost_tracker_pricing` adapters (production
  hand-rolls the dict) and resolves the singleton-vs-wrapper duplication
  to one surface.

### Phase 4 — Typed schemas, de-singleton, concurrency

- **FR-4.1** A typed `UsageRecord` (TypedDict or dataclass) with
  `to_dict/from_dict`; all readers route through it.
- **FR-4.2** `AuthStrategy` gains `schema_version` with a `from_dict`
  migration branch; `from_dict` validates enums/thresholds with safe
  fallbacks instead of raising.
- **FR-4.3** Replace the `UsageTracker` / `get_auth_strategy` singletons
  with dependency injection; hoist `atexit` wiring to an explicit
  `install_process_hooks()` called only by the CLI/app entry point.
- **FR-4.4** Fix the `flush()` concurrency bug: serialize each record to
  a string and write under the lock (or one `write()` per record), so
  concurrent flushes can't interleave.

## Non-functional requirements

- **NFR-1 Back-compat:** every public symbol callers use today
  (`UsageTracker(...)`, `.get_stats`, `get_auth_strategy`,
  `MODEL_REGISTRY`, `get_pricing_for_model`, the MCP `telemetry_stats`
  path at `mcp/server.py:584`, `help/feedback.py:149`) keeps working
  through each phase. Facades absorb the split.
- **NFR-2 Dogfood:** the telemetry round-trip (`track → flush → rebuild →
  get_stats`) is exercised by a non-mocked test after each phase, not
  just mocked unit tests.
- **NFR-3 No coverage regression** on the touched modules.

## Out of scope

- Changing telemetry storage format, retention policy, or the wire
  payload schema of `usage_ping`.
- The `attune.llm.providers.anthropic` provider internals beyond the
  pricing-table reconciliation in FR-1.3.
- Any behavior change to what is tracked / sent (privacy surface is
  unchanged).

## Acceptance criteria

- **AC-1** A single pricing source: `TIER_PRICING` and
  `AuthStrategy.estimate_cost` both derive from `MODEL_REGISTRY`; a drift
  test fails if any hard-coded price reappears.
- **AC-2** `audit_doc_imports` / an import-direction test confirms
  `attune.telemetry.*` and `attune.models.registry` import nothing from
  `attune.config` / consumer modules.
- **AC-3** Each split module is independently unit-tested; the facade
  tests prove the old public API is unchanged (same return shapes).
- **AC-4** `UsageRecord` typed; readers use it; `AuthStrategy` round-trips
  an old (no-`schema_version`) config without raising.
- **AC-5** A concurrency test writes from N threads through `flush()` and
  asserts zero dropped/corrupted records (currently fails — see
  #1167 follow-up).
- **AC-6** CI green on all required + Windows lanes; no coverage drop.

## Phasing rationale

Phase 1 is shippable alone and retires a long-standing memory item
(`project_model_pricing_three_sites`) with a drift guard — do it first.
Phases 2–4 escalate in blast radius; each is its own PR behind facades so
a regression is contained and revertible. Phase 3 (the SRP splits) is the
largest and should not start until Phases 1–2 have removed the coupling
that makes the splits hard.
