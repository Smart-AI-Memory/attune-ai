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

## D7 — Phase 5 unblocked: gate defined, execution ordered, server and home settled (chair via four-field form, 2026-09-05)

Prompted by a 69-agent independent read (three readers, 65 verified
claims each refutation-tested, one synthesis) run while the
adaptive-session-interactions T4 trial collects from live use. Its
recommendation was "Phase 5 after a one-paragraph D7, not a bare go";
the chair ruled all four items it named (response
`resp-20260905-173921-88eaed1e`).

1. **The D6 gate is SATISFIED by submission, not listing.** "Phase 4's
   submission clears" means the attune-forms Console submission has been
   MADE (the chair's own act, R4.1) — the same submission-vs-approval split
   D5 item 4 applies to the announcement. The chair chose to submit rather
   than waive. Until the Console act happens, Phase 5 execution below is
   authorized but the gate is recorded as pending the act; the 08-12
   submission pack is refreshed to 0.12.3 for it.
2. **Execution order: R5.3 → R5.2 → R5.4; R5.1 HELD** until the
   adaptive-session-interactions T4 record reaches its trigger (that
   spec's D11). Reason: R5.1 rewrites the Socratic rule and rebinds
   `plugin/skills/spec/SKILL.md`, which is the T2 guidance defining T4's
   Condition A under a frozen protocol; R5.2–R5.4 do not touch the
   workspace path. R5.3 goes first because it has no dependency on items
   3–4 and lands the cast-every-template gate every later template needs
   (codex lane finding 2). Note for R5.3: attune-forms' loader pops only
   `slots` and its definition parser rejects a top-level `example_slots`
   key, so R5.3 begins as an attune-forms change.
3. **R5.2's template+slots path lands in BOTH servers, schema-identical**
   (the D3 mirror rule): attune-forms' standalone server and attune-ai's
   `elicitation_render_widget` gain the same `template` + `slots`
   arguments and result shape; convergence stays a pure swap.
4. **R5.1 binds to `attune_forms.intake_template.TEMPLATES`** (the
   registry attune-ai already populates with its nineteen Python
   intakes), with `template_store`'s JSON entries FOLDED INTO it — one
   home, addressable by R5.2. The `/spec` name collision (spec_intake's
   "session contract" vs the store's `session-contract`) is resolved as
   part of that fold, not before.

Premise corrections applied the same day: the measurement dependency
named under Phase 5 shipped in attune-forms 0.8.0 (2026-08-24; installed
0.12.3 emits `form_build.source = template:<name>`); the live meter reads
117 dict builds against 0 template casts, which is the adoption gap Phase
5 exists to close. Counter-case retained: the gate rests on an external
queue that has already swallowed two attune-ai submissions; if the
Console act stalls, the chair may convert item 1 to a written waiver.

**Execution record (2026-09-05, lead):** R5.3 EXECUTED — attune-forms
#79 (`example_slots` on stored templates, `template_example_slots()`,
cast-every-template gate) MERGED on the chair's "merge 79 on green"
(squash `81d229e`, head `da8c26f` unmoved, 7/7 green). R5.2 EXECUTED —
attune-forms #80 (the standalone server) and the attune-ai mirror on
branch `claude/dynamic-ui-forms-2e776f`, schema-identical per item 3:
every form-taking tool takes `template` + `slots` through ONE shared
parse seam (exactly one of `form` / `template`, problems listed, never
raised; `collect_response` carries `template_id`). Scope note recorded
in both PRs: item 3 names `elicitation_render_widget`, but the seam is
shared by all four handlers and `collect_response` needs it or the agent
would still hold the form dict to validate answers. No skill or guidance
text changed — R5.1 stays HELD (item 2).
**Same evening:** #80 MERGED (`d5b0d1b`) and the mirror #2437 MERGED
(`7434fb5c5` head, squash on main) on the chair's "merge 80 and 2437".
R5.4 EXECUTED on the chair's "go 5.4" — attune-forms #81
(`attune_forms.preview`: every stored template cast with its
`example_slots` through the PRODUCTION `form_to_widget_html` into one
standalone page, light/dark host tokens, a `sendPrompt` stub showing the
posted payload, telemetry suppressed for preview casts; live-fire receipt
in the PR thread). Scope: `template_store` entries; the intake registry
becomes addressable when R5.1's fold lands. Phase 5 remaining: R5.1
(HELD), then a forms release carrying #79/#80/#81 and the attune-ai floor
bump that turns the `_template_props` parity test live.
