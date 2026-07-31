---
feature: fix
summary: Outcome-first fixes — state the goal and its probes, get a verified receipt
tags: [fixes, verification, cli]
source_globs:
  - src/attune/cli_commands/fix_commands.py
  - src/attune/cli_commands/fix_receipt.py
  - src/attune/workflows/fix_workflow.py
nav:
  help: fix
  mkdocs:
    how-to: how-to/fix
    architecture: architecture/fix
    reference: reference/fix
---

## Overview

`attune fix` is the outcome-first entry point: you state **what should
be true** and **how to check it**, and Attune reports what it actually
did with evidence. You do not pick a workflow tier, write a prompt, or
read an internal report format.

Two artifacts carry the whole surface:

- the **contract** — your goal, its done conditions, the scope the fix
  may touch, and one or more verification **probes** (each an argv
  list, never a shell string);
- the **receipt** — what changed (attributed against a pre-run
  baseline), which probes ran with their exact argv and exit codes,
  what remains uncertain, and the safest next action.

The rule that makes the receipt worth reading: **the workflow's own
exit never decides success.** Probes are executed by the CLI after the
fix agent finishes, in a real subprocess, and their results alone set
the exit code.

> **Scope — `attune fix` vs the `/fix-test` skill.** These are
> different surfaces and neither replaces the other. **`attune fix`**
> is a CLI command: you supply the goal and the probes, and it returns
> a verified receipt. **`/fix-test`** is a skill on the Claude Code
> conversational surface that auto-diagnoses failing tests and iterates
> on them for you. Reach for `/fix-test` when you want the diagnosis
> done for you in conversation; reach for `attune fix` when you already
> know the outcome you want and need it verified and attributed.

## Concepts

### The contract is data, not a prompt

`FixContract` holds the goal verbatim — no inference — plus done
conditions, constraints, and probes. It is an **internal** boundary
DTO: no JSON schema is emitted and no import stability is promised
outside `attune.*`. It stays internal until at least two outcome
intents demonstrate identical semantics.

### Probes are argv, and they are the authority

