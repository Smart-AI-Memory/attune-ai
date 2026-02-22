# Documentation Consistency Audit

**Created:** 2026-02-22
**Source:** /brainstorm session
**Route:** audit
**Status:** in-progress

## Problem

Documentation across the project may have drifted from
reality as commands and features evolved. Users could
encounter stale or contradictory information that
misleads rather than helps.

## Goals

- Identify every doc that's stale, inconsistent, or
  contradicts another doc
- Categorize findings by severity (Critical / Medium /
  Low)
- Produce an actionable audit report for prioritized
  fixes

## End State

A severity-grouped audit report covering all
documentation: slash commands, CLAUDE.md, README, docs/,
and internal rules. Each finding describes the
inconsistency and suggests a fix.

## Scope

- **Files:** `.claude/commands/*.md`, `.claude/CLAUDE.md`,
  `.claude/rules/**/*.md`, `README.md`, `CHANGELOG.md`,
  `docs/**/*.md`, `docs/**/*.rst`
- **Type:** audit

## Approach

1. Audit slash command definitions against actual
   behavior
2. Audit CLAUDE.md hub table against command files
3. Audit docs/ reference guides against codebase
4. Audit internal rules for staleness
5. Cross-reference docs for contradictions
6. Compile severity-grouped report

## Task Prompts

