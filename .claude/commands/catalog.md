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

## CRITICAL: Two-Step Interactive Flow

### Step 1: Display the catalog immediately

Do NOT ask questions first. Show the full table grouped
by domain. Then immediately proceed to Step 2.

### Step 2: Ask what to run

After displaying the catalog, use `AskUserQuestion` to
let the user pick an item to launch:

```yaml
question: "What would you like to run?"
header: "Launch from catalog"
multiSelect: false
options:
  - label: "test-gen (workflow)"
    description: "Generate tests for low-coverage files"
  - label: "test-audit (workflow)"
    description: "Measure coverage gaps and verify improvement"
  - label: "test-gen (wizard)"
    description: "Interactive guided test generation"
  - label: "security-audit (workflow)"
    description: "OWASP-focused security scan"
  - label: "secure-release (workflow)"
    description: "Security gate before publishing"
  - label: "security (wizard)"
    description: "Guided vulnerability scanning"
  - label: "code-review (workflow)"
    description: "Tiered code analysis with architect review"
  - label: "bug-predict (workflow)"
    description: "Predict bugs from code patterns"
  - label: "perf-audit (workflow)"
    description: "Performance bottleneck detection"
  - label: "simplify-code (workflow)"
    description: "Identify refactoring opportunities"
  - label: "refactor-plan (workflow)"
    description: "Prioritize tech debt by impact"
  - label: "refactor (wizard)"
    description: "Guided safe refactoring"
  - label: "debug (wizard)"
    description: "Guided error investigation"
  - label: "doc-gen (workflow)"
    description: "Generate documentation for modules"
  - label: "doc-audit (workflow)"
    description: "Validate docs for staleness and links"
  - label: "doc-orchestrator (workflow)"
    description: "End-to-end doc maintenance"
  - label: "release-prep (workflow)"
    description: "Multi-agent release readiness"
  - label: "release-prep (wizard)"
    description: "Guided release checklist"
  - label: "dependency-check (workflow)"
    description: "Audit dependencies for vulnerabilities"
  - label: "research-synthesis (workflow)"
    description: "Multi-tier research and comparison"
  - label: "brainstorm"
    description: "Conversational thinking partner"
  - label: "plan"
    description: "Feature planning and architecture"
  - label: "orchestrated-health-check (workflow)"
    description: "Meta-orchestration health check"
  - label: "batch"
    description: "Batch API processing (50% cost savings)"
  - label: "Just browsing"
    description: "No action needed"
```

### Step 3: Execute the selection

When the user picks an item, invoke it with the Skill
tool:

- Items ending in `(workflow)` → invoke `/workflows`
  skill with `run <name>` as the argument
- Items ending in `(wizard)` → invoke `/wizard` skill
  with `run <name>` as the argument
- `brainstorm` → invoke `/brainstorm` skill
- `Just browsing` → end, no action

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
