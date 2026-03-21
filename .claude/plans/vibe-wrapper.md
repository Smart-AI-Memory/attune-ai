# Vibe Wrapper — Unified Voice Layer for Attune AI

**Created:** 2026-03-21
**Source:** /brainstorm session

## Problem

Attune has 18+ workflows, 36 MCP tools, 5 wizards, and
multiple CLI commands — each producing output in its own
style. There's no consistent voice, tone, or personality
tying them together. It feels like a toolbox, not a
product. Users also get no guidance on what to do next
after a workflow completes.

## Goals

- **Must-have:** Single unified voice wrapping ALL output
  surfaces (workflows, MCP tools, CLI, errors)
- **Must-have:** Personality is a friendly senior engineer
  where empathy is natural, not performative
- **Must-have:** 1-3 contextual next steps at the end of
  each output (only when genuinely useful, no padding)
- **Must-have:** Spec-aware lifecycle — when an active
  spec exists, next steps follow the spec's stages
- **Must-have:** Retire `/pipeline`, absorb its lifecycle
  guidance into the wrapper
- **Nice-to-have (v2):** Configurable tone/verbosity

## End State

A user runs any attune workflow or tool. The output:

1. Speaks in one consistent voice — friendly senior
   engineer who naturally communicates with empathy
2. Presents findings clearly and directly
3. Ends with 1-3 contextual next steps based on what
   just happened and (if present) what the active spec
   says should come next
4. Feels like one product, not a collection of scripts

Testable: pick any two workflows, run them back to back.
The output should sound like the same person talking.
Run with and without an active spec — next steps should
adapt to lifecycle context.

## Architecture

**Location:** `src/attune/voice/`

A Python module that ALL output flows through before
reaching the user. This is the right layer because:

- A plugin/skill layer would miss MCP responses, direct
  CLI output, and error messages
- A Python module can be the single bottleneck for all
  output surfaces

### Proposed Package Structure

```text
src/attune/voice/
  __init__.py        # Public API: format_output()
  personality.py     # Voice constants, tone guidelines
  formatter.py       # Takes raw results, produces voiced
                     #   output with consistent structure
  next_steps.py      # Contextual next-step engine
  spec_context.py    # Reads active spec, maps lifecycle
                     #   stage to relevant suggestions
```

### Integration Points

Every output surface calls `voice.format_output()`:

- `workflows/base.py` — after `execute()` returns
- `mcp/server.py` — before returning tool results
- `cli_commands/*.py` — before printing to terminal
- Error handlers — wrap exceptions in voiced messages

### Next Steps Engine

The next-step engine considers:

1. **What just ran** — a code review suggests tests or
   commit; a security audit suggests fixing findings
2. **Active spec** (if any) — maps current stage to the
   next stage in the spec's lifecycle
3. **Recent history** (if available) — avoids suggesting
   what the user just did

Suggestions are phrased as the engineer would say them:
"I'd run the security audit on that auth module next"
not "Available commands: attune workflow run security-audit"

## Approach

1. **Create `src/attune/voice/` package** with
   personality constants and the formatter
2. **Build the next-steps engine** with workflow-to-
   suggestion mappings and spec awareness
3. **Integrate into workflow base** — wrap `execute()`
   output through the formatter (highest visibility,
   covers 18 workflows at once)
4. **Integrate into MCP server** — wrap tool responses
5. **Integrate into CLI commands** — wrap print output
6. **Retire `/pipeline`** — migrate any unique lifecycle
   logic into `spec_context.py`
7. **Add tests** — voice consistency tests, next-step
   relevance tests, spec-aware tests

## Open Questions

- Should the voice layer have access to telemetry (what
  workflows the user runs most) to personalize next-step
  suggestions?
- How should the wrapper handle streaming output from
  long-running workflows?
- What's the migration path for existing users who may
  have tooling that parses current raw output?
- Should `--json` mode bypass the voice layer entirely
  (likely yes — machine output stays structured)?

## Next Steps

- [ ] Design the `format_output()` API signature
- [ ] Write 3-5 before/after examples showing current
      output vs voiced output for key workflows
- [ ] Prototype `personality.py` with voice guidelines
- [ ] Build and test with one workflow before wiring all
