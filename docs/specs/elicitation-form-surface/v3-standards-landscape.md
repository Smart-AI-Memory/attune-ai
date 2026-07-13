# Elicitation v3 — standards landscape and the factory verdict

**Status:** research memo (2026-07-13) — 26-agent verified sweep
(6 standards researched from primary sources, top claims
adversarially checked; grammar-as-built reviewed from repo).
**Constraints honored (ratified 2026-07-13):** projector-not-
platform; adapters-not-foundations.

---

## The verdict first: the factory already exists

The grammar review found the single-source pattern is ALREADY the
architecture: one `FormSchema` master (`attune.meta_workflows.models`,
built via `form_from_dict`) projects to three render targets today —
`form_to_widget_html` (show_widget), `form_to_elicitation_schema`
(MCP native), and the AskUserQuestion mapping — all validated
through the one `collect_form_response` seam (R4), zero API calls.

So "build a widgets/agents factory" resolves to: **recognize
FormSchema as the master, and add standards adapters as new
projection targets.** No new subsystem. The opportunity is which
targets to add, and one correction to v3.

## Correction to v3-construct-protocol (from the grammar review)

The shipped widget postback already has a sentinel channel:
`__elicitation_response__`-marked fenced JSON through `sendPrompt`,
parsed by `elicitation_collect_response`. The v3 construct-response
envelope must EXTEND this channel (same sentinel family, add
`action`/instance fields), not introduce a parallel
`construct-response` prefix. One reply channel, one validator —
R4 discipline holds.

## The landscape (primary-source, verified)

| Standard | State | Projection fit |
|---|---|---|
| **MCP Apps** (`io.modelcontextprotocol/ui`, ex SEP-1865) | **Stable official MCP extension 2026-01-26**, co-developed by Anthropic + OpenAI; Claude ships it on web/desktop/mobile/Cowork, all plans | **Tier 1 — the adapter to build.** Widgets are pre-declared MCP resources (`ui://` URIs, `text/html;profile=mcp-app`), tools link via `_meta.ui.resourceUri`, round-trip via `tools/call` from the iframe. attune already ships an MCP server: registering `ui://attune/<construct>` resources projects the whole grammar into every MCP Apps host |
| **OpenAI Apps SDK** (ChatGPT apps) | Preview Oct 2025 → converged ON MCP Apps (same `ui://` + profile); app directory live | **Free-rider on the Tier-1 adapter** — one generic construct-renderer template reaches ChatGPT too |
| **MCP elicitation** (`elicitation/create`) | Spec 2025-11-25 added multi-select (oneOf/anyOf-const), defaults, URL mode — the gaps D8/D10 hit are partially fixed at SPEC level; Claude Code still auto-declines (D10 stands locally) | Tier 2 — lossy flat-form fallback target; the `form_to_elicitation_schema` projector already emits it. Re-test per host as clients catch up |
| **AG-UI** (CopilotKit) | Adopted agent-to-UI event protocol | Tier 2 — near-1:1: construct → `Tool` entry (fields as JSON Schema) in `RunAgentInput.tools`; build when a consumer exists |
| **Google A2A** (Linux Foundation, v1.0.1) | Big-vendor backing; **no UI story** — elicitation = `TASK_STATE_INPUT_REQUIRED` lifecycle | Tier 3 — lifecycle mapping only; park until an A2A consumer is real |
| **Adaptive Cards** (v1.5/1.6) | The 10-year prior art for portable widget grammars | Not a target — a design teacher: closed element catalogs + host-config adaptation + semantic (not pixel) schemas are what survive hosts. Validates the FormSchema approach |

## The agent-factory half

Agent-definition formats are fragmented at runtime but convergent
at packaging: `{name, description, instructions, [tools], [model]}`
in markdown + YAML frontmatter — exactly the Claude Code
subagent/skill shape, now the **Agent Skills open standard**
(agentskills.io, created by Anthropic, ~40 adopting clients incl.
Codex, Copilot, Cursor, Gemini CLI). attune already authors
skills/agents in this shape; a factory that emits the convergent
tuple from a workflow/construct definition is a small projector,
not a platform. No standard carries a form schema — the grammar
remains differentiating IP that projects INTO these containers.

## Recommended sequence (post-freeze; design-only until 07-28)

1. **v3 envelope correction** — extend the shipped sentinel channel
   (this memo's correction section) in the protocol doc. Free.
2. **MCP Apps adapter** — `ui://attune/<construct>` resources on
   the existing MCP server; one generic construct renderer,
   grammar-driven. Reaches Claude (all surfaces) + ChatGPT with
   one artifact. This is the widgets factory shipping as ~one
   module + resources, replacing nothing and adding no family.
3. **Skills projector** — emit Agent Skills-standard SKILL.md from
   construct/workflow definitions where a real consumer exists.
4. Re-test MCP elicitation per host quarterly (D10 is a host
   behavior, not a spec limit anymore); AG-UI/A2A stay parked
   until a consumer names itself.

Full per-standard findings with sources: workflow
`wf_c2de6139-e5a` journal (26 agents, verified claims noted
per-standard).
