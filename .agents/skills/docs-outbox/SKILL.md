---
name: docs-outbox
description: "Sweep the docs outbox — dedupe, lint, and digest pending small docs (lessons, reports, drafts), then chair-approve via chip into ONE batched PR. Triggers on: docs outbox, outbox sweep, sweep the outbox, pending docs, outbox status, approve digest."
---
# Docs Outbox

**IMPORTANT: Start your response by telling the user:** you are
running the docs-outbox sweep — it composes a digest for approval
and never ships anything on its own.

## What It Does

Small docs artifacts (lessons, roundtable reports, process drafts,
plans) land as per-artifact timestamped files in
`~/.attune/docs-outbox/` instead of shipping as their own PRs.
This skill runs the curating sweep: dedupe, lint, core-worthy
flagging, ONE digest — then the chair approves via chip before a
single batched PR opens. `decisions.md` rulings and spec status
flips NEVER route here; they merge now (R2).

Invariants:

- No auto-shipping — the chair (or their chip-spawned session)
  approves the digest before any PR opens (R4).
- One swept PR per approval, auto-merge, containing every clean
  artifact in timestamp order.
- Artifacts with lint issues stay in the outbox untouched.

## Step 1 — status

Version preflight first: if `python -m attune.docs_outbox status`
fails with "No module named attune.docs_outbox", the installed
`attune-ai` wheel predates this module — upgrade it
(`pip install --upgrade attune-ai`) before continuing rather than
working around it with PYTHONPATH.

Run `python -m attune.docs_outbox status`. If the outbox is empty,
say so and stop. If the status line says STALE (oldest 2+ days),
surface the warning prominently.

## Step 2 — sweep

Run `python -m attune.docs_outbox sweep` from the repo root and
show the digest to the user verbatim (it is one screen: pending
count, per-artifact table with core-worthy / related-slug / lint
flags, dropped exact duplicates).

## Step 3 — chip approval

Present the digest as a chip via the `spawn_task` tool:

- title: `Approve docs-outbox digest (N docs)`
- tldr: one sentence — how many docs, oldest age, any flags.
- prompt: the digest text, plus instructions for the spawned
  session: create a branch off origin/main, run
  `python -m attune.docs_outbox apply --repo-root .`, review the
  diff, commit (`docs(outbox): sweep N artifacts`), push, open ONE
  auto-merge PR, and report skipped artifacts.

If the surface has no `spawn_task` tool, show the digest and ask
the user directly whether to apply — same contract, no chip.

## Step 4 — after approval

The spawned (or continuing) session applies, opens the PR, and the
applied artifacts move to `~/.attune/docs-outbox/swept/<date>/`.
Nothing else to do here — the outbox row on the ops Collaboration
page clears once the sweep lands.
