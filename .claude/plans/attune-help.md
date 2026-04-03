# attune-help: Lightweight Help Runtime Package

**Created:** 2026-04-02
**Updated:** 2026-04-02
**Source:** /brainstorm sessions (2)
**Status:** Planning

## Problem

Developers follow coding conventions (Google docstrings,
type hints, YAML frontmatter, class attributes, CLI help
strings) that already contain their documentation — they
just don't know it pays off as living docs. And shipping
the full `attune-ai` authoring toolkit to end users is
overkill when they only need the help runtime.

## Goals

- **Must-have:** `attune-help` package — lightweight
  runtime-only help engine for AI apps
- **Must-have:** `attune-ai` remains the authoring and
  maintenance tool (full toolkit)
- **Must-have:** 7-phase iterative pipeline with template
  refinement and discovery
- **Must-have:** Refinement agents review accuracy,
  completeness, style, tone — suggest improvements
- **Must-have:** Conditional human quality gate with diff
  for structural/meaning changes
- **Must-have:** Discovery agents surface new template
  opportunities as a separate phase
- **Must-have:** User-facing workflow orchestrating the
  iterative loop
- **Must-have:** Blog series: articles 1-5 (architecture)
  + articles 6+ (build tutorials)
- **Must-have:** Build prototype locally first, write
  tutorials from real experience

## End State

### attune-help package

A pip-installable package containing only:

- **Help engine** — template loader, topic resolution
- **Progressive depth** — concept -> task -> reference
  escalation with session state
- **Storage protocol** — `get_session(user_id)` /
  `set_session(user_id, state)` interface with default
  local file implementation (extensible to Redis, DB,
  etc.)
- **Templates** — bundled in package at build time, with
  optional external directory override (Flask pattern:
  external wins when present, bundled is fallback)
- **Renderers** — all shipped (plain markdown, CLI/rich,
  Claude Code, marketplace). Default: plain markdown.
  App chooses via `renderer="cli"` at init. Auto-detect
  available as `renderer="auto"` but opt-in only.

**Explicitly excluded** (stays in attune-ai):

- 18 multi-agent workflows
- 38 MCP tools (except help_lookup)
- Security hooks
- Agent orchestration
- CLI commands
- Cost tracking / telemetry

### 7-Phase Iterative Pipeline

The pipeline is a loop, not a linear sequence. Each
iteration the knowledge base gets more complete and
more polished. The human quality gate is the checkpoint
that decides when to stop.

```
detect → map → regenerate → refine → discover → rebuild → validate
  ^                                                          |
  |__________ iterate until knowledge base converges ________|
```

**Phase 1: Detect** — SHA-256 hash comparison against
source manifest. Find stale templates. No LLM calls.

**Phase 2: Map** — Identify all template types affected
by changed sources. One source can produce many
templates.

**Phase 3: Regenerate** — Produce new templates from
code sources. Immediate or batch (50% cost via Anthropic
Batch API). Priority queue: low-confidence first, then
high-usage, then by age.

**Phase 4: Refine** (NEW) — Agents review generated
templates for:

- Accuracy — does the content match the source code?
- Completeness — are all sections populated?
- Style — consistent voice, formatting, conventions?
- Tone — appropriate for the template type?
- Improvements — agents suggest rewrites, not just flags

Quality gate rules:

- Trivial changes (typos, formatting, minor wording)
  auto-approve
- Structural changes (paragraph restructuring, emphasis
  shifts) require human review
- Meaning changes (different resolution steps, changed
  recommendations) always require human review
- Diff view shows what changed and why for all flagged
  templates

**Phase 5: Discover** (NEW) — Separate phase, runs after
refine. Agents analyze the refined template set and
surface:

- Missing templates (error with no matching
  troubleshooting, concept with no task)
- Consolidation opportunities (three FAQs that should be
  one comparison)
- New template types suggested by code sources that
  aren't covered yet
- Gap analysis across the 11 types

Discovered templates feed back into regenerate on the
next iteration of the loop.

**Phase 6: Rebuild** — Cross-links, tag index, workflow
map. Seven deterministic link rules.

**Phase 7: Validate** — Generators run in check mode.
Pre-commit hook integration.

### Developer workflow

1. Developer installs `attune-ai` during development
2. Writes code with Google docstrings, type hints,
   frontmatter, class attributes
3. Runs the 7-phase pipeline (orchestrated by a
   user-facing workflow)
4. Reviews flagged templates at the human quality gate
5. Iterates until the knowledge base converges
6. Ships `attune-help` as a dependency in their app
7. End users get progressive depth, audience adaptation,
   "tell me more" — without the authoring toolkit

### Blog series

**Architecture (articles 1-5, drafted):**

1. We Built a Help System That Maintains Itself
2. Your Code Is Already the Documentation
3. 11 Template Types That Turn Code Into a Help System
4. Help That Knows Who's Reading and What's Coming
5. A Knowledge Base That Maintains Itself

**Tutorials (articles 6+, planned):**

6. Building attune-help: extracting the runtime
7. The refinement phase: agents as quality reviewers
8. The discovery phase: finding what's missing
9. The iterative loop: orchestrating convergence
10. Shipping a help system as a lightweight dependency

Series arc: author with `attune-ai`, ship with
`attune-help`. Tutorials written from real build
experience.

## Approach

### Phase 1: Articles 1-5 (DONE)

All five architecture articles drafted (LinkedIn +
Discord versions).

### Phase 2: Local prototype

1. Build `attune-help` locally — extract runtime modules
2. Define storage protocol interface
3. Define renderer selection API
4. Implement template bundling + override mechanism
5. Run locally, shake out problems

### Phase 3: Refinement phase

1. Design refinement agent prompts (accuracy,
   completeness, style, tone)
2. Implement trivial vs significant change detection
3. Build diff view for human quality gate
4. Define auto-approve vs review-required thresholds
5. Test on real templates

### Phase 4: Discovery phase

1. Design discovery agent prompts (gap analysis,
   consolidation, new template opportunities)
2. Implement gap detection across 11 template types
3. Feed discovered templates back into regenerate loop
4. Test on real template set

### Phase 5: Iterative workflow

1. Build user-facing workflow orchestrating the 7-phase
   loop
2. Human quality gate as iteration checkpoint
3. Convergence detection (no more stale, no more gaps)
4. Tutorial articles written from the build experience

### Phase 6: Tutorial articles (6-10)

1. Write from real prototype experience
2. Each article covers one phase of the build
3. Include real problems encountered and solutions

## Open Questions

- Package name: `attune-help` or something else?
- Should `attune-help` include `help_lookup` as an MCP
  tool, or only expose a Python API?
- What's the minimum Python version for `attune-help`?
  (attune-ai requires 3.10+)
- License: same Apache 2.0?
- Mono-repo or separate repo?
- How does the refinement agent determine "trivial" vs
  "structural"? Token diff count? AST comparison of
  markdown sections? LLM classification?
- Should discovery suggestions auto-generate templates
  or just produce a proposal list for human approval?
- What's the convergence criterion for the loop? Zero
  stale + zero gaps? Human says "good enough"?

## Next Steps

- [x] Draft blog articles 1-5
- [ ] Build attune-help prototype locally
- [ ] Design refinement agent prompts
- [ ] Design discovery agent prompts
- [ ] Implement human quality gate with diff
- [ ] Build iterative workflow
- [ ] Draft tutorial articles 6-10
