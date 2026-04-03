---
type: concept
name: tool-smart-test
tags: [testing, coverage, generation]
source: plugin/skills/smart-test/SKILL.md
---

# Smart Test

Smart-test finds untested code and generates pytest tests
to cover it. Instead of guessing what needs tests, you get
a gap analysis that shows exactly which public functions,
branches, and error paths have zero coverage — then it
writes the tests for you.

## What it finds

| Gap type | What it catches | Risk if untested |
|----------|----------------|------------------|
| **Untested functions** | Public APIs with no test file | High — regressions slip through silently |
| **Missing branches** | if/else paths never executed | Medium — edge cases cause production bugs |
| **Error paths** | Exception handlers never triggered | High — failures cascade unpredictably |
| **Boundary values** | Empty inputs, None, zero, max-length | Medium — users hit edges you didn't |
| **Parametrized combos** | Input combinations never paired | Low — interaction bugs are subtle |

## When you'd use it

After writing new modules or public functions — catch
gaps before they become tech debt. When coverage drops
below the 80% threshold — find exactly what's missing.
Before a release — verify error paths actually work.
Or to bootstrap tests for legacy code with no coverage
at all.

## What it produces

| Output | Description |
|--------|-------------|
| Coverage gap report | Ranked list of untested functions with risk scores |
| Generated tests | Working pytest functions with assertions |
| Edge cases | Boundary values, empty inputs, None handling |
| Error path tests | Tests for expected exceptions and failures |
| Parametrized tests | `@pytest.mark.parametrize` for input combos |

## What to expect

When you ask for test generation, you'll be guided
through a couple of quick questions first — which module
to target and whether you want gap analysis, test
generation, or both. This keeps the output focused
instead of dumping tests for your entire codebase at
once. If you provide both details upfront (e.g.
"generate tests for src/auth/") the questions are
skipped and it runs immediately.

Runs on your Claude subscription — no API key or
additional cost.

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is code quality?"** to review code health first
- Say **"scan for vulnerabilities"** for security-focused analysis
