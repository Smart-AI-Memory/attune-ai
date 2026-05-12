# Tasks: Sibling-Package Pre-commit Parity

**Status**: approved — Phase 0 complete, Phase 1+ pending

---

## Phase 0 — design decisions ✓ complete 2026-05-12

See [decisions.md](decisions.md) for D1 (baseline hook list +
versions) and D2 (per-repo exclusion table).

1. ✓ **Lock the baseline hook list.** D1 locked 11 hooks
   pinned to attune-ai's currently-shipping versions (black
   24.10.0, ruff v0.8.4, detect-secrets v1.5.0, pre-commit-
   hooks v5.0.0). Bandit + mypy + repo-local hooks
   explicitly excluded from baseline.

2. ✓ **Per-repo exclusions inventory.** D2 documents
   exclusions per sibling:
   - `attune-rag`: `tests/golden/`, shipped HTML/JSON
     templates
   - `attune-author`: hallucination eval baselines, `.j2`
     templates
   - `attune-help`: `templates/**/*.{md,json}`, demos
   - `attune-gui`: `editor-frontend/` (separate toolchain)

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
