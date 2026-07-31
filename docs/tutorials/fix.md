# Tutorial: Outcome-First Fix

You'll finish this tutorial having watched `attune fix` repair a
real bug you seeded yourself — and, more importantly, having read
the receipt that *proves* it: which file changed, which
verification commands ran, and why the tool's own exit code can be
trusted. Then you'll do the same thing again without typing a
single path, using the `/fix` guided intake form in Claude Code.

## Prerequisites

- Python 3.10 or newer
- `attune-ai` 11.2.0 or newer (`pip install -U attune-ai`)
- A git repository to work in (scope verification uses git)
- For Step 5: the attune-ai plugin installed in Claude Code

## The idea in one paragraph

You state **what should be true** ("exactly 100 units should price
as bulk") and **how to check it** (a probe: any command whose exit
code verifies the claim, like `pytest`). Attune runs the fix, then
re-runs your probes itself, in a real subprocess, *after* the fix
agent has finished — and the receipt's verdict comes from those
probes, never from the agent's own opinion of how it did.

## Step 1 — Seed a bug you can verify

Create a scratch module with one off-by-one bug and a test suite
that catches it:

```bash
mkdir scratch_pricing
```

`scratch_pricing/pricing.py`:

```python
BULK_THRESHOLD = 100


def tier_for_units(units: int) -> str:
    """Orders of BULK_THRESHOLD units OR MORE are bulk."""
    if units > BULK_THRESHOLD:  # BUG: should be >=
        return "bulk"
    return "standard"
```

`scratch_pricing/pricing_suite.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pricing import tier_for_units


def test_boundary_order_is_bulk():
    assert tier_for_units(100) == "bulk"


def test_small_order_is_standard():
    assert tier_for_units(99) == "standard"


def test_large_order_is_bulk():
    assert tier_for_units(101) == "bulk"
```

Confirm the bug is real — the boundary test fails:

```bash
pytest scratch_pricing/pricing_suite.py
```

## Step 2 — Preview the contract (nothing runs)

```bash
attune fix "exactly 100 units should price as bulk" --workflow fix --scope scratch_pricing --probe "pytest scratch_pricing/pricing_suite.py"
```

Without `--run`, this is a dry preview. It renders the contract —
your goal verbatim, the derived done conditions, the constraints,
and the validated probes — and ends with:

```text
note: execution not requested — pass --run to execute this contract
dry preview — nothing was executed
```

Read the "Done when" list carefully. This is the checkpoint where
you confirm the probes actually test what you meant.

## Step 3 — Run it and read the receipt

Arrow-up and append `--run`. The fix workflow edits the code, then
the CLI verifies independently:

```text
workflow finished (success=True) — verifying independently...

🧾 Fix receipt

Changes made (attributed to this run):
  - scratch_pricing/pricing.py
Probes (evaluated independently):
  - [PASS] pytest scratch_pricing/pricing_suite.py (exit 0, 2902ms)
Safest next action: review the attributed diff and commit
receipt reflects independently evaluated probes — workflow exit was not trusted
```

Three things to notice:

1. **Attribution is measured, not claimed.** The receipt compares
   against a pre-run snapshot. Files you already had in flight are
   listed separately as pre-existing and never blamed on the run.
2. **The probe was re-run by the CLI**, argv and exit code
   recorded. The workflow saying `success=True` did not decide
   anything — the trailer line says so explicitly.
3. **The exit code follows the probes.** `echo $?` prints 0 only
   because every probe passed, the diff stayed inside
   `scratch_pricing`, and scope was verifiable.

Check the diff yourself — the fix should be `>` → `>=` in
`pricing.py`, and the tests untouched:

```bash
git diff scratch_pricing/
```

## Step 4 — Verify more than one thing

Plural probes are the point. A target probe plus a full-suite probe
tells you the fix worked *and* broke nothing:

```bash
attune fix "exactly 100 units should price as bulk" --workflow fix --scope scratch_pricing --probe "pytest scratch_pricing/pricing_suite.py::test_boundary_order_is_bulk" --probe "pytest scratch_pricing/pricing_suite.py" --run
```

Each probe becomes its own line in the receipt, evaluated
independently. If any fails, the receipt names every failing probe
with its exact command, and the exit code is 1.

## Step 5 — The same flow without typing paths (`/fix`)

In a Claude Code session with the attune-ai plugin, say:

```text
/fix exactly 100 units should price as bulk
```

The guided intake presents ONE form: your goal (carried from the
invocation), a **scope picker** whose options are derived from your
working tree's changed paths, a **probe picker** offering matching
test files, and a preview-vs-run choice. The composed
`attune fix ...` command is shown before anything executes — the
same contract, the same receipt, no paths typed from memory.

## Exit codes

| Exit | Meaning |
|---|---|
| 0 | every probe passed, scope held, and scope was verifiable |
| 1 | the run completed but a done condition failed |
| 2 | the workflow crashed (a partial receipt is still printed) |
| 3 | CLI error or abstention — nothing ran |

## Where to go next

- `attune fix` vs `/fix-test`: the skill diagnoses a failing test
  for you in conversation; `attune fix` verifies an outcome you
  state. Neither replaces the other.
- The full option reference lives in
  [reference/fix](../reference/fix.md); the design rationale in
  [architecture/fix](../architecture/fix.md).
