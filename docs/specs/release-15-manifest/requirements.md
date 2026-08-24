# 15.0.0 Major-Release Manifest

**Status:** approved (2026-08-24) — merged as the major's scope
document (#2262); D2 RATIFIED same day (Option B — `empathy_level`
dies with the framework), so no gating decision remains open.
**Slug:** `release-15-manifest`
**Provenance:** several pre-authorized breaking changes were
assembling toward the next major with no single document scoping
it — the exceptions-removal hold (chair, 2026-08-22), issue #2238's
breaking half, and the #2243 migration question. This manifest is a
scope document, not implementation.

## Timing constraint (chair, recorded verbatim)

> the major must NOT ship before mid-to-late September 2026.
> attune-ai's first external user begins onboarding 2026-09-01 and
> a stable 14.x during his first weeks is worth more than the
> architecture.

## Passengers

### 1. `attune.exceptions` removal (first passenger — pre-authorized)

Done on branch `claude/eager-mendeleev-3352e2` (92a3714b7, `feat!:
remove the legacy attune.exceptions hierarchy`); chair
PRE-AUTHORIZED into the next major 2026-08-22 (D1). Branch state
verified 2026-08-24: exists locally, 1 commit ahead of the
merge-base, and `git merge-tree` against current `origin/main`
shows two content conflicts — `CHANGELOG.md` and
`src/attune/__init__.py` — both mechanical (version-churn overlap),
not structural. Rebase at boarding time.

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

## Deprecation story (14.x pre-work, so 15.0.0 removes rather than surprises)

Land in 14.x, each with a `DeprecationWarning`:

1. `AttuneMCPServer` rename with `EmpathyMCPServer` alias.
2. Dual-read entry-point discovery: `attune.workflows` alongside
   `empathy.workflows`; keep `attune_framework.plugins` legacy
   read; delete the never-read `empathy_framework.plugins`
   declaration (removable in 14.x — nothing reads it).
3. The replacement plugin `BaseWorkflow` contract published
   alongside the old one (old contract warns on instantiation) —
   per D2, level-free signature; `attune_get_level`/
   `attune_set_level` also warn in 14.x ahead of their 15.0.0
   deletion.
4. `attune.exceptions` needs no 14.x shim — the removal branch is
   the pre-authorized cutover itself.

## Sequencing

1. 14.x: #2253 ✅ merged → #2239 layering → deprecation-story items
   1–3.
2. D2 ✅ ruled 2026-08-24 (Option B) — #2238's breaking half is
   unblocked.
3. 15.0.0 (not before mid-to-late September 2026): board passenger
   1 (rebase), passenger 2 including the D2 level removal.
