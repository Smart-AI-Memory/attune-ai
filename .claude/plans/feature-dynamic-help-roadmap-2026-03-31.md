# Dynamic Help System: Multi-Release Roadmap

**Created:** 2026-03-31
**Source:** /plan feature
**Route:** feature
**Status:** completed

## Problem

The help system has strong infrastructure (540+
templates, type-driven progression, cross-links) but
is disconnected from the runtime. Users only discover
it via `/learn`. No workflows surface help, no hooks
trigger it, and templates go stale silently when
source code changes.

## Goals

- Wire help into the runtime so users encounter it
  naturally (must-have)
- Close manifest coverage gaps so staleness detection
  works for all 540 templates (must-have)
- Auto-derive concept templates from new skills
  (must-have)
- Build an agent that detects stale templates and
  regenerates them (must-have)
- Feedback-driven regeneration priority (nice-to-have)

## End State

A living knowledge base where:

1. Help appears automatically after workflows and
   errors — users don't need to know `/learn` exists
2. Adding a new skill auto-generates all three
   template levels (concept, task, reference)
3. Editing CLAUDE.md or SKILL.md flags dependent
   templates as stale
4. A single command (`help_maintain`) regenerates
   stale templates
5. A session-start check warns when the KB is stale

---

## Phase 1 — Integration (v5.2)

Make the existing help discoverable without users
needing to know about it.

### 1A. Post-Workflow Help Suggestions

Add help templates to workflow suggestions output.

**Modify:** `src/attune/workflows/suggestions.py`

- Add `_suggestions_from_help(workflow_name)` that
  calls `get_workflow_help()` from `engine.py`
- Convert each `PopulatedTemplate` to a `NextAction`
  with `action_type="learn"`
- Wire as Source 4 in `generate_suggestions()` (~20
  lines, same try/except pattern as existing sources)

**Outcome:** After running any workflow, the user
sees "Learn more about security-audit" alongside
existing suggestions.

### 1B. Skill-Level Help Hints

Add `## Help` section to 6 high-traffic SKILL.md
files instructing Claude to call `help_lookup` after
presenting results.

**Modify (6 files):**

- `plugin/skills/security-audit/SKILL.md`
- `plugin/skills/code-quality/SKILL.md`
- `plugin/skills/smart-test/SKILL.md`
- `plugin/skills/release-prep/SKILL.md`
- `plugin/skills/doc-gen/SKILL.md`
- `plugin/skills/workflow-orchestration/SKILL.md`

**Outcome:** After any major skill completes, Claude
offers workflow-specific tips.

### 1C. Session State Persistence

Persist progressive depth across MCP server restarts.

**Modify:** `src/attune/help/engine.py`

- Add `_SESSION_FILE = ~/.attune/help_session.json`
- Load state on module init (4-hour TTL, reset if
  stale)
- Write state atomically after `populate_progressive`
- Store: `{last_topic, depth_level, timestamp}`

**Outcome:** "Tell me more" works across sessions.

### 1D. Error-Context Help Hook

Suggest help when Bash commands fail.

**Create:** `plugin/hooks/help_on_error.py`

- PostToolUse hook for Bash
- Pattern-match stderr against known error signatures
- Print hint: `attune: see /learn {topic} for help`
- Exit 0 always (never blocks)

**Modify:** `plugin/hooks/hooks.json` — add PostToolUse
entry for Bash.

**Outcome:** `ModuleNotFoundError` in Bash →
`see /learn imports for help`.

---

## Phase 2 — Knowledge Base Expansion (v5.3)

Close coverage gaps so every template is tracked
and new skills auto-generate all three levels.

### 2A. Full Source Manifest Coverage

**Modify:** `scripts/generate_all.py`

- Expand `_build_source_manifest()` from 4 type dirs
  to all 11 (2-line change at line 76)
- All 540 templates get hash-tracked for staleness

### 2B. Auto-Derive Concepts from Skills

**Modify:** `scripts/generate_concept_templates.py`

- Add `_discover_concepts_from_skills()` that reads
  `plugin/skills/*/SKILL.md` frontmatter
