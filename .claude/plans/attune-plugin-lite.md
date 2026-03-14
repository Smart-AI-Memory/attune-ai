# Attune Plugin Lite — Focused Plugin for Anthropic Library

**Created:** 2026-03-14
**Source:** /brainstorm session

## Problem

Attune-ai has been rejected 3 times from Anthropic's plugin
library. The full framework (15 workflows, CLI, memory,
orchestration) is too broad. Accepted plugins are focused:
a few skills, commands, and a clean plugin.json. No external
Python dependencies.

## Goals

- Get accepted into Anthropic's Claude Code plugin library
- Surface attune-ai's best workflows as self-contained
  prompt-based skills (no pip install required)
- Keep attune-ai on PyPI as the full product — the plugin
  is a lightweight storefront, not a replacement
- Showcase Agent SDK best practices (model routing, budget
  awareness, structured output) via prompt engineering

## End State

A standalone plugin directory (`attune-plugin/`) with:

- `plugin.json` manifest
- 5 prompt-based skills (no Python, no CLI dependency)
- 5 corresponding slash commands with argument support
- A README tailored for the plugin library submission

A reviewer installs the plugin, types `/code-review`, and
gets a structured multi-agent report. Nothing else to
configure or install.

## Approach

### Phase 1: Plugin Scaffold

1. Create `attune-plugin/` directory (separate from
   `src/attune/`)
2. Write `plugin.json` with metadata, description, and
   component registration
3. Add a focused `README.md` for the plugin (not the full
   attune-ai README)

### Phase 2: Extract Skills (5 skills)

For each workflow, extract the agent definitions, system
prompts, and orchestration logic into a self-contained
markdown skill file. The skill prompt should include:

- System prompt (persona/behavioral preamble)
- Subagent role descriptions and specializations
- Model routing guidance (baked into prompt text)
- Output format expectations
- Budget/scope awareness

#### Skill 1: `/code-review`

- **Source:** `src/attune/workflows/code_review.py`
- **Agents:** architecture, quality, security, performance
- **Key feature:** Structured output with findings by
  category, severity, and file location
- **Arguments:** `<path>` (default: `.`)

#### Skill 2: `/security-audit`

- **Source:** `src/attune/workflows/security_audit.py`
- **Agents:** vulnerability scanner, dependency checker,
  configuration reviewer, attack surface analyzer
- **Key feature:** OWASP-aligned findings with severity
  ratings
- **Arguments:** `<path>` (default: `.`)

#### Skill 3: `/smart-test`

- **Source:** `src/attune/workflows/test_gen/workflow.py`
  and `test_audit/workflow.py`
- **Agents:** test gap analyzer, test generator, coverage
  estimator
- **Key feature:** Generates tests for uncovered code,
  identifies test gaps
- **Arguments:** `<path>`, `--lf` (last failed),
  `--changed` (recently changed files only)

#### Skill 4: `/bug-predict`

- **Source:** `src/attune/workflows/bug_predict.py`
- **Agents:** pattern scanner, complexity analyzer,
  history reviewer
- **Key feature:** Predicts likely bug locations based on
  code patterns and complexity
- **Arguments:** `<path>` (default: `.`)

#### Skill 5: `/doc-gen`

- **Source:** `src/attune/workflows/document_gen/workflow.py`
- **Agents:** API documenter, README generator, docstring auditor
- **Key feature:** Generates and maintains documentation
  automatically
- **Arguments:** `<path>`, `--type` (readme, api, module)

### Phase 3: Add Commands

Create slash commands that map to each skill with argument
parsing. Commands are the user-facing entry points;
skills provide the orchestration prompts.

### Phase 4: Polish & Submit

1. Review all skill prompts for clarity and completeness
2. Test each command end-to-end in Claude Code
3. Verify plugin.json is valid
4. Write submission description
5. Submit to Anthropic plugin library

## Key Design Decisions

### Self-contained prompts, not Python wrappers

Each skill is a markdown file with agent orchestration
instructions baked into the prompt. Claude Code executes
them natively — no `pip install`, no subprocess calls,
no external dependencies.

### Model routing via prompt guidance, not code

Instead of `model=get_subagent_model("security")` in
Python, the skill prompt says: "For the security review
agent, prioritize depth and thoroughness over speed."
Claude Code's own model selection handles the rest.

### Budget awareness via prompt scoping, not max_budget_usd

Instead of `max_budget_usd=2.00`, the skill prompt
scopes the analysis: "Focus on the top 10 most critical
findings rather than exhaustive coverage." This achieves
the same goal (bounded cost) without SDK parameters.

### Structured output via prompt formatting, not JSON schema

Instead of `output_format=WORKFLOW_OUTPUT_SCHEMA`, the
skill prompt specifies: "Present findings as a markdown
table with columns: File, Line, Severity, Description."
The output is structured for humans, not machines.

## What This Is NOT

- Not a replacement for attune-ai on PyPI
- Not a deletion of any existing workflows
- Not a rewrite of the SDK integration work
- Not dependent on attune-ai being installed

## Relationship to attune-ai

```
attune-ai (PyPI)          attune-plugin (Plugin Library)
├── 15 SDK workflows      ├── 5 prompt-based skills
├── CLI                   ├── 5 slash commands
├── Memory/orchestration  ├── plugin.json
├── Wizards               └── README.md
└── Full framework
```

The plugin is a curated window into attune-ai's best
ideas, implemented as native Claude Code prompts. Users
who want more can install the full package.

## Next Steps

- [ ] Read existing accepted plugins for format/style
      reference
- [ ] Create `attune-plugin/` directory with scaffold
- [ ] Extract code-review skill from workflow source
- [ ] Extract security-audit skill from workflow source
- [ ] Extract smart-test skill from workflow source
- [ ] Extract bug-predict skill from workflow source
- [ ] Extract doc-gen skill from workflow source
- [ ] Add slash commands with argument support
- [ ] Test all 5 commands in Claude Code
- [ ] Write submission-ready README
- [ ] Submit to Anthropic

## Open Questions

- What name for the plugin? `attune`, `attune-workflows`,
  `attune-dev`?
- Should the plugin reference attune-ai PyPI as an
  "upgrade path" in its README, or keep them decoupled?
- Are there plugin library guidelines or review criteria
  we can find to align with?
