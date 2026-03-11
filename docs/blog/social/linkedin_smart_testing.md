# LinkedIn Article: Stop Running Your Entire Test Suite

**Format:** LinkedIn Article (long-form, supports headers
and code blocks)
**Target:** Developers using Claude Code, Python developers
with large test suites, AI-assisted testing practitioners
**Cross-post:** Claude Code Discord, attune-ai blog

---

## Title

Stop Running Your Entire Test Suite After Every Change

## Subtitle

Two Claude Code skills that cut my test feedback loop from
10 minutes to 3 seconds — and fix the failures for me.

---

## Article Body

I have 17,000 tests.

That's not a brag. That's a problem. Every time I change a
file, I have a choice: run the full suite and wait 10-15
minutes, or guess which tests matter and hope I didn't miss
something.

Most days I'd guess wrong. I'd push, CI would fail, and I'd
spend another 20 minutes figuring out which test broke and
why. Usually it was a mock that pointed to an old import
path. Or an assertion checking a value that changed three
commits ago.

So I built two Claude Code skills that solve both problems.
Zero Python code. Just markdown files that tell Claude
exactly what to do.

### /smart-test: Run Only What Changed

The idea is simple. When I type /smart-test, Claude Code:

1. Runs git diff to find every file I've changed (staged,
   unstaged, untracked)
2. Maps each source file to its test file using a naming
   convention (src/attune/foo/bar.py maps to
   tests/unit/foo/test_bar.py)
3. Filters to tests that actually exist on disk
4. Runs only those tests

--- CODE START ---
$ /smart-test

Smart Test Results
------------------
Changed files: 3
Test files run: 2
Passed: 14 | Failed: 0 | Skipped: 1
Time: 0.8s (full suite estimate: ~10min)
--- CODE END ---

Three seconds instead of ten minutes. And if I changed a
file that has no tests yet, it tells me and offers to
generate them.

The entire implementation is a markdown file with YAML
frontmatter. No Python. No dependencies. No config. Drop
it in .claude/commands/smart-test.md and it works.

### /fix-test: Diagnose, Fix, Re-run

This is the one that actually saves time. When a test fails,
I used to do this manually:

1. Read the error message
2. Open the test file
3. Open the source file
4. Figure out what changed
5. Fix the test (or the source)
6. Re-run to verify

Now I type /fix-test and Claude Code does all six steps. It
reads the traceback, identifies the error type, reads both
files, diagnoses the root cause, and applies the fix.

If the fix doesn't work, it tries again. Up to three
attempts per test. Then it reports what it fixed and what
still needs manual attention.

--- CODE START ---
$ /fix-test tests/unit/test_config.py

Fix-Test Results
----------------
Tests examined: 3
Fixed: 2 (re-ran successfully)
Still failing: 1 (after 3 attempts)
Skipped: 0
--- CODE END ---

The most common fixes it handles automatically:

- Mock paths that drifted when I renamed a module
- Assertion values that changed because the source changed
- Missing fixtures after a refactor
- Import errors from moved code

It has safety rules built into the prompt. It never deletes
test files. It always shows diffs before changing source
code. If a fix would change how production code behaves, it
asks first. And it preserves test intent — it doesn't just
make tests pass by asserting whatever the code returns.

### Combining Them: /smart-test --fix

The best part is they chain together. /smart-test --fix runs
only the affected tests, and if any fail, automatically
hands them to /fix-test for diagnosis and repair.

One command. Changed files identified, tests run, failures
diagnosed and fixed, re-run verified. The whole loop that
used to take 15-20 minutes now takes under a minute.

### How It Works Under the Hood

Both skills are Claude Code slash commands — markdown files
in .claude/commands/ with YAML frontmatter. No Python
runtime, no package to install, no configuration.

--- CODE START ---
# .claude/commands/smart-test.md
---
name: smart-test
description: Run tests affected by recent changes
aliases: [st]
---

## Context (pre-computed)

git diff --name-only HEAD
git diff --name-only --cached
git ls-files --others --exclude-standard '*.py'

## Instructions

1. Collect changed Python files from context above
2. Map each to its test counterpart using naming convention
3. Filter to tests that exist on disk
4. Run: uv run pytest <test_files> -x -q --tb=short
5. Report results with time saved estimate
--- CODE END ---

The Context section runs git commands before the prompt even
reaches Claude. The Instructions section tells it what to do
with the results. That's the entire implementation.

/fix-test is slightly more involved — it has a diagnosis
table mapping error types to common root causes, safety
rules, and a retry loop — but it's still just markdown.

### Why This Matters

The insight that changed how I think about AI-assisted
development: the most valuable automation isn't the
flashiest. It's the one that eliminates the thing you do
twenty times a day without thinking about it.

Running tests and fixing failures isn't hard. It's just
tedious. And tedium is exactly where an AI assistant should
live — handling the repetitive diagnosis so you can stay in
the creative part of the work.

If you have a Claude Code plugin or a project with a large
test suite, try building these two skills. The ROI is
immediate.

### Try It

Both files are in the Attune AI repo:

- .claude/commands/smart-test.md
- .claude/commands/fix-test.md

Copy them into your project's .claude/commands/ directory.
Adjust the naming convention in the mapping step to match
your project structure. That's it.

Or install attune-ai and get them along with 30+ other
developer workflow skills:

--- CODE START ---
pip install 'attune-ai[developer]'
--- CODE END ---

---

## Discord Version (shorter)

**For Claude Code Discord #share-your-plugins or
#tips-and-tricks:**

---

Built two Claude Code skills for faster testing feedback:

/smart-test - Runs git diff, maps changed files to their
test counterparts, runs only those tests. My 17k test suite
takes 10+ min. This runs the relevant subset in seconds.

/fix-test - Reads the traceback, opens the test and source
files, diagnoses the root cause (stale mock, assertion
drift, import error, etc.), applies a fix, re-runs to
verify. Up to 3 attempts. Has safety rules: never deletes
tests, asks before changing source behavior.

/smart-test --fix chains them: smart select + auto-fix.

Both are pure markdown (no Python) — drop them in
.claude/commands/ and they work.

Files:
- .claude/commands/smart-test.md
- .claude/commands/fix-test.md

Available in attune-ai or just copy the markdown.

---

## Blog Version Metadata

**For website blog:**

- **Title:** Stop Running Your Entire Test Suite After
  Every Change
- **Slug:** smart-test-skills
- **Author:** Patrick Roebuck
- **Date:** 2026-03-10
- **Tags:** claude-code, testing, pytest, developer-tools,
  plugins
- **Description:** Two Claude Code skills that map changed
  files to tests and auto-fix failures — cutting the
  feedback loop from minutes to seconds.
