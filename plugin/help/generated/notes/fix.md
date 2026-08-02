---
name: fix
source: content/features/fix.md
tags:
- fixes
- verification
- cli
type: note
---

# Fix Receipts — state the goal and its probes, get a verified receipt

## Overview

`attune fix` is **Fix Receipts** — the outcome-first entry point: you
state **what should be true** and **how to check it**, and Attune
reports what it actually did with evidence. You do not pick a workflow
tier, write a prompt, or read an internal report format.

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
