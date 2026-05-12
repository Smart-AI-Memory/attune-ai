# Tasks: Sibling-Package Pre-commit Parity

**Status**: draft (pending requirements approval)

---

## Phase 0 — design decisions

1. **Lock the baseline hook list.** Confirm requirements'
   "baseline" set (black, ruff, detect-secrets,
   trailing-whitespace, eof-fixer, check-yaml/toml/json,
   check-added-large-files, check-merge-conflict). Document
   chosen hook versions in `decisions.md`. Match attune-ai's
   pinned versions where possible — no churn from a sibling
   running newer black than the umbrella.

2. **Per-repo exclusions inventory.** For each sibling, list
   what must NOT be auto-formatted:
   - `attune-rag`: `tests/golden/`, `benchmarks/` fixtures
   - `attune-author`: generated dirs (grep
     pyproject.toml for `[tool.setuptools.package-data]`)
   - `attune-help`: pre-baked `.help/templates/` content (if
     any committed); check what's tracked vs generated
   - `attune-gui`: static assets, any generated docs

   Capture as a table in `decisions.md`.

## Phase 1 — attune-rag (first; API contract source of truth)

3. **Author `attune-rag/.pre-commit-config.yaml`** with the
   baseline + the exclusions decided in Phase 0.

4. **Generate `attune-rag/.secrets.baseline`** by running
   `detect-secrets scan > .secrets.baseline` on a clean
   checkout. Verify nothing real is in it before committing.

5. **Run `pre-commit run --all-files` locally** — fix any
   violations in the same PR. If the violation count is
   large (>50 files), the PR splits into "config + clean
   slate" + "fix remaining violations" — don't ship a noisy
   one-shot.

6. **Add `pre-commit` job to `attune-rag/.github/workflows/
   tests.yml`** (or a new `lint.yml` if it bloats tests.yml).
   Job runs `uv run pre-commit run --all-files`. Required
   check on PRs.

7. **Update `attune-rag/CONTRIBUTING.md` or `README.md`** dev
   section: `uv sync --extra dev && pre-commit install`.

8. **Open the PR.** Title: `chore(dev): add pre-commit
   parity with attune-ai`. Land it. Capture any per-repo
   surprises (a specific exclusion that surfaced, a hook
   that was too noisy and got removed) in a session lesson
   for future repos.

## Phase 2 — attune-author

9. Repeat Phase 1 for `attune-author`. Watch for: the polish
   pipeline's `_anthropic.py` and the regeneration scripts —
   these have long string literals (LLM prompts) that ruff
   may complain about. Likely needs `noqa` or
   per-file-ignores.

## Phase 3 — attune-help

10. Repeat Phase 1 for `attune-help`. Watch for: the manifest
    YAML files have stable schemas; check-yaml should
    validate them. The `.help/templates/` content is markdown
    — trailing-whitespace fires on every multi-line LLM-
    generated paragraph. Exclude or tune.

## Phase 4 — attune-gui

11. Repeat Phase 1 for `attune-gui`. Watch for: any committed
    frontend assets (HTML, CSS, JS) — pre-commit's
    trailing-whitespace and EOF rules apply but black/ruff
    don't. May want a follow-up to add prettier; out of
    scope here.

## Phase 5 — close

12. **Daily briefing carryover update** — once all four land,
    explicitly mark the carryover item ✓ in the next briefing.

13. **Spec status → complete.** No CHANGELOG entry needed —
    pre-commit additions are dev-loop changes, not user-
    facing.

---

## Out of band

- Each PR is independent and individually mergeable. No
  cross-repo coordination required.
- If the order in Phases 1-4 needs to change (attune-help is
  smaller and finishes faster, for instance), that's fine.
  The order is "lowest-risk first" not a hard sequence.
- Resist the urge to add bandit or mypy as part of any of
  these PRs. The "parity baseline" is precisely the subset
  of attune-ai's config that's universally safe. Anything
  beyond that earns its own follow-up spec.
