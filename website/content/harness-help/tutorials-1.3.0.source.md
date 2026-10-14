# Four training walkthroughs for Harness 1.3.0

These short processes open the Navigation, Specification Workflow, Four
Workflows and Session Continuity tutorials. They describe released
[Harness 1.3.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.3.0),
at commit `0ecf8e6058cee9ed6f9b9510e043e3af3cbe1da0`. The matching editable
PowerPoint and HTML tutorials use the action tables below as their instruction
source. Keep those tables, expected results and limits together when revising
the training files. The concepts that follow the walkthroughs remain useful
for real work, where participants, scope and independent review matter.

Control names are bold; literal values and commands use code font. Writing
follows the [Google developer documentation style guide](https://developers.google.com/style),
with agreed project exceptions. Match verified labels and use accessible names
for icons. Preserve the tutorials' visual design.

## Navigation: an accepted intent

Deck title: **Start and continue work**.

<!-- walkthrough:navigation -->
Title: What happens when you accept an intent?

Prerequisite: Harness 1.3.0 with a registered editable draft missing its goal and success criteria.

| Step | Action |
| --- | --- |
| 1 | Click **Continue form**. |
| 2 | In “**What should this work accomplish?**”, enter “`Group saved work by the decision it needs`”. |
| 3 | In “**What observable result establishes success? Enter one item per line.**”, enter “`Each saved task shows its next decision`”. |
| 4 | Click **Save answers**. |
| 5 | Click **Review your answers**. Check the goal, success criteria and allowed files. |
| 6 | If those answers are correct, click **Accept this intent**. |

Expected: **Saved work** shows “Intent accepted”. Execution requires separate authority.

Limit: Browser build dispatch and execution resume are unavailable in 1.3.0.
<!-- /walkthrough -->

Launch the forms for your existing canonical task directory:

```sh
python -m attune_harness.gui --task /absolute/path/to/task --edit --launch-json
```

Keep the listener running and open the returned private `launch_url`. The JSON
reports `editable: true` and `execution_enabled: false`. This command registers
saved work; it does not create a new task. With `--launch-json`, it leaves browser
opening to you. Treat the launcher link as private access information. Read
[browser forms in the CLI guide](cli-guide.md#plan-and-build) for the complete
boundary. A trainer can prepare the blank draft with the fixture below.

## Specification workflow: preview and acceptance

<!-- walkthrough:spec-workflow -->
Title: How does a sample plan become accepted?

Prerequisite: Harness 1.3.0. P = prepared Git checkout, T = new task outside P, R = release checkout, PY = active Python.

| Step | Action |
| --- | --- |
| 1 | Run: `attune-harness init --for plan --goal "Repair addition" --project "$P" --scope calc.py --interpreter "$PY" --tests tests/test_calc.py --task-dir "$T"` |
| 2 | Run: `attune-harness plan --request "$T.work.json" --project "$P" --config "$R/examples/starter/participants.json" --task-dir "$T"`. Copy `checkpoint_digest` into `C`. |
| 3 | Inspect the preview. If its scope is correct, run: `attune-harness plan --task-dir "$T" --accept --checkpoint "$C"` |

Expected: JSON shows status “accepted”. calc.py still contains a - b.

Limit: Acceptance starts no build. The starter reviewer approves without judging.
<!-- /walkthrough -->

This is a released CLI alternative to the proposed specification editor. Use a
fresh disposable Git checkout, not a working project. Activate the environment
with Harness 1.3.0 first. `examples/` comes from a repository checkout, not the
installed package. Set `R` to an absolute checkout path at the pinned release
commit. Set `P` and `T` to unused absolute paths, with `T` outside `P`. For
example, after setting `R`:

```sh
P="$PWD/training-plan-project"
T="$PWD/training-plan-task"
PY="$(python -c 'import sys; print(sys.executable)')"
mkdir -p "$P/tests"
printf 'def add(a, b):\n    return a - b\n' > "$P/calc.py"
printf 'from calc import add\n\ndef test_add():\n    assert add(2, 2) == 4\n' > "$P/tests/test_calc.py"
git init "$P"
git -C "$P" add calc.py tests/test_calc.py
git -C "$P" commit -m "Training fixture"
```

Run the three actions. Set `C` to the full `checkpoint_digest` returned by step
2, for example `C='the-full-returned-digest'`. It changes with your task; do not
copy a digest from someone else's report. Step 1 returns `created` and writes
`$T.work.json` beside the task directory. Step 2 returns `draft` with no missing
questions for this fixture. Step 3 returns `accepted`. Confirm with:

```sh
attune-harness status "$T"
```

This process stops before `build`. It exercises request creation and the
checkpoint-bound acceptance decision. It does not prove that a plan is good or
that an independent reviewer judged it. For real participants and build
authority, read [Plan and build](cli-guide.md#plan-and-build).

## Four workflows: research a question

<!-- walkthrough:four-workflows -->
Title: What can you check in a local source?

Prerequisite: A normal Harness 1.3.0 installation includes rag and verify. E = copied local-workflow example directory.

| Step | Action |
| --- | --- |
| 1 | Run: `attune-harness retrieve "quartz retention policy" --corpus "$E/project" --output "$E/retrieval-report.json"` |
| 2 | Read retrieval-report.json, then project/reference.md. Inspect both returned sources. |
| 3 | Run: `attune-harness verify "$E/project/guide.md" --context "$E/context.json" --output "$E/verification-report.json"` |
| 4 | Read verification-report.json. Check status, passed, coverage and semantic_ran. |

Expected: Two matching sources. Verification shows “verified”, passed true and one link claim.

Limit: semantic_ran is false. This example establishes link validity, not policy correctness.
<!-- /walkthrough -->

With the release checkout `R` from the previous section, copy its example into
a new directory outside that checkout. Set `E` to the absolute copy path:

```sh
E="$PWD/training-research"
cp -R "$R/examples/local-workflow" "$E"
```

Use a fresh copy so report output paths do not replace prior evidence. The
query matches `guide.md` and `reference.md`; each result carries an excerpt
and a source hash. The verification result has `coverage.total: 1` and
`coverage.verified: 1`. Its claim kind is `links`, subject `reference.md`, at
line 3 of the guide. `semantic_ran: false` rules out a semantic policy verdict.
This offline sample makes no model calls. The tutorial's later concepts also
cover picking an opportunity, scoped repair and resuming saved work. Read
[Local verification and retrieval](local-workflow.md) for dependency and input
limits.

## Session continuity: saved answers in another session

<!-- walkthrough:session-continuity -->
Title: What survives a new form session?

Prerequisite: Harness 1.3.0 with a registered editable draft missing its goal and success criteria. TASK = its canonical directory.

| Step | Action |
| --- | --- |
| 1 | Click **Continue form**. |
| 2 | In “**What should this work accomplish?**”, enter “`Review quartz retention documentation`”. |
| 3 | Click **Save answers**. Leave the success question empty. |
| 4 | Stop the listener with `Ctrl-C`. Run: `python -m attune_harness.gui --task "$TASK" --edit --launch-json` |
| 5 | Open the new private `launch_url`. Click **Continue form**. |

Expected: “**Saved answers**” retains the goal above the empty success question.

Limit: Reopening a form continues intake. Eligible execution resumes through the CLI.
<!-- /walkthrough -->

Use the same task directory in both sessions, and a fresh private launcher link
after restarting. Opening a new form or restarting expires the earlier form
checkpoint. Saved answers remain in the task record. Unsaved text is not part
of this result. This process ends with the draft still `draft`; it grants no
execution authority. The later tutorial sections teach explicit saved memory,
project scope, revision and current execution evidence. See
[Save memories and task intent](memory-saving.md) for that separate CLI store.

## Trainer setup for the two form walkthroughs

Prepare a separate disposable fixture for each process. The following Python
uses the released work contract to create an intake draft with no goal or
success criteria. Run it with the active Harness 1.3.0 interpreter. Replace
`training-form` with an unused absolute directory. It makes no model calls.

```python
from pathlib import Path
import json
from attune_harness.work_contract import SIGNALS, create_work

root = Path('/absolute/path/to/training-form')
root.mkdir(parents=True, exist_ok=False)
project = root / 'project'
project.mkdir()
(project / 'source.py').write_text('def value():\n    return 1\n')
(project / 'plan.md').write_text('Keep saved tasks linked to their current decision.\n')
config = root / 'participants.json'
config.write_text(json.dumps({'schema_version': 1, 'participants': {
    'local': {'adapter': 'deterministic', 'tools': [], 'max_turns': 1,
              'max_tool_calls': 0}}}))
budget = {'max_operations': 20, 'max_attempts': 1, 'max_output_bytes': 10000}
create_work(project, config, directory=root / 'saved-task',
    intent={'goal': None, 'context': ['Training example'],
            'scope': ['source.py'], 'constraints': ['No implementation or model calls'],
            'acceptance': [], 'questions': []},
    signals={**dict.fromkeys(SIGNALS, False), 'existing_artifact': None},
    assignments=[{'role': 'planner', 'participant': 'local',
                  'output_contract': 'Bounded plan with observable checks',
                  'budgets': budget}],
    inputs=['source.py'], artifact='plan.md', budget=budget)
```

Launch with `--task /absolute/path/to/training-form/saved-task --edit
--launch-json`. This sample uses the Python API only to prepare training data.
It does not imply a released browser “New task” control.

## Verification and release boundary

All four processes ran against installed Harness 1.3.0 on macOS in isolated
synthetic tasks. The two browser sequences used fresh headless Chromium
contexts. Navigation reached `accepted`; continuity retained its saved goal
after a listener restart and remained `draft`. Planning returned `created`,
`draft`, then `accepted`; it changed no sample source and created no build run.
Retrieval returned two matching Markdown sources, and verification passed the
single supported link claim with semantic checks absent.

These observations establish those local sample outcomes. They do not qualify
Windows, real participant quality, paid-provider behavior or all possible
projects. No released code changed for this training update. The broader
workspace navigation, specification editor and browser execution/resume designs
are outside the 1.3.0 forms boundary.

The [released CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/0ecf8e6058cee9ed6f9b9510e043e3af3cbe1da0/docs/cli-guide.md),
[local workflow guide](https://github.com/Smart-AI-Memory/attune-harness/blob/0ecf8e6058cee9ed6f9b9510e043e3af3cbe1da0/docs/local-workflow.md)
and [saved memory guide](https://github.com/Smart-AI-Memory/attune-harness/blob/0ecf8e6058cee9ed6f9b9510e043e3af3cbe1da0/docs/memory-saving.md)
retain the implementation baseline independently of current development docs.
