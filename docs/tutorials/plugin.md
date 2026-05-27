---
type: tutorial
name: plugin
tags: [plugin, claude-code, hooks, security, workspace]
source: developer-guidance
---

# Tutorial: Plugin

You'll build a small Python script that wires together three of attune's plugin hooks — security validation, workspace state inspection, and a formatted resume prompt — and see exactly what each hook returns. When you're done, you'll have a runnable file you can adapt as the foundation for your own hook integrations.

## What you will build

A script called `plugin_tour.py` that:

1. Validates a shell command through the security guard
2. Reads live workspace state (Git branch, last commit, in-flight specs)
3. Renders a resume prompt the same way attune's `/handoff` command does

---

## Prerequisites

- Python 3.10 or newer
- attune installed in your environment (`import hooks` must succeed)
- A Git repository to run the script inside (any repo works)

---

## Step by step

### Step 1 — Create the script file

Create a new file called `plugin_tour.py` in any directory inside your Git repository. Starting here rather than in a REPL means you'll have a persistent artifact to review and modify.

```python
# plugin_tour.py
```

**What you should see:** The file exists. Nothing runs yet.

---

### Step 2 — Import the hooks you'll use

Add these imports to `plugin_tour.py`. Each import maps to one subsystem: security validation, state discovery, and resume-prompt rendering.

```python
from hooks.security_guard import validate_bash_command
from hooks._state import git_state, discover_specs, workspace_roots
from hooks._resume_prompt import build_resume_prompt
from pathlib import Path
```

The `hooks._state` module is the shared source of truth that most other hooks call internally, so reading it directly gives you the same data the plugin runtime sees.

**What you should see:** Running `python plugin_tour.py` produces no output and exits cleanly.

---

### Step 3 — Validate a shell command

Append this block. The security guard exposes `validate_bash_command`, which returns a `(bool, str)` tuple — `True` means the command is allowed, `False` means it was blocked, and the string explains why.

```python
allowed, reason = validate_bash_command("grep -r TODO .")
print(f"[security] allowed={allowed}, reason={reason!r}")
```

`grep` appears in `SEARCH_COMMAND_PREFIXES`, so attune treats it as a safe read-only operation and passes it through.

**What you should see:**

```
[security] allowed=True, reason=''
```

Now try a blocked command to see the other branch:

```python
blocked, why = validate_bash_command("rm -rf /tmp/scratch")
print(f"[security] allowed={blocked}, reason={why!r}")
```

**What you should see:** `allowed=False` with a non-empty reason string explaining the block.

---

### Step 4 — Read live Git and workspace state

Append this block. `git_state` snapshots the working tree; `workspace_roots` guesses which directories to scan for specs; `discover_specs` walks those roots and returns every in-flight spec it finds.

```python
cwd = Path(".")
state = git_state(cwd)
print(f"[git] branch={state.branch!r}")
print(f"[git] last_sha={state.last_sha!r}")
print(f"[git] last_subject={state.last_subject!r}")
print(f"[git] uncommitted={state.uncommitted}")

roots = workspace_roots(cwd)
specs = discover_specs(roots)
print(f"[specs] found {len(specs)} in-flight spec(s)")
for s in specs:
    print(f"  slug={s.slug!r} layer={s.layer!r} phase={s.phase!r} status={s.status!r}")
```

`GitState` and `SpecInfo` are plain dataclasses, so you can read any field directly without further parsing.

**What you should see:** Your current branch name, the short SHA of your last commit, its subject line, any uncommitted filenames, and a list of specs (possibly empty if you have no specs directory yet).

---

### Step 5 — Render a resume prompt

Append this block. `build_resume_prompt` combines the Git snapshot and the first spec (if any) into the exact formatted string that attune's `/handoff` command uses. Calling it yourself shows you how session-continuity context is assembled.

```python
first_spec = specs[0] if specs else None
prompt = build_resume_prompt(first_spec, state)
print("\n[resume prompt] ---")
print(prompt)
```

`spec_info` is `SpecInfo | None` — passing `None` is valid and produces a prompt without spec context.

**What you should see:** A multi-line string describing your branch, last commit, and (if present) the in-flight spec. This is the text Claude receives when a session resumes.

---

### Step 6 — Run the complete script

Run the finished script from inside your Git repository:

```bash
python plugin_tour.py
```

**What you should see:** All five sections of output — the two security checks, the Git state block, the spec list, and the resume prompt — printed in order with no exceptions.

---

## What you learned

- **Step 3** — `validate_bash_command` from `hooks.security_guard` returns a `(bool, str)` tuple and uses `SEARCH_COMMAND_PREFIXES` to allow safe read-only commands automatically.
- **Step 4** — `git_state`, `workspace_roots`, and `discover_specs` from `hooks._state` give you a live snapshot of the repository and any in-flight specs as typed dataclasses (`GitState`, `SpecInfo`) you can read field by field.
- **Step 5** — `build_resume_prompt` from `hooks._resume_prompt` assembles that state into the session-continuity prompt, and accepts `None` for `spec_info` when no spec is active.
- **All steps** — The plugin hooks are ordinary Python functions; wiring them together is a matter of importing each module and passing the outputs of one function as inputs to the next.

---

## Next steps

Read the `hooks.security_guard` reference to see the full list of blocked path prefixes in `SYSTEM_DIRECTORIES` and understand which command patterns `validate_bash_command` allows or rejects by default — that's the right place to go before writing a hook that needs to make security decisions.

<!-- attune-generated: source_hash=ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f feature=plugin kind=tutorial generated_at=2026-05-27 -->

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 48 (code fence) | error | `from hooks.security_guard import …` — module not importable |
| Line 48 (code fence) | error | `from hooks._state import …` — module not importable |
| Line 48 (code fence) | error | `from hooks._resume_prompt import …` — module not importable |
| Line 66 (python fence) | error | Name "validate_bash_command" is not defined  [name-defined] |
| Line 81 (python fence) | error | Name "validate_bash_command" is not defined  [name-defined] |
| Line 94 (python fence) | error | Name "Path" is not defined  [name-defined] |
| Line 95 (python fence) | error | Name "git_state" is not defined  [name-defined] |
| Line 101 (python fence) | error | Name "workspace_roots" is not defined  [name-defined] |
| Line 102 (python fence) | error | Name "discover_specs" is not defined  [name-defined] |
| Line 119 (python fence) | error | Name "specs" is not defined  [name-defined] |
| Line 120 (python fence) | error | Name "build_resume_prompt" is not defined  [name-defined] |
| Line 120 (python fence) | error | Name "state" is not defined  [name-defined] |
