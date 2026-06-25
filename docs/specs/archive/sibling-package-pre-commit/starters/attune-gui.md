# Starter: pre-commit parity for attune-gui

Paste this into a fresh Claude Code session opened in the **attune-gui**
repo. Self-contained. Phase 4 (last) of `sibling-package-pre-commit`
(keyless). Produce ONE mergeable PR.

**Before starting:** confirm you are in attune-gui, then branch off
`origin/main` (the repo may be in detached HEAD — branch explicitly):

```bash
git fetch origin main
git checkout -b chore/pre-commit-parity origin/main
```

This is a **hybrid repo**: Python sidecar + a TypeScript/React frontend
under `editor-frontend/` with its own toolchain (eslint/prettier/vite).
Pre-commit here only meaningfully applies to the Python surface
(`sidecar/`, `scripts/`, `specs/`). `editor-frontend/` is OUT OF SCOPE —
a prettier hook is a possible follow-up, not this PR.

## Step 1 — write `.pre-commit-config.yaml`

Exclude the frontend and build/cache artifacts that live at repo root:

```yaml
exclude: |
  (?x)^(
    \.venv/|
    build/|
    dist/|
    .*\.egg-info/|
    .*__pycache__/|
    node_modules/|
    editor-frontend/
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

Do NOT add bandit, mypy, or any frontend hook (prettier/eslint) — all
out of scope for this baseline parity PR.

**Repo-specific watch-for:** any committed frontend assets OUTSIDE
`editor-frontend/` (stray HTML/CSS/JS at root or under `sidecar/static`)
— black/ruff don't apply, but `trailing-whitespace`/`end-of-file-fixer`
will rewrite them. If that's noisy, narrow with an added exclude rather
than dropping the hook. There's no `[tool.setuptools.package-data]`, so
the exclusion surface is simpler than the other three siblings.

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
Confirm `editor-frontend/` was untouched. Report the count.

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
Note in the body whether a prettier/eslint follow-up is worth a separate
spec for the frontend.

## Done when

- `.pre-commit-config.yaml` + `.secrets.baseline` committed.
- `pre-commit run --all-files` passes; `editor-frontend/` untouched.
- CI runs pre-commit on PRs and fails on violations.
- Contributor docs point at `pre-commit install`.
- PR open and green. This is the last sibling — once merged, report back
  so the attune-ai spec flips to **complete** (Phase 5).
