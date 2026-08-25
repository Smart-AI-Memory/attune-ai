# 15.0.0 Major-Release Manifest

**Status:** approved (2026-08-24) — merged as the major's scope
document (#2262); D2 RATIFIED same day (Option B — `empathy_level`
dies with the framework), so no gating decision remains open.
**Amended 2026-08-25:** D5 inverts the timing (ship BEFORE
2026-09-01 — the onboarding cohort is a class that starts on
15.0.0); D6 records passenger 1 as already shipped in 14.0.0.
**Slug:** `release-15-manifest`
**Provenance:** several pre-authorized breaking changes were
assembling toward the next major with no single document scoping
it — the exceptions-removal hold (chair, 2026-08-22), issue #2238's
breaking half, and the #2243 migration question. This manifest is a
scope document, not implementation.

## Timing constraint (D5 — supersedes the original D4 text)

**Ship BEFORE 2026-09-01.** The onboarding cohort is a class that
starts working on attune-ai 2026-09-01, and the chair ruled
(2026-08-25) that the class starts on 15.0.0 — the major ships
before they arrive rather than breaking mid-course. The original
D4 constraint (verbatim in [decisions.md](decisions.md)) read the
onboarding as a lone user best served by weeks of stable 14.x; D5
inverts it.

## Passengers

### 1. `attune.exceptions` removal — ✅ ALREADY SHIPPED (D6)

Merged as PR #2177 (`093cd7acd`) and shipped in 14.0.0;
`src/attune/exceptions.py` is absent from `origin/main` (verified
2026-08-25). The D1 pre-authorization was discharged by that
merge. Nothing boards for this item; the parked branch
`claude/eager-mendeleev-3352e2` is superseded.

### 2. Empathy-framework excision remainder — breaking half (#2238)

The 9.0.0 excision left live surfaces targeting the retired
contract (all verified against the 2026-08-24 tree):

- **Public plugin `BaseWorkflow` replacement**
  ([base.py:45](../../../src/attune/plugins/base.py)) — takes
  `empathy_level: int` in `__init__` and requires an `analyze()`
  abstract the engine cannot run. Replacing the contract is
  breaking for third-party plugins; per D2 (Option B) the
  replacement is level-free.
- **`EmpathyMCPServer` → `AttuneMCPServer` alias removal** — the
  rename-with-alias itself lands in 14.x (deprecation story
  below); 15.0.0 removes the alias. As of 2026-08-24 the rename
  has not landed ([server.py:89](../../../src/attune/mcp/server.py)
  is still `EmpathyMCPServer`, no alias).
- **Entry-point namespace standardization on `attune.*`** — the
  current state is a three-way split, verified: workflow discovery
  reads ONLY `empathy.workflows`
  ([workflows/\_\_init\_\_.py:469](../../../src/attune/workflows/__init__.py));
  plugin discovery reads `attune.plugins` plus legacy
  `attune_framework.plugins`
  ([registry.py:17](../../../src/attune/plugins/registry.py));
  and pyproject additionally declares an `empathy_framework.plugins`
  group no discovery path reads, while its own `attune.workflows`
  declarations are not consumed by `discover_workflows()`. 15.0.0
  standardizes discovery on `attune.*` and drops the empathy-named
  groups; 14.x dual-reads with deprecation warnings first.

### 3. `empathy_level` dies with the framework (D2 — RATIFIED chair 2026-08-24, Option B)

The 1–5 level concept is plumbed through agent_factory, config,
llm state, plugin discovery, and the live MCP tools
`attune_get_level`/`attune_set_level`. The chair ruled Option B:
15.0.0 removes the level plumbing end-to-end, the replacement
plugin `BaseWorkflow` carries no level parameter, and the MCP
level tools are deleted (14.x `DeprecationWarning` first). Full
ruling and consequences in [decisions.md D2](decisions.md); this
unblocks #2238's breaking half.

## Not a passenger

- **anthropic SDK 1.x migration (#2243)** — decided and recorded
  in D3: it landed in 14.x, deliberately, and does not ride the
  major. The `<1.0.0` ceiling premise is stale: 14.1.0 already
  ships `anthropic>=0.40.0,<2.0.0` (#2254, 2026-08-24), with core
  1.x-compatibility verified live on both a 0.125 lock env and a
  scratch 1.0.0 env. Remainder (dev-lockfile adoption of 1.x) is
  blocked upstream on langchain-anthropic's `<1.0.0` pin and
  carries a live-fire receipt requirement at adoption time —
  neither is major-scoped.
- **#2239 (models↔workflows cycle → neutral lower layer)** — its
  layering work is non-breaking and belongs in 14.x, queued behind
  the adapter split (PR #2253, MERGED 2026-08-24). Only if a
  public import path must move does a slice of it board the major.

## Deprecation story — MOOT per D5 (2026-08-25)

The 14.x warning window protected existing external consumers;
telemetry signal is ~0 and the class starts fresh on 15.0.0, so
the window is dropped. State at ruling time: items 1 and 2
(rename+alias, dual-read discovery) and the level-tool warnings
had already landed in 14.x and simply ride until their 15.0.0
removal; item 3's old-contract instantiation warning was never
built and is dropped rather than built.

## Sequencing (per D5)

1. Record D5/D6 (this amendment).
2. #2238's breaking half, all in the 15.0.0 window: the D2
   `empathy_level` end-to-end removal (incl.
   `attune_get_level`/`attune_set_level` deletion and the
   level-free plugin `BaseWorkflow` contract), the
   `EmpathyMCPServer` alias removal, and entry-point
   standardization on `attune.*` (drop the `empathy.workflows`
   read and the legacy plugin groups).
3. Release prep + release-audit sitting + tag/publish, complete
   BEFORE 2026-09-01. #2239 layering does not board unless a
   public import path must move.
