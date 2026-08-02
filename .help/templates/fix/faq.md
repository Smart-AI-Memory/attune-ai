---
type: faq
name: fix-faq
feature: fix
depth: faq
generated_at: 2026-08-02T16:17:23.326205+00:00
source_hash: 02c4fd57871efde0e308241968a30e45d0a63f6ba866385c62a363e28a5f4b4b
status: generated
---

# Fix FAQ

## Does a successful workflow run mean my fix worked?

No. The workflow's exit is never trusted. Only the probes, run
independently by the CLI after the fix, decide the outcome.

## What happens if the agent edits a file outside my scope?

The edit is denied at tool-call time by a `PreToolUse` guard,
and if anything still slipped through it is reported as a scope
violation with a non-zero exit and a targeted revert as the next
action.

## Will my own uncommitted work get blamed on the run?

No. Paths dirty before the run are attributed as pre-existing
and are never named in revert advice.

## Is `attune fix` the same as the `/fix-test` skill?

No. `/fix-test` diagnoses failing tests conversationally in
Claude Code; `attune fix` takes an outcome you have already defined
and returns a verified, attributed receipt from the CLI.

## Is my request text stored anywhere?

The `attune fix` command persists nothing — the contract lives
for the length of the run.

## Can I use it without a scope?

Only for previews. `--run` requires `--scope`.
