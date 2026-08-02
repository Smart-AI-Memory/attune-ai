---
type: reference
name: fix-reference
feature: fix
depth: reference
generated_at: 2026-08-02T16:17:23.326205+00:00
source_hash: 02c4fd57871efde0e308241968a30e45d0a63f6ba866385c62a363e28a5f4b4b
status: generated
---

# Fix Receipts — state the goal and its probes, get a verified receipt

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
