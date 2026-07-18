---
name: docs
description: Documentation generation and explanation
---
# docs

Documentation generation, explanation, and accuracy auditing.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `audit` | Quick inline accuracy checks (10 checks) |
| `audit-deep` | Full DocAuditWorkflow with auto-fix |
| `explain` | Explain how code works |
| `generate` | Generate documentation |
| `readme` | Update README |
| `changelog` | Generate changelog |
| `overview` | High-level project overview |

## Usage

```bash
/docs                   # Ask what to do
/docs audit             # Verify doc accuracy
/docs explain           # Explain code
/docs generate          # Generate documentation
/docs readme            # Update README
/docs changelog         # Generate changelog
```

## Behavior

### audit

Cross-reference documentation claims against the actual
codebase. Run all checks below and report a summary table
with pass/fail per check and file:line references for any
mismatches.

#### 1. Test count

Run:

```bash
pytest --collect-only -q 2>/dev/null | tail -1
```

Compare the collected/passing count against:

- The static badge in README.md (the number in the
  `img.shields.io/badge/tests-` URL)
- Any "X+ tests" claims in README body text
- Any test counts in CHANGELOG.md (current release only)

Flag if the README count exceeds the actual count by
more than 5%.

#### 2. Workflow count

Count entries under `[project.entry-points."attune.workflows"]`
in `pyproject.toml`. Compare against any "N built-in" claims
in README.md. Flag mismatches.

#### 3. Skill count

Count directories in `plugin/skills/` (each directory with
a `SKILL.md` is one skill). Compare against:

- README.md (any "N skills" claims)
- CHANGELOG.md (current release section)
- `.claude-plugin/marketplace.json`
- `plugin/.claude-plugin/marketplace.json`

Flag mismatches.

#### 4. MCP tool count

Count `@server.tool()` decorators or tool registrations in
`src/attune/mcp/server.py`. Compare against any "N tools" or
"N MCP tools" claims in README.md and plugin/README.md.
Flag mismatches.

#### 5. File line limits

If README.md claims a maximum file size (e.g., "no file
exceeds X lines"), verify by running:

```bash
find src/attune -name "*.py" -exec wc -l {} + \
  | sort -rn | head -5
```

Flag any files that exceed the claimed limit.

#### 6. Install extras

Grep README.md and plugin/README.md for `attune-ai[` to
find all referenced extras. Verify each extra name exists
in `pyproject.toml` under `[project.optional-dependencies]`.
Flag any extras that are referenced in docs but do not exist
in pyproject.toml (e.g., `[redis]` when the actual extra is
`[memory]`).

#### 7. Stale command references

Grep all `*.md` files for these removed/legacy patterns:

- `empathy-memory` (removed in v2.6.2)
- `empathy workflow` (renamed to `attune workflow`)
- `empathy` as a CLI prefix (e.g., `empathy workflow`)

Report file:line for each occurrence. Exclude CHANGELOG
entries that document historical changes (those are
intentionally referencing old names).

#### 8. Version consistency

Compare the version string across:

- `pyproject.toml` (`version = "X.Y.Z"`)
- `src/attune/__init__.py` (`__version__`)
- `CHANGELOG.md` (latest `## [X.Y.Z]` heading)
- `plugin/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `plugin/.claude-plugin/marketplace.json`

Flag any that do not match.

#### 9. Cross-doc number consistency

Check that the same metric uses the same number everywhere:

- Cost savings percentages (README vs FAQ vs pitch docs)
- Test counts (README badge vs README body vs CHANGELOG)
- Skill counts (README vs CHANGELOG vs marketplace.json)
- Tool counts (README vs plugin README)

Flag any contradictions.

#### 10. Documentation links

For each markdown link in README.md that points to a local
file (not a URL), verify the target file exists. Report
broken links.

#### Output format

Present results as:

```markdown
## Doc Audit Results

| # | Check | Status | Details |
|---|-------|--------|---------|
| 1 | Test count | PASS/FAIL | ... |
| 2 | Workflow count | PASS/FAIL | ... |
...

### Issues Found

- [README.md:76](README.md#L76): claims "14,000+ tests"
  but actual count is 11,016
...
```

### audit-deep

Trigger the DocAuditWorkflow for a full documentation
audit with automatic fixes. This is the autonomous
pipeline with 4 stages:

1. **Audit** — Run all 10 doc checks programmatically
2. **Plan** — For each failing check, generate a fix plan
3. **Execute** — Apply auto-fixable changes (counts,
   versions, stale refs)
4. **Verify** — Re-run checks, confirm score improved,
   build MkDocs to verify

Show audit results and fix plan for approval before
the execute phase.

```bash
# Interactive mode (default)
uv run attune workflow run doc-audit

# With --batch flag for fire-and-forget
uv run attune workflow run doc-audit --batch
```

Use `AskUserQuestion` before running:

- Auto-fix safe changes? (default: yes)
- Build MkDocs to verify? (default: yes)
- Approve plan before executing?

### explain

Use `AskUserQuestion` to scope:

- Which file, function, or module to explain?
- What level of detail? (overview, deep dive, or
  architecture)

Then read the code and provide a clear explanation
with context.

### generate

Use `AskUserQuestion` to scope:

- What to document? (API, module, function)
- Format? (docstrings, markdown, or both)

Then generate documentation using the codebase.

### readme

Read the current README and project structure, then
suggest or apply updates based on current state.

### changelog

Use git log to generate a changelog:

```bash
git log --oneline --since="last tag"
```

Format as a markdown changelog grouped by type
(features, fixes, refactoring).

### overview

Use `AskUserQuestion` to scope:

- Which scope? (full project, specific module,
  or subsystem)
- What audience? (new contributor, external user,
  or architecture review)

Then read the project structure and generate a
high-level overview covering purpose, key modules,
and how they connect.
