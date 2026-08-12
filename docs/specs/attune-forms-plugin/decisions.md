# attune-forms Plugin & Beta — Decisions

## D1 — Announcement gate + build order ratified (chair, 2026-08-12, in-discussion)

Ruled in the plugin discussion hours after the extraction shipped
(attune-ai #2058; PyPI attune-forms 0.1.0):

1. **The beta announcement is GATED on two ships:** the
   communication-grammar article publishing, and the plugin itself.
   The chair accepted the lead's timing pushback unprompted — the
   library was a day old with one consumer; announcing before the
   story (article) and the install path (plugin) exist wastes the
   launch. Chair's words: "I agree with your pushback on timing. I
   will announce the beta after we publish the article on the grammar
   as well as this library/plugin."
2. **Build order:** de-attune the config surface (0.2.0) → standalone
   MCP server (`[mcp]` extra) → plugin wrapper → marketplace
   submission. Nothing public ever sees the attune-branded config.
3. **Overlap boundary:** attune-forms ships the GENERIC skill;
   attune-ai's plugin keeps only its attune-specific intakes layered
   on top — mirroring the code split of the extraction.

Counter-case carried per D11d (COUNTER-CASE): the strongest argument
against the gate is momentum — the extraction is fresh, the demo
material (this very session's forms) is at hand, and a delayed beta
risks the announcement never happening. The chair weighed this
implicitly in accepting the pushback; re-opening it requires a new
ruling, not drift.

Recorded same-day in memory (`project_attune_forms_plugin_roadmap`)
and phased into requirements.md (this spec).

## D2 — P1 naming ruled and executed (chair via decision form, 2026-08-12 evening)

Chair picked all three recommended names (widget decision form,
same session as D1): config `attune-forms.config.json`, env prefix
`ATTUNE_FORMS_` (`_KEYBOARD_MODE` / `_TELEMETRY` / `_HOME`), data
home = XDG state dir (`$XDG_STATE_HOME/attune-forms`, default
`~/.local/state/attune-forms`) with an EXISTING `~/.attune` honored.
Framing refinement accepted in-discussion: the phase is
COLLISION-proofing, not de-branding — the package is named
attune-forms, so package-branded names are the fix, not a leak.

**Write-target nuance (lead call, recorded for the R1.3 receipt):**
the fresh-write default in `set_keyboard_mode` stays the LEGACY
filename so attune-ai needs zero changes at 0.2.0 (its CLI test pins
`attune.config.json` creation); public surfaces (P2 MCP server, P3
skill) pin `config_name="attune-forms.config.json"` explicitly.
Flipping the library default is deferred until attune-ai pins its
own name.

**Executed same evening** (attune-forms #2, 0.2.0): read precedence
new > legacy > default; env new-wins; home resolution
`ATTUNE_FORMS_HOME` > `ATTUNE_HOME` > existing `~/.attune` > XDG;
16 precedence tests. Receipts: 376 attune-forms tests green;
attune-ai elicitation/mcp/telemetry/meta_workflows suites 1,962
green against 0.2.0 editable, unchanged.