`VerificationProbe` holds an argv list and an expected exit code.
Probe strings containing shell metacharacters (`;` `|` `&` `<` `>`
`` ` `` `$`) are rejected outright rather than silently treated as
literals — probes are never run through a shell. Every probe runs
through `subprocess.run` **after** the fix, and the receipt records the
argv, return code, and duration as provenance.

A probe that cannot run records `SKIPPED` with a reason and appears
under remaining uncertainty. It never silently counts as a pass.

### Scope is enforced twice

Prevention: the fix workflow installs a `PreToolUse` guard that denies
`Edit`/`Write` outside the contract's scope paths at tool-call time.
Detection: the receipt re-checks the post-run diff against the pre-run
baseline and reports any out-of-scope path as a violation, forcing a
non-zero exit.

### Attribution is measured from a pre-run baseline

Before execution, `attune fix` snapshots the dirty-path set and content
hashes. Only paths that changed **relative to that snapshot** are
attributed to the run. Files you already had in flight are listed
separately as pre-existing and are never named in revert advice.

If git is unavailable, scope cannot be verified at all — the receipt
says so and the run does not report success, because passing probes
would prove the goal but not the scope constraint.

## Quickstart

Preview a fix without executing anything (the default — nothing runs,
nothing is written):

```bash
attune fix "boundary order must price as bulk" --probe "python -m pytest tests/test_pricing.py -q"
```

Execute it, scoped to one file:

```bash
attune fix "boundary order must price as bulk" --workflow fix --scope src/pricing.py --probe "python -m pytest tests/test_pricing.py -q" --run
```

Read the exit code:

| Exit | Meaning |
|---|---|
| 0 | every probe passed, scope held, and scope was verifiable |
| 1 | the run completed but a done condition failed or could not be verified |
| 2 | the workflow crashed (a partial receipt is still printed) |
| 3 | CLI error or abstention — nothing ran |

## Tasks

### Preview before you commit to a run

Run without `--run`. The preview prints the goal, the derived done
conditions, the constraints, and the validated probes, then states that
nothing was executed. Use it to check that your probes say what you
meant before spending a run.

### Scope a fix to one file or directory

Pass `--scope <path>`. The path is validated against the enclosing
repository root, so any spelling — relative, absolute, or `./`-prefixed
— resolves to the same place. A directory scope permits edits to its
descendants. `--run` requires `--scope`: an unbounded fix is not
runnable.

### Verify with more than one probe

Repeat `--probe`. Each probe becomes its own done condition, and the
receipt reports each independently. Plural probes are the point — one
probe that is also the fix target proves very little, whereas a target
probe plus a full-suite probe plus a scope constraint tells you the fix
worked *and* broke nothing.

### Read a failed run

When probes fail, the receipt names **every** failing probe with its
exact command, so re-running verification is a copy-paste. If the run
changed no files at all, the receipt says that plainly rather than
advising you to inspect a diff that does not exist.

### Recover from a scope violation

The receipt lists the out-of-scope paths by name and the next action is
a targeted revert. Pre-existing dirty paths are excluded from that
advice by construction.

## Reference

### CLI

`attune fix "<request>" [--probe CMD]... [--workflow NAME] [--scope PATH] [--explain] [--run]`

| Flag | Effect |
|---|---|
| `--probe CMD` | A verification command as an argv string. Repeatable. At least one is required. |
| `--workflow NAME` | Which registered workflow performs the fix. Without it, selection **abstains** and lists candidates rather than guessing. `--run` accepts only `fix`. |
| `--scope PATH` | Bound the edit surface. Required with `--run`. |
| `--explain` | Preview only, suppressing the "pass --run" notice. |
| `--run` | Execute the contract, then verify it independently. |

### Python

`attune.cli_commands.fix_commands` — `FixContract`,
`VerificationProbe`, `build_contract(args)`, `cmd_fix(args)`.

`attune.cli_commands.fix_receipt` — `capture_baseline(repo_root,
scope_paths)`, `run_probes(probes, cwd)`, `assemble_receipt(contract,
baseline, scope_paths, probe_outcomes)`, and the `ProbeOutcome` /
`FixReceipt` dataclasses. `FixReceipt.exit_code()` returns 0 only when
every probe passed, no scope violation was found, **and** scope was
verifiable.

`attune.workflows.fix_workflow` — `FixWorkflow` (registered as `fix`)
and `make_edit_scope_guard(scope_paths)`.

### Receipt sections

`Changes made` · `Pre-existing changes` (when present) · `SCOPE
VIOLATIONS` (when present) · `Probes (evaluated independently)` ·
`Remaining uncertainty` (when present) · `Safest next action`.

## Comparison

| | `attune fix` | `/fix-test` skill | `attune workflow run` |
|---|---|---|---|
| Surface | CLI | Claude Code conversation | CLI |
| You supply | goal + probes + scope | a failing test | workflow name + inputs |
| Verification | probes run by the CLI, independently | the skill re-runs the test as it iterates | whatever the workflow reports |
| Best for | a known outcome you want verified | a failure you want diagnosed | direct access to a specific workflow |

`attune workflow run` is unchanged and remains the expert path.
Outcome-first does not mean the internal machinery disappears — it
means you should not *need* it.

## Failure modes

**"no verification probes given — cannot verify a fix"** — a fix with
no probe cannot be verified, so the command abstains (exit 3) instead
of running something it could not check. Add `--probe`.

**"no --workflow given — selection abstains rather than guess"** — a
false confident route is worse than an abstention. Pass `--workflow
fix`.

**"probe contains shell metacharacters"** — probes are argv lists.
Rewrite the probe without pipes or redirection; if you need shell
semantics, put them in a script and probe the script.

**"cannot run: --run requires --scope"** — an unscoped fix has no edit
boundary to enforce, so `--run` refuses.

**"SCOPE NOT VERIFIED — no git available"** — attribution fell back to
content hashes of the declared scope files, so edits elsewhere are
undetectable. The run will not report success; review the tree by hand.

**Probe reported `SKIPPED`** — the command could not be executed (most
often a missing binary). This is uncertainty, not a pass; the exit code
is non-zero.

## FAQ seeds

- **Q:** Does a successful workflow run mean my fix worked?
  **A:** No. The workflow's exit is never trusted. Only the probes, run
  independently by the CLI after the fix, decide the outcome.
- **Q:** What happens if the agent edits a file outside my scope?
  **A:** The edit is denied at tool-call time by a `PreToolUse` guard,
  and if anything still slipped through it is reported as a scope
  violation with a non-zero exit and a targeted revert as the next
  action.
- **Q:** Will my own uncommitted work get blamed on the run?
  **A:** No. Paths dirty before the run are attributed as pre-existing
  and are never named in revert advice.
- **Q:** Is `attune fix` the same as the `/fix-test` skill?
  **A:** No. `/fix-test` diagnoses failing tests conversationally in
  Claude Code; `attune fix` takes an outcome you have already defined
  and returns a verified, attributed receipt from the CLI.
- **Q:** Is my request text stored anywhere?
  **A:** The `attune fix` command persists nothing — the contract lives
  for the length of the run.
- **Q:** Can I use it without a scope?
  **A:** Only for previews. `--run` requires `--scope`.

## Notes & tips

- Preview first. The preview costs nothing and catches malformed probes
  before a run.
- Prefer plural probes that are distinct from the fix target — a target
  probe plus a suite probe plus a scope constraint is the shape that
  actually proves something.
- The receipt distinguishes "changed nothing and the conditions already
  held" from "fixed and verified". If you see the former, check that
  your goal described a real gap.
- Probe subprocesses run with bytecode and pytest-cache writes disabled
  so their own artifacts are never mistaken for the fix's changes.

## Design & extension

The surface deliberately adds no new machinery. `FixWorkflow` is one
workflow in the existing registry, executed by the existing Agent SDK
adapter, returning the existing `WorkflowResult`. There is no new
planner, executor, evidence store, telemetry system, or execution
lifecycle — the receipt is computed from a baseline diff plus probe
subprocess results, both of which are read at the moment they are
needed.

Subprocess use is confined to `fix_receipt.py` (the probe runner and
git plumbing); `fix_commands.py` stays subprocess-free.

The DTO stays internal on purpose. Promoting it into a public
abstraction requires evidence that a second outcome intent shares its
semantics; if a second intent does not survive that test, a separate
adapter is the honest design rather than a forced universal model.

Full design record: `docs/specs/outcome-first-fix/`.
