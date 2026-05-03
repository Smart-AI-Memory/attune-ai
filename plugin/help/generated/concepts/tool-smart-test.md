---
name: tool-smart-test
source: plugin/skills/smart-test/SKILL.md
summary: Smart Test is a developer tool that analyzes code coverage to identify untested
  public APIs and automatically generates pytest tests for edge cases, error paths,
  and parametrized inputs to close coverage gaps.
tags:
- testing
- coverage
- generation
type: concept
---

# Smart Test

## What

Smart Test analyzes code coverage to identify untested public APIs and generates pytest tests covering edge cases, error paths, and parametrized inputs. It targets the gaps that matter most: public functions with no tests, branches with zero coverage, and error handlers that have never been exercised.

## Why

Writing tests after the fact is tedious and easy to skip. Smart Test identifies exactly where coverage is missing and generates working test scaffolds, so you start with a solid baseline instead of a blank file.

## When to Use

- After writing new modules or public functions
- When coverage drops below the 80% threshold
- Before a release to catch untested edge cases
- To bootstrap tests for legacy code with no existing coverage

## What It Produces

| Output | Description |
|---|---|
| Coverage gaps | List of untested functions and branches |
| Generated tests | pytest functions with assertions |
| Edge cases | Boundary values, empty inputs, and `None` handling |
| Error paths | Tests for expected exceptions and failure conditions |
| Parametrized tests | `@pytest.mark.parametrize` for multiple input combinations |

## Related Topics

- **Task:** Use the Smart Test skill — step-by-step walkthrough
- **Reference:** Smart Test skill — full reference
