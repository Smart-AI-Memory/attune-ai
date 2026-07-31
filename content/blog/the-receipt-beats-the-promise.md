---
title: "The Receipt Beats the Promise: Shipping an AI Fix That Proves Itself"
date: "2026-08-01"
author: "Patrick Roebuck"
excerpt: "Every AI coding tool says it fixed your bug. attune fix has to prove it — with a receipt built from independently re-run verification commands. Then a cold UX review caught the receipt itself lying on the happy path, and the fix for that is the most interesting part of the story."
tags: ["verification", "receipts", "Claude Code", "attune fix", "AI workflows"]
coverImage: "/images/blog/fix-receipt-loop.svg"
published: false
---
# The Receipt Beats the Promise: Shipping an AI Fix That Proves Itself

Every AI coding assistant ends the same way: "Done! I've fixed the
issue." Sometimes it has. The problem is that the sentence looks
identical either way — and if you've worked with these tools long
enough, you've learned that "exited successfully" and "worked" are
different claims.

attune-ai 11.2.0 ships `attune fix`, and its design rule is one
sentence: **a successful workflow exit is never sufficient proof
that a done condition was satisfied.** You state the outcome and
how to verify it; the tool has to produce a receipt.

## The contract

```bash
attune fix "exactly 100 units should price as bulk" \
    --workflow fix \
    --scope scratch_pricing \
    --probe "pytest scratch_pricing/pricing_suite.py"
```

Three statements, all yours: the goal in your own words, the scope
the diff must stay confined to, and one or more probes — any
command whose exit code verifies the claim. Run bare, that renders
a preview of the contract and executes nothing. Add `--run` and the
fix executes — and then the part that matters happens.

## The receipt

After the fix agent finishes, the CLI re-runs every probe itself,
in a real subprocess, and takes its verdict from those exits — not
from the agent:

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

![Anatomy of a fix receipt — attribution, independent probes, next action, and the trailer, annotated](/images/blog/fix-receipt-anatomy.svg)

Attribution is measured against a snapshot taken before the run, so
your own in-flight edits are listed separately and never blamed on
the agent. Scope is enforced twice — a guard denies out-of-scope
edits at tool-call time, and the receipt re-checks the diff
afterward. A probe that can't run records SKIPPED with a reason; it
never silently counts as a pass.

## The receipt lied once — and that's the good part

Two days before release I asked for a cold review of the surface:
run it like a first-time user, before reading any docs. The
reviewer copied the demo fixture into an untracked scratch
directory — the most natural thing in the world — and got this:

```text
Changes made (attributed to this run):
  (none — this run changed no files)
Safest next action: nothing to commit — this run changed no files;
the done conditions were already satisfied before it ran
```

Which was false. The fix had landed; the probe had passed. The
receipt — the component whose entire job is honesty — was wrong on
the happy path.

The cause was a quiet git behavior: `git status --porcelain`
collapses an untracked directory to a single `dir/` entry,
identical before and after the run, and a directory can't be
content-hashed. So inside an untracked scope directory, nothing
was attributable, and the receipt concluded nothing had happened.

Worth pausing on: our own live-fire dogfood run had passed cleanly,
because it used a scratch copy that was its own git repository —
where git lists files individually. Same command, same flags; the
only difference was where `.git` sat. The receipt had been proven
for one git topology and trusted for all of them.

The fix expands directories to per-file hashes at baseline and
rescans them afterward, so created files are attributed too. It
shipped with a regression test that seeds exactly that untracked
scratch directory — and the false receipt is now impossible to
reproduce.

I'm telling this story rather than burying it because it's the
thesis, demonstrated on ourselves: the tool that says "trust the
receipt, not the promise" had a receipt bug, and it was caught by
running the real thing cold — not by the 91 unit tests that were
already green. Receipts beat promises all the way down.

## Composing the contract without typing paths

In a Claude Code session, the `/fix` skill gathers the whole
contract as one form: the goal, a scope picker derived from the
paths you've actually been changing, probe suggestions from
matching test files, and a preview-or-run choice. It shows you the
composed `attune fix` command before anything executes. Same
contract, same receipt — no paths from memory.

## Try it

```bash
pip install -U attune-ai
attune fix --help
```

The full tutorial — seed a bug, preview, run, read the receipt —
is in the docs. The spec, its decision log, and the receipt-bug
regression test are public in the repository, receipts included.
