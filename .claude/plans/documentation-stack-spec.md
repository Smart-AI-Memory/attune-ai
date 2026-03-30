# Documentation Stack Spec

**Status:** Draft
**Author:** Patrick Roebuck
**Created:** 2026-03-29
**Audience:** Claude Code users, agentskills.io marketplace

---

## Vision

A 21st century documentation stack where AI generates,
maintains, and delivers help content — not as static
pages, but as typed templates that adapt to context,
audience, and moment. The user never reads a manual.
The right answer surfaces at the right time.

**Core principles (derived from the sync paradigm):**

1. **No hand-holding, just smart output** — understand
   the source context, apply rules, produce the right
   result. No wizard dialogs, no 20-question flows.
2. **One source of truth, multiple intelligent outputs**
   — a single canonical source transforms for different
   consumers (Claude Code interactive vs marketplace
   discoverable).

---

## Exhibit A: The Sync Script

`scripts/sync_agents_skills.py` is the first concrete
implementation of this philosophy. It demonstrates:

| Principle | How sync implements it |
| --------- | --------------------- |
| Context-aware transformation | Reads Claude Code plugin skills, strips platform-specific fields, outputs agentskills.io format |
| Validation without user input | Enforces naming rules, field allowlists, directory conventions automatically |
| One source, two consumers | `plugin/skills/` serves Claude Code; `.agents/skills/` serves marketplace |
| Idempotent correctness | `--check` mode verifies sync state; generate mode produces identical output every run |

This is not a build tool. It is the prototype for every
feature in this spec. Each new feature follows the same
pattern: understand context, apply intelligence,
deliver the right output.

---

## Template Taxonomy

All documentation content is typed into templates. Each
template has a defined structure and purpose. AI
populates them from code analysis, error patterns, and
usage telemetry.

### Template Types

#### Task

Procedural content for completing a goal.

```text
Structure:
  1. Introductory text — sets context for why and when
  2. Steps — ordered (sequential procedure) or
     unordered (independent actions)
  3. Related Topics — cross-links to other templates
```

**Example:** "Set up MCP server for attune-ai"

- Intro: When to configure MCP, prerequisites
- Steps: install, configure `.mcp.json`, verify
- Related: Reference (MCP tool list), Tip (workspace
  root configuration), Error (common MCP failures)

#### Reference

Factual, structured information. API docs, config
options, command signatures, tool schemas.

```text
Structure:
  1. Name and purpose
  2. Parameters / fields / options
  3. Return values / output format
  4. Related Topics
```

**Example:** "attune workflow run" command reference

#### FAQ

Question-answer pairs. Dynamically maintained from
support patterns, error frequency, and user queries.

```text
Structure:
  1. Question (natural language)
  2. Answer (concise, actionable)
  3. Related Topics
```

**Example:** "Why does `attune doctor` say MCP is
unavailable?" -> Answer + link to Task (MCP setup)

#### Warning

Caution notices for actions with consequences.

```text
Structure:
  1. Condition — when this warning applies
  2. Risk — what can go wrong
  3. Mitigation — how to avoid or recover
  4. Related Topics
```

**Example:** "Changing skill names breaks marketplace
references" -> Risk: users can't find the skill ->
Mitigation: use deprecation alias

#### Error

Error pattern recognition and resolution. This is
where contextual help meets the template system.

```text
Structure:
  1. Error signature — regex or exact match
  2. Root cause — why this happens
  3. Resolution — step-by-step fix (embeds a Task)
  4. Related Topics
```

**Example:** `ModuleNotFoundError: attune.workflows`
-> Root cause: shadow directory at repo root ->
Resolution: remove `attune/` directory, reinstall

#### Tip

Best practices, shortcuts, and efficiency patterns.
Surfaced progressively based on usage (integrates with
`discovery.py`).

```text
Structure:
  1. Context — when this tip is relevant
  2. Recommendation — what to do
  3. Why — benefit or rationale
  4. Related Topics
```

**Example:** After 5 workflow runs -> "Use `/spec` to
chain brainstorm, plan, and execute in one flow"

#### Note

