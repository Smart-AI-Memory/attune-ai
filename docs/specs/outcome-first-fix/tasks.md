# Outcome-First Fix — Tasks

**Status:** shipped (2026-08-02; flipped at 2026-08-08 triage) —
Tasks 0–4 all executed, each behind its own explicit chair go
(spend gate honored on Task 2; live-fire receipt in decisions.md
D6). Task 3 shipped in #1818, Task 4 (guided intake form) in #1824
with hardening in #1837/#1839/#1919; feature name ratified as
"Fix Receipts" in D9. No further tasks authored — Phase 4 routing
metrics stay gated on a labeled corpus (decisions.md D2), Phases
5–6 are a named non-goal.

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
- **Task 2 — Phase 2 executable Fix proof** (chair go +
  spend gate 2026-07-30): `attune fix --run` executes
  FixWorkflow (existing registry/executor, Edit-scope PreToolUse
  guard) and computes the receipt from a pre-run baseline +
  independently evaluated probes; exit 0/1 never trusts
  WorkflowResult.success. 14 keyless tests through real git
  repos and pytest subprocesses (coverage 97/94%); live-fire
  receipt recorded in decisions.md D6 — the real agent made
  exactly the minimal in-scope fix and both probes passed.
- **Task 3 — Phase 3 robustness, compatibility, measurement**
  (chair go 2026-07-31, keyless — no spend): the six measured
  gaps closed. G1 no-change runs are named instead of advising a
  nonexistent diff; G2 every failing probe is named; G3 answered
  by an evidence-chain walk and recorded in D7 (the Fix surface
  persists nothing; the ops run record is a generic inherited
  surface, deliberately unchanged); G4 the `attune fix` feature
  master ships and projects to 15 outputs, with the drift guard
  demonstrated firing on a hand-edited twin; G5+G6 the four D3
  metrics reported in [metrics.md](metrics.md), each with the
  command that produced it. One pre-existing assertion was
  amended — `test_workflow_success_with_failing_probes_exits_one_h2`
  asserted "inspect the diff" for a stub that changes nothing,
  which is exactly the advice G1 corrects; its H2 subject (exit 1
  plus a truthful FAIL row) is untouched. Also corrected: the
  `fix` subparser's help still claimed "dry — no execution yet"
  after `--run` shipped.
- **Task 4 — guided intake form** (chair go in-session; PR #1824,
  hardened in #1837/#1839/#1919; bullet backfilled at the
  2026-08-08 triage): `src/attune/elicitation/fix_intake.py` +
  `plugin/skills/fix/SKILL.md` + `tests/unit/elicitation/
  test_fix_intake.py` — the `/fix` intake picks scope and probes,
  previews the contract, runs with a verified receipt.

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

## Task 3 — Phase 3: robustness, compatibility, measurement

