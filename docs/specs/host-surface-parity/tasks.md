# Host Surface Parity — Tasks

**Status:** draft (2026-09-03) — no task authorized. Each task
executes only behind its own chair go; a go on one task is not a go
on the next. Tasks 7 and 8 are additionally gated on
release-16-manifest Phases A and B.

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
  <validation>
    <check>Both suites green on main with no production change.</check>
    <check>The projector's existing tests still refuse a hand edit inside the marked block.</check>
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

## Task 7 — Local reranker extension (R6a) — gated on Phase A

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

## Task 8 — Local role workflows and LOCAL tier (R6b) — gated on Phase B

```xml
<task id="8" name="local-role-workflows">
  <depends-on>6,7</depends-on>
  <gated-on>release-16-manifest Phase B shipped (workflow contract); decisions.md D2 ruled</gated-on>
  <objective>
    Add the LOCAL tier per D2 and ship workflow extensions for
    classification, triage pre-sort, low-stakes skeptic/countersign
    and fact-check probes, each with a PREMIUM fallback above a
    chair-set stakes threshold.
  </objective>
  <files-to-modify>
    <file path="src/attune/models/registry.py" />
    <file path="src/attune/config/agent_config.py" />
    <file path="src/attune/workflows/compat.py" />
    <file path="src/attune/workflows/progressive/core.py" />
    <file path="tests/unit/test_model_tiers_drift.py">
      Mirror check extended to LOCAL; attune-rag mirror bumped in the same release.
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="extensions/attune-ext-local-roles/" />
  </files-to-create>
  <validation>
    <check>Tier drift guard green with LOCAL present in all copies and the mirror.</check>
    <check>A low-stakes skeptic pass routed to LOCAL produces a parseable verdict; above threshold it routes to PREMIUM and the ledger shows both.</check>
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
