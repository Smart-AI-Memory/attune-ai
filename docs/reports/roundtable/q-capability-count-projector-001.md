# Capability Count Projector

**Roundtable thread:** `q-capability-count-projector-001`
**Chair ruling:** Promote board items 10, 11, and 12
**Artifact tier:** XML task
**Status:** Approved design; implementation not yet authorized

## Goal

Replace manual skill and MCP-tool count maintenance with a narrow,
deterministic projector while retaining independently derived drift
gates.

## Approved scope

Create `scripts/project_capabilities.py` to derive exactly three
values from the checked-out revision:

1. `skill_count` — publishable skills under
   `plugin/skills/*/SKILL.md`.
2. `mcp_registered_tool_count` — unique names in
   `EmpathyMCPServer().tools`, including bundled plugin tools.
3. `mcp_core_schema_tool_count` — unique names returned by the
   canonical `attune.mcp.tool_schemas.get_*_tools()` getters.

The projector must not use network data, cached counts, caller
overrides, remembered constants, or anticipated future capabilities.
Empty, duplicate, malformed, unavailable, or environment-dependent
discovery fails closed.

## Ownership model

Maintain an explicit target manifest. Every entry declares:

- the semantic value it publishes;
- an exact locator;
- its renderer;
- expected match cardinality;
- post-render validation.

Format rules:

- Markdown owns complete, uniquely marked claim fragments rather than
  isolated numbers.
- `website/lib/features.ts` updates exact named numeric fields inside
  the existing `CAPABILITIES` object. It does not consume a generated
  JSON sidecar.
- `.claude-plugin/marketplace.json` is parsed as JSON. Only its exact
  allowlisted description field is rendered; JSON receives no comment
  markers.
- Generated downstream documentation is never edited directly. The
  projector targets its owning source.

Explicit exclusions:

- `.claude/CLAUDE.md` and `AGENTS.md`;
- versions, workflows, and other marketing metrics;
- changelogs and historical release material;
- repository-wide regex or numeric replacement.

## CLI contract

```text
python scripts/project_capabilities.py
python scripts/project_capabilities.py --check
python scripts/project_capabilities.py --write
```

- Default and `--check` are identical and read-only.
- Drift exits nonzero with the semantic value, target, expected
  rendering, and observed rendering.
- `--write` computes and validates the complete edit plan before any
  file changes, writes deterministically, and then reruns the check.
- A repeated `--write` is byte-idempotent.
- Unknown or incompatible arguments fail closed.

## Rollout

1. Keep the immediate PR #1605 and PR #1607 count corrections in
   their owning feature PRs.
2. Inventory and freeze the exact current skill/tool claim allowlist.
3. Add the projector, target ownership, and tests against the
   corrected baseline.
4. Add `python scripts/project_capabilities.py --check` to an existing
   import-capable Linux PR/push CI job.
5. Retain the existing independently implemented claim-drift and
   website-accuracy gates.
6. Document that capability-changing PRs run `--write` in the same
   change.

Do not add a pre-commit projector or marker-only approximation. The
authoritative MCP derivation requires an importable project
environment, and a weaker local definition would add maintenance
without proving the boundary.

## Required verification

- Unit tests derive all three values independently.
- A regression fixture keeps registered-tool and core-schema totals
  different and proves they cannot be interchanged.
- Every governed target detects drift and is repaired by `--write`.
- `--check` never writes.
- A second `--write` produces no changes.
- Missing, duplicate, renamed, malformed, ambiguous, or wrong-type
  locators fail before any write.
- One invalid target prevents every planned write.
- Marketplace JSON remains valid and changes only its owned field.
- TypeScript changes only owned `CAPABILITIES` keys.
- Unrelated prose, formatting, newline style, and files are preserved.
- Subprocess tests verify CLI exit codes and diagnostics.
- Existing independent gates do not import projector manifests,
  locators, renderers, or derivation helpers.
- The existing 29 focused Python drift tests remain green.
- The Python website capability-accuracy gate remains green.
- CI exercises server construction in a controlled keyless
  environment; network, credentials, mutable external state, or
  nondeterministic registration are hard failures.

## Principal risks

1. **Semantic count confusion:** a total registered-tool count could
   be projected into a surface describing core tools. Distinct value
   names, explicit per-target mappings, and deliberately unequal test
   fixtures are mandatory.
2. **Environment-dependent registration:** constructing
   `EmpathyMCPServer` could acquire optional-dependency or ambient-state
   behavior. The projector must fail rather than publish a count from
   an unstable environment.
3. **Correlated false-green results:** sharing projector derivation
   with drift tests could validate the same mistake twice. Small,
   intentional duplication preserves independence.

## Done when

The XML task is implemented only after separate authorization, all
required verification receipts are green, the exact projector check
runs in import-capable CI, and the independent drift gates still catch
deliberately corrupted claims.
