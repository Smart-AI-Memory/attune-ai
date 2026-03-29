# Skills-Centric Plugin Migration

**Created:** 2026-03-28
**Source:** /brainstorm session

## Problem

Anthropic officially announced that skills are the primary
plugin surface for Claude Code. The attune-ai plugin is
currently command-heavy (14 commands, 10 skills) with
skills serving mainly as MCP tool documentation. Commands
give short `/attune` names but don't align with the
recommended approach. Skills are namespaced
(`/attune-ai:skill-name`) which hurts UX, but auto-trigger
from natural language via description fields — making
explicit invocation less important.

## Goals

- **Must-have:** Skills become the primary plugin surface
  with full Socratic scoping, execution instructions, and
  MCP tool wiring
- **Must-have:** Commands reduced to 2 — `/attune` (hub
  router) and `/spec` (interactive workflow)
- **Must-have:** Skill descriptions tuned for
  auto-triggering from natural language
- **Must-have:** `plugin.json` at repo root (not in
  `.claude-plugin/` subdirectory)
- **Nice-to-have:** `.agents/skills/` mirror stays in sync
- **Nice-to-have:** Retire or archive old command files
  cleanly

## End State

A user installs the attune-ai plugin. They see:

- 2 commands: `/attune` and `/spec`
- ~12 skills, each self-contained with Socratic scoping,
  execution flow, and MCP tool calls
- Claude auto-triggers skills from natural language
  (e.g., "review my code" fires `code-quality` skill)
- `/attune` hub routes to skills by reference
- `plugin.json` at repo root passes install validation

**Testable criteria:**

- `ls plugin/commands/` shows exactly 2 files
- `ls plugin/skills/` shows ~12 directories
- Each skill `description` contains trigger phrases
- `plugin.json` exists at `plugin/plugin.json` (repo root
  of plugin dir)
- No skill uses disallowed frontmatter fields
- No orphaned command references in CLAUDE.md or
  plugin docs

## Approach

### Step 1: Verify plugin.json location

~~REVERTED: `plugin.json` belongs inside
`.claude-plugin/`, not at plugin root.~~ The original
location `plugin/.claude-plugin/plugin.json` was correct.
The lesson in CLAUDE.md was wrong and has been fixed.

### Step 2: Inventory command-to-skill mapping

Map each command to its target skill:

| Command | Target Skill | Status |
|---------|-------------|--------|
| `attune.md` | KEEP as command | Hub router |
| `spec.md` | KEEP as command | Interactive workflow |
| `bug-predict.md` | NEW skill needed | Create |
| `code-quality.md` | `code-quality` exists | Merge |
| `doc-gen.md` | `doc-gen` exists | Merge |
| `fix-test.md` | `fix-test` exists | Merge |
| `plan.md` | `planning` exists | Merge |
| `refactor.md` | `refactor-plan` exists | Merge |
| `release.md` | `release-prep` exists | Merge |
| `remember.md` | `memory-and-context` exists | Merge |
| `security.md` | `security-audit` exists | Merge |
| `smart-test.md` | `smart-test` exists | Merge |
| `workflows.md` | `workflow-orchestration` exists | Merge |

### Step 3: Enrich existing skills (10 skills)

For each skill that has a corresponding command:

1. Read the command file's routing logic, scoping
   questions, and execution instructions
2. Merge that content into the skill's SKILL.md
3. Ensure the `description` field has rich trigger
   phrases for auto-invocation
4. Drop `compatibility`, `license`, `metadata` from
   frontmatter. Valid fields: `name`, `description`,
   `argument-hint`, `disable-model-invocation`,
   `user-invocable`, `allowed-tools`, `model`,
   `effort`, `context`, `agent`, `hooks`, `paths`,
   `shell`
5. Remove `disable-model-invocation: true` from
   `fix-test` and `release-prep` (keep only on
   `memory-and-context`)

### Step 4: Create new skills (2 skills)

Commands without existing skills need new skill
directories:

- `plugin/skills/bug-predict/SKILL.md` — from
  `bug-predict.md` command
- `plugin/skills/deep-review/SKILL.md` — if not already
  covered by `code-quality` skill's "deep" mode

### Step 5: Trim commands to 2

Remove 12 command files from `plugin/commands/`:

- `bug-predict.md`
- `code-quality.md`
- `doc-gen.md`
- `fix-test.md`
- `plan.md`
- `refactor.md`
- `release.md`
- `remember.md`
- `security.md`
- `smart-test.md`
- `workflows.md`

