---
name: catalog
description: Browse all available workflows, wizards, and tools
category: primary
aliases: [list, browse, menu]
tags: [catalog, discovery, navigation, list]
version: "1.0.0"
---

# catalog

Single command to browse everything Attune AI offers.

## Routes

| Shortcut | Behavior |
| -------- | -------- |
| `/catalog` | Show full catalog + interactive picker |
| `/catalog workflows` | Show workflows only |
| `/catalog wizards` | Show wizards only |
| `/catalog testing` | Filter by domain |
| `/catalog run <name>` | Skip catalog, run item directly |

## Direct Invocation (Power Users)

When invoked with `run <name>`, skip the catalog display
and `AskUserQuestion` entirely. Route directly:

| Example | Action |
| ------- | ------ |
| `/catalog run test-gen` | `/workflows run test-gen` |
| `/catalog run security-audit` | `/workflows run security-audit` |
| `/catalog run debug` | `/wizard run debug` |
| `/catalog run refactor` | `/wizard run refactor` |
| `/catalog run brainstorm` | `/brainstorm` |
| `/catalog run plan` | `/plan` |
| `/catalog run batch` | `/batch` |

**Routing rules:**

- Match `<name>` against the catalog tables below
- If type is **workflow** → invoke `/workflows run <name>`
- If type is **wizard** → invoke `/wizard run <name>`
- If type is **tool** → invoke `/<name>` skill directly
- If no match → show error: "Unknown item: `<name>`.
  Run `/catalog` to see available options."

## CRITICAL: Three-Step Interactive Flow

`AskUserQuestion` supports max 4 options per question.
Use a two-tier picker: domain first, then item.

### Step 1: Display the catalog immediately

Do NOT ask questions first. Show the full table grouped
by domain (see Catalog Display below). Then proceed to
Step 2.

### Step 2: Pick a domain

Use `AskUserQuestion` with these 4 domain groups:

```yaml
question: "Which area interests you?"
options:
  - "Testing & Security" (test-gen, test-audit, security-audit, secure-release, security wizard)
  - "Code Quality" (code-review, bug-predict, perf-audit, simplify-code, refactor-plan, refactor wizard, debug wizard)
  - "Docs & Release" (doc-gen, doc-audit, doc-orchestrator, release-prep, dependency-check)
  - "Research & Ops" (research-synthesis, brainstorm, plan, batch, orchestrated-health-check)
```

If the user picks "Other" and names a specific item,
skip Step 3 and route directly.

### Step 3: Pick an item

Show a second `AskUserQuestion` with items from the
chosen domain (max 4 options per question). For domains
with more than 4 items, pick the 4 most commonly used
and let the user type "Other" for the rest.

**Testing & Security:**

- test-gen — Generate tests
- security-audit — OWASP scan
- test-audit — Coverage gaps
- secure-release — Security gate

**Code Quality:**

- code-review — Tiered analysis
- bug-predict — Pattern detection
- debug (wizard) — Error investigation
- refactor (wizard) — Safe refactoring

**Docs & Release:**

- doc-gen — Generate docs
- release-prep — Release readiness
- doc-audit — Staleness check
- dependency-check — Vulnerability audit

**Research & Ops:**

- brainstorm — Thinking partner
- plan — Architecture planning
- batch — 50% cost savings
- research-synthesis — Multi-tier research

### Step 4: Execute the selection

When the user picks an item, invoke it with the Skill
tool:

- Items tagged `(workflow)` → invoke `/workflows`
  skill with `run <name>` as the argument
- Items tagged `(wizard)` → invoke `/wizard` skill
  with `run <name>` as the argument
- `brainstorm` → invoke `/brainstorm` skill
- `plan` → invoke `/plan` skill
- `batch` → invoke `/batch` skill

## Catalog Display

Show this table to the user in Step 1:

### Testing

| Name | Type | Description |
| ---- | ---- | ----------- |
| test-gen | workflow | Generate tests for files with low coverage or bug history |
| test-audit | workflow | Measure coverage gaps, plan batches, verify improvement |
| test-gen | wizard | Interactive guided test generation (Socratic flow) |

### Security

| Name | Type | Description |
| ---- | ---- | ----------- |
| security-audit | workflow | OWASP-focused security scan |
| secure-release | workflow | Security gate before publishing |
| security | wizard | Guided vulnerability scanning and remediation |

### Code Quality

| Name | Type | Description |
| ---- | ---- | ----------- |
| code-review | workflow | Tiered code analysis with optional crew and architect review |
| bug-predict | workflow | Predict bugs from code patterns |
| perf-audit | workflow | Performance bottleneck detection |
| simplify-code | workflow | Identify refactoring opportunities |
| refactor-plan | workflow | Prioritize tech debt by impact |
| refactor | wizard | Guided safe refactoring (Socratic flow) |

### Documentation

| Name | Type | Description |
| ---- | ---- | ----------- |
| doc-gen | workflow | Generate documentation for modules |
| doc-audit | workflow | Validate docs for staleness and broken links |
| doc-orchestrator | workflow | End-to-end doc maintenance (scout + write) |

### Release

| Name | Type | Description |
| ---- | ---- | ----------- |
| release-prep | workflow | Multi-agent release readiness assessment |
| release-prep | wizard | Guided release checklist (Socratic flow) |
| dependency-check | workflow | Audit dependencies for vulnerabilities |

### Research & Planning

| Name | Type | Description |
| ---- | ---- | ----------- |
| research-synthesis | workflow | Multi-tier research and comparison |
| brainstorm | tool | Conversational thinking partner — turns ideas into plans |
| plan | tool | Feature planning, architecture, TDD scaffolding |

### Debugging

| Name | Type | Description |
| ---- | ---- | ----------- |
| debug | wizard | Guided error investigation and fix planning |

### Operations

| Name | Type | Description |
| ---- | ---- | ----------- |
| orchestrated-health-check | workflow | Meta-orchestration health check |
| batch | tool | Batch API processing (50% cost savings) |

## Quick Reference

- **Workflow** = automated pipeline. No interaction needed.
- **Wizard** = guided flow. Asks questions first.
- **Tool** = direct command or conversational feature.

## Filtering

If invoked with an argument (e.g., `/catalog testing`),
show only the matching domain section and offer only
those items in `AskUserQuestion`. Match against domain
names: testing, security, quality, docs, release,
research, debugging, operations.