- Merge with existing `_CONCEPTS` (curated overrides
  take precedence)
- New skills auto-get a concept template

### 2C. CLAUDE.md Lessons Tracking

**Modify:** Error, warning, and FAQ generators

- Set `source: ".claude/CLAUDE.md"` on items derived
  from Lessons Learned entries
- Enables `--stale` to detect when CLAUDE.md edits
  make templates outdated

### 2D. Enhanced Coverage Report

**Modify:** `scripts/generate_all.py` `check_coverage()`

- Check every skill has concept + task + reference
- Check every workflow_map entry has a tip
- Report gaps grouped by type

---

## Phase 3 — Auto-Generation Agent (v5.4)

The self-healing layer that keeps the KB alive.

### 3A. Help Maintenance Workflow

**Create:** `src/attune/workflows/help_maintenance.py`

SDK-native `BaseWorkflow` subclass with 5 phases:

1. **DETECT** — `ProjectIndex.refresh_incremental()`
   finds changed source files
2. **MAP** — cross-reference changes against
   `source_manifest.json` for stale templates
3. **REGENERATE** — `subprocess.run()` the appropriate
   generator for each stale type
4. **REBUILD** — run `build_cross_links.py`
5. **VALIDATE** — run `generate_all.py --check`

Returns `WorkflowResult` with `regenerated` list,
`validated` bool, and `coverage_gaps`.

### 3B. MCP Tool: `help_maintain`

**Modify:** `src/attune/mcp/tool_schemas.py` and
`src/attune/mcp/server.py`

- Add `help_maintain` tool with `dry_run` parameter
- Handler instantiates `HelpMaintenanceWorkflow`
- Wire into dispatch table

### 3C. Session Freshness Check

**Create:** `plugin/hooks/help_freshness_check.py`

SessionStart hook:

- Read `source_manifest.json` last-modified time
- If older than 24h, run `generate_all.py --stale`
- If stale found, print count to stderr
- Must complete under 500ms

**Modify:** `plugin/hooks/hooks.json` — add
SessionStart entry.

### 3D. Skill Update for Maintenance

**Modify:** `plugin/skills/learn/SKILL.md`

- Add maintenance mode: "update help" / "refresh
  templates" → `help_maintain(dry_run=false)`
- Preview mode: `help_maintain(dry_run=true)`

### 3E. Feedback-Driven Priority

**Modify:** `help_maintenance.py` MAP phase

- Sort stale templates by: feedback score (bad first),
  usage weight (popular first), staleness age
- Uses existing `get_template_confidence()` and
  `get_usage_weights()` from engine.py

---

## Dependencies

```
Phase 1: All items independent, parallelizable
Phase 2: 2A first, then 2B/2C, then 2D
Phase 3: Depends on 2A (full manifest)
         3A first, then 3B/3C/3D/3E
```

## Scope

- **Files (create):** 3 (help_on_error.py,
  help_freshness_check.py, help_maintenance.py)
- **Files (modify):** ~15 across all phases
- **Type:** feature (multi-release)

## Verification

### Phase 1

- `generate_suggestions("security-audit", result)`
  returns NextAction with `action_type="learn"`
- `grep help_lookup plugin/skills/*/SKILL.md` → 7
- `~/.attune/help_session.json` persists depth
- Bash error triggers help hint in hook stderr

### Phase 2

- `source_manifest.json` has ~540 entries
- New stub skill auto-generates concept template
- Edit CLAUDE.md → `--stale` flags dependent templates
- `--coverage` reports missing concept/task/ref gaps

### Phase 3

- `help_maintain(dry_run=true)` lists stale templates
- `help_maintain(dry_run=false)` regenerates them
- Session start warns when KB is stale
- Bad-rated templates regenerate first

## Open Questions

- Should `help_maintain` auto-commit regenerated
  templates, or leave them as unstaged changes for
  the user to review?
- Should the freshness check be async (background
  thread) to avoid adding latency to session start?
- Should concept auto-derivation use LLM to write
  richer "Why" sections, or keep it rule-based?