Supplementary information that enriches understanding
but isn't actionable on its own.

```text
Structure:
  1. Context — what this note relates to
  2. Content — the information
  3. Related Topics
```

**Example:** "The sync script strips `argument-hint`
because agentskills.io doesn't support Claude Code
frontmatter extensions"

### Related Topics

Every template includes a Related Topics section that
cross-links to other templates by type:

| Link type | Points to | When to use |
| --------- | --------- | ----------- |
| Reference | Reference template | User needs detailed specs |
| Task | Task template | User needs to do something |
| FAQ | FAQ template | Common follow-up question |
| Warning | Warning template | Action has consequences |
| Error | Error template | Known failure mode |
| Tip | Tip template | Efficiency improvement |
| Note | Note template | Background context |

**AI-powered linking:** Related Topics are generated
by analyzing code relationships, error co-occurrence,
and workflow transition patterns — not manually
authored.

---

## Feature 1: Smarter Contextual Help

**What exists today:**
[contextual.py](src/attune/patterns/contextual.py)
scores and filters bug/security patterns by file type,
error type, and recency.

**What changes:**

### 1a. Error Template Integration

Replace the flat pattern list with typed Error
templates. When a user hits an error, the system:

1. Matches the error signature against Error templates
2. Retrieves the resolution (which embeds a Task)
3. Cross-links to related Warning and Tip templates
4. Adapts output for Claude Code (interactive fix) vs
   marketplace (documentation page)

### 1b. Codebase-Aware Pattern Scoring

Current scoring uses file extension and error string.
Enhanced scoring adds:

- **Import graph proximity** — patterns from modules
  the current file imports score higher
- **Git blame recency** — patterns from recently
  changed code score higher
- **Workflow history** — if the user just ran
  `security-audit`, security-related Error templates
  score higher

### 1c. Resolution Confidence

Each Error template resolution carries a confidence
score:

- **Verified** — resolution has been confirmed by test
  or prior fix (from Lessons Learned)
- **Likely** — pattern matches a known root cause
- **Speculative** — AI-inferred, not yet validated

Display confidence to the user so they know how much
to trust the suggestion.

### Source of truth

Error templates are authored in a canonical format
(source). The sync paradigm generates:

- Claude Code output: inline contextual help with
  embedded fix steps
- Marketplace output: browsable error catalog with
  search

---

## Feature 2: Context-Aware Help

**What exists today:**
[discovery.py](src/attune/discovery.py) shows tips
after usage thresholds.
[suggestions.py](src/attune/workflows/suggestions.py)
suggests next steps after workflows.

**What changes:**

### 2a. Anticipatory Help

Instead of reacting to errors or thresholds, the
system anticipates needs:

- **File-open context** — when the user opens a test
  file, surface Tip templates about testing patterns
  for that module
- **Workflow chain prediction** — after `code-quality`,
  predict `smart-test` is likely next; pre-load
  relevant Task templates
- **Error precursors** — detect patterns that
  frequently precede errors (e.g., modifying a
  dataclass without updating its parser) and surface
  Warning templates before the error occurs

### 2b. Audience-Adaptive Delivery

Same content, different delivery:

| Audience | Delivery |
| -------- | -------- |
| Claude Code user | Inline in conversation — concise, actionable, with tool calls |
| Marketplace browser | Rendered documentation page with navigation and search |
| CLI user (`attune help`) | Terminal-formatted with color and links |

The template is the source. A transformer (following
the sync paradigm) produces the right output for each
consumer.

### 2c. Progressive Depth

Templates support progressive disclosure:

1. **Summary** — one-line answer (shown by default)
2. **Detail** — full explanation with steps
3. **Deep dive** — related references, edge cases,
   history

The system starts with Summary. If the user asks
follow-up questions or the context suggests confusion,
it escalates to Detail, then Deep dive.

---

## Feature 3: Intelligent Templates

**What exists today:** Nothing — templates are static
markdown files or hardcoded strings.

**What changes:**

### 3a. Template Engine

A template engine that:

1. Takes a template type (Task, Error, FAQ, etc.)
2. Accepts context parameters (file path, error
   message, workflow name, codebase state)
