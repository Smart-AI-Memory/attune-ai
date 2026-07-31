# Outcome-First Fix — Tasks

**Status:** active (2026-07-30) — Tasks 0–1 executed, each
behind its own explicit chair go (PRs #1806, #1808). Task 2
authored 2026-07-30 (chair-authorized authoring); executing it
requires its own chair go AND trips the spend gate (first task
with real LLM execution). This file carries the executed log
plus the next executable unit only (decisions.md D2).

## Executed log

- **Task 0 — Phase 0 characterization proof** (PR #1806):
  seam inventory dry-trace-checked, canonical fixture live at
  `tests/fixtures/outcome_first_fix/`, characterization pins
  green keyless. Premise corrections recorded in the inventory:
  exit-code contract already 0/1/2/3 (legacy no-`success`
  loophole documented); keyless NL fix-routing goes to
  bug-predict at 0.17 confidence with no abstention.
- **Task 1 — Phase 1 dry Fix contract** (PR #1808):
  `attune fix "<request>" --explain` ships preview-or-abstain
  with internal DTOs; 20 keyless tests through the real `main()`
  entry, module coverage 96%, no execution paths (grep-checked).
  Scope validation anchors to the enclosing repo root (codex
  lane fix); selection is explicitly compatibility-unverified
  until Phase 2. Same-session chair addition: `fix` keyword →
  dev/debug in the router builtin map (Phase 0 absence pin
  flipped as the change receipt).

## Task 2 — Phase 2: executable Fix proof

```xml
<task id="2" name="outcome-first-fix-phase2-executable-proof">
  <objective>
    Execute one representative Fix end-to-end: translate the
    FixContract ONCE into existing workflow inputs, run the fix
    through the existing registry/executor, evaluate every probe
    INDEPENDENTLY through a real subprocess boundary, and render
    one unified receipt (changes made, probes + provenance,
    results, remaining uncertainty, safest next action). A
    workflow exit alone never marks success (H2).
  </objective>

  <context>
    <existing-code path="src/attune/cli_commands/fix_commands.py">
      Phase 1 surface: FixContract/VerificationProbe DTOs,
      build_contract, cmd_fix preview. Phase 2 extends cmd_fix
      with an execution path behind --run; --explain and the
      bare form keep Phase 1 preview semantics unchanged.
    </existing-code>
    <existing-code path="src/attune/workflows/test_gen_parallel.py">
      Precedent (D5a): workflows already write project files via
      _validate_file_path(...).write_text(...) (line ~336).
    </existing-code>
    <existing-code path="src/attune/workflows/agent_sdk_adapter.py">
      The ONLY executor: sdk_isolation_kwargs() must wrap every
      ClaudeAgentOptions construction (drift-guarded); Bash
      PreToolUse guard rides along.
    </existing-code>
    <existing-code path="src/attune/cli_commands/_exit_codes.py">
      Exit contract reuse: 0 = every done condition VERIFIED by
      its probe; 1 = workflow ran but >=1 done condition failed
      or was unverifiable; 2 = uncaught crash; 3 = CLI error /
      abstention. The 0/1 boundary is decided by PROBE RESULTS,
      never by WorkflowResult.success alone.
    </existing-code>
    <constraint>
      D5: ONE new FixWorkflow registered in the EXISTING
      registry, executed by the EXISTING adapter, returning the
      EXISTING WorkflowResult. No new registry, executor,
      lifecycle, evidence store, or telemetry (H3). The SDK
      agent gets Edit/Read/Glob/Grep ONLY — no Bash (probes are
      the CLI's job, not the agent's), scoped to the contract's
      scope path(s).
    </constraint>
    <constraint>
      Probes are evaluated by the CLI via subprocess.run(argv)
      AFTER the workflow returns — never by the agent, never
      trusted from workflow output. Probe provenance in the
      receipt = exact argv + returncode + duration; a probe that
      cannot run records SKIPPED with the reason (truthful
      uncertainty, not silent omission).
    </constraint>
    <constraint>
      Pre-run baseline is MANDATORY (codex lane finding):
      before execution, record the dirty-path set and content
      hashes of scope files. The receipt attributes ONLY paths
      that changed relative to that baseline; pre-existing
      dirty paths render in their own "pre-existing changes
      (not attributed)" section, and the next-action line never
      recommends reverting a path that was dirty before the
      run. Without this, a post-run diff would blame the
      user's own in-flight work on the agent.
    </constraint>
    <constraint>
      Scope enforcement is layered: (1) PREVENTION — FixWorkflow
      installs a PreToolUse Edit/Write path guard through the
      EXISTING adapter hook mechanism (same pattern as the Bash
      guard in sdk_isolation_kwargs), denying edits outside the
      contract's scope paths at tool-call time; (2) DETECTION —
      after execution, diff vs the pre-run baseline; changed
      paths outside scope are reported as a violation and force
      exit 1, with the exact paths named so recovery is a
      targeted revert. Git plumbing is allowed ONLY in the
      probe-runner/diff-check module (fix_receipt.py);
      fix_commands.py itself stays subprocess-free and its
      Phase 1 grep check narrows to it.
    </constraint>
    <constraint>
      Spend gate: executing this task's live-fire receipt makes
      real SDK calls (~1-3 sessions, single-digit dollars). CI
      tests stay keyless-deterministic via a stub workflow; the
      LLM path is proven by ONE spend-gated dogfood run recorded
      in decisions.md with the receipt pasted.
    </constraint>
    <constraint>
      Default remains dry: `attune fix` without --run previews
      exactly as Phase 1. --run requires the fix workflow
      selection and at least one probe; anything less abstains
      (exit 3). Do not persist prompt text beyond the run
      (ruling: no sensitive-prompt persistence by default).
    </constraint>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/fix_workflow.py">
      FixWorkflow (SDK-native, registered like every other
      workflow): input = goal, scope paths, done-condition
      descriptions (data, not prose prompts); agent brief
      instructs minimal in-place edit within scope; returns
      WorkflowResult whose metadata lists agent-reported changed
      files (advisory only — the receipt trusts the DIFF, not
      the agent's claim).
    </file>
    <file path="src/attune/cli_commands/fix_receipt.py">
      Receipt assembly + rendering, separated from the preview:
      dataclasses for ProbeOutcome (argv, returncode, duration,
      status PASS/FAIL/SKIPPED+reason) and FixReceipt (baseline
      snapshot, changed paths ATTRIBUTED via baseline diff,
      pre-existing dirty paths listed unattributed, probe
      outcomes, scope violations, remaining uncertainty, safest
      next action).
      Next-action rules: all probes pass -> "review and commit";
      any fail -> "inspect diff, re-run probe X"; scope
      violation -> "revert out-of-scope paths". Renderer prints
      the receipt and computes the 0/1 exit per the contract
      above.
    </file>
    <file path="tests/unit/cli_commands/test_fix_receipt.py">
      Keyless deterministic coverage (>=85% on both new
      modules): a STUB fix workflow registered in-test applies
      the known one-character fix to a tmp COPY of
      tests/fixtures/outcome_first_fix/ (never the tracked
      fixture); probes run via REAL pytest subprocess against
      the copy — the initially-failing target probe passes
      after the stub fix (ruling Phase 2 acceptance, through a
      real CLI/subprocess/file boundary). Negative paths: probe
      fails -> exit 1 + truthful FAIL row; probe binary missing
      -> SKIPPED + uncertainty line + exit 1; out-of-scope edit
      -> violation row + exit 1; WorkflowResult.success True
      with failing probes -> exit 1 (H2 pinned at the receipt
      layer); workflow crash -> exit 2.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/cli_commands/fix_commands.py">
      <change location="cmd_fix / subparser">
        BEFORE: preview-only; no --run.
        AFTER: --run flag executes: contract -> single
        translation into FixWorkflow input -> existing executor
        -> probe evaluation -> receipt render -> exit per
        contract. Preview paths byte-identical to Phase 1
        (regression-pinned by the existing 20 tests).
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Existing Phase 1 suite passes UNMODIFIED (preview
      semantics frozen).</check>
    <check>Stub-workflow round trip: target probe fails before,
      passes after, via real pytest subprocess on the fixture
      copy; receipt lists the changed file from the actual
      baseline diff.</check>
    <check>Baseline attribution: a pre-dirtied file in the
      fixture copy is listed as pre-existing, NOT attributed to
      the run, and never named in a revert next-action.</check>
    <check>Prevention layer: the Edit path guard denies an
      out-of-scope edit at tool-call time in a unit test of the
      hook function itself (keyless).</check>
    <check>H2 pin: a WorkflowResult with success=True and a
      failing probe yields exit 1 and a FAIL row — workflow
      exit never marks success.</check>
    <check>Characterization + gates suites stay green; the
      status-line corpus sweep passes (STATUS_VOCABULARY
      leading token).</check>
    <check>Coverage >=85% on fix_workflow.py and
      fix_receipt.py; serial keyless run.</check>
    <check>Live-fire (spend-gated, chair go at execution time):
      one real `attune fix --run` on a fixture copy through the
      real FixWorkflow; receipt pasted into decisions.md as the
      dogfood record. Declared receipt types: suite +
      behavioral + live-fire + metric.</check>
  </validation>

  <risks>
    <risk severity="high">Agent edits outside scope or edits the
      test to make it pass — mitigation: post-hoc diff check
      forces exit 1 on out-of-scope paths, and the canonical
      scenario's third done condition (diff confined to
      pricing.py) makes test-editing a reported violation.</risk>
    <risk severity="medium">Stub-based CI proof diverging from
      the live LLM path — mitigation: stub and FixWorkflow share
      the same registration/translation/receipt code; only the
      edit step differs, and the live-fire dogfood receipt
      covers the real path once.</risk>
    <risk severity="medium">Subprocess allowlist creep in
      fix_commands — mitigation: probe-runner and diff-check
      live in fix_receipt.py; fix_commands itself stays
      subprocess-free and the grep check narrows to it.</risk>
  </risks>
</task>
```

**Acceptance (ruling Phase 2):** an initially failing probe
passes through a real CLI/subprocess/file boundary. Changed
artifacts, failed or skipped probes, uncertainty, and the next
action are truthfully reported. Workflow exit alone never marks
success.
