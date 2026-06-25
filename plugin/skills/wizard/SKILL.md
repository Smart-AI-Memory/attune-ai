---
name: wizard
description: "Run a guided multi-step wizard (debug, refactor, release-prep, security, test-gen) conversationally. Triggers on: run a wizard, debug wizard, refactor wizard, security wizard, test-gen wizard, walk me through, guided wizard."
argument-hint: "<wizard id, or leave empty to list>"
---

# Wizard

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="wizard", mode="preamble")` and display the
returned `preamble` text as a blockquote. Then tell the user they can
say "tell me more" for a step-by-step guide, or answer the scoping
question below to proceed.

If the MCP call fails, fall back to:

> **Wizard** — Runs a guided, multi-step wizard. I'll show you the
> wizard's steps, ask you each question, then run it and present the
> result.

## Scoping

1. **Which wizard?** If the user didn't name one, list the registered
   wizards (id + description) and ask. Get the live list — never
   hand-author it:

   ```bash
   python -c "import json; from attune.wizards import list_wizards; print(json.dumps([{'id': w.wizard_id, 'description': w.description} for w in list_wizards()]))"
   ```

2. **Any starting context?** e.g. a file path or error message the
   wizard should begin from.

## Execution

This wizard runs on an interactive engine, so you (the model) drive it:
show the steps, collect the answers, then run it once with those
answers supplied.

1. **Inspect the steps** for the chosen wizard:

   ```bash
   python -c "import json; from attune.wizards import describe_wizard_steps; print(json.dumps(describe_wizard_steps('debug')))"
   ```

   Each entry has `id`, `type`, `name`, `description`; `question` steps
   also carry `questions` (in `AskUserQuestion` format).

2. **Ask the user the question-step questions** via `AskUserQuestion`
   (batch up to 4 at a time). Collect answers keyed by each question's
   `question_id`. `review`/`confirm` steps need no upfront answer — the
   engine auto-proceeds on their defaults this cut.

3. **Run the wizard** with the collected answers. Write them to a temp
   JSON file (avoids shell-quoting issues) and run:

   ```bash
   ANSWERS_JSON=/tmp/wizard_answers.json python -c "
   import json, os, asyncio
   from attune.wizards import run_wizard_prefilled
   answers = json.load(open(os.environ['ANSWERS_JSON']))
   result = asyncio.run(run_wizard_prefilled('debug', answers=answers, initial_context={}))
   print(json.dumps(result.to_dict() if hasattr(result, 'to_dict') else result.__dict__, default=str))
   "
   ```

   Pass `initial_context` (e.g. `{"target": "src/foo.py"}`) when the
   user gave a starting path or error.

## Output

Present the `WizardResult` readably: lead with `generated_output`, then
any `tasks` it produced (as a checklist), then run metadata (steps
completed, cost, duration). If `success` is false, surface `error`.

## How this differs from other skills

- **wizard** *runs* a guided flow step-by-step (this skill).
- **catalog** *lists* wizards (and workflows, agents, tools) but does
  not run them.
- **attune-hub** *routes* you to the right skill for a goal.

## Anti-Patterns

- DO NOT hand-author the wizard list or its steps — always read them
  live (`list_wizards()` / `describe_wizard_steps()`).
- DO NOT skip the question steps — collect every `question`-step answer
  before running, or the wizard runs with missing input.
- DO NOT use this to *create* a wizard — that is the authoring flow,
  not this runner.