3. Produces populated content adapted to the audience

```text
Input:  template=Error, error="ModuleNotFoundError",
        file="src/attune/workflows/base.py",
        audience=claude_code
Output: Error template with resolution steps,
        confidence=Verified (matches Lessons Learned),
        related=[Task(fix imports), Tip(shadow dirs)]
```

### 3b. Template Generation from Code

AI generates templates by analyzing:

- **Lessons Learned** in CLAUDE.md -> Error + Warning
  templates
- **Skill descriptions** -> Reference templates
- **CLI help text** -> Task templates
- **Workflow output patterns** -> FAQ templates
- **Test failures** -> Error templates with verified
  resolutions

This is the sync paradigm applied broadly: code is
the source of truth, templates are the intelligent
output.

### 3c. Template Composition

Templates compose into larger structures:

- A **Task** can embed an **Error** (for common
  failure modes at specific steps)
- A **Reference** can embed **Tips** (for best
  practices alongside API docs)
- An **FAQ** answer can embed a **Task** (for "how
  do I..." questions)
- A **Warning** can embed a **Task** (for mitigation
  steps)

This composition is defined in the template schema,
not hardcoded — allowing AI to assemble documentation
dynamically.

---

## Graphics Strategy

### Phase 1: Text-First

All documentation starts as text-based templates.
This is the foundation — fast to generate, easy to
version, works in every delivery channel (terminal,
conversation, web).

### Phase 2: UI Component Graphics

When documentation references a UI component, surface
an associated graphic. Use cases:

| Context | Graphic type |
| ------- | ------------ |
| Task referencing a CLI command | Terminal screenshot or ASCII rendering of expected output |
| Task referencing a skill trigger | Annotated screenshot of the Claude Code conversation showing the trigger in action |
| Reference for MCP tool schema | Visual diagram of input/output flow |
| Error template | Screenshot of the error in context (IDE, terminal) with annotations |
| Cheat sheet (e.g. README skill table) | Visual card layout showing skill -> trigger -> result |

### Principles

- **Graphics are supplementary, not primary** — every
  graphic must have a text equivalent. Text is the
  source; the graphic is a rendered view.
- **Auto-generate where possible** — terminal output
  can be captured programmatically. Skill trigger
  examples can be rendered from the template registry.
  Manual screenshots are a last resort.
- **Audience-adaptive rendering** — Claude Code
  conversation: no graphics (text-only channel).
  Marketplace/web: graphics alongside text. CLI: ASCII
  art or omitted.

### Open: Tooling

Candidates for auto-generation:

- `asciinema` / `terminalizer` for CLI recordings
- `mermaid` for flow diagrams (renders in GitHub
  markdown and mkdocs)
- Playwright/Puppeteer for capturing web UI states
- SVG templates for annotated component diagrams

---

## Autogenerated Topics

> **Status:** TODO — architecture defined, generation
> rules to be specified in a follow-up session.

### Concept

An autogenerated topic is a complete help page
assembled by the template engine from code analysis,
without manual authoring. The system discovers what
needs documenting and produces it.

### How It Works

```text
Code/Registry -> Analyzer -> Template Selection
    -> Content Population -> Cross-linking -> Output
```

1. **Discovery** — scan a source (skill registry,
   workflow registry, CLI parser, MCP tool schemas,
   Lessons Learned)
2. **Template selection** — choose the right template
   type based on what was found (skill -> Reference,
   error pattern -> Error, CLI command -> Task)
3. **Population** — fill the template fields from the
   discovered data
4. **Cross-linking** — generate Related Topics by
   analyzing relationships (skill X calls workflow Y,
   error Z occurs in skill X)
5. **Output** — render for each audience via the sync
   paradigm transformers

### Autogeneration Sources

| Source | Produces | Template type |
| ------ | -------- | ------------- |
| `plugin/skills/*/SKILL.md` | Skill reference pages | Reference |
| `src/attune/workflows/` registry | Workflow reference pages | Reference |
| `src/attune/cli_minimal.py` argparse | CLI command docs | Task |
| `src/attune/mcp/tool_schemas.py` | MCP tool reference | Reference |
| Lessons Learned in CLAUDE.md | Error/Warning pages | Error, Warning |
| `discovery.py` tip definitions | Tip pages | Tip |
| Error frequency from telemetry | FAQ candidates | FAQ |
| README cheat sheet (13 skills) | Quick-start guide | Task |
| Workflow transition patterns | "What's next" guides | Tip |

### Example: Autogenerated Skill Reference

Given `plugin/skills/security-audit/SKILL.md`, the
system produces:

```text
Template: Reference
Name: security-audit
Purpose: (from description field)
Triggers: (from description's trigger keywords)
What it does: (from SKILL.md body, summarized)
MCP tools used: (grep SKILL.md for tool names,
    cross-reference tool_schemas.py)
Related Topics:
  - Task: "Run a security audit on your code"
  - FAQ: "What does the security score mean?"
  - Error: "MCP server not responding"
  - Tip: "Run security audit before /release"
  - Warning: "Audit scope defaults to cwd"
```

No manual authoring. The content and cross-links are
derived from code.

### Example: Autogenerated Error Topic

Given a Lessons Learned entry like "Shadow directories
at repo root break imports", the system produces:

```text
Template: Error
Signature: ModuleNotFoundError on attune submodules
Root cause: attune/ directory at repo root shadows
    the installed src/attune/ package
Resolution: (Task template)
  1. Check for rogue top-level directories
  2. Remove the shadow directory
  3. Reinstall: pip install -e .
Confidence: Verified (from Lessons Learned)
Related Topics:
  - Warning: "Prototyping directories can shadow
    installed packages"
  - Tip: "Always check for shadow dirs before
    debugging import errors"
```

### TODO: Generation Rules

To be defined in follow-up:

- Staleness detection — when source changes, flag
  autogenerated topics for regeneration
- Conflict resolution — when manual edits exist
  alongside autogenerated content
- Quality thresholds — minimum completeness before
  an autogenerated topic is surfaced to users
- Incremental generation — only regenerate topics
  whose sources changed (like sync's `--check` mode)

---

## Broader Roadmap: Documentation Stack

### Phase 1: Foundation (COMPLETE)

| Component | Status | Description |
| --------- | ------ | ----------- |
| Sync script | Done | Exhibit A — one source, two outputs |
| Template taxonomy | Done | 7 types defined (4 implemented) |
| Error templates | Done | 143 from Lessons Learned |
| Warning templates | Done | 102 from Lessons Learned (preventive) |
| Tip templates | Done | 16 from discovery + suggestions |
| Reference templates | Done | 44 from 13 skills + 31 tools |
| Shared utilities | Done | template_utils.py + generate_all.py |

**Total: 305 generated templates, 4 schemas, 4 Jinja2
templates, 6 scripts.**

### Phase 2: Intelligent Content (DESIGNED)

| Component | Status | Description |
| --------- | ------ | ----------- |
| Reference subtypes | Designed | Procedural, tabular, free-form |
| Cross-link index | Designed | Deterministic relationships between all 305 templates |
| Template engine | Designed | `src/attune/help/engine.py` — context in, populated template out |
| Audience transformers | Designed | Claude Code, marketplace, CLI renderers |
| CLI help command | Designed | `attune help [topic]` with search + tag filtering |
| Marketplace sync | Designed | `.agents/docs/` parallel to `.agents/skills/` |

### Phase 3: Anticipatory System

| Component | Description |
| --------- | ----------- |
| Error precursor detection | Warn before errors happen |
| Workflow chain prediction | Pre-load help for likely next actions |
| Progressive depth | Summary -> Detail -> Deep dive escalation |
| Template composition | Dynamic assembly of compound help content |

### Phase 4: Self-Maintaining

| Component | Description |
| --------- | ----------- |
| Stale content detection | Flag templates whose source code has changed |
| Coverage analysis | Identify undocumented errors, workflows, or features |
| Usage-driven priority | Surface most-needed content first based on telemetry |
| Feedback loop | User corrections update template confidence scores |

---

## Architecture

```text
Source of Truth
  |
  v
+-------------------+
| Template Registry  |  <-- Canonical templates (typed)
+-------------------+
  |
  +---> Sync Transformer ---> .agents/skills/ (marketplace)
  |
  +---> Claude Code Adapter ---> Inline conversation help
  |
  +---> CLI Adapter ---> Terminal-formatted help
  |
  +---> Search Index ---> Full-text search
  |
  +---> FAQ Generator ---> Dynamic FAQ from patterns
```

Each transformer follows the sync paradigm:

1. Read the source template
2. Apply context-specific rules
3. Validate the output
4. Deliver to the consumer

---

## Sync Paradigm Summary

Every feature in this stack follows the same pattern
that `sync_agents_skills.py` established:

| Step | Sync script | Documentation stack |
| ---- | ----------- | ------------------- |
| 1. Discover | Find `plugin/skills/*/SKILL.md` | Find templates in registry |
| 2. Parse | Extract frontmatter + body | Extract template type + content |
| 3. Transform | Strip Claude Code fields | Adapt for audience + context |
| 4. Validate | Name rules, field allowlist | Schema compliance, link integrity |
| 5. Output | Write to `.agents/skills/` | Deliver to consumer (conversation, page, terminal) |
| 6. Verify | `--check` mode | Stale content detection |

This is the design pattern. Every new documentation
feature is an instantiation of these six steps.

---

## Decisions

Resolved from design review (2026-03-29):

### D1. Template schemas live in the repo

Template schemas (the *structure*, not populated
content) are defined as files in `plugin/help/schemas/`:

```text
plugin/help/schemas/
  task.md
  reference.md
  faq.md
  warning.md
  error.md
  tip.md
  note.md
```

Each schema file uses YAML frontmatter for metadata
(type, required fields, optional fields) and markdown
body for the structural template. The AI engine reads
these schemas and fills them with content from code
analysis.

This mirrors how `plugin/skills/*/SKILL.md` defines
skill structure — schemas are the documentation
equivalent.

### D2. Search: index first, unified later

Start with a local index over generated template
content (practical, shippable). Evolve toward unified
knowledge search that also covers code, Lessons
Learned, and telemetry. The index is Phase 2; unified
search is Phase 4.

### D3. FAQ sourcing (four channels)

FAQs are sourced from:

1. **Unmatched user queries** — questions that don't
   match existing templates become FAQ candidates
2. **Repeated error patterns** — errors that appear
   frequently in telemetry get promoted to FAQ
3. **GitHub issues** — questions from issues/
   discussions feed the FAQ pipeline
4. **Author-curated** — the developer can associate
   FAQ entries with features manually when shipping
   new functionality

All four channels feed into FAQ templates. The engine
deduplicates and ranks by frequency.

### D4. Code is the source of truth

`contextual.py`, `discovery.py`, and `suggestions.py`
evolve into **consumers** of the template registry —
they don't get replaced, they get upgraded. Instead of
maintaining their own pattern lists and tip
definitions, they query autogenerated templates that
are derived from code.

The flow becomes:

```text
Code (source of truth)
  -> Template engine (autogenerates content)
    -> Template registry (stores typed templates)
      -> contextual.py (queries Error templates)
      -> discovery.py (queries Tip templates)
      -> suggestions.py (queries Task templates)
```

The existing modules keep their role (contextual
scoring, progressive discovery, post-workflow
suggestions) but their *data source* shifts from
hardcoded lists to the template registry.

### D5. Intelligent templates = the engine

Intelligent templates are the **engine** (context in,
populated template out). Autogenerated topics are a
**use case** of that engine (scan code, produce help
pages without manual authoring).

The engine is general-purpose. Autogenerated topics
are its first and primary application.

### D6. Proof of concept: Lessons Learned -> Error templates

**Status: DONE** (2026-03-29)

Built and validated. The pipeline:

```text
CLAUDE.md Lessons Learned (140 entries)
  -> parse_lessons_learned() extracts title + body
  -> lesson_to_template() populates ErrorTemplate
  -> Jinja2 renders via error.md.jinja2
  -> Output to plugin/help/generated/errors/
  -> --check mode verifies sync state
```

**Results:** 140 entries -> 140 Error templates, 0
failures. All templates have frontmatter (type, name,
confidence, tags, source), structured sections
(Signature, Root Cause, Resolution, Related Topics),
and auto-classified tags.

**Files created:**

- `plugin/help/schemas/error.md` — schema definition
- `plugin/help/templates/error.md.jinja2` — Jinja2
  render template
- `scripts/generate_error_templates.py` — generator
  (follows sync paradigm: discover, parse, transform,
  validate, output, verify)
- `plugin/help/generated/errors/*.md` — 140 generated
  Error templates

**Libraries used:**

- `jinja2` — template rendering (already in codebase,
  now declared in pyproject.toml)
- `python-frontmatter` — YAML frontmatter parsing
  (new dependency, for future schema reading)

**Key design choices:**

- Sentence splitting respects backtick-quoted code
  (e.g. `Path.read_text()` not split at the dot)
- Tag classification uses keyword matching across 10
  categories (ci, testing, security, imports, git,
  windows, macos, claude-code, packaging, python)
- Signature extraction prefers backtick-quoted error
  names (e.g. `ModuleNotFoundError`) over title text
- Resolution extraction finds Fix: markers and
  imperative sentences (Always, Never, Use, etc.)
- Related Topics auto-generated from content analysis
  (Warning for "avoid/never", Tip for "always/prefer")

---

## Remaining Open Questions

1. **Schema evolution** — when a template schema
   changes (e.g., Error gains a new field), how do we
   handle already-generated content? Regenerate all,
   or migrate incrementally?
2. **FAQ deduplication** — when the same question
   arrives from multiple channels (user query + GitHub
   issue), how do we merge them? Highest-frequency
   wins? Or keep both with different phrasings?
3. **Author-curated FAQ workflow** — what's the UX for
   a developer associating FAQ entries with a feature?
   A frontmatter field in the feature's PR? A CLI
   command? A skill?

---

## Success Criteria

### Phase 1 (ACHIEVED)

- 143 error templates from Lessons Learned (target
  was 80+)
- 102 warning templates with zero manual authoring
- 305 total templates across 4 types
- All generators pass `--check` mode

### Phase 2 (TARGET)

- Same template source produces correct output for all
  three audiences (Claude Code, marketplace, CLI)
- Skill references have procedural steps; tool
  references have parameter tables
- Cross-links connect Error <-> Warning, Skill <-> Tool
- `attune help` surfaces templates in the terminal
- `contextual.py` queries the template engine at
  runtime instead of hardcoded pattern lists

---

## Phase 2 Specification

### 2.1 Reference Subtypes

**Problem:** 44 Reference templates use one structure
for skills and tools, but these have fundamentally
different shapes.

**Solution:** Three Jinja2 subtemplates:

| Subtype | Structure | Sources |
| ------- | --------- | ------- |
| procedural | Intro + ordered steps | 13 skills |
| tabular | Description + param table | 31 tools |
| freeform | Paragraphs + sections | Future: concepts |

**Procedural** parses SKILL.md body sections (Scoping,
Execution, Output Format) into structured steps with
introductory context.

**Tabular** extracts parameters from `input_schema
.properties` in tool_schemas.py, preserving type,
description, default, and required flag.

**Free-form** is a schema-only placeholder for future
architecture docs and concept explanations.

**Auto-selection:** Generator picks subtype from source
path. `plugin/skills/` -> procedural, `tool_schemas.py`
-> tabular.

**Files:**

```text
plugin/help/templates/
  reference-procedural.md.jinja2  (new)
  reference-tabular.md.jinja2     (new)
  reference-freeform.md.jinja2    (new)
  reference.md.jinja2             (removed)
```

Update `scripts/generate_reference_templates.py` with
subtype dispatch.

---

### 2.2 Cross-Link Index

**Problem:** Related Topics say "None generated yet"
across most templates. Templates are disconnected.

**Solution:** Deterministic cross-link builder.

| Relationship | Derivation |
| ------------ | ---------- |
| Error <-> Warning | Same slug (same source entry) |
| Skill -> Tool | Grep SKILL.md body for tool names |
| Tool -> Skill | Inverse of above |
| Error -> Tip | 2+ non-stopword token overlap |
| All -> Tags | From classify_tags() |

**Output:** `plugin/help/generated/cross_links.json`

```json
{
  "links": {
    "err-windows-ci-encoding": {
      "related_warning": ["warn-windows-ci-encoding"],
      "prevented_by": ["tip-use-utf8"],
      "tags": ["encoding", "windows", "ci"]
    },
    "ref-security-audit": {
      "references_tools": ["security_audit"],
      "referenced_by_skills": ["security-audit"],
      "tags": ["security", "audit"]
    }
  },
  "tag_index": {
    "security": ["err-eval-exec", "ref-security-audit"]
  }
}
```

**Files:**

- `scripts/build_cross_links.py` (sync paradigm +
  `--check`)
- Update `scripts/generate_all.py`

---

### 2.3 Template Engine

**Problem:** Templates are static markdown. No runtime
adaptation for context or audience.

**Solution:** `src/attune/help/engine.py` — a runtime
module with pure-function API.

```python
@dataclass(frozen=True)
class TemplateContext:
    file_path: str | None = None
    error_message: str | None = None
    workflow_name: str | None = None

@dataclass(frozen=True)
class AudienceProfile:
    channel: str  # claude-code | marketplace | cli
    verbosity: str = "normal"

@dataclass(frozen=True)
class PopulatedTemplate:
    template_id: str
    type: str
    title: str
    body: str
    related: list[str]
    tags: list[str]

def populate(
    template_id: str,
    context: TemplateContext | None = None,
    audience: AudienceProfile | None = None,
) -> PopulatedTemplate: ...
```

**Pipeline:** load -> context fill -> cross-link
resolve -> audience adapt -> return.

**Audience adaptation rules:**

| Rule | Claude Code | Marketplace | CLI |
| ---- | ----------- | ----------- | --- |
| Max body | 500 chars | unlimited | 2000 |
| Tool hints | yes | no | no |
| Navigation | no | breadcrumbs | no |
| Related | inline | linked cards | numbered |

**Lives in `src/attune/`** so `contextual.py` can
import and use it at runtime. Generators stay in
`scripts/`.

---

### 2.4 Audience Transformers + CLI Help

**Problem:** No way to render templates for different
output channels.

**Solution:** Three render functions in
`src/attune/help/transformers.py`:

- `render_claude_code(t)` — concise MD, tool hints
- `render_marketplace(t)` — YAML frontmatter + full MD
- `render_cli(t)` — Rich panels + color

**Marketplace sync:**
`scripts/sync_docs_marketplace.py` writes to
`.agents/docs/` (parallel to `.agents/skills/`).
Follows sync_agents_skills.py pattern exactly.

**CLI integration:**

```bash
attune help                       # List categories
attune help errors                # List error templates
attune help err-windows-encoding  # Show specific
attune help --tag security        # Filter by tag
```

**Files:**

- `src/attune/help/transformers.py`
- `scripts/sync_docs_marketplace.py`
- `src/attune/cli_commands/help_commands.py`
- Update `src/attune/cli_minimal.py`

---

### 2.5 Implementation Order

```text
Step 1: Reference Subtypes (no deps)
    |
Step 2: Cross-Links (needs subtypes for skill->tool)
    |
Step 3: Template Engine (needs cross-links to resolve)
    |
Step 4: Audience Transformers + CLI (needs engine)
```

Each step is independently shippable and testable.

### 2.6 Design Decisions

- **Pure functions, not class hierarchies** — simpler
- **Deterministic cross-links, not LLM** — auditable,
  works in CI without API keys
- **Engine in src/attune/, generators in scripts/** —
  engine is runtime (contextual.py uses it), generators
  are build-time
- **Marketplace in `.agents/docs/`** — same repo,
  single `--check` flow, industry standard
- **Three Jinja2 templates, not conditionals** — each
  subtype has fundamentally different structure
