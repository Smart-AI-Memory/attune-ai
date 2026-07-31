# Shooting Script: Outcome-First Fix (video tutorial)

Target length: ~3.5 minutes. One terminal window (large font, dark
theme) plus one Claude Code panel for the final scene. Every
command below is real — rehearse once against
`docs/tutorials/fix.md` (the written version) so outputs match.

Pre-roll checklist:

- `pip install -U attune-ai` (11.2.0+), `attune fix --help` renders
- fresh scratch dir seeded per the tutorial (bug IN place)
- terminal history cleared; prompt short (`$`)

---

## Scene 1 — The promise problem (0:00–0:25)

**Screen:** empty terminal, then run the failing suite.

```bash
pytest scratch_pricing/pricing_suite.py
```

**Narration:** "Every AI coding tool tells you it fixed your bug.
Almost none of them can prove it. This is `attune fix` — you state
the outcome you want and how to verify it, and you get a receipt,
not a promise. Here's a real bug: orders of exactly 100 units
should be bulk-priced, and this test says they aren't."

**Beat:** let the red `1 failed, 2 passed` sit on screen a moment.

## Scene 2 — State the outcome, preview the contract (0:25–1:10)

**Screen:** type the preview command.

```bash
attune fix "exactly 100 units should price as bulk" --workflow fix --scope scratch_pricing --probe "pytest scratch_pricing/pricing_suite.py"
```

**Narration:** "I state the goal in my own words. `--scope` is the
only place the diff is allowed to land. `--probe` is any command
whose exit code verifies the claim — here, the test suite. Notice
what happens: nothing. This is a preview. It shows me the
contract — the done conditions, the constraints, the probes — and
tells me nothing was executed. This is where I check that my
probes test what I actually meant."

**Beat:** zoom or highlight the `Done when:` block and the last
line `dry preview — nothing was executed`.

## Scene 3 — Run it, read the receipt (1:10–2:10)

**Screen:** arrow-up, append ` --run`, execute. Wait through the
run; the receipt prints.

**Narration:** "Now the same command with `--run`. The fix agent
edits the code — and then the part that matters: attune re-runs my
probe itself, in a separate process, after the agent is done. The
receipt says exactly one file changed, attributed against a
snapshot taken before the run — my own in-flight edits can't get
blamed on the agent. The probe passed, with the exit code and
duration recorded. And read the last line: the workflow's own exit
was not trusted. The agent doesn't grade its own homework."

**Beat:** highlight three lines in order: `Changes made`, the
`[PASS]` probe row, the trailer
`receipt reflects independently evaluated probes`.

**Screen:** prove it:

```bash
git diff scratch_pricing/
echo $?
```

**Narration:** "One character: greater-than became
greater-or-equal. Tests untouched. Exit code zero — and zero here
means the probes passed, not that the agent felt good about it."

## Scene 4 — Guided intake in Claude Code (2:10–3:05)

**Screen:** Claude Code panel. Type:

```text
/fix exactly 100 units should price as bulk
```

**Narration:** "In Claude Code the same contract composes itself.
One form: my goal is already filled in, the scope picker offers the
paths I've actually been changing, the probes are matching test
files — nothing typed from memory. It shows me the composed
command before anything runs. Same preview, same run, same
receipt."

**Beat:** click through the form deliberately; pause on the
composed command line before confirming.

## Scene 5 — Close (3:05–3:30)

**Screen:** the receipt from scene 4, then a title card.

**Narration:** "State the outcome. Bound the scope. Name the
verification. And keep the receipt. `attune fix` ships in
attune-ai 11.2.0 — pip install attune-ai, and the written tutorial
is linked below."

**Title card:** `attune fix — the receipt beats the promise` +
install command + docs URL.

---

## Cutaway / caption notes

- Caption scene 3's trailer line verbatim — it is the thesis.
- If a take's receipt shows `Pre-existing changes`, keep it and
  improvise one line ("my own edits, listed separately, never
  blamed on the agent") — it demonstrates attribution honestly.
- Do not trim the preview beat; the no-execution default is the
  demo's trust moment.
