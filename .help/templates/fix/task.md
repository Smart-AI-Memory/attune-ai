---
type: task
name: fix-task
feature: fix
depth: task
generated_at: 2026-07-31T11:22:57.025655+00:00
source_hash: 4069f8ae171ca3c4ccb53ebae95b598ce6d800fcd66ed605ccb4583f5d3f9290
status: generated
---

# Outcome-first fixes — state the goal and its probes, get a verified receipt

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
