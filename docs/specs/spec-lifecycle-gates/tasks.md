# Spec-Lifecycle Gates v1 — Tasks

**Status: executed** (2026-07-19, chair go "go on implementation";
all seven tasks landed in one PR — receipts per task below and in
`decisions.md`'s closure entry). One implementation-discovered
deviation: the design's `src/attune/gates/` destination was already
the collaboration-gates package, resolved as the
`attune.gates.lifecycle` subpackage (parent untouched).

## T1 — Protocol + ledger (RR-1, RR-2, G1)

```xml
<task id="gates-1" name="protocol-and-ledger">
  <objective>
    Ship the four-state GateReceipt contract and the G1 machine
    ledger — the substrate every later task writes through.
  </objective>
  <context>
    <existing-code path="src/attune/roundtable/producing.py">
      FAILURE_CODES closed-taxonomy pattern; FailureReceipt
      dataclass shape (to_dict, evidence cap) to mirror.
    </existing-code>
    <existing-code path="src/attune/models/telemetry/storage.py">
      _canonical_runs_file: the ATTUNE_HOME resolution idiom the
      ledger must copy (suite isolation rides the same fixture).
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/gates/__init__.py">Public exports.</file>
    <file path="src/attune/gates/protocol.py">
      GateReceipt dataclass per design.md (closed state enum
      PASS/REVISE/CHAIR_REQUIRED/BLOCKED; unknown state raises).
    </file>
    <file path="src/attune/gates/ledger.py">
      append(receipt), latest_for(target),
      unresolved_chair_required(); path
      &lt;ATTUNE_HOME&gt;/ops/gates/verdicts.jsonl; append-only.
    </file>
    <file path="tests/unit/gates/test_protocol_ledger.py">
      State-enum closure (unknown raises), receipt round-trip,
      ledger append/read under ATTUNE_HOME isolation, drift guard
      asserting the suite never touches the real ledger.
    </file>
  </files-to-create>
  <validation>
    <check>pytest tests/unit/gates/ serial — all pass (suite receipt)</check>
    <check>Drift guard: default ledger path resolves under the test's ATTUNE_HOME, never ~/.attune</check>
  </validation>
  <risks>
    <risk severity="low">Complexity ratchet on ledger read helpers — keep functions flat.</risk>
  </risks>
</task>
```

## T2 — Activation policy + waivers (RR-3, RR-4, RR-8; G2, G3, G4)

```xml
<task id="gates-2" name="activation-and-waivers">
  <objective>
    Pure-function risk policy: blast-radius classification over
    the design's surface map, tier-based gate selection, and
    parse-only waiver reading with expiry.
  </objective>
  <context>
    <existing-code path="docs/specs/spec-lifecycle-gates/design.md">
      The chair-ruled surface map (security, public re-exports,
      plugin/, record schemas, workflows, packaging, deletions,
      migrations → chair; unclassifiable → chair). G4 batching
      threshold: CHAIR_REQUIRED &gt; 20% of measured baseline.
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/gates/activation.py">
      blast_radius(changed_paths) -> "isolated"|"chair";
      active_gates(tier, radius) -> list[str]; parse_waivers
      (decisions.md text) -> unexpired waiver set (WAIVER: line
      format per design; date or commit-count expiry); baseline
      re-measure helper recording into ledger config (G4).
    </file>
    <file path="tests/unit/gates/test_activation.py">
      Surface-map cases incl. conservative default; sub-spec tier
      → baseline only; waiver parse/expiry boundaries; waived
      gate logs PASS(waived) receipt tagged waived=true.
    </file>
  </files-to-create>
  <validation>
    <check>pytest tests/unit/gates/test_activation.py serial — all pass</check>
    <check>Every surface-map bullet in design.md has a matching test case (trace check)</check>
  </validation>
  <risks>
    <risk severity="medium">Waiver line format drift vs future decisions.md style — pin with round-trip fixtures.</risk>
  </risks>
</task>
```

## T3 — Baseline gate adapters (RR-4; the symbol-reality + falsifiability gates)

```xml
<task id="gates-3" name="baseline-adapters">
  <objective>
    The mandatory mechanical baseline as GateReceipt-returning
    adapters: round-table compiler lints, symbol-reality
    resolution, falsifiability lint. CI enforcers are CITED not
    wrapped (design ruling).
  </objective>
  <context>
    <existing-code path="src/attune/roundtable/compiler.py">
      lint_draft/lint_critique/lint_final — call directly.
    </existing-code>
    <existing-code path="docs/specs/spec-lifecycle-gates/decisions.md">
      The confabulation episode: symbol-reality must catch
      seat-cited paths that do not resolve (import probe + path
      existence + [[?slug]] escape hatch per requirements RR-4).
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/gates/baseline.py">
      lint_gate(document, kind), symbol_reality_gate(document,
      project_root) — extracts backticked paths/modules, probes
      existence/importability, honors a not-yet-built annotation;
      falsifiability_gate(document) — acceptance bullets name a
      receipt type or failing probe; flags
      configured/registered/exits-0 phrasings.
    </file>
    <file path="tests/unit/gates/test_baseline.py">
      Positive/negative per gate; the slot-3 confabulated-path
      fixture MUST fail symbol-reality (regression from the live
      episode); falsifiability catches the banned phrasings.
    </file>
  </files-to-create>
  <validation>
    <check>pytest tests/unit/gates/test_baseline.py serial — all pass</check>
    <check>Behavioral receipt: running symbol_reality_gate over the slot-3 final draft text yields BLOCKED with the seven missing paths in findings</check>
  </validation>
  <risks>
    <risk severity="medium">Path-extraction false positives on prose backticks — scope to path-shaped tokens (contains / or .py/.md).</risk>
  </risks>
</task>
```

## T4 — Runner + CLI (RR-2, RR-5)

```xml
<task id="gates-4" name="runner-and-cli">
  <objective>
    run_boundary(phase, spec_slug, *, tier, changed_paths) —
    select via activation, run serially, append every receipt,
    return them, never advance; plus the thin `attune gates
    check` CLI rendering receipts with G5 exit semantics
    (BLOCKED → exit 2, CHAIR_REQUIRED → exit 1, else 0).
  </objective>
  <context>
    <existing-code path="src/attune/cli_minimal.py">
      CLI registration convention for the `attune` entry point.
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/gates/runner.py">Per design.</file>
    <file path="tests/unit/gates/test_runner.py">
      Receipts appended for every gate run; runner never mutates
      spec files (assert tree untouched); exit-code mapping.
    </file>
  </files-to-create>
  <files-to-modify>
    <file path="src/attune/cli_minimal.py">
      <change location="command registration">
        BEFORE: no gates command
        AFTER: `attune gates check &lt;phase&gt; --spec &lt;slug&gt;` wired to runner
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>pytest tests/unit/gates/ serial — all pass</check>
    <check>Live-fire: `attune gates check requirements --spec spec-lifecycle-gates` against the real spec dir exits per G5 and appends real receipts to a scratch ATTUNE_HOME ledger</check>
  </validation>
  <risks>
    <risk severity="low">CLI surface count gates (MCP/README counts do NOT change — this is a CLI subcommand, not an MCP tool).</risk>
  </risks>
</task>
```

## T5 — Trigger wiring: /spec skill + producing post-compile (RR-1, G5)

```xml
<task id="gates-5" name="trigger-wiring">
  <objective>
    Wire the two non-CI event triggers: /spec skill boundary
    instructions call the CLI and honor G5 (hard-block BLOCKED,
    soft-block CHAIR_REQUIRED with recorded acknowledgment);
    producing runs gate the compiled requirements document
    post-compile.
  </objective>
  <context>
    <existing-code path=".claude/skills/spec/SKILL.md">
      Skill source; remember the sync_agents_skills projector +
      plugin mirror (single-source rule).
    </existing-code>
    <existing-code path="src/attune/roundtable/producing.py">
      Post-compile seam: after compile_requirements, before
      staging.
    </existing-code>
  </context>
  <files-to-modify>
    <file path=".claude/skills/spec/SKILL.md">
      <change location="each phase-gate section">
        BEFORE: proceed on approval
        AFTER: run `attune gates check` at the boundary; render receipts; G5 semantics
      </change>
    </file>
    <file path="src/attune/roundtable/producing.py">
      <change location="_rounds / staging">
        BEFORE: compile then stage
        AFTER: baseline gates over the final document; BLOCKED receipts join the digest (taxonomy code reuse, no new codes)
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>python scripts/sync_agents_skills.py --write; both sides committed; drift-guard test green</check>
    <check>Producing-run unit test: a final draft with confabulated paths yields a digest carrying the BLOCKED gate receipt</check>
  </validation>
  <risks>
    <risk severity="medium">Producing taxonomy is CLOSED — gate outcomes must map to existing codes (LINT_DIRTY family) or ride the digest body, not add codes without a spec amendment.</risk>
  </risks>
</task>
```

## T6 — Spec-drift curator source (RR-6)

```xml
<task id="gates-6" name="spec-drift-source">
  <objective>
    curator/sources/spec_drift.py implementing SourceReader:
    highest-phase status header vs git/PR reality; candidates in
    SourceSummary; must-not-raise; stable state_hash.
  </objective>
  <context>
    <existing-code path="src/attune/curator/sources/specs.py">
      Closest existing reader — mirror its shape and registration.
    </existing-code>
    <existing-code path="src/attune/curator/sources/__init__.py">
      SourceReader protocol (verified in design.md).
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/curator/sources/spec_drift.py">Reader.</file>
    <file path="tests/unit/curator/test_source_spec_drift.py">
      Fixture spec dirs: stale status surfaces a candidate; clean
      spec yields empty summary with stable hash; unreadable dir
      does not raise. Integration: candidate reaches curator
      output (RR-5-style proof, mirrors existing source tests).
    </file>
  </files-to-create>
  <validation>
    <check>pytest tests/unit/curator/ — all pass incl. the new reader</check>
  </validation>
  <risks>
    <risk severity="low">Highest-phase-file status rule (reconciler lesson) — read tasks &gt; design &gt; requirements, matching _phase_for_dir.</risk>
  </risks>
</task>
```

## T7 — Full-seam integration + closure (RR-9; G4 re-measure)

```xml
<task id="gates-7" name="full-seam-integration">
  <objective>
    The RR-9 end-to-end receipt: fixture spec → run_boundary →
    real ledger write → decisions.md fixture citing receipt_id →
    linkage asserted; plus the G4 baseline re-measure recorded;
    spec status flip to implemented with closure evidence in
    decisions.md.
  </objective>
  <files-to-create>
    <file path="tests/unit/gates/test_full_seam.py">Per design test plan.</file>
  </files-to-create>
  <files-to-modify>
    <file path="docs/specs/spec-lifecycle-gates/tasks.md">
      <change location="status header">
        BEFORE: tasks drafted
        AFTER: executed, per-task receipts checked off
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>Full unit suite green (suite receipt, serial for gates modules)</check>
    <check>Live-fire: one real /spec boundary run over this spec itself — the gates gate their own spec (dogfood receipt in decisions.md)</check>
  </validation>
  <risks>
    <risk severity="low">Status-flip inertness (reconciler reads highest-phase file) — flip THIS file's header, not requirements.md.</risk>
  </risks>
</task>
```

## Sequencing and receipts

Strict order T1 → T2 → T3 → T4 → T5 → T6 → T7 (each imports the
prior's surface). Receipt types per task are declared in their
validation blocks (suite / behavioral / live-fire); the
executor re-runs receipts centrally before shipping — a lane's
self-report is never the receipt.
