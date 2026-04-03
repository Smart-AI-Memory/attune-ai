---
type: task
name: task-debugging-sessions
tags: [debugging, python, tools]
source: developer-guidance
---

# How to Systematically Debug a Problem

## Step 1: Reproduce the bug

Before fixing anything, make the bug happen on command.
A bug you can't reproduce is a bug you can't verify as
fixed.

- Run the exact command or test that triggers the failure
- Note the **full error message and stack trace** -- copy
  it, don't paraphrase
- Check: does it fail every time, or only sometimes?
- Check: does it fail on your machine only, or also in CI?

If you can't reproduce it, add logging around the suspected
area and wait for it to happen again. Guessing at fixes for
unreproducible bugs wastes time.

## Step 2: Read the stack trace

Python stack traces read **bottom to top**. The last frame
is where the error was raised, but the cause is often
higher up:

```
Traceback (most recent call last):
  File "main.py", line 12, in run       <-- caller
    result = process(data)
  File "process.py", line 45, in process <-- cause
    return data["key"]                    is often here
KeyError: 'key'                          <-- symptom
```

Look at each frame and ask: "Is the input to this function
what I expected?" The frame where the answer is "no" is
where the real bug lives.

## Step 3: Isolate the scope

Narrow down where the bug lives. You're looking for the
**smallest piece of code** that still exhibits the problem.

- **Comment out code** -- does the bug survive? If not,
  you just found the region.
- **Simplify inputs** -- can you trigger the bug with a
  minimal input?
- **Use git bisect** -- if it used to work, find the exact
  commit that broke it:

```bash
git bisect start
git bisect bad          # current commit is broken
git bisect good abc123  # this old commit worked
# Git checks out a midpoint -- test it and say good/bad
```

## Step 4: Use breakpoints effectively

Drop a breakpoint right before the line you suspect:

```python
def process(data):
    breakpoint()  # execution pauses here
    return data["key"]
```

When the debugger pauses, you can:

- **Inspect variables** -- type `data` to see its value
- **Check types** -- `type(data)` to verify it's what you
  expect
- **Step through** -- `n` (next line), `s` (step into
  function), `c` (continue)
- **Evaluate expressions** -- try the operation that's
  failing to see the exact result

Remove breakpoints after you're done. Don't commit them.

## Step 5: Form a hypothesis and test it

Based on what you've seen:

1. State your theory in one sentence: "The bug happens
   because `data` is `None` when the API returns a 404."
2. Design a test: add an assertion or print that would
   confirm or deny this specific theory.
3. Run it. If confirmed, you know the fix. If denied,
   the failed test gives you new evidence for a better
   hypothesis.

Change **one thing at a time**. If you change three things
and the bug disappears, you don't know which change fixed
it -- and you might have introduced a new bug.

## Step 6: Verify the fix

After applying your fix:

- Run the **original failing test** to confirm it passes
- Run the **full test suite** to check for regressions
- If the bug was in production, verify the fix in a
  staging environment before deploying

## When to ask for help

Ask sooner rather than later if:

- You've spent more than 30 minutes without a new
  hypothesis
- The bug involves unfamiliar code or infrastructure
- You've confirmed the bug is in a dependency, not your
  code
- The stack trace points to C extensions or interpreter
  internals

When asking for help, provide: the exact error, steps to
reproduce, what you've already tried, and what you've
ruled out.

## Want to learn more?

- Say **"what are the debugging strategies?"** for the
  conceptual overview
- Say **"show me all debugging tools and commands"** for
  the full reference
- Say **"something is broken and I don't know why"** for
  the quick triage guide
- Try **/fix-test** when a test is failing and you want
  automated diagnosis
- Try **/bug-predict** to find which parts of your code
  are most likely to have bugs
