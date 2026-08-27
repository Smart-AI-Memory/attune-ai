# 16.0.0 Major-Release Manifest

**Status:** destructive half SHIPPED as 16.0.0 (2026-08-27 — PRs
#2331, #2333, #2334, release PR; passengers 1-3 and 5 executed, D6's
deprecations discharged). Remaining scope: passenger 4 (the
extension system, 16.x) pending the chair's D2 ruling — see the
`project_release16_d2_pending` state.
**Slug:** `release-16-manifest`
**Provenance:** 16.0.0-class breaking work began accumulating the
day 15.1.0 shipped — the dead-module deletion PR #2331, the D4/D6
deprecations from `models-workflows-layering`, and the root-level
deprecation shims — with no single document scoping the major. This
manifest is a scope document, not implementation. Its D1 (the
architecture ruling) was deliberated by the full round table
(3 seats, 2 rounds including a steelman round) and chair-ruled
2026-08-26; the full transcript is machine-local at
`~/.attune/reports/roundtable/q-core-plugins-vs-post-framework-001.md`.

## Architecture frame (D1 — chair-ruled 2026-08-26)

16.0.0 is the release where the architecture commits to
**harness-lite**: a core that runs with zero extensions, exactly two
hardened capability contracts (workflows, memory backends), and
Codex's extension system as the loading mechanism. See
[decisions.md](decisions.md) D1 for the full ruling, the design, and
the dissent register.

## Passengers

### 1. Dead framework-era root modules — ✅ SHIPPED (#2331)

Nine modules (~2,200 lines) deleted with caller-grep receipts:
`discovery`, `pattern_cache`, `cache_stats`, `cache_monitor`,
`vscode_bridge`, `template_engine`, `template_defs_basic`,
`template_defs_web`, `templates`. The discovery tips catalog moved
into its only consumer (`scripts/generate_tip_templates.py`).
Merging this PR is what commits the next release to being 16.0.0.

### 2. Root-level deprecation shims — ✅ SHIPPED (#2333)

The already-declared shims at package root, each announcing its
replacement today: `coordination` (shim since 6.8.0),
`redis_memory`, `redis_memory_storage`, `redis_memory_coordination`,
`redis_memory_patterns` (all "use attune_redis"), `persistence`
(facade), `state_manager` (deprecated at 9.0.0).

### 3. `models-workflows-layering` scheduled removals — ✅ SHIPPED (#2333)

- `config/agent_config.AgentWorkflowConfig` + `WorkflowMode` —
  deletion pre-ruled by that spec's D4, timing ruled by its D6; the
  PEP 562 deprecation shipped in 15.1.0 and
  `scripts/check_deprecation_markers.py` fails the build the moment
  16.0.0 opens.
- Hard renames whose alias phase ships in 15.x per D2/D5 of that
  spec (`config.sections.WorkflowsConfig`,
  `agent_factory.AgentGraphConfig`).

### 4. Harness-lite extension system (D1 — the constructive half)

The shared consensus core plus Codex's mechanism, as ruled in D1:

- Two dependency-light capability contracts (workflow, memory
  backend), frozen and documented semver-stable.
- One unified `attune.extensions` entry-point group with a frozen
  `Extension` manifest; `attune.memory_backends` supported through
  16.x as a compatibility adapter.
- Trust gating: installed code is NOT executed until
  `attune extension enable`; `list / inspect / enable / disable /
  doctor` CLI.
- Contract test kits (`attune.testing`) and a minimal example
  extension in-repo.
- Built-ins dogfood the public contracts (drift-guarded).
- Fail-open loading: a broken extension is a named diagnostic,
  never a crashed CLI; `import attune` can never fail because of an
  extension.
- Four receipts prove the loop (discovery does not import;
  enablement executes in-process; a broken extension cannot block
  startup; a standalone package works without attune while its
  adapter works with it).

### 5. Seam collapses — ✅ SHIPPED (#2334)

- `attune.plugins` and `attune.wizards` entry-point groups collapse
  to direct imports/registration (both have exactly one effective
  configuration: attune registering its own bundled code).
- The empty `attune.workflows` entry-point group is deleted, not
  populated; the unified `attune.extensions` manifest replaces it.

## Non-goals (D1's explicit out-of-scope list)

Remote installation, marketplaces, dependency solving, sandboxing
claims, hot reload, lifecycle hooks, capability negotiation.
Extraction of bundled components into separate PyPI packages remains
value-driven per the attune-redis precedent — the extension system
imposes no packaging split.

## Open questions

- Timing: no ship-by constraint ruled yet. The 15-manifest's D5
  ("before the 2026-09-01 onboarding") applied to 15.0.0 and is
  discharged; whether 16.0.0 rides the same urgency is unruled.
- Whether passenger 4 ships whole in 16.0.0 or contracts-first with
  the CLI following in a 16.x minor (additive either way once the
  contracts freeze).
