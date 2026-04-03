---
type: task
name: use-smart-test
tags: [skill, task]
source: plugin/skills/smart-test/SKILL.md
---

# How to Find Test Gaps and Generate Tests

## Quick start

Say what you want tested:

```
generate tests for src/auth/
```

Or use the skill directly:

```
/smart-test src/auth/
```

You'll get a gap analysis and generated test files
ready to run with pytest.

## The guided flow

When you ask for tests, you'll be guided through two
quick questions before anything runs:

| Step | What you're asked | Why |
|------|-------------------|-----|
| 1. Target | "Which file or module needs tests?" | Focuses on one area instead of scanning everything |
| 2. Approach | "Gap analysis, generate tests, or both?" | Gap analysis is fast; generation takes longer but gives you runnable code |

If you provide both upfront ("generate tests for
src/auth/") the questions are skipped and it runs
immediately.

## Choosing what to target

| Command | What it covers | When to use |
|---------|---------------|-------------|
| `/smart-test src/auth/login.py` | One file | Quick check after editing a file |
| `/smart-test src/auth/` | A directory tree | Cover a whole module before PR |
| "what needs testing?" | Entire project gaps | Find where coverage is weakest |
| "test the top 10 gaps" | Worst offenders | Maximize coverage with minimal effort |

## Choosing an approach

| Approach | What you get | Time |
|----------|-------------|------|
| **Gap analysis** | List of untested functions ranked by risk | Seconds |
| **Generate tests** | Working pytest files with edge cases | ~1-2 min per module |
| **Both** | Gaps first, then tests for the top gaps | ~2-3 min |

Natural language works:

- "find untested code in src/" — gap analysis
- "write tests for src/auth/" — generation
- "audit and generate tests for src/" — both

## Reading the results

### Gap analysis results

```
Test Gap Analysis
Coverage: 62% | Untested Functions: 14

Gaps by Priority

  HIGH (5 functions)
  src/auth/session.py  validate_token()     0% — handles auth, no tests
  src/auth/login.py    authenticate()       0% — 3 branches, none covered
  src/api/webhook.py   process_event()      0% — error path untested

  MEDIUM (6 functions)
  src/config.py        load_from_env()      partial — else branch missing
  src/cache.py         evict()              partial — empty-cache edge case

  LOW (3 functions)
  src/utils.py         format_timestamp()   partial — only happy path tested
```

### Generated tests results

```
Generated Tests
Files: 3 | Tests: 18 | Edge Cases: 12

  tests/test_session.py    6 tests (2 edge cases, 1 error path)
  tests/test_login.py      7 tests (3 parametrized, 2 error paths)
  tests/test_webhook.py    5 tests (2 edge cases, 1 error path)

All generated tests use pytest conventions with
descriptive names and docstrings.
```

## What to do next

After the results, you'll be offered follow-up options:

| Goal | What to say |
|------|-------------|
| Generate tests for top gaps | "write tests for those gaps" |
| Run the generated tests | "run the tests to verify" |
| Check a different module | "now check src/api/" |
| See coverage after | "show me coverage now" |
| Review code quality | "review src/auth/ for quality" |
| Go deeper | say "tell me more" for the full reference |

## Want to learn more?

- Say **"tell me more"** for the complete reference
  with all check types, output format, and scoring
- Say **"what is smart test?"** to go back to the
  overview
- Say **"review src/"** to run a code quality review
  instead
