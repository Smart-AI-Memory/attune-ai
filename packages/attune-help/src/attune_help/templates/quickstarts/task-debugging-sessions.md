---
type: quickstart
name: task-debugging-sessions
tags: [debugging, python, tools]
source: developer-guidance
---

# Something Is Broken and I Don't Know Why

Five-step triage when you're staring at an error and have
no idea where to start.

## Step 1: Read the last line first

The error type and message are at the **bottom** of the
stack trace. Read that line before anything else.

```
KeyError: 'user_id'
```

That one line tells you: a dictionary lookup failed because
the key `user_id` doesn't exist. You already know what
happened -- now you need to find where and why.

## Step 2: Find the frame you own

Scan the stack trace from the bottom upward. Skip frames
in library code (`site-packages/`, `lib/python3.x/`) and
find the **first frame in your code**. That's where the
investigation starts.

```
  File "src/auth/session.py", line 34, in get_session
    return cache[request.user_id]  <-- start here
```

## Step 3: Check the obvious

Before diving deep, rule out the simple causes:

- **Did you save the file?** Editors sometimes don't
  auto-save.
- **Are you in the right environment?** `which python`
  and `pip list | grep <package>` to verify.
- **Did you restart the process?** Old code may still be
  running.
- **Is the input what you expect?** Add one
  `print(repr(variable))` right before the failing line.

## Step 4: Add one breakpoint

If the obvious check didn't solve it, add a single
breakpoint just before the failing line:

```python
breakpoint()  # add this line, then run again
```

When it pauses, inspect the variables. Type the variable
names to see their values. Type the expression that's
failing to see what it returns. This usually reveals the
mismatch between what you expected and what's actually
there.

## Step 5: Ask the right question

Now that you've seen the actual state, form one specific
question:

- **"Why is `request.user_id` None here?"** -- trace
  where `request` comes from.
- **"Why is `cache` empty?"** -- check the initialization
  path.
- **"Why is this code running at all?"** -- check the
  caller in the stack trace.

One question leads to the next. Follow the chain until you
find the root cause.

## Still stuck?

| Symptom | Try this |
|---------|----------|
| Test is failing after a refactor | **/fix-test** auto-diagnoses and repairs |
| Not sure which commit broke it | `git bisect start`, then mark good/bad |
| Error is in unfamiliar code | Step through with `s` in pdb to build a mental model |
| Bug only happens sometimes | Add logging and wait for it to recur |
| Everything looks correct but it still fails | Rubber duck -- explain the problem out loud from scratch |

## Want to learn more?

- Say **"what are the debugging strategies?"** for
  techniques beyond print statements
- Say **"how do I debug a problem step by step?"** for
  the full systematic walkthrough
- Say **"show me all debugging tools"** for the complete
  reference -- pdb commands, VSCode setup, profiling,
  and Python gotchas
- Try **/fix-test** to let Attune diagnose a failing test
  automatically
- Try **/bug-predict** to find the riskiest parts of your
  codebase
