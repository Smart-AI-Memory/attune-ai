# Starter: pre-commit parity for attune-rag

Paste this into a fresh Claude Code session opened in the **attune-rag**
repo. It is self-contained — the session does not need the attune-ai
spec loaded.

---

You are adding pre-commit parity to **attune-rag**, matching the mature
config in the sibling `attune-ai` repo. This is Phase 1 of the
`sibling-package-pre-commit` spec (keyless; zero API cost). Produce ONE
mergeable PR.

**Before starting:** confirm you are in the attune-rag repo, then branch
off the current `origin/main` (do not pile onto any in-progress feature
branch). There may be an untracked `site/.gitignore` — leave it alone,
don't stage it.

```bash
git fetch origin main
git checkout -b chore/pre-commit-parity origin/main
```

## Step 1 — write `.pre-commit-config.yaml`

Use exactly these pinned versions (they match attune-ai; never run a
newer formatter than the umbrella, or every merged PR churns):

```yaml
exclude: |
  (?x)^(
    \.venv/|
    build/|
    dist/|
    .*\.egg-info/|
    .*__pycache__/|
    node_modules/|
    tests/golden/|
    src/attune_rag/dashboard/templates/.*\.html|
    src/attune_rag/editor/template_schema\.json
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

**Repo-specific exclusions (already in the regex above):**
`tests/golden/` (retrieval-regression fixtures — exact-byte stability
is the whole point; nothing may rewrite them), the shipped dashboard
HTML templates, and `editor/template_schema.json` (package data).

If a `mkdocs.yml` with custom `!!python/...` tags exists and
`check-yaml` chokes on it, add `exclude: ^mkdocs.*\.yml$` to the
`check-yaml` hook only.

Do NOT add bandit or mypy — they're deliberately out of the baseline.

## Step 2 — generate `.secrets.baseline`

Fresh scan (not seeded from attune-ai):

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
```

Open `.secrets.baseline` and confirm every entry is a false positive /
test fixture before committing. If anything real appears, STOP and
report it — do not commit.

## Step 3 — run the hooks, fix violations in this PR

```bash
uv run --with pre-commit pre-commit install
uv run --with pre-commit pre-commit run --all-files --show-diff-on-failure
```

Fix everything in this same PR. **If more than ~50 files need
reformatting, split** into "config + clean slate" and "fix remaining
violations" PRs — don't ship one noisy 500-file diff. Report the count
either way.

## Step 4 — add a CI gate

Add a `pre-commit` job that runs on PRs. **First inspect this repo's
existing `.github/workflows/` and match its conventions** (runner,
action SHA-pinning vs tags, uv-vs-pip). If actions are SHA-pinned
elsewhere, pin yours too. A minimal shape:

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

Put it in a new `lint.yml` (preferred) or the existing `tests.yml` if
that's the repo's pattern.

## Step 5 — contributor docs

Add to `CONTRIBUTING.md` (or the `README.md` dev section if there's no
CONTRIBUTING) a dev-setup line:

```bash
uv sync --extra dev && uv run pre-commit install
```

## Step 6 — open the PR

Title: `chore(dev): add pre-commit parity with attune-ai`. No CHANGELOG
entry (dev-loop change, not user-facing). In the PR body, note any
per-repo surprises (an exclusion you had to add, a hook that was too
noisy) so the next sibling's session benefits.

## Done when

- `.pre-commit-config.yaml` + `.secrets.baseline` committed.
- `pre-commit run --all-files` passes on the branch (violations fixed
  in-PR).
- CI runs `pre-commit run --all-files` on PRs and fails on violations.
- Contributor docs point at `pre-commit install`.
- PR open and green.

After it merges, report back so the attune-ai
`sibling-package-pre-commit` spec can tick Phase 1 and capture the
lesson.
