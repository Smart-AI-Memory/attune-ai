# Plugin Reference Validation

**Created:** 2026-03-25
**Source:** /brainstorm session
**Status:** completed

## Problem

AI sessions building or modifying plugin components (skills,
commands, hooks) can reference Python code that doesn't
exist - workflow names, MCP tools, class names, CLI commands.
Nothing catches these mismatches until a user hits a silent
failure at runtime.

## Goals

- **Must-have:** CLAUDE.md rule requiring grep verification
  before writing any plugin component that references code
- **Must-have:** Automated test suite that parses all plugin
  `.md` files and validates every reference resolves to real
  code
- **Nice-to-have:** Run validation in CI

## End State

Every plugin component that references Python code is
validated against the actual codebase:

- Skill descriptions mentioning workflow names verified
  against `list_workflows()` and class imports
- Commands referencing MCP tool names verified against
  `server.py` registered tools
- Skills describing CLI commands verified against actual
  CLI subcommands
- `Read skill` or file references verified the target
  file exists
- Class names and function names in routing verified
  with grep/import

Two enforcement layers:

1. CLAUDE.md rule requiring `grep` verification before
   writing plugin components that reference code
2. Test suite parsing all plugin `.md` files, extracting
   references, and asserting they resolve

## Approach

1. **Add CLAUDE.md rule** (`.claude/CLAUDE.md`)
   - New "Plugin Development" section
   - Rule: before writing/modifying any skill, command,
     or hook that references a workflow, MCP tool, CLI
     command, or Python class, `grep` for it in `src/`
     first
   - Include specific verification commands for each
     reference type

2. **Build reference extraction** (`tests/unit/plugin/`)
   - Parse all `.md` files under `plugin/skills/`,
     `plugin/commands/`, `commands/`
   - Extract patterns: workflow names, MCP tool names
     (`attune_*`), class names (`*Workflow`, `*Agent`),
     CLI subcommands, file path references
   - Use regex to find references in skill descriptions
     and command bodies

3. **Build resolution checks**
   - Workflow names: import `list_workflows()` or grep
     `src/attune/workflows/` for class definitions
   - MCP tools: grep `server.py` for `@tool` or handler
     registrations
   - CLI commands: grep `cli_minimal.py` and
     `cli_router.py` for registered subcommands
   - File paths: `Path.exists()` check relative to repo
     root
   - Class names: grep `src/` for `class ClassName`

4. **Wire into test suite**
   - `tests/unit/plugin/test_plugin_references.py`
   - One test per reference type
   - Clear error messages: "Skill X references workflow
     Y but no such workflow exists in src/"

5. **Add CI step** (optional follow-up)
   - Add to existing pytest CI workflow
   - Fails the build if any plugin reference is dangling

## Next Steps

- [ ] Draft the CLAUDE.md rule text
- [ ] Inventory all plugin `.md` files to understand
      reference patterns
- [ ] Write reference extraction regexes
- [ ] Implement `test_plugin_references.py`
- [ ] Run validation and fix any current mismatches

## Open Questions

- Should the test also validate that skill `description`
  fields in YAML frontmatter accurately describe what the
  underlying code does, or just that references resolve?
- Should hook scripts (Python files under `hooks/`) also
  be validated for import correctness?
