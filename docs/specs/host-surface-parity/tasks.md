# Host Surface Parity — Tasks

**Status:** active (2026-09-03) — Tasks 0–12 authored; each task
executes only behind its own chair go; a go on one task is not a
go on the next. D8 (2026-09-03) granted the 16.3 execution gos for
the ungated items: Task 2 (R1 tier 0), Task 4 (R4 receipt), Task
10 (R9 foundation) and Task 12 (D2 placement-label wiring). Task
11 (R10, adopted in D9) awaits its own execution go. Tasks 7 and 8
are additionally gated on release-16-manifest Phases A and B.

## Task 0 — Characterize the surfaces, roster and projector as they are

```xml
<task id="0" name="characterize-baseline">
  <objective>
    Pin current behavior before any change: which forms reach which
    Surface tier, the exact roster gates, and the projector's
    targets and refusal of hand edits.
  </objective>
  <files-to-create>
    <file path="tests/unit/elicitation/test_surface_tiers_characterization.py">
      One demo form rendered on RICH, PORTABLE, HEADLESS; identical
      validated output asserted.
    </file>
    <file path="tests/unit/roundtable/test_roster_characterization.py">
      CANONICAL_SEATS, SEAT_RECIPES, PLAN_ONLY_SEATS and the
      workspace round_complete roster check pinned byte-for-byte.
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="tests/unit/scripts/test_project_collaboration_contract.py">
      Pin a hand edit inside a valid projected block as stale.
    </file>
  </files-to-modify>
  <validation>
    <check>Both suites green on main with no production change.</check>
    <check>The projector suite refuses a hand edit inside the marked block.</check>
  </validation>
</task>
```

## Task 1 — Surface parity gate (R2)

```xml
<task id="1" name="surface-parity-gate">
  <depends-on>0</depends-on>
  <objective>
    Add the drift guard that fails when any RICH-tier renderer or
    host-specific hook/template lacks PORTABLE and HEADLESS twins
    and a three-render receipt. Land it green against the current
    tree, then it gates every later task.
  </objective>
  <files-to-create>
    <file path="tests/unit/gates/test_surface_parity.py" />
    <file path="docs/specs/host-surface-parity/receipts.md">
      Receipt ledger: one line per (form, RICH render, PORTABLE
      render, HEADLESS render, identical validated output).
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="content/collaboration/contract.md">
      Principle 1 gains "Enforcer (surfaces): tests/unit/gates/test_surface_parity.py"; re-run scripts/project_collaboration_contract.py.
    </file>
  </files-to-modify>
  <validation>
    <check>Gate green on main before any new renderer exists.</check>
    <check>Deleting one PORTABLE twin in a scratch branch makes the gate fail with the exact shortfall named.</check>
    <check>Projected contract blocks in AGENTS.md, .claude/CLAUDE.md and .agents/AGENTS.md are byte-identical to the master.</check>
  </validation>
</task>
```

## Task 2 — Host tier 0 renderer (R1)

```xml
<task id="2" name="host-tier-zero-renderer">
  <depends-on>1</depends-on>
  <objective>
    In attune-forms, project a single-question choice form onto the
    host's structured question contract; fall through to PORTABLE
    for anything richer; validate the answer on the same path as
    every other tier.
  </objective>
  <files-to-create>
    <file path="attune-forms: src/attune_forms/host_question.py" />
    <file path="attune-forms: tests/test_host_question.py" />
  </files-to-create>
  <files-to-modify>
    <file path="scripts/render_demo_forms.py">
      Add the tier-0 render of the existing audit demo form.
    </file>
    <file path="pyproject.toml">
      Bump the attune-forms floor to the release that ships host_question.
    </file>
  </files-to-modify>
  <validation>
    <check>A 5-option form returns None from render_host_question and renders on PORTABLE unchanged.</check>
    <check>A recommended option is first and suffixed " (Recommended)"; a form with no recommendation has no suffix.</check>
    <check>A malformed host answer is re-asked on PORTABLE, never accepted.</check>
    <check>Parity gate green with the new receipt line.</check>
  </validation>
</task>
```

## Task 3 — Memory index projection (R3)

