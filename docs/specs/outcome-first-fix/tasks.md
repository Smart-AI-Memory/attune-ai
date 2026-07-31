# Outcome-First Fix — Tasks

**Status:** active (2026-07-30) — Task 0 executed
(chair-authorized; PR #1806, acceptance MET — see
[phase0-inventory.md](phase0-inventory.md)); Task 1 authored,
awaiting its own chair go before execution. This file carries
the executed log plus the next executable unit only; later phase
tasks are authored per-phase behind chair gates (decisions.md
D2).

## Executed log

- **Task 0 — Phase 0 characterization proof** (PR #1806):
  seam inventory dry-trace-checked, canonical fixture live at
  `tests/fixtures/outcome_first_fix/`, 24 characterization pins
  green keyless. Premise corrections recorded in the inventory:
  exit-code contract already 0/1/2/3 (legacy no-`success`
  loophole documented); keyless NL fix-routing goes to
  bug-predict at 0.17 confidence with no abstention.

## Task 1 — Phase 1: dry explicit Fix contract

```xml
<task id="1" name="outcome-first-fix-phase1-dry-contract">
  <objective>
    Ship the smallest internal boundary DTO (goal, done
    conditions, constraints, verification probes) and a dry
    `attune fix "<request>" --explain` preview that validates the
    contract and names the selected existing workflow WITHOUT
    executing anything. Truthful preview or abstention on every
    input class; no universal public outcome schema.
  </objective>

  <context>
    <existing-code path="src/attune/cli_minimal.py">
      Subparser registration pattern (_add_workflow_subparsers,
      _add_diagnose_subparser). `attune fix` becomes a sibling.
    </existing-code>
    <existing-code path="src/attune/cli_commands/_exit_codes.py">
      Exit contract 0/1/2/3 (pinned by Phase 0). Phase 1 uses:
      0 = truthful preview rendered; 3 (EXIT_CLI_ERROR) =
      invalid input OR abstention (insufficient input to
      preview truthfully). No new exit codes.
    </existing-code>
    <existing-code path="src/attune/workflows/__init__.py">
      get_workflow/list_workflows — the ONLY selection surface.
    </existing-code>
    <existing-code path="tests/fixtures/outcome_first_fix/">
      Canonical scenario; representative preview input in tests.
    </existing-code>
    <constraint>
      NO execution paths: Phase 1 never runs a workflow, never
      spawns a probe subprocess, never writes files. Probes are
      VALIDATED (well-formed argv list, no shell string), not
      run. No LLM calls; all behavior keyless-deterministic.
    </constraint>
    <constraint>
      Selection must abstain safely: `--workflow <name>` is the
      only selection input in Phase 1. Given and registered ->
      selected; given and unknown -> exit 3 naming the failure;
      absent -> ABSTAIN (exit 3) listing registered candidates.
      No inference, no default guess — a false confident route
      is worse than abstention (ruling).
    </constraint>
    <constraint>
      The DTO is internal (gate 2): dataclass in
      src/attune/cli_commands/fix_commands.py, no JSON schema
      published, no import promise outside attune.*. Docstring
      states this explicitly.
    </constraint>
  </context>

  <files-to-create>
    <file path="src/attune/cli_commands/fix_commands.py">
      VerificationProbe (argv list + description + expected exit)
      and FixContract (goal, done_conditions, constraints,
      probes) dataclasses; build_contract(args) mapping CLI flags
      -> contract with validation (goal = request verbatim —
      no inference; probes from repeated `--probe "<argv>"`
      flags, shlex-split, never shell-executed; optional
      `--scope <path>` constraint validated inside the repo via
      the existing path-validation helper); cmd_fix(args)
      rendering the preview: contract fields, selected workflow
      (or abstention), and a "dry preview — nothing was
      executed" trailer line. Preview is non-blocking: it never
      prompts; anything unresolvable is abstention text + exit 3.
    </file>
    <file path="tests/unit/cli_commands/test_fix_commands.py">
      Keyless unit coverage (>=85% on the new module):
      representative input (canonical-scenario probes ->
      truthful preview, exit 0, trailer present); ambiguous
      input (no probes -> abstention naming --probe, exit 3;
      no --workflow -> abstention listing candidates, exit 3);
      risky input (unknown workflow -> exit 3; --scope escaping
      the repo -> rejected via path validation; probe given as
      shell metacharacters -> rejected, never interpreted);
      truthfulness (preview output contains NO claim of
      execution, selection, or verification beyond what
      happened).
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/cli_minimal.py">
      <change location="subparser registration block">
        BEFORE: no `fix` subparser (namespace verified free,
        Phase 0).
        AFTER: _add_fix_subparser wiring `attune fix
        "<request>" [--explain] [--workflow N] [--probe CMD]...
        [--scope PATH]` to cmd_fix. In Phase 1 the bare form
        behaves exactly like --explain plus one notice line that
        execution arrives in a later phase — no divergence
        between the two paths.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>New unit suite passes serially and keyless
      (ANTHROPIC_API_KEY=""); no test mocks the contract
      validation it claims to cover.</check>
    <check>Phase 0 characterization suite still passes
      unmodified — `attune workflow run`, router, and exit-code
      pins unaffected.</check>
    <check>`attune fix "x" --workflow no-such --explain` exits 3;
      `attune fix "x" --explain` (no probes, no workflow)
      abstains with exit 3; canonical-scenario invocation
      previews truthfully with exit 0 — each proven through the
      real CLI entry (subprocess or main() call), not only unit
      calls.</check>
    <check>grep confirms no subprocess/exec/file-write calls in
      fix_commands.py (preview is dry by construction); the
      path-validation gate test stays green.</check>
    <check>Coverage on changed code >=85% locally; codecov
      project + patch gates green.</check>
  </validation>

  <risks>
    <risk severity="medium">Scope creep from "preview" into
      "almost executed" — mitigation: the no-execution
      constraint is grep-checked in validation and the trailer
      line is pinned by tests.</risk>
    <risk severity="medium">The DTO leaking public (gate 2) —
      mitigation: internal-only docstring + no schema emission;
      Phase 3 drift guards extend this.</risk>
    <risk severity="low">Advertised-command/help gates flagging
      the new subcommand — mitigation: run the gates suite; add
      the minimal registration the gate requires without
      authoring user-facing docs (Phase 3 owns docs).</risk>
  </risks>
</task>
```

**Acceptance (ruling Phase 1):** representative, ambiguous, and
risky inputs produce truthful previews or abstention. No
universal public outcome schema is promised.
