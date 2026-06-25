# Starter: pre-commit parity for attune-author

Paste this into a fresh Claude Code session opened in the
**attune-author** repo. Self-contained. Phase 2 of
`sibling-package-pre-commit` (keyless). Produce ONE mergeable PR.

**Before starting:** confirm you are in attune-author, then branch off
`origin/main` (the repo may be in detached HEAD — branch explicitly):

```bash
git fetch origin main
git checkout -b chore/pre-commit-parity origin/main
```

## Step 1 — write `.pre-commit-config.yaml`

Pinned versions match attune-ai exactly (never run a newer formatter
than the umbrella). Repo-specific excludes are the hallucination eval
baselines/artifacts and the Jinja templates:

```yaml
exclude: |
  (?x)^(
    \.venv/|
    build/|
    dist/|
    .*\.egg-info/|
    .*__pycache__/|
    node_modules/|
    benchmarks/hallucination-v.*/|
    benchmarks/.*\.yaml|
    src/attune_author/meta_templates/.*\.j2
  )

repos:
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
        args: ['--line-length=100']
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: ['--fix', '--exit-non-zero-on-fix']
      - id: ruff
        name: ruff-bare-exception-check
        args: ['--select=BLE', '--no-fix']
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1200']
      - id: check-merge-conflict
      - id: mixed-line-ending
        args: ['--fix=lf']
```

Do NOT add bandit or mypy (out of baseline).

**Repo-specific watch-for:** the polish pipeline's `_anthropic.py` and
regeneration scripts have long LLM-prompt string literals that ruff may
flag (E501 / line length). attune-author's `pyproject.toml` already has
`[tool.ruff] line-length = 100` and `select = ["E","F","W","I","UP","BLE"]`,
so this is pure dev-loop gain. Resolve any prompt-string trips with a
per-line `# noqa: E501` (or the specific code) — do NOT exclude the whole
files. Capture which lines needed it in the PR body.

## Step 2 — `.secrets.baseline`

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
```

Verify every entry is a false positive before committing; if anything
real appears, STOP and report.

## Step 3 — run hooks, fix in this PR

```bash
uv run --with pre-commit pre-commit install
uv run --with pre-commit pre-commit run --all-files --show-diff-on-failure
```

Fix in-PR. If >~50 files reformat, split into "config" + "fix" PRs.
Report the count.

## Step 4 — CI gate

Add a `pre-commit` job running on PRs. Inspect existing
`.github/workflows/` first and match conventions (runner, SHA-pin vs
tag, uv vs pip):

```yaml
name: Lint
on:
  pull_request:
  push:
    branches: [main]
concurrency:
  group: lint-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
jobs:
  pre-commit:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@<match-repo-convention>
      - uses: actions/setup-python@<match-repo-convention>
        with:
          python-version: '3.12'
      - run: pip install pre-commit
      - run: pre-commit run --all-files --show-diff-on-failure
```

## Step 5 — contributor docs

Add to `CONTRIBUTING.md` (or README dev section):

```bash
uv sync --extra dev && uv run pre-commit install
```

## Step 6 — open the PR

Title: `chore(dev): add pre-commit parity with attune-ai`. No CHANGELOG.
Note in the body which prompt-string lines needed `# noqa`, for the next
sibling's session.

## Done when

- `.pre-commit-config.yaml` + `.secrets.baseline` committed.
- `pre-commit run --all-files` passes on the branch.
- CI runs pre-commit on PRs and fails on violations.
- Contributor docs point at `pre-commit install`.
- PR open and green. Report back for spec Phase 2 tick + lesson.