```xml
<task id="3" name="lesson-index-projection">
  <depends-on>1</depends-on>
  <objective>
    Generate a promoted-lesson index from the store and project it
    to MEMORY.md, .claude/CLAUDE.md, AGENTS.md and .agents/AGENTS.md
    through the existing projector; regenerate on promote.
  </objective>
  <files-to-create>
    <file path="scripts/project_lesson_index.py" />
    <file path="content/collaboration/lesson-index.md">
      Generated; header states it is generated and names the script.
    </file>
    <file path="tests/unit/memory/test_lesson_index_projection.py" />
  </files-to-create>
  <files-to-modify>
    <file path="scripts/project_collaboration_contract.py">
      Second master + target set; MEMORY.md added as a target.
    </file>
    <file path="src/attune/memory/promotion.py">
      promote() triggers regeneration; failure to regenerate is reported, never swallowed.
    </file>
  </files-to-modify>
  <validation>
    <check>A promotion in a scratch store produces the same index line in all four targets.</check>
    <check>Exceeding the line budget fails the drift guard with the count.</check>
    <check>A hand edit inside any projected block is refused exactly as the contract block is today.</check>
    <check>Recall eval numbers are unchanged (the index is not consulted by recall).</check>
  </validation>
</task>
```

## Task 4 — MCP Apps round-trip receipt (R4)

```xml
<task id="4" name="mcp-apps-roundtrip-receipt">
  <depends-on>1</depends-on>
  <objective>
    Record whether the Cowork host renders the Fix preview through
    the ui:// profile and returns a bound action intact; record the
    Markdown fallback if it does not. No production change unless
    the receipt fails.
  </objective>
  <files-to-modify>
    <file path="docs/specs/host-surface-parity/receipts.md">
      R4 block: profile advertised (yes/no), render captured, action response with revision/nonce/hash, replay refused.
    </file>
  </files-to-modify>
  <validation>
    <check>Replayed action fails closed on the server with the existing fix_workspace error.</check>
    <check>If the profile is absent, the Markdown preview matches the terminal preview argv exactly.</check>
  </validation>
</task>
```

## Task 5 — Scheduled and monitored delivery, twinned (R5)

```xml
<task id="5" name="scheduled-delivery-twinned">
  <depends-on>1</depends-on>
  <objective>
    Ship host scheduled-task and monitor templates for sweep,
    bug-predict, release-prep and the context_fit.jsonl watch, each
    beside its cron + attune CLI twin, both under the spend gate.
  </objective>
  <files-to-create>
    <file path="plugin/templates/scheduled/README.md" />
    <file path="plugin/templates/scheduled/discovery-sweep.md" />
    <file path="plugin/templates/scheduled/bug-predict.md" />
    <file path="plugin/templates/scheduled/release-prep.md" />
    <file path="plugin/templates/scheduled/context-fit-monitor.md" />
    <file path="plugin/templates/scheduled/crontab.example" />
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/workflows/base.py">
      Run receipts carry origin: scheduled | monitor | interactive.
    </file>
  </files-to-modify>
  <validation>
    <check>One scheduled run and its cron twin produce receipts in .attune/workflow_runs.jsonl differing only in origin.</check>
    <check>The spend gate refuses a scheduled run whose prompt omits a cap.</check>
    <check>Parity gate green: every host template has its twin.</check>
    <check>The context_fit.jsonl monitor either fires on the first row or the task records that the writer path is not exercised (closing the TASKS.md item either way).</check>
  </validation>
</task>
```

## Task 6 — Roster as data (R7)

```xml
<task id="6" name="roster-as-data">
  <depends-on>0</depends-on>
  <objective>
    Move the roster to a role-slot document with the current three
    as the embedded default; derive CANONICAL_SEATS, SEAT_RECIPES and
    PLAN_ONLY_SEATS from it; gate workspace roster checks on the
    roster's length; template the brief preamble.
  </objective>
  <files-to-create>
    <file path="src/attune/roundtable/roster.py" />
    <file path="src/attune/roundtable/roster.default.yaml" />
    <file path="tests/unit/roundtable/test_roster.py" />
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/roundtable/rotation.py" />
    <file path="src/attune/roundtable/routine.py" />
    <file path="src/attune/roundtable/workspace.py" />
    <file path="src/attune/roundtable/skeptic.py" />
    <file path="src/attune/roundtable/countersign.py" />
  </files-to-modify>
  <validation>
    <check>Task 0's roster characterization suite passes unchanged against the derived views.</check>
    <check>A roster naming a fourth seat with no enabled extension fails to load with the exact shortfall.</check>
    <check>A roster swapping the plan_reviewer's vendor changes the recipe and nothing else.</check>
  </validation>
</task>
```

