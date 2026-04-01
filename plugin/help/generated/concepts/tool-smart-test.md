---
type: concept
name: tool-smart-test
tags: [testing, coverage, generation]
source: plugin/skills/smart-test/SKILL.md
---

# Smart Test

## What

Analyzes code coverage to find untested public APIs and
generates pytest tests with edge cases, error paths, and
parametrized inputs. Targets the gaps that matter most --
public functions without any test, branches with zero
coverage, and error handlers that were never exercised.

## Why

Writing tests after the fact is tedious and easy to skip.
Smart-test identifies exactly where coverage is missing and
generates working test scaffolds so you start with passing
tests instead of a blank file.

## When to use

- After writing new modules or public functions
- When coverage drops below the 80% threshold
- Before a release to catch untested edge cases
- To bootstrap tests for legacy code with no coverage

## What it produces

| Output | Description |
|--------|-------------|
| Coverage gaps | List of untested functions and branches |
| Generated tests | pytest functions with assertions |
| Edge cases | Boundary values, empty inputs, None handling |
| Error paths | Tests for expected exceptions and failures |
| Parametrized tests | `@pytest.mark.parametrize` for input combos |

## Related Topics

- **Task**: Use the smart-test skill -- step-by-step
- **Reference**: Skill: smart-test -- full reference
