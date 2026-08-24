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

## D3 — P2 tool surface: mirror all four (chair via decision form, 2026-08-12 evening)

Chair picked the recommendation: the standalone server ships
attune-ai's four elicitation tools with identical names, schemas,
and result shapes — convergence stays a pure swap. Executed as
attune-forms #3 (0.3.0, published + endpoint-verified): `attune_forms
.mcp_server` + `attune-forms-mcp` console script under `[mcp]`,
pinned `mcp>=1.23,<2.0` (the 2.0 SDK removed the 1.x server API;
matching attune-ai's generation is deliberate). Receipt (R2.4):
non-mocked stdio round-trip — real subprocess, MCP handshake, all
four tools exercised; `elicitation_ask` degrades to
`action: "unsupported"` without an eliciting client.

## D4 — P3 skill approved and plugin shipped (chair, 2026-08-12 night)

Chair approved the generic `forms` skill text ("skill approved,
finish P3"). Shipped as attune-forms #4: skill + marketplace/plugin
manifests (attune-ai's proven `source: ./plugin` layout) +
`.mcp.json` launching `uvx --from 'attune-forms[mcp]'
attune-forms-mcp`. Receipts: trigger-phrase disjointness verified
against every attune-ai skill (zero overlap — R3.2); uvx live-fire
against PUBLISHED PyPI 0.3.0 (four tools listed, widget rendered
over live stdio — the plugin's exact launch command). The plugin is
installable now: `claude plugin marketplace add
Smart-AI-Memory/attune-forms` → `claude plugin install
attune-forms@attune-forms`. Remaining: Phase 4 (directory
submissions — chair names targets) and the beta announcement,
still gated on the grammar article (D1).

## D5 — Phase 4 go; README rewrite; submission preconditioned on attune-ai status check (chair via decision form, 2026-08-14)

Gate check: D1's both ships verified — article published 2026-08-13
(canonical URL in `reference_linkedin_communication_grammar_article`),
plugin shipped and cold-start-verified (D4). Chair ruled:

1. **Phase 4 GO.**
2. **R4.2 full rewrite:** README leads with the problem + grammar
   (article framing), plugin install first, library API second;
   attune-ai lineage demoted to a Provenance section. PyPI inherits.
3. **Submission target:** before submitting attune-forms to the
   Anthropic directory, check the stalled attune-ai submission.
   **Check executed same day (2026-08-14):** live catalog
   (claude-plugins-community, 2,281 plugins) contains attune-lite
   ONLY (07ae2ae91) — attune-ai still unlisted 39 days after the
   2026-07-06 Console submission. No public status surface exists;
   next move (Console status check / resubmit at current version) is
   the chair's. attune-forms submission decision follows that.
4. **Announcement: draft after submission** — the announcement cites
   the article + install path; it does NOT wait on directory approval.

Premise corrections applied to requirements.md same day: test count
358 → 384 (2026-08-14), CHANGELOG now exists (attune-forms #10).

## D6 — Phase 5 placement: template-bound forms (chair via pushback form, 2026-08-24)

Chair leaned "add it to the spec"; the lead pushed back on the slot
(Phase 4 is a distribution phase, announcement-gated and mid-flight)
and the chair adopted the pushback's recommendation: **new Phase 5**,
drafted now, executing after Phase 4's submission clears. Response
id resp-20260824-151530-5dc15ee6. Scope = R5.1–R5.4 (binding
convention, fused render call, authoring gate, authoring preview),
with the form-events stage instrumentation (chipped the same day) as
the measurement dependency. Standalone-spec alternative declined —
one roadmap artifact for the plugin.
