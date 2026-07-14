---
name: smart-test
source: content/features/smart-test.md
tags:
- tests
- coverage
- generation
type: faq
---

# Smart Test FAQ

## Does smart-test find gaps or write tests?

Both — `test-audit` finds and ranks coverage gaps;
`test-gen` writes pytest tests to close them. The `/smart-test`
skill can do either or both in sequence.

## Why does `attune workflow run smart-test` fail?

`smart-test` is the skill / topic name, not a workflow
slug. Run `attune workflow run test-audit` or
`attune workflow run test-gen`.

## How do I generate tests for many modules at once?

Use `ParallelTestGenerationWorkflow().execute(top=N,
batch_size=M)` (the `test_gen_parallel` MCP tool), which writes
to `tests/behavioral/generated` by default.

## Which calls are async?

Every smart-test workflow's `execute` is a coroutine —
`await` it or use `asyncio.run`.

## Can I trust the generated tests?

Treat them as a reviewed starting point. Generation is
predictive — run the tests and check the assertions before
committing.