**Scoping receipt (2026-07-31, code-first):** the ruling's
Phase 3 bullet list was checked against the tree before this
task was authored, per the spec-scope-drift lesson. Of the six
named robustness paths, FOUR are already covered by the 48
tests in `tests/unit/cli_commands/test_fix_commands.py` +
`test_fix_receipt.py` (malformed, ambiguous, failed
verification, abstention — plus crash, git-unavailable, and
scope-unverified, hardened by the #1814/#1815 re-review). This
task therefore executes against the SIX measured gaps below,
not the ruling's list verbatim:

| # | Gap | Evidence |
|---|---|---|
| G1 | No-change path is silent | `assemble_receipt` renders `(none detected)` and `exit_code()` returns 0 when probes pass with zero attributed changes — "verified fix" and "agent did nothing" are indistinguishable |
| G2 | Partial success unpinned | `_next_action` names `failed[0]` only; no test covers mixed PASS/FAIL across several probes |
| G3 | Prompt text reachable by a persistence surface | `fix_workflow.py` puts verbatim `goal` in `WorkflowResult.metadata`, and `fix` is reachable through the ops runner (`PATH_ARG_REGISTRY`); telemetry itself records cost/tokens only |
| G4 | No user-facing `attune fix` surface docs | no feature master, no `.help` kind, no docs page; requirements demand the `/fix-test` relationship be stated explicitly |
| G5 | Compatibility unmeasured as a metric | Task 0 characterization pins exist but are not NAMED as the compatibility-regression measurement |
| G6 | The four D3 metrics have no measurement mechanism | H3 forbids new telemetry, so they must be suite-derived properties |

```xml
<task id="3" name="outcome-first-fix-phase3-robustness-measurement">
  <objective>
    Close the six measured gaps above so the Fix surface is
    truthful on its remaining paths, is documented on the
    projected surfaces, and reports the four ratified metrics
    (D3) as properties derived from the existing suite — with
    NO new telemetry, store, or lifecycle (H3).
  </objective>

  <context>
    <existing-code path="src/attune/cli_commands/fix_receipt.py">
      `FixReceipt.exit_code()` / `.render()` / `_next_action()`
      own every honesty decision. G1 and G2 are changes HERE,
      not in the CLI: the receipt is the single place the run's
      truth is computed.
    </existing-code>
    <existing-code path="src/attune/workflows/fix_workflow.py">
      `metadata={"goal": goal, ...}` (line ~159) is the only
      place the verbatim request text leaves the process.
    </existing-code>
    <existing-code path="src/attune/ops/runner.py">
      The ops runner reaches registered workflows and writes
      run artifacts; whether any of them carries `goal` is the
      G3 question to ANSWER, not assume.
    </existing-code>
    <existing-code path="docs/specs/outcome-first-fix/phase0-inventory.md">
      Task 0's characterization pins — the compatibility
      baseline G5 names.
    </existing-code>
    <constraint>
      H3 holds: no new registry, executor, evidence store,
      telemetry system, or execution lifecycle. Metrics are
      computed from artifacts the suite ALREADY produces.
    </constraint>
    <constraint>
      Phases 1 and 2 semantics are frozen. Preview output stays
      byte-identical; the only receipt changes are ADDITIVE
      honesty (a no-change row, a multi-failure next action).
      The existing 48 tests pass unmodified, or the change is
      wrong.
    </constraint>
    <constraint>
      The feature page is a single-source master that PROJECTS
      to `.help` kinds and the docs page (contract principle 3).
      No hand-edited twins; the drift guard is the receipt that
      the projection is real.
    </constraint>
    <constraint>
      Keyless and deterministic. No spend gate applies to this
      task — G1–G6 are all provable without an SDK call. If any
      sub-item is found to need live-fire, it stops and asks
      rather than spending.
    </constraint>
  </context>

  <files-to-modify>
    <file path="src/attune/cli_commands/fix_receipt.py">
      <change location="FixReceipt.render / _next_action">
        BEFORE: zero attributed changes renders
        "(none detected)" and, with passing probes, exits 0
        with next action "review the attributed diff and
        commit" — advice for a diff that does not exist.
        AFTER: a no-change run is named as such. The probes
        still decide the exit (H2 is not weakened: passing
        probes on an unchanged tree mean the conditions were
        ALREADY true), but the receipt says the run changed
        nothing and the next action reflects that — verify the
        goal was already satisfied rather than "commit".
      </change>
      <change location="_next_action failure branch">
        BEFORE: names `failed[0]` only, so a multi-probe
        partial success under-reports what must be re-run.
        AFTER: all failing probes are named (worst-problem-
        first ordering preserved).
      </change>
    </file>
    <file path="src/attune/workflows/fix_workflow.py">
      <change location="execute metadata (~line 159)">
        BEFORE: `metadata={"goal": goal, ...}` unconditionally.
        AFTER: only after G3's answer. If no persistence
        surface writes it, the metadata STAYS and a test pins
        the property (no speculative change). If a surface does
        write it, the goal is omitted or redacted there and the
        test pins the redaction. The verification decides the
        change — not the other way round.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="tests/unit/cli_commands/test_fix_phase3.py">
      G1: no-change run + passing probes renders the no-change
      row and its distinct next action (real tmp repo).
      G2: three probes, two failing — both failures named.
      G3: a real ops-runner-shaped invocation of the `fix`
      workflow writes no artifact containing the goal text
      (assert over the actual files written, not a mock).
      G5: the characterization pins are asserted to still hold
      as the named compatibility-regression check.
      G6: receipt-completeness property — every receipt the
      suite renders carries all required sections; and
      verification-failure honesty — every negative path emits
      a FAIL/SKIPPED row rather than a silent omission.
    </file>
    <file path="docs/features/fix.md (or the authored master path the projector owns)">
      Single-source `attune fix` feature master: what it does,
      the contract/receipt model, the exit contract, and an
      EXPLICIT statement of the `/fix-test` skill relationship
      (requirements: the surfaces must not blur). Projected to
      `.help` kinds + the docs page via the existing projector;
      never hand-written on both sides.
    </file>
  </files-to-create>

  <validation>
    <check>The existing 48 fix tests pass UNMODIFIED (Phase 1
      preview byte-identical, Phase 2 receipt semantics
      unchanged except the additive rows).</check>
    <check>G1: no-change + passing probes — receipt states the
      run changed nothing and does not advise committing a
      diff that does not exist.</check>
    <check>G2: multi-probe partial success names every failing
      probe.</check>
    <check>G3: the ops-path artifact assertion runs against
      real written files; the resulting decision (pin as-is vs
      redact) is recorded in decisions.md with the evidence.</check>
    <check>G4: the feature master exists, the projector runs
      clean, and the drift guard fails on a hand-edited
      projection (demonstrate the failure, don't assert it).</check>
    <check>G5+G6: the four D3 metrics are reported in the spec
      with the command that produced each number — no new
      telemetry, store, or lifecycle introduced (grep-checked).</check>
    <check>Coverage stays >=85% on the touched modules; serial
      keyless run.</check>
    <check>Declared receipt types: suite + behavioral +
      evidence-chain (G3's per-claim file assertions). NO
      live-fire, NO spend.</check>
  </validation>

  <risks>
    <risk severity="medium">Scope creep into Phase 4 routing
      metrics — mitigation: D3 defers every routing metric to
      Phase 4; this task reports FOUR metrics and no more.</risk>
    <risk severity="medium">G1's honesty change quietly altering
      the 0/1 boundary — mitigation: the exit rule is untouched;
      only rendering and next-action text change, pinned by the
      unmodified existing tests.</risk>
    <risk severity="low">The feature page tripping projector
      drift guards on first authorship — mitigation: author via
      the existing single-source path, run the projector, and
      commit both sides in one change.</risk>
  </risks>
</task>
```

**Acceptance (ruling Phase 3):** the remaining robustness paths
report truthfully, documented `attune workflow run` behavior is
preserved and named as the compatibility measurement, the
projected help/docs surface exists with a drift guard, prompt
text persistence is answered with evidence, and the four
ratified metrics are reported from suite-derived properties
with no new telemetry.

## Task 4 — Fix intake form (scope/probe picker, plugin surface)

**Authored 2026-07-31; chair go given in-session ("go", with
may-demo-Saturday framing — the CLI flow stays the demo fallback).
Input ergonomics only: no new execution surface, no NL inference,
the CLI contract is unchanged.**

```xml
<task id="4" name="fix-intake-form">
  <objective>
    Give interactive users a form-driven Fix intake: scope and
    probes picked from derived candidates instead of typed, the
    composed `attune fix` command previewed before any run.
    Fires on the plugin/skill surface only — `attune fix` itself
    stays bare argparse and scriptable.
  </objective>
  <context>
    <existing-code path="src/attune/elicitation/bridge.py">
      form_from_dict builds a validated FormSchema
      (single_select / multi_select / textarea supported);
      select_form_surface routes widget-first with
      AskUserQuestion fallback (D21).
    </existing-code>
    <existing-code path="src/attune/cli_commands/fix_commands.py">
      The CLI contract being composed: request positional,
      --workflow fix, repeatable --probe, --scope, --run.
    </existing-code>
    <constraint>
      Candidates are DERIVED, never hand-maintained: scope from
      git-changed paths (the likeliest fix target), probes from
      matching test files. No new YAML/registry (one source,
      projected; H3). Degrade to free-text fields when git or
      candidates are absent — the form never blocks.
    </constraint>
  </context>
  <files-to-create>
    <file path="src/attune/elicitation/fix_intake.py">
      scope_candidates(), probe_candidates(),
      build_fix_intake_form() -> FormSchema,
      compose_fix_command(answers) -> argv-safe string; a
      python -m entry printing the form as JSON and composing
      from answers JSON (the thin seam the skill calls).
    </file>
    <file path="plugin/skills/fix/SKILL.md">
      The /fix skill: helper -> form (rendered per the
      communication grammar) -> composed preview -> confirm ->
      --run -> receipt walkthrough. States the /fix-test
      relationship (requirements: surfaces must not blur).
    </file>
    <file path="tests/unit/elicitation/test_fix_intake.py">
      Real tmp git repos: candidate derivation, empty-repo
      degrade, form validity via form_from_dict, command
      composition quoting, shell-metacharacter safety.
    </file>
  </files-to-create>
  <validation>
    <check>Form builds validly with and without candidates.</check>
    <check>Composed command round-trips through the real
      `attune fix` preview (exit 0 with --workflow fix).</check>
    <check>plugin reference validation passes (skill names only
      real tools/paths).</check>
    <check>Skills mirror re-synced; projection gates green.</check>
  </validation>
  <risks>
    <risk severity="medium">Demo-eve timing — mitigation: the
      skill is additive; the CLI demo path is unchanged and
      remains the fallback if this lands after the cut.</risk>
    <risk severity="low">Trigger collision with /fix-test —
      mitigation: distinct trigger phrases + an explicit
      relationship note in both skill bodies.</risk>
  </risks>
</task>
```
