---
name: fix
description: "Outcome-first fix with a guided intake form — pick scope and probes from derived candidates, preview the contract, run with a verified receipt. Triggers on: attune fix, scoped fix, fix with receipt, outcome fix, fix intake."
argument-hint: "<what should be fixed, in your words>"
---

# Fix (guided intake)

**IMPORTANT: Start your response by telling the user:**

> **Fix** — Composing an outcome-first fix: goal, scope, and
> verification probes, then a preview before anything runs.

## What It Does

Interactive intake for `attune fix` (the outcome-first Fix surface,
`docs/specs/outcome-first-fix/`): one form gathers the goal, the
`--scope` the diff must stay confined to, and the `--probe`
commands that verify the fix — with scope and probe options DERIVED
from the working tree (changed paths and matching test files), not
typed from memory. The composed CLI command is previewed before any
execution; the receipt independently verifies every probe.

Relationship to `/fix-test`: that skill diagnoses and fixes a
FAILING TEST in-session. This skill drives the `attune fix` CLI
contract — goal + scope + probes + receipt — for any code fix.
Neither replaces the other.

## Step 1 — Derive candidates and build the form

```bash
python -m attune.elicitation.fix_intake
```

The JSON payload contains a validated form definition
(`attune.elicitation.fix_intake.build_fix_intake_form`) plus the
derived `scopes` and `probes` lists. If the user's invocation
already stated the goal, carry it into the request field as the
default rather than asking again.

## Step 2 — Render the form (communication grammar)

Render ONE form — request, scope, probes, mode — per the Socratic
rule: widget surface when available, `AskUserQuestion` fallback
(batch the questions; `metadata.source` containing "form" opts into
the batch). Never ask these as sequential single questions. When a
field came back with no derived options it is free text — accept a
path or command, do not invent options.

## Step 3 — Compose and preview

```bash
echo '<answers JSON>' | python -m attune.elicitation.fix_intake --compose
```

Run the composed command WITHOUT `--run` first and show the user
the rendered contract preview (goal, done conditions, constraints,
probes). This is the checkpoint: the user confirms or edits before
anything executes.

## Step 4 — Run and read the receipt

On confirmation (or when the form answered "preview then run"),
re-run with `--run`. Walk the user through the receipt:

- **Changes made (attributed to this run)** — what the fix touched,
  measured against a pre-run baseline, never blamed onto the user's
  in-flight work.
- **Probes (evaluated independently)** — each verification command
  re-run outside the workflow; the workflow's own exit is never
  trusted as success.
- **Safest next action** — worst problem first; on full success,
  "review the attributed diff and commit".

Exit codes: 0 all probes passed and scope held; 1 a done condition
failed; 2 the workflow crashed (partial receipt printed); 3 CLI
error or abstention — nothing ran.
