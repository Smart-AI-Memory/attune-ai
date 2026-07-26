# Dynamic Forms Demo — transcript and receipts

**Status:** template — fill after the capture; the honesty-gate
pass reviews this page alongside the cut. **Video:** dynamic
forms demo, main cut (~4 min), per
[DEMO_DYNAMIC_FORMS_script.md](DEMO_DYNAMIC_FORMS_script.md).
**Published URL:** _(YouTube link after upload)_

This page is the receipt surface the video points at: every
claim narrated on camera maps to something checkable — a live
command, a file in this repository, or a published release.
The `docs/` tree projects to attune-ai.dev automatically, so
this page is linkable from the YouTube description and the
article embed once it lands on `main`.

## Transcript

Verbatim narration per segment, corrected from auto-captions.
Timestamps match the final export, not the script's estimates.

### Cold open (0:00–0:30)

> _(paste corrected narration here)_

### One form (0:30–1:45)

> _(paste corrected narration here)_

### The pushback form (1:45–2:45)

> _(paste corrected narration here)_

### Dogfood (2:45–3:30)

> _(paste corrected narration here)_

### Close (3:30–4:00)

> _(paste corrected narration here)_

## Claims and receipts

| Claim (as narrated) | Receipt |
|---------------------|---------|
| Socratic discovery asks one question per turn by default | Live session shown on camera; the interaction rule is in the repo's `.claude/CLAUDE.md` (Socratic Interaction Rule) |
| `/elicit` batches the independent dimensions of a decision into one form | Rendered live by the installed plugin; skill source at `plugin/skills/elicit/` |
| The form never invents fields — dependent questions stay sequential, answered questions aren't re-asked | Batching-restraint rules narrated on screen; _(link the governing rule/spec section)_ |
| Forms are declarative data, validated in and out, served over MCP | `elicitation_render_form` / `elicitation_collect_response` MCP tools, listed by `list_capabilities` |
| Pushback renders as a one-click decision, reasoning on the record | Live pushback form shown on camera; construct documented in `.claude/rules/attune/communication-grammar.md` |
| Every chair ruling in this repo runs through these forms | The promotion-ruling form shown is from this week's roundtable work; _(link the promoted report)_ |
| Everything shown ships today | PyPI `attune-ai` 10.5.0 — https://pypi.org/project/attune-ai/ |

Rows marked with a placeholder must be resolved before publish —
an unresolved receipt fails the honesty gate.

## Capture provenance

- Recorded: _(date, machine, screen 1 / LG HDR 4K)_
- Plugin version live during capture: _(pip show attune-ai)_
- Takes archived: _(path of the copied `.screenstudio` bundles)_
