---
name: testing
description: Test runner, generation, and coverage analysis
category: primary
aliases: [test, t]
tags: [testing, coverage, test-gen]
version: "1.0.0"
question:
  header: "Test action"
  question: "What testing task do you need?"
  multiSelect: false
  options:
    - label: "Run tests"
      description: "Execute test suite (full or subset)"
    - label: "Check coverage"
      description: "Analyze test coverage and find gaps"
    - label: "Generate tests"
      description: "Create new tests for existing code"
---

# testing

Test runner, generation, and coverage analysis.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `run` | Run test suite |
| `coverage` | Coverage analysis |
| `gen` | Generate tests |
| `generate` | Generate tests |
| `benchmark` | Run benchmarks |
| `generate --batch` | Batch test generation |

## Usage

```bash
/testing                # Ask what to do
/testing run            # Run tests
/testing coverage       # Coverage report
/testing gen            # Generate tests
```

## Behavior

### run

Use `AskUserQuestion` to scope:

- Full suite, specific directory, or pattern match?
- Quick smoke test or thorough run?

Then run:

```bash
uv run pytest <target> -q
uv run pytest -k "<pattern>"
uv run pytest tests/unit/ -x -q
```

### coverage

Use `AskUserQuestion` to scope:

- Which module or full project?

Then run:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

### gen

Use `AskUserQuestion` to scope:

- Which file or function needs tests?
- Unit tests, integration tests, or edge cases?

Then run:

```bash
uv run attune workflow run test-gen --path <target>
```

### benchmark

Use `AskUserQuestion` to scope:

- Full benchmark suite, specific module, or function?
- Compare against a baseline?

Then run:

```bash
uv run pytest benchmarks/ --benchmark-only
```

### generate --batch

Use `AskUserQuestion` to scope:

- Which directory or module?
- Test type? (unit, integration, or both)
- Any exclusions?

Then run:

```bash
uv run attune workflow run test-gen --path <target> --batch
```
