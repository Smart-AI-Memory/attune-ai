---
name: testing
description: Test runner, generation, and coverage analysis
---
# testing

Test runner, generation, and coverage analysis.

**Default mode:** Module-level testing for daily development.
Full suite reserved for release verification and deep audits.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `run` | Run tests (changed modules by default) |
| `quick` | Run tests for recently changed files |
| `coverage` | Coverage analysis (module or full) |
| `gen` | Generate tests |
| `generate` | Generate tests |
| `audit` | Deep coverage audit (TestAuditWorkflow) |
| `benchmark` | Run benchmarks |
| `generate --batch` | Batch test generation |

## Usage

```bash
/testing                # Ask what to do
/testing run            # Run tests for changed modules
/testing run --all      # Run full test suite
/testing quick          # Run tests for changed files
/testing coverage       # Module-level coverage
/testing coverage --full # Full codebase coverage
/testing audit          # Deep coverage audit workflow
/testing gen            # Generate tests
```

## Fast-Path Detection

When explicit args satisfy scoping, skip questions:

- `/testing run --all` → full suite immediately
- `/testing gen src/auth` → generate for that module
- `/testing coverage --full` → full codebase coverage
- `/testing run` → ask which tests
- `/testing` → ask what to do

**Rule:** If input contains BOTH an action AND a
target (or `--all`/`--full` flag), proceed to
execution. If either is missing, use
`AskUserQuestion`.

## Behavior

### run

Default behavior: detect changed files via `git diff` and
run only their corresponding test files (module-level).

Use `AskUserQuestion` to scope if no flags provided:

- Changed modules only (default), specific directory, or
  full suite?
- Quick smoke test or thorough run?

```bash
# Default: changed modules only
git diff --name-only HEAD | grep '\.py$'
# Map source files to test files, then:
uv run pytest <test_files> -q

# With --all flag: full suite
uv run pytest tests/unit/ -q

# With --coverage flag: add coverage for changed modules
uv run pytest <test_files> --cov=attune.<module> -q
```

### quick

Detect changed files from `git diff` (staged + unstaged)
and run their corresponding tests. No scoping questions.

```bash
git diff --name-only HEAD
# Map each src/attune/foo/bar.py -> tests/unit/foo/test_bar.py
uv run pytest <mapped_test_files> -x -q
```

### coverage

Default: module-level coverage for changed files.

Use `AskUserQuestion` to scope:

- Which module? Or changed files only (default)?

```bash
# Default: changed modules
uv run pytest <test_files> --cov=attune.<module> --cov-report=term-missing

# With --full flag: full codebase coverage
# Warning: This takes 5-10 minutes on large codebases
uv run pytest tests/unit/ --cov=src/attune --cov-report=term-missing
```

### audit

Trigger the TestAuditWorkflow for a deep coverage audit.
This is the autonomous pipeline with 4 stages:

1. **Audit** — Run pytest with coverage JSON, parse results,
   produce prioritized module list
2. **Plan** — Group modules into batches, generate XML task
   prompts per batch
3. **Execute** — Generate tests per batch (parallel)
4. **Verify** — Run full suite, compare coverage before/after

Show the plan for approval before the execute phase.

```bash
# Interactive mode (default)
uv run attune workflow run test-audit

# With --batch flag for fire-and-forget
uv run attune workflow run test-audit --batch

# Quick audit (audit + targeted run only, no generation)
uv run attune workflow run test-audit --mode quick
```

Use `AskUserQuestion` before running:

- Target coverage? (default: 90%)
- Quick audit or full deep pipeline?
- Approve plan before executing?

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
