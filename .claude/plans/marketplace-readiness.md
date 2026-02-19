# Marketplace Readiness Plan

**Created:** 2026-02-19
**Updated:** 2026-02-19
**Source:** /brainstorm session

## Problem

Attune is a capable framework with strong bones — hubs,
Socratic discovery, workflows, batch API — but it hasn't
been through the discipline of making it ready for
another developer to install and trust. Files are
oversized, some workflows may overlap, and wiring between
features hasn't been fully verified. It needs to go from
"strong prototype" to "marketplace-ready product."

## Goals

- Audit and eliminate redundant workflows (must-have)
- Refactor all source files under 1000 lines, target 500
  (must-have, excludes test files)
- Verify every hub, route, and feature is wired and works
  end-to-end (must-have)
- Build a curated batch runner for non-interactive
  workflows — tests, docs, security audits (must-have)
- Package and publish as a Claude Code marketplace
  extension following Anthropic best practices (must-have)

## End State

A new developer installs Attune from the Claude Code
marketplace, types `/attune`, and every hub, workflow,
and batch operation works out of the box. The codebase is
clean (no file over 500 lines excluding tests), has zero
redundant workflows, and includes a batch runner for
maintenance tasks.

---

## Audit Results (completed 2026-02-19)

### File Size Audit

| Category | Count |
|----------|-------|
| Over 1000 lines | 5 |
| 500-1000 lines | 109 |
| 300-500 lines (watch) | 124 |
| Under 300 lines | 267 |
| **Total source files** | **505** |

**Top 5 largest files:**

| File | Lines |
|------|-------|
| `workflows/code_review.py` | 1575 |
| `agent_factory/crews/health_check.py` | 1262 |
| `agent_factory/crews/refactoring.py` | 1131 |
| `agent_factory/crews/code_review.py` | 1113 |
| `mcp/server.py` | 1022 |

**Deprecated files to delete (~3,900 lines):**

- `workflows/release_prep_crew.py` (966)
- `workflows/test_coverage_boost_crew.py` (852)
- `workflows/test_maintenance_crew.py` (842)
- `workflows/manage_documentation.py` (821)

### Redundancy Audit

**HIGH severity:**

- Dead hubs: `/learning`, `/context`, `/wizard`, `/agent`
  route to skills that don't exist
- Must remove routes or implement handlers

**MEDIUM severity:**

- `perf-workflow` routes to `/workflows` while
  `perf`/`perf-audit` route to `/dev` — inconsistent
- Auth commands route through `/workflows` skill (smell)

**LOW severity:**

- 5 SEO keywords for same endpoint (reduce to 2)
- 3 redundant release workflows (2 deprecated)
- 3 redundant doc workflows (1 deprecated)

### Marketplace Research

**Plugin format:** Directory with
`.claude-plugin/plugin.json` manifest.

**Key components:**

- `skills/*/SKILL.md` — primary extension (maps to hubs)
- `commands/*.md` — slash commands (already have these)
- `hooks/hooks.json` — event handlers
- `.mcp.json` — MCP server configs

**Publishing paths:**

1. Self-hosted marketplace (any GitHub repo, instant)
2. Official Anthropic directory (curated, submit at
   clau.de/plugin-directory-submission)

---

## Approach (revised after audits)

### Phase 0: Quick Wins (NOW)

```xml
<task id="0.1" name="delete-deprecated-files">
  <objective>
    Remove 4 deprecated workflow files (~3,900 lines).
    These are already replaced by newer implementations
    and handled by the migration system.
  </objective>
  <files-to-modify>
    <file path="src/attune/workflows/release_prep_crew.py">
      DELETE — replaced by agents.release module
    </file>
    <file path="src/attune/workflows/test_coverage_boost_crew.py">
      DELETE — migrated to test-gen-parallel
    </file>
    <file path="src/attune/workflows/test_maintenance_crew.py">
      DELETE — migrated to test-maintenance workflow
    </file>
    <file path="src/attune/workflows/manage_documentation.py">
      DELETE — migrated to doc-gen
    </file>
  </files-to-modify>
  <validation>
    <check>All tests still pass after deletion</check>
    <check>Migration system handles old workflow names
    </check>
  </validation>
</task>

<task id="0.2" name="fix-dead-routes">
  <objective>
    Remove keyword routes that map to non-existent
    skills, or implement the missing skill handlers.
  </objective>
  <files-to-modify>
    <file path="src/attune/cli_router.py">
      Remove or fix: learning, context, wizard, agent
      routes that have no handler
    </file>
  </files-to-modify>
  <validation>
    <check>Every keyword in _keyword_to_skill maps to a
      reachable skill or command</check>
  </validation>
</task>

<task id="0.3" name="fix-routing-inconsistencies">
  <objective>
    Fix perf-workflow routing inconsistency and reduce
    redundant SEO keyword mappings.
  </objective>
  <files-to-modify>
    <file path="src/attune/cli_router.py">
      BEFORE: "perf-workflow": ("workflows", "run perf-audit")
      AFTER: "perf-workflow": ("dev", "perf-audit")
      Remove: docs-seo, meta-tags, check-seo, optimize-seo
    </file>
  </files-to-modify>
  <validation>
    <check>All perf keywords route to same destination
    </check>
    <check>SEO has 2 canonical keywords max</check>
  </validation>
</task>
```