## Task 7 — Local reranker extension (R6a) — gated on Phase A; ships alone, first (D5, unanimous)

```xml
<task id="7" name="local-rerank-extension">
  <depends-on>3</depends-on>
  <gated-on>release-16-manifest Phase A shipped (attune.extensions on disk, enable CLI live)</gated-on>
  <objective>
    Ship the Phase A example extension as an Ollama-backed reranker
    under the memory-backend contract's optional rerank capability,
    with fail-open fallback to store ranking.
  </objective>
  <files-to-create>
    <file path="extensions/attune-ext-local-rerank/" />
    <file path="tests/unit/extensions/test_local_rerank.py" />
  </files-to-create>
  <validation>
    <check>attune extension enable local-rerank loads and constructs the backend in-process (D1 receipt 2 wording).</check>
    <check>With Ollama stopped, recall returns store ranking and the doctor reports the degradation.</check>
    <check>memory-recall-eval reports P@3 with and without the reranker on the frozen benchmark; both numbers in receipts.md.</check>
  </validation>
</task>
```

## Task 8 — Local role workflows via placement label (R6b) — gated on Phase B

*(Amended 2026-09-02 per the D2 ruling: routing label, not enum
member. The tier enum, its four copies, and the attune-rag mirror do
not change; the original enum-edit mechanics are superseded.
Amended 2026-09-03: the label field and its resolution semantics
land earlier as Task 12 under D8's 16.3 go; this task consumes the
label, it no longer introduces it.)*

```xml
<task id="8" name="local-role-workflows">
  <depends-on>6,7,12</depends-on>
  <gated-on>release-16-manifest Phase B shipped (workflow contract)</gated-on>
  <objective>
    Add a placement routing label (placement: local) on the role
    routing record per the D2 ruling, and ship workflow extensions
    for classification, triage pre-sort, low-stakes
    skeptic/countersign and fact-check probes, each advisory-labeled
    with a PREMIUM fallback above a chair-set stakes threshold
    (fact-check probes additionally hosted-model countersigned per
    D5's H4 ruling).
  </objective>
  <files-to-modify>
    <file path="src/attune/config/agent_config.py">
      Consumes the placement label landed by Task 12; local roles
      route to the enabled workflow extension. Tier enum untouched.
    </file>
    <file path="tests/unit/test_model_tiers_drift.py">
      Unchanged three-member assertion stands as the D2 receipt.
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="extensions/attune-ext-local-roles/" />
  </files-to-create>
  <validation>
    <check>Tier drift guard green with the enum unchanged in all copies and the mirror (no LOCAL member anywhere).</check>
    <check>A role routed "CHEAP, prefer local" runs on the local extension when present and falls back hosted when absent; the ledger shows placement.</check>
    <check>A low-stakes skeptic pass routed local produces a parseable advisory verdict; above threshold it routes to PREMIUM and the ledger shows both.</check>
    <check>No change to ModelProvider.</check>
  </validation>
</task>
```

## Task 9 — Asks-per-outcome (R8)

```xml
<task id="9" name="asks-per-outcome">
  <depends-on>1</depends-on>
  <objective>
    Count structured asks and receipted outcomes in the session
    ledger and surface the ratio through friction_gate at session end.
  </objective>
  <files-to-modify>
    <file path="src/attune/gates/session_ledger.py" />
    <file path="plugin/hooks/friction_gate.py" />
    <file path="tests/unit/gates/test_session_ledger.py" />
  </files-to-modify>
  <validation>
    <check>A session with three asks and one Fix receipt reports 3.0; a headless run with zero asks reports 0.0, not an error.</check>
    <check>No new file or store; fields live in the existing ledger JSONL.</check>
  </validation>
</task>
```

