# Template Refinement: Quality Pass

**Created:** 2026-03-30
**Source:** /plan feature
**Route:** feature
**Status:** pending

## Context

All 7 template types exist with 478 templates total.
The content is functional but has quality gaps: awkward
FAQ questions, generic Task steps, sparse Notes, and
cross-links only covering 4 of 7 types.

## Problem

Generated templates need a quality pass before they're
production-ready for the help system.

## Goals

- Natural FAQ questions that read like real user queries
- Specific Task steps parsed from SKILL.md body content
- More Notes from additional sources (README, docstrings)
- Full cross-linking across all 7 template types

## End State

- FAQs: natural questions, not "Why does {title}?"
- Tasks: specific steps with code examples from source
- Notes: 20+ from expanded sources
- Cross-links: all 7 types interconnected
- `generate_all.py --check` passes (8/8)

---

## Phase 1: Cross-Link All 7 Types

Extend `scripts/build_cross_links.py` to connect the
new types:

| Relationship | Derivation |
| ------------ | ---------- |
| FAQ -> Error | Same slug (same Lessons Learned entry) |
| Task -> Reference | Skill task -> skill reference by name |
| Task -> Tool | Extract tool calls from task code examples |
| Note -> Reference | Design decisions -> related features |
| FAQ -> Tip | Same prevented_by logic as Error -> Tip |

**Tasks:**

1. Add `_build_faq_error_links()` — match by slug
2. Add `_build_task_reference_links()` — match by
   skill/tool name in task source
3. Add `_build_note_reference_links()` — keyword match
4. Update `_build_tag_index()` to include all 7 types
5. Regenerate cross_links.json and verify

**Files:** `scripts/build_cross_links.py`

---

## Phase 2: FAQ Question Quality

Improve `scripts/generate_faq_templates.py` question
generation:

**Current:** Pattern-match title -> "Why does {title}?"
produces awkward questions like "Why does Shadow
directories at repo root break imports?"

**Improved approach:**

1. Clean the title: strip backticks, normalize case
2. Classify question type from content:
   - Error/crash patterns -> "Why do I get {error}?"
   - Configuration patterns -> "How do I configure {X}?"
   - Behavior patterns -> "Why does {X} happen?"
   - Best practice patterns -> "What's the best way
     to {X}?"
3. Extract the actual error signature (if present)
   and use it in the question
4. Improve answer formatting: separate explanation
   from fix steps more cleanly

**Tasks:**

1. Rewrite `_generate_question()` with smarter NLP
2. Add `_clean_title()` for backtick/case normalization
3. Improve `_build_answer()` to separate explanation
   from actionable fix
4. Strip trailing whitespace in code_example extraction
5. Regenerate and verify

**Files:** `scripts/generate_faq_templates.py`

---

## Phase 3: Task Content Depth

Improve `scripts/generate_task_templates.py` to parse
richer steps from SKILL.md:

**Current:** Generic steps ("Scope the X request",
"Execute the X workflow", "Review results").

**Improved approach:**

1. Parse numbered steps from Scoping section body
   (the `1. **Scope**: ...` patterns)
2. Extract multiple tool calls from Execution section
   (not just the first code block)
3. Parse Follow-Up options as named steps
4. Extract MCP Tools table as a "Tools Used" section
5. Add output format description to the results step

**Tasks:**

1. Rewrite `parse_skill_tasks()` with section-aware
   step extraction
2. Extract numbered items from Scoping as individual
   steps
3. Extract all code blocks from Execution (not just
   first)
4. Extract Follow-Up bullet points as named options
5. Regenerate and verify

**Files:** `scripts/generate_task_templates.py`

---

## Phase 4: Note Coverage Expansion

Add more sources to `scripts/generate_note_templates.py`:

**Current:** 8 notes (2 architecture, 6 design decisions)
**Target:** 20+ notes

**New sources:**

| Source | Content | Est. |
| ------ | ------- | ---- |
| Socratic rules in CLAUDE.md | Interaction philosophy | 1 |
| Critical rules in CLAUDE.md | Security/coding rules | 1 |
| Code simplification in CLAUDE.md | Engineering philosophy | 1 |
| Markdown formatting in CLAUDE.md | Formatting standards | 1 |
| Workflow base class docstrings | How workflows work | 2-3 |
| CLI welcome text | Quick-start orientation | 1 |
| Terms table fix | Fix regex to match format | 10+ |

**Tasks:**

1. Fix `parse_terms()` regex (currently returns 0)
2. Add `parse_claude_md_sections()` for Socratic,
   Critical Rules, Code Simplification, Markdown
3. Add `parse_readme_notes()` for key README sections
4. Regenerate and verify 20+ notes

**Files:** `scripts/generate_note_templates.py`

---

## Implementation Order

Phase 1: Cross-links (30 min) ->
Phase 2: FAQ quality (30 min) ->
Phase 3: Task depth (30 min) ->
Phase 4: Note coverage (30 min) ->
Final: regenerate all, verify, commit

Each phase is independently committable.

## Verification

After each phase:

- `generate_all.py --check` passes (8/8)
- Spot-check 2-3 templates per type
- Cross-links.json reflects new relationships

## Open Questions

None.