### Phase 1: Refactor and Right-Size

```xml
<task id="1.1" name="refactor-large-files">
  <objective>
    Split files over 500 lines into logical modules
    while preserving all public APIs and imports.
    Start with the 5 files over 1000 lines.
  </objective>
  <risks>
    <risk severity="high">Breaking imports — must update
      all callers and re-export from __init__.py</risk>
    <risk severity="medium">Test breakage — run full
      suite after each file split</risk>
  </risks>
  <validation>
    <check>All existing tests pass after each split</check>
    <check>No source file exceeds 500 lines</check>
    <check>Public API unchanged (imports still work)</check>
  </validation>
</task>
```

### Phase 2: Wiring Verification

```xml
<task id="2.1" name="end-to-end-wiring-check">
  <objective>
    Verify every hub, slash command, keyword route, and
    natural language pattern resolves to a working
    workflow or command.
  </objective>
  <validation>
    <check>Every entry in _keyword_to_skill maps to a
      real, reachable skill</check>
    <check>Every intent pattern in INTENT_PATTERNS routes
      to a working workflow</check>
    <check>Every hub in CLAUDE.md has a corresponding
      command file or CLI handler</check>
  </validation>
</task>

<task id="2.2" name="test-consolidation">
  <objective>
    Organize tests into a logical structure that supports
    batch execution. Group by feature area so test
    subsets can be run independently.
  </objective>
  <validation>
    <check>pytest tests/unit/ passes</check>
    <check>Test directories mirror source structure</check>
  </validation>
</task>
```

### Phase 3: Batch Operations

```xml
<task id="3.1" name="curated-batch-runner">
  <objective>
    Build a batch workflow runner that executes
    pre-qualified non-interactive workflows: test
    generation, documentation, security audits. Exclude
    interactive workflows (debug, brainstorm, refactor).
  </objective>
  <validation>
    <check>Batch runner lists only non-interactive
      workflows</check>
    <check>Each batch workflow completes without user
      input</check>
    <check>Results are collected and summarized</check>
  </validation>
</task>
```

### Phase 4: Marketplace Packaging

```xml
<task id="4.1" name="create-plugin-structure">
  <objective>
    Convert Attune to Claude Code plugin format with
    .claude-plugin/plugin.json manifest, skills in
    skills/*/SKILL.md, and proper hook configuration.
  </objective>
  <validation>
    <check>claude plugin validate . passes</check>
    <check>claude --plugin-dir . loads successfully</check>
    <check>All hubs accessible as namespaced skills</check>
  </validation>
</task>

<task id="4.2" name="publish-to-marketplace">
  <objective>
    Publish to self-hosted marketplace first, then
    submit to official Anthropic directory.
  </objective>
  <validation>
    <check>Plugin installs from marketplace</check>
    <check>/attune discovery flow works for new user
    </check>
    <check>All batch operations functional</check>
  </validation>
</task>
```

## Next Steps

- [x] Run file size audit (task 1.2)
- [x] Run redundancy audit (task 1.1)
- [x] Research marketplace requirements (task 5.1)
- [ ] Delete deprecated files (task 0.1)
- [ ] Fix dead routes (task 0.2)
- [ ] Fix routing inconsistencies (task 0.3)
- [ ] Reassess refactoring scope after quick wins
- [ ] Begin refactoring largest files (task 1.1)

## Answered Questions

- **Marketplace format:** `.claude-plugin/plugin.json`
  manifest with skills, commands, hooks, MCP configs
- **Publishing:** Self-hosted marketplace (GitHub repo)
  or official Anthropic directory (curated submission)
- **Deprecated workflows to remove:** 4 files, ~3,900
  lines — already handled by migration system

## Open Questions

- Which dead hubs should be implemented vs removed?
  (`/learning`, `/context`, `/wizard`, `/agent`)
- What's the minimum viable set of hubs for a v1
  marketplace release?
- Should batch operations use the existing Batch API
  infrastructure or a simpler approach?
