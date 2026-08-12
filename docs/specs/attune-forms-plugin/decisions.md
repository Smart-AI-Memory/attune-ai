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