## Task 10 — Capability descriptor and conformance foundation (R9)

*(Authored 2026-09-03 under D8's go; D9 records the motivation.
Motivation receipt: the 2026-09-03 guard-intervention audit ("The
Prose Gap", `~/.attune/reports/guard-intervention-record-2026-09-03.md`,
ledger entry 2) logged a live instance of the exact failure this
task kills — a widget emitted to a host that does not render
MCP-app content, with the render claimed successful unverified.
The chair ruled R9/R10 the one mechanical enforcer to adopt from
that audit, declining all other new gates. Sequencing per D5:
after Task 4's R4 receipt, before Task 2. D6 probe 2 verified that
installed attune-forms already exports `HostCapabilities`,
`InteractionProfile`, and the `attune_forms.conformance` types
`ConformanceReceipt`, `ConformanceReport`, `ConformanceStatus`, and
`ConformanceFinding` — this task wires against them, it does not
reinvent them. The deferred round-2
questions (attestation schema for host-UI resolutions; the single
no-privileged-host receipt producible in CI) become concrete here
and reopen with a fresh chair go per D5 — do not design past them
silently.)*

```xml
<task id="10" name="capability-descriptor-foundation">
  <depends-on>1</depends-on>
  <objective>
    Give every host adapter and extension a machine-readable
    capability descriptor, an `attune surfaces doctor` probe that
    writes capability receipts, a generated hosts × capabilities
    matrix, and a conformance suite — all assertable in CI with no
    host present. Renderers consult the probe instead of sniffing
    per call; host-capability absence becomes a recorded fact, not
    an assumption.
  </objective>
  <files-to-create>
    <file path="src/attune/surfaces/__init__.py" />
    <file path="src/attune/surfaces/descriptor.py">
      Capability descriptor record per host adapter and extension:
      structured-question shape, memory surfaces, ui:// profiles,
      scheduling/monitoring support, action round-trip guarantees,
      receipt schema versions. Reuses attune-forms
      HostCapabilities/InteractionProfile where they fit.
    </file>
    <file path="src/attune/surfaces/doctor.py">
      Probe + `attune surfaces doctor` CLI: records which
      contracts the current host actually advertises and writes a
      capability receipt; with no host present it writes the
      all-fallback receipt and exits 0.
    </file>
    <file path="src/attune/surfaces/matrix.py">
      Generates the hosts × capabilities matrix (each cell
      native / fallback-receipted / absent) from accumulated
      receipts.
    </file>
    <file path="docs/specs/host-surface-parity/capability-matrix.md">
      Generated; header states it is generated and names the
      generator; drift-guarded.
    </file>
    <file path="tests/unit/surfaces/test_descriptor.py" />
    <file path="tests/unit/surfaces/test_surfaces_doctor.py" />
    <file path="tests/unit/surfaces/test_conformance_suite.py">
      Canonical transcripts against each adapter: unsupported
      capabilities degrade deliberately; semantic outputs stay
      equivalent; receipts keep provenance and replay protection;
      removing any host adapter leaves PORTABLE and HEADLESS
      usable; no workflow silently selects a privileged host.
    </file>
    <file path="tests/unit/gates/test_capability_matrix_drift.py" />
  </files-to-create>
  <validation>
    <check>The doctor with no host present writes the all-fallback receipt and the matrix's fallback column is green — the whole suite passes keyless and hostless in CI.</check>
    <check>A descriptor advertising a capability its adapter cannot demonstrate fails the conformance suite with the cell named.</check>
    <check>A hand edit inside the generated matrix fails the drift guard; regeneration is deterministic.</check>
    <check>With any single host adapter removed, PORTABLE and HEADLESS conformance stays green and no privileged host is silently selected.</check>
    <check>Changed code carries ≥90% coverage (D7); no API-billed call anywhere in the task (D8 zero-spend).</check>
  </validation>
</task>
```

## Task 11 — Tier provenance on validated answers (R10)

*(Authored 2026-09-03 under D8's go; requirement adopted in D9 from
the same guard-intervention audit — the audit's ledger entry 2 is
the failure made visible: with provenance stamped from the response
envelope, a render claimed on a surface that never displayed it
becomes a recorded fall-through instead of an unverifiable prose
claim. Executes only behind its own chair go. Pairs with Task 10 as
H1's falsifier: the doctor says which tiers the host offers;
provenance says which tier each answer actually used.)*