Keep only:

- `attune.md` — hub router (update to reference skills)
- `spec.md` — interactive spec-driven workflow

### Step 6: Update /attune hub command

Rewrite `attune.md` to route users to skills instead
of other commands. The `AskUserQuestion` options should
map to skill names. When a user picks "Run a workflow",
the command should tell Claude to invoke the
`workflow-orchestration` skill.

### Step 7: Sync .agents/skills/

Run `scripts/sync_agents_skills.py` or manually mirror
updated skills to `.agents/skills/`.

### Step 8: Validate

- Run plugin validation tests
- Verify `plugin.json` location
- Check all skill frontmatter is valid
- Grep for orphaned references to removed commands
- Test natural language triggering ("run a security
  audit" should fire the skill)

## Architecture Notes

### Skill description as routing key

The `description` field in SKILL.md frontmatter is the
primary mechanism for auto-triggering. Anthropic's model
matches user intent against skill descriptions. Format:

```yaml
description: "What the skill does. Triggers on: keyword1,
  keyword2, keyword3."
```

The "Triggers on:" suffix is the established pattern in
the existing skills and should be preserved.

### Command-skill relationship

```
/attune (command) -> routes to skills by name
/spec (command) -> self-contained interactive workflow
Skills -> auto-triggered by natural language OR
          referenced by /attune hub
```

### What NOT to migrate

- `.claude/skills/` (24 local skills) — these are personal
  workflow skills, not part of the installable plugin
- `src/attune/commands/` — PyPI-distributed commands for
  non-plugin installs
- MCP server tools — skills reference these, don't replace
  them

## Resolved Questions

- **Hub routing:** `/attune` routes via description-based
  natural language (e.g., "run a security audit"), NOT
  namespaced skill references. Let Claude match intent to
  skill descriptions.

- **Frontmatter allowlist (updated March 2026):**
  `name`, `description`, `argument-hint`,
  `disable-model-invocation`, `user-invocable`,
  `allowed-tools`, `model`, `effort`, `context`, `agent`,
  `hooks`, `paths`, `shell`. Drop `compatibility`,
  `license`, `metadata` — not in official docs.

- **Auto-triggering:** Remove `disable-model-invocation`
  from `fix-test` and `release-prep`. Keep it ONLY on
  `memory-and-context` (sensitive operations). All other
  skills should be auto-triggerable.

## Tasks

<!-- spec-state: {"completed": ["1", "2", "3", "4",
"5", "6", "7", "8"], "current": null,
"auto_run": false,
"last_updated": "2026-03-28T20:00:00"} -->

<task id="1" name="move-plugin-json">
  <objective>
    Move plugin.json to plugin/ root so Claude Code
    finds it alongside skills/ and commands/.
  </objective>
  <files-to-modify>
    <file path="plugin/plugin.json">
      Copy from plugin/.claude-plugin/plugin.json
    </file>
  </files-to-modify>
  <validation>
    <check>plugin/plugin.json exists at plugin root</check>
    <check>plugin/.claude-plugin/ can be removed or
      kept as backward compat</check>
  </validation>
</task>

<task id="2" name="clean-skill-frontmatter">
  <objective>
    Update all 10 existing skill SKILL.md files: drop
    compatibility, license, metadata fields. Remove
    disable-model-invocation from fix-test and
    release-prep (keep only on memory-and-context).
  </objective>
  <files-to-modify>
    <file path="plugin/skills/code-quality/SKILL.md">
      Remove compatibility, license, metadata
    </file>
    <file path="plugin/skills/doc-gen/SKILL.md">
      Remove compatibility, license, metadata
    </file>
    <file path="plugin/skills/fix-test/SKILL.md">
      Remove compatibility, metadata; remove
      disable-model-invocation
    </file>
    <file path="plugin/skills/memory-and-context/SKILL.md">
      Remove compatibility, metadata; KEEP
      disable-model-invocation
    </file>
    <file path="plugin/skills/planning/SKILL.md">
      Remove compatibility, license, metadata
    </file>
    <file path="plugin/skills/refactor-plan/SKILL.md">
      Remove compatibility, license, metadata
    </file>
    <file path="plugin/skills/release-prep/SKILL.md">
      Remove compatibility, metadata; remove
      disable-model-invocation
    </file>
    <file path="plugin/skills/security-audit/SKILL.md">
      Remove compatibility, license, metadata
    </file>
    <file path="plugin/skills/smart-test/SKILL.md">
      Remove compatibility, license, metadata
    </file>
    <file path="plugin/skills/workflow-orchestration/SKILL.md">
      Remove compatibility, license, metadata
    </file>
  </files-to-modify>
  <validation>
    <check>No skill contains compatibility, license,
      or metadata in frontmatter</check>
    <check>Only memory-and-context has
      disable-model-invocation: true</check>
  </validation>
</task>

<task id="3" name="enrich-skills-from-commands">
  <objective>
    The 10 thin delegator commands add no unique logic
    (they just say "Read skill file:///..."). But the
    skills themselves need self-contained Socratic
    scoping. Verify each skill has: (1) scoping
    questions, (2) execution instructions, (3) MCP tool
    usage examples. Most already do. Fix any gaps.
  </objective>
  <files-to-modify>
    <file path="plugin/skills/*/SKILL.md">
      Audit and fill gaps in scoping/execution sections
    </file>
  </files-to-modify>
  <validation>
    <check>Each skill has a ## Scoping section with
      numbered questions</check>
    <check>Each skill has a ## Execution section with
      MCP tool call examples</check>
  </validation>
</task>

<task id="4" name="create-bug-predict-skill">
  <objective>
    Create new skill from bug-predict.md command. This
    command has unique scoping (target path + severity
    filter) and execution logic (runs attune workflow
    run bug-predict).
  </objective>
  <files-to-create>
    <file path="plugin/skills/bug-predict/SKILL.md">
      Frontmatter: name, description with trigger
      phrases, argument-hint. Body: scoping questions
      (path, severity filter), execution via
      bug_predict MCP tool, output format (markdown
      table grouped by severity).
    </file>
  </files-to-create>
  <validation>
    <check>plugin/skills/bug-predict/SKILL.md exists</check>
    <check>Description contains trigger phrases</check>
    <check>No disallowed frontmatter fields</check>
  </validation>
</task>

<task id="5" name="remove-delegator-commands">
  <objective>
    Remove the 11 command files that are now fully
    covered by skills. Keep only attune.md and spec.md.
  </objective>
  <files-to-modify>
    <file path="plugin/commands/">
      Remove: bug-predict.md, code-quality.md,
      doc-gen.md, fix-test.md, plan.md, refactor.md,
      release.md, remember.md, security.md,
      smart-test.md, workflows.md
    </file>
  </files-to-modify>
  <validation>
    <check>ls plugin/commands/ shows only attune.md
      and spec.md</check>
  </validation>
</task>

<task id="6" name="update-attune-hub">
  <objective>
    Rewrite attune.md hub command to route via natural
    language descriptions instead of referencing other
    commands. When a user picks "Run a workflow", the
    command body should describe the intent so Claude
    matches it to the right skill automatically.
  </objective>
  <files-to-modify>
    <file path="plugin/commands/attune.md">
      <change location="routing table and execution">
        Replace file:///skills/ references and command
        cross-references with description-based routing.
        Remove shortcuts to deleted commands.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>No references to deleted command files</check>
    <check>No file:///skills/ references (use
      description-based routing instead)</check>
  </validation>
</task>

<task id="7" name="sync-agents-skills">
  <objective>
    Mirror updated plugin/skills/ to .agents/skills/.
    Run sync script or manually copy.
  </objective>
  <files-to-modify>
    <file path=".agents/skills/">
      Mirror all skill directories from plugin/skills/
    </file>
  </files-to-modify>
  <validation>
    <check>diff -r plugin/skills/ .agents/skills/ shows
      no differences</check>
  </validation>
</task>

<task id="8" name="validate-plugin">
  <objective>
    Final validation: check plugin structure, frontmatter,
    no orphaned references, and natural language
    triggering readiness.
  </objective>
  <validation>
    <check>plugin.json at plugin root</check>
    <check>Exactly 2 commands (attune.md, spec.md)</check>
    <check>12 skill directories in plugin/skills/</check>
    <check>No skill uses compatibility/license/metadata</check>
    <check>Only memory-and-context has
      disable-model-invocation</check>
    <check>No orphaned command references in CLAUDE.md
      or skill docs</check>
    <check>Each skill description has trigger phrases</check>
  </validation>
</task>
