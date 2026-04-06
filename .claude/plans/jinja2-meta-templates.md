# Jinja2 Meta Templates for Help System

**Created:** 2026-04-05
**Source:** /brainstorm session
**Status:** Ready

## Problem

Template structure is hardcoded in Python string-building
functions (`_render_concept()`, `_render_task()`,
`_render_reference()` in `src/attune/help/generator.py`).
Generated content is generic filler ("This feature provides
X functionality for the project"). Improving content quality
requires editing Python code.

## Goals

- Extract template structure into Jinja2 `.j2` files
- Follow Google's developer documentation style guide
  - Concepts: noun phrase headings, what/when/why
  - Tasks: bare infinitive headings, numbered steps,
    imperative verbs
  - Reference: full API surface, tables, edge cases
- Add an LLM polish pass after Jinja2 rendering to
  check writing style and accuracy against source code
- Regenerate all existing feature templates

## End State

- Three Jinja2 meta templates in a dedicated directory
  produce well-structured, Google-style documentation
- `generator.py` loads and renders via Jinja2 instead of
  inline string building
- Every generated template goes through an automatic LLM
  polish pass (style, tone, accuracy) before being written
- Tech writers or programmers can manually edit the output
  (status: manual templates are preserved)
- All 14 existing features regenerated with new templates
- `jinja2` added as a project dependency

## Approach

### 1. Add Jinja2 dependency

- Add `jinja2>=3.1.0` to `pyproject.toml` dependencies
- Verify it doesn't conflict with existing deps

### 2. Create meta template directory and files

Defaults ship in: `src/attune/help/meta_templates/`
Copied to project during `/coach init`:
`.help/meta_templates/`

`generator.py` resolves templates with:

1. Project's `.help/meta_templates/` (if exists)
2. Fallback to package defaults in `src/attune/help/`

This lets teams customize structure while new projects
get sensible defaults.

- `concept.md.j2` — Google conceptual style
  - `# {Feature Title}` (noun phrase)
  - `## What` — description from manifest + module
    docstrings
  - `## When to use` — guidance on when this feature
    applies
  - `## Key components` — classes/functions with one-line
    descriptions
  - `## Related` — tags and cross-references

- `task.md.j2` — Google procedural style
  - `# Run {feature}` (bare infinitive)
  - `## Prerequisites` — what you need before starting
  - `## Steps` — numbered, imperative, one action per step
  - `## Key files` — where to look and modify
  - `## Common modifications` — functions to extend

- `reference.md.j2` — Google reference style
  - `# {Feature Title} Reference` (noun phrase)
  - `## Classes` — table: name, description, file
  - `## Functions` — table: name, description, file
  - `## Configuration` — config keys and defaults
  - `## Source files` — glob patterns
  - `## Tags` — feature tags

### 3. Update generator.py

- Load Jinja2 environment from `meta_templates/` dir
- Replace `_render_concept()`, `_render_task()`,
  `_render_reference()` with single
  `_render_via_jinja(depth, feature, source_info)` call
- Keep `_extract_source_info()` as-is — it feeds the
  template context
- Keep frontmatter generation in Python (not in the
  template) for consistency

### 4. Add LLM polish pass

- New function: `_polish_template(content, feature,
  source_info)` in generator.py (or a new `polish.py`)
- Runs after Jinja2 render, before writing to disk
- Prompt: "You are a technical writer following Google's
  developer documentation style guide. Polish this help
  template. Fix generic filler, verify accuracy against
  the provided source info, maintain the section
  structure. Return only the improved markdown."
- Uses subscription-first routing (existing model
  infrastructure)
- Automatic — no opt-in flag needed
- Errors in polish pass should fall back to the Jinja2
  output (don't block generation)

### 5. Regenerate all feature templates

- Run `generate_feature_templates()` for all 14 features
  in `.help/features.yaml`
- Verify output quality on 2-3 features manually
- Commit the regenerated templates

### 6. Update attune-help package

- If meta templates or template format changed in ways
  that affect the runtime, update
  `packages/attune-help/` accordingly
- Bump version if needed

## Design Principle: Help Where You Are

The preamble is not just a skill feature — it is the
entry point to a universal contextual help layer.
Anywhere a feature name appears, the preamble answers
"what is that?" without the user leaving their current
workflow.

**Progressive depth stack:**

| Depth | Content | Access |
|-------|---------|--------|
| Preamble | One-liner when/why | Always visible |
| Concept | What/when/why | "tell me more" |
| Task | Step-by-step | "tell me more" |
| Reference | Full API surface | "tell me more" |

**Apply preambles to:**

- `/coach status` — feature staleness table
- `/coach init` — proposed features list
- Template regeneration output
- Error messages that name a feature
- Any UI or report that enumerates features

## Decisions

- **Polish pass runs on all regeneration** — both
  initial generation and maintenance (`/coach maintain`,
  `help_update`).
- **`.j2` files are copied into the project's `.help/`
  during `/coach init`** — `attune-ai` ships the default
  meta templates as a starting point. The project owns
  them after scaffolding, so teams can customize structure
  for their audience. `/coach maintain` can detect when
  `attune-ai` ships newer meta templates and suggest
  updating (like staleness detection for source files).

### 7. Context-sensitive help preamble

When a user invokes a workflow skill (e.g. `/security`),
show the task template's opening line as a preamble
before the Socratic scoping questions. The user can
answer to proceed, or say "tell me more" to get the
full procedural and reference topics.

**Data source:** first non-frontmatter paragraph of
`.help/templates/<feature>/task.md` — the "Use X
when..." line.

**Implementation:**

- Add `get_preamble(feature_name)` to the help engine
  that reads the task template and returns the opening
  line
- Add MCP tool or extend `help_lookup` with a
  `mode="preamble"` that returns just the one-liner
- Update workflow skills (security, code-quality,
  smart-test, etc.) to call preamble before scoping
- User says "tell me more" → progressive depth kicks
  in at task level (skip concept, already contextual)

## Next Steps

- [x] Add `jinja2` dependency to `pyproject.toml`
- [x] Create `src/attune/help/meta_templates/` with
      three `.j2` files
- [x] Refactor `generator.py` to use Jinja2 renderer
- [x] Implement LLM polish pass
- [x] Regenerate all feature templates
- [x] Run tests, verify output quality
- [ ] Wire context-sensitive preamble into workflow
      skills
- [ ] Update `attune-help` package if needed
