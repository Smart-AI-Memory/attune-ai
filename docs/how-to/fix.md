# Fix

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

<!-- attune-generated: source_hash=8353dc181cc2bbc4f89d2c0e7750e99d9f99fe6786cb7cc1ce92a14ad2ab3762 feature=fix kind=how-to generated_at=2026-07-31 -->