```xml
<task id="audit-1" name="slash-command-audit">
  <objective>
    Audit every .claude/commands/*.md file against
    actual behavior. Check that documented routes,
    subcommands, and usage examples match what the
    skill definitions actually instruct Claude to do.
  </objective>

  <context>
    <existing-code path=".claude/commands/">
      Command files define slash command behavior via
      markdown frontmatter (name, description, options)
      and body text (routes, usage, behavior sections).
      Routes listed in the "Routes" table should match
      the behavior sections below. Usage examples should
      be valid invocations.
    </existing-code>
    <existing-code path="src/attune/cli_router.py">
      cli_router.py maps keywords to (skill, subcommand)
      tuples. Commands referenced in docs should have
      matching router entries.
    </existing-code>
  </context>

  <files-to-read>
    <file path=".claude/commands/plan.md" />
    <file path=".claude/commands/dev.md" />
    <file path=".claude/commands/testing.md" />
    <file path=".claude/commands/workflows.md" />
    <file path=".claude/commands/release.md" />
    <file path=".claude/commands/docs.md" />
    <file path=".claude/commands/attune.md" />
    <file path=".claude/commands/brainstorm.md" />
    <file path=".claude/commands/agent.md" />
    <file path=".claude/commands/batch.md" />
    <file path=".claude/commands/wizard.md" />
    <file path="src/attune/cli_router.py" />
  </files-to-read>

  <validation>
    <check>
      Every route in each command's Routes table has a
      matching behavior section
    </check>
    <check>
      Every usage example is a valid invocation
    </check>
    <check>
      Router keyword mappings match command definitions
    </check>
    <check>
      Frontmatter options align with documented routes
    </check>
  </validation>

  <output>
    Markdown report section: findings grouped by
    severity with file, line, issue, and suggested fix.
  </output>
</task>

<task id="audit-2" name="claude-md-hub-table-audit">
  <objective>
    Audit the CLAUDE.md Command Hubs table against
    actual command files. Verify every hub listed exists,
    every route listed is real, and descriptions match.
  </objective>

  <context>
    <existing-code path=".claude/CLAUDE.md">
      Contains a "Command Hubs" table listing all hubs,
      their key routes, and descriptions. This is the
      primary navigation reference for users.
    </existing-code>
  </context>

  <files-to-read>
    <file path=".claude/CLAUDE.md" />
    <file path=".claude/commands/*.md" />
  </files-to-read>

  <validation>
    <check>
      Every hub in CLAUDE.md has a corresponding
      .claude/commands/{hub}.md file
    </check>
    <check>
      Key routes listed in CLAUDE.md exist in the
      command file's Routes table
    </check>
    <check>
      Descriptions in CLAUDE.md match command file
      descriptions
    </check>
    <check>
      No command files exist that are missing from
      the CLAUDE.md table
    </check>
  </validation>

  <output>
    Markdown report section: mismatches between
    CLAUDE.md hub table and actual command definitions.
  </output>
</task>

<task id="audit-3" name="docs-reference-audit">
  <objective>
    Audit docs/ directory for stale content. Check that
    referenced files, classes, functions, and CLI
    commands still exist in the codebase.
  </objective>

  <context>
    <existing-code path="docs/">
      Contains reference guides, architecture docs,
      coding standards, and guides. These reference
      specific source files, class names, function
      signatures, and CLI commands that may have
      changed.
    </existing-code>
  </context>

  <files-to-read>
    <file path="docs/ARCHITECTURE.md" />
    <file path="docs/CODING_STANDARDS.md" />
    <file path="docs/EXCEPTION_HANDLING_GUIDE.md" />
    <file path="docs/reference/cli-reference.md" />
    <file path="docs/guides/*.md" />
  </files-to-read>

  <validation>
    <check>
      File paths referenced in docs exist in codebase
    </check>
    <check>
      Class and function names referenced still exist
    </check>
    <check>
      CLI commands documented still work
    </check>
    <check>
      Version numbers are current
    </check>
  </validation>

  <output>
    Markdown report section: stale references grouped
    by severity.
  </output>
</task>

<task id="audit-4" name="internal-rules-audit">
  <objective>
    Audit .claude/rules/ files for staleness. Check
    that referenced patterns, file paths, and
    recommendations still apply to the current codebase.
  </objective>

  <context>
    <existing-code path=".claude/rules/">
      Contains coding standards, scanner patterns,
      debugging history, optimization plans, and
      formatting rules. These reference specific files
      and patterns that may have moved or changed.
    </existing-code>
  </context>

  <files-to-read>
    <file path=".claude/rules/attune/coding-standards-index.md" />
    <file path=".claude/rules/attune/scanner-patterns.md" />
    <file path=".claude/rules/attune/debugging.md" />
    <file path=".claude/rules/attune/advanced-optimization-plan.md" />
    <file path=".claude/rules/attune/os-walk-dirs-pattern.md" />
    <file path=".claude/rules/attune/list-copy-guidelines.md" />
    <file path=".claude/rules/attune/output-formatting.md" />
    <file path=".claude/rules/attune/documentation-patterns.md" />
    <file path=".claude/rules/attune/vscode-extension-limitations.md" />
    <file path=".claude/rules/attune/xml-enhanced-prompts.md" />
    <file path=".claude/rules/attune/markdown-formatting.md" />
  </files-to-read>

  <validation>
    <check>
      File paths referenced in rules still exist
    </check>
    <check>
      Patterns described still match codebase reality
    </check>
    <check>
      Version numbers and dates are reasonable
    </check>
    <check>
      No rules reference deleted features or files
    </check>
  </validation>

  <output>
    Markdown report section: stale rules grouped by
    severity.
  </output>
</task>

<task id="audit-5" name="cross-reference-check">
  <objective>
    Cross-reference all documentation sources for
    contradictions. Find cases where two docs describe
    the same feature differently.
  </objective>

  <context>
    <note>
      This task depends on findings from audit-1
      through audit-4. Run after those complete.
      Focus on: version numbers, feature descriptions,
      command syntax, file paths, and architectural
      claims that appear in multiple docs.
    </note>
  </context>

  <validation>
    <check>
      No two docs claim different versions for the
      same component
    </check>
    <check>
      Command syntax is consistent across all docs
      that reference the same command
    </check>
    <check>
      Architecture descriptions don't contradict
      between ARCHITECTURE.md and CLAUDE.md
    </check>
  </validation>

  <output>
    Markdown report section: contradictions between
    docs, grouped by severity.
  </output>
</task>

<task id="audit-6" name="compile-report">
  <objective>
    Compile findings from audit-1 through audit-5
    into a single severity-grouped report saved to
    .claude/plans/docs-audit-report-2026-02-22.md.
  </objective>

  <context>
    <note>
      This task runs last. Collect all findings,
      deduplicate, assign severity, and format into
      the final report structure.
    </note>
  </context>

  <output-format>
    ## Documentation Audit Report

    **Date:** 2026-02-22
    **Scope:** Full audit — commands, CLAUDE.md,
    docs/, rules/

    **Summary:**
    X findings total | Y Critical | Z Medium | W Low

    ### Critical
    Issues that actively mislead users or reference
    things that don't exist.

    | Source | Issue | Suggested Fix |
    |--------|-------|---------------|
    | ... | ... | ... |

    ### Medium
    Stale content that could confuse but isn't
    blocking.

    | Source | Issue | Suggested Fix |
    |--------|-------|---------------|
    | ... | ... | ... |

    ### Low
    Minor inconsistencies, cosmetic issues, or
    slightly outdated info.

    | Source | Issue | Suggested Fix |
    |--------|-------|---------------|
    | ... | ... | ... |
  </output-format>

  <validation>
    <check>
      Report includes all findings from audit-1
      through audit-5
    </check>
    <check>
      Every finding has a severity, source file,
      and suggested fix
    </check>
    <check>
      Report is saved to .claude/plans/
    </check>
  </validation>
</task>
```

## Execution Order

1. Tasks audit-1 through audit-4 can run in parallel
   (independent scopes)
2. Task audit-5 depends on 1-4 (cross-referencing)
3. Task audit-6 depends on all (compilation)

## Next Steps

- [ ] Run audit-1: Slash command definitions
- [ ] Run audit-2: CLAUDE.md hub table
- [ ] Run audit-3: docs/ reference guides
- [ ] Run audit-4: Internal rules
- [ ] Run audit-5: Cross-reference check
- [ ] Run audit-6: Compile final report

## Open Questions

- Should the README.md and CHANGELOG.md be included
  in audit-3 or get their own task?
- Should the audit check for dead links (URLs that
  404)?
