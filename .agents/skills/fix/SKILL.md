---
name: fix
description: "Fix Receipts — outcome-first fixing: guided intake picks scope and probes, previews the contract, runs with a verified receipt. Triggers on: attune fix, fix receipts, scoped fix, fix with receipt, outcome fix, fix intake."
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
derived `scopes` and `probes` lists. Changed paths lead; on a clean
tree the candidates fall back to recently-touched directories from
git history, so pickers render in either state — empty lists mean
the repo has no usable history at all. If the user's invocation
already stated the goal, carry it into the request field as the
default rather than asking again.

## Step 2 — Render the form (communication grammar)

Render ONE form — request, scope, probes. The enhanced
widget is the DEFAULT surface: build the `FormSchema` from the
Step 1 payload, route it through `select_form_surface`, and when
it returns "widget" render `form_to_widget_html(form)` on the
widget surface — answers post back as an
`__elicitation_response__` payload; parse them with
`collect_form_response`. Carry an already-stated goal into the
request field as its default.

Fall back to `AskUserQuestion` ONLY when no widget surface exists
(batch the questions; `metadata.source` containing "form" opts
into the batch). Never ask these as sequential single questions —
and never hand-write the ask turn without consulting
`select_form_surface` first: steering that names the fallback
concretely gets the fallback executed. When a field came back with
no derived options it is free text — accept a path or command, do
not invent options.

When the user picks the "other (type a path)" scope option, offer a
folder drill-down instead of bare free text:

```bash
python -m attune.elicitation.fix_intake --list-dirs .
```

Render the returned `dirs` as pills plus a "use this folder" pill
for the current `path`; on a pick, re-run `--list-dirs` with the
picked directory and repeat until "use this folder" (or a typed
path) settles the scope. The payload validates paths against the
repo root — an `error` key means degrade to free text.

## Step 3 — Compose and preview

```bash
echo '<answers JSON>' | python -m attune.elicitation.fix_intake --compose
```

Run the composed command WITHOUT `--run` first and show the user
the text preview only when the dynamic workspace tools are unavailable.

On the normal path, pass the validated Step 2 responses to
`fix_workspace_preview`. It rebuilds the CLI contract, normalizes the
repo-relative scope, hashes the exact future argv, stores canonical
server state, and returns workspace HTML plus a Markdown fallback. Pass
the HTML to the widget surface when available; otherwise show the
Markdown. Do not hand-build or modify the workspace, binding, nonce, or
hash. Nothing has executed at this checkpoint.

## Step 4 — Validate approval, then run and read the receipt

Parse the workspace's `__elicitation_response__` JSON and pass it
unchanged to `fix_workspace_collect_action`. An `edit_contract` result
invalidates the old preview; return to the intake, then call
`fix_workspace_preview` again with its `workspace_id` and the revised
answers. A failed action result is terminal for that response — never
repair a nonce, revision, or hash yourself.

Only a successful `run_fix` result authorizes execution. Execute the
returned `approved_command_argv` exactly once through the existing CLI
boundary; never reconstruct it from the rendered widget or the original
form answers. The action validator itself executes nothing and consumes
the nonce before returning, so stale or replayed clicks fail closed.
Walk the user through the resulting receipt:

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
