# Starter: pre-commit parity for attune-help

Paste this into a fresh Claude Code session opened in the **attune-help**
repo. Self-contained. Phase 3 of `sibling-package-pre-commit` (keyless).
Produce ONE mergeable PR.

**Before starting:** confirm you are in attune-help, then branch off
`origin/main` (the repo may be on a `docs/...` branch — branch off main
explicitly, don't pile onto it):

```bash
git fetch origin main
git checkout -b chore/pre-commit-parity origin/main
```

## Step 1 — write `.pre-commit-config.yaml`

The **load-bearing** exclusion here is the LLM-polished template content:
without it, `trailing-whitespace` + `end-of-file-fixer` silently rewrite
hundreds of generated `.md` files and `check-json` rejects schema
variants — corrupting polished content. Exclude templates + demos:

```yaml
exclude: |
  (?x)^(
    \.venv/|
    build/|
    dist/|
    .*\.egg-info/|
    .*__pycache__/|
    node_modules/|
    src/attune_help/templates/.*\.(md|json)|
    src/attune_help/demos/.*\.md
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

**Repo-specific watch-for:** the manifest YAML files have stable schemas
— `check-yaml` should validate them fine (that's desired). The
`templates/`/`demos/` markdown exclusion above is the critical move;
verify after Step 3 that no generated `.md` got rewritten (`git diff
--stat` should show none under those paths).

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

Fix in-PR. If >~50 files reformat (excluding the templates, which must
stay untouched), split into "config" + "fix" PRs. Confirm the template
exclusion held. Report the count.

## Step 4 — CI gate

Add a `pre-commit` job on PRs. Inspect existing `.github/workflows/`
first and match conventions:

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
Note in the body whether the template exclusion fully protected the
generated content.

## Done when

- `.pre-commit-config.yaml` + `.secrets.baseline` committed.
- `pre-commit run --all-files` passes; generated templates untouched.
- CI runs pre-commit on PRs and fails on violations.
- Contributor docs point at `pre-commit install`.
- PR open and green. Report back for spec Phase 3 tick + lesson.
