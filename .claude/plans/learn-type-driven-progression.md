# Learn: Type-Driven Progression

**Created:** 2026-03-31
**Source:** /brainstorm session

## Problem

Progressive help breaks down at the second "tell me more"
because the current model just shows more of the same
template (verbosity-based) instead of shifting to a
different *type* of help content.

## Goals

- Each depth level serves a fundamentally different
  template type (must-have)
- Context-aware entry point — post-workflow skips the
  overview (must-have)
- User can navigate forward ("tell me more") and back
  ("start from the beginning") (must-have)
- Core topics have distinct content at all three levels
  (must-have)
- Works for at least 5-10 topics at launch (nice-to-have)

## End State

For a core set of topics (starting with security-audit
as proof):

1. Cold `/learn security-audit` → concept overview
   ("what it does, when to use it")
2. "Tell me more" → procedural walkthrough ("run it like
   this, interpret results like that")
3. "Tell me more" again → full reference with cross-links
   and edge cases
4. Post-workflow `/learn security-audit` → starts at
   procedural (level 2), skipping the concept

## Approach

### 1. Define the three-level type mapping

| Level | Template Type | Purpose |
|-------|--------------|---------|
| 0 | Concept | "What is this?" — orienting overview |
| 1 | Task/Procedural | "How do I use this?" — steps, flags, interpretation |
| 2 | Reference | "Tell me everything" — full detail, cross-links, edge cases |

### 2. Update the help engine

- Modify `populate()` or add a new method that accepts
  a `level` parameter and maps it to the correct template
  type for the given topic
- Add context-awareness: accept optional `last_workflow`
  signal to determine starting level
- Support navigation: "go deeper" increments level,
  "start over" resets to 0

### 3. Create distinct content for proof topic

Write three genuinely different templates for
`security-audit`:

- `con-tool-security-audit` (concept)
- `tas-tool-security-audit` (task/procedural)
- `ref-tool-security-audit` (reference — may already
  exist)

### 4. Update the /learn skill

- Update SKILL.md to use the new type-driven progression
  instead of the current depth counter
- Document navigation commands ("tell me more", "start
  from the beginning")

### 5. Wire context-awareness

- The `help_lookup` MCP tool needs to accept an optional
  `context` parameter (e.g., last workflow run)
- Map context signals to starting levels

### 6. Test end-to-end

- Cold call → concept
- Repeat → procedural
- Repeat → reference
- Post-workflow call → procedural (skips concept)
- "Start from the beginning" → resets to concept

## Next Steps

- [ ] Audit existing template types — which map to
      concept/task/reference?
- [ ] Write three distinct security-audit templates
- [ ] Update engine.py with level-to-type routing
- [ ] Update help_lookup MCP tool with context parameter
- [ ] Update /learn skill
- [ ] Test the full progression end-to-end
- [ ] Extend to 4 more topics

## Open Questions

- Should the level indicator be visible to the user?
  (e.g., "concept view" / "procedural view" / "reference")
- How does this interact with the existing 540 templates?
  Are most of them one type, or spread across types?
- Should "go back" be an explicit command or just re-call
  with a flag?