```xml
<task id="11" name="tier-provenance">
  <depends-on>2,10</depends-on>
  <objective>
    Stamp every validated answer with the surface tier that
    actually rendered it (tier 0 host-native / RICH / PORTABLE /
    HEADLESS), derived from the response envelope and never from
    the render request; surface tier-0 fall-through and Other-rate
    through the existing telemetry stores.
  </objective>
  <files-to-modify>
    <file path="src/attune/elicitation/ask_payload.py">
      Validated-answer envelope gains a rendered_tier field,
      stamped where the response is collected.
    </file>
    <file path="src/attune/mcp/server.py">
      elicitation_collect_response records the actual tier and
      whether the host "Other" free-text escape was used.
    </file>
    <file path="src/attune/gates/session_ledger.py">
      Fall-through and Other counters beside Task 9's ask/outcome
      fields; raw counts, never ratios (D5's R8 rule applies).
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/unit/elicitation/test_tier_provenance.py" />
  </files-to-create>
  <validation>
    <check>A form exceeding the current host profile records rendered_tier portable and increments the fall-through counter; a tier-0 answer records the host tier.</check>
    <check>A render requested RICH whose response arrives on a fallback surface records the fallback, never the request — the audit's ledger-2 case is a recorded fall-through.</check>
    <check>An answer via the host "Other" escape increments the Other counter; both rates are computable from the existing JSONL with no new file or store.</check>
    <check>A headless run records rendered_tier headless and zero asks stays 0.0, not an error (aligns with Task 9).</check>
    <check>Answer contents are never recorded in the counters (D5's R8 privacy rule).</check>
    <check>Changed code carries ≥90% coverage (D7); no API-billed call anywhere in the task (D8 zero-spend).</check>
  </validation>
</task>
```

## Task 12 — Placement-label wiring (D2)

*(Authored 2026-09-03 under D8's go, which names the D2
placement-label wiring an ungated 16.3 item with its execution go
granted. This is the label mechanics only — the field, its
resolution semantics, and the drift-guard receipt — landed ahead of
any local extension so Tasks 7 and 8 find the routing seam waiting.
Before Phase A/B ships an extension, every resolution falls back
hosted, so observable routing behavior is unchanged. The ops-tile
"not a tier" case stays with Task 8 per D2. The tier enum, its four
copies, and the attune-rag mirror do not change — that is the
ruling's whole point.)*

```xml
<task id="12" name="placement-label-wiring">
  <objective>
    Add the D2-ruled placement routing label to the role routing
    record: an optional placement field (default hosted) on
    UnifiedAgentConfig expressing "CHEAP, prefer local, fall back
    hosted". Resolution prefers an enabled local extension when one
    provides the role and falls back hosted when none does — which,
    pre-Phase-A, is always. No enum member anywhere.
  </objective>
  <files-to-modify>
    <file path="src/attune/config/agent_config.py">
      UnifiedAgentConfig gains placement: "local" | None (default
      None = hosted); get_model_id()/routing consults it; with no
      enabled local extension the resolved model is byte-identical
      to today's.
    </file>
    <file path="src/attune/gates/session_ledger.py">
      Invocation rows record placement when set, so the fall-back
      is visible in the ledger, not inferred.
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/unit/config/test_placement_label.py">
      Field default, validation (only "local" or absent), hosted
      fall-back with no extension enabled, ledger row carries
      placement.
    </file>
  </files-to-create>
  <validation>
    <check>tests/unit/test_model_tiers_drift.py passes UNCHANGED — the three-member enum assertion in all four copies and the attune-rag mirror is the D2 receipt.</check>
    <check>With no local extension enabled, a role with placement local resolves to the same model id as the same role without the label.</check>
    <check>A placement value other than "local" fails validation with the field named; absent means hosted with no warning.</check>
    <check>No change to ModelProvider; no new routing store — the label lives on the existing record.</check>
    <check>Changed code carries ≥90% coverage (D7); no API-billed call anywhere in the task (D8 zero-spend).</check>
  </validation>
</task>
```
