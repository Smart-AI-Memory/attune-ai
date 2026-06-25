# Tasks: Sibling-Package Pre-commit Parity

**Status**: ✓ **complete 2026-06-20** — all 5 phases done; all four
siblings shipped (attune-rag #187, attune-author #74 + #75,
attune-help #19, attune-gui #78). See "Outcomes & lessons" below.

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

## Phase 1 — attune-rag ✓ complete 2026-06-20 ([#187](https://github.com/Smart-AI-Memory/attune-rag/pull/187))

> **Landed.** New `lint.yml` gate (not folded into tests.yml).
> **Surprise:** CI only lints `src/ tests/`, so whole-tree ruff
> surfaced 21 pre-existing issues in `scripts/`/`docs/` — including a
> real latent **F821** (`measure_reranker.py` used `QueryScore` in
> annotations without importing it, masked by `from __future__ import
> annotations`). Fixed the real ones (F821, UP038, BLE bare-except);
> used the repo's per-file-ignore idiom for legitimately-exceptional
> E402 (sys.path-hack diagnostic runners) and E501 (embedded CSS/HTML).

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

## Phase 2 — attune-author ✓ complete 2026-06-20 ([#74](https://github.com/Smart-AI-Memory/attune-author/pull/74), [#75](https://github.com/Smart-AI-Memory/attune-author/pull/75))

> **Landed.** The predicted prompt-string E501 noqas **did not
> occur** — the polish-pipeline literals were already within
> line-length. The real surprise: the `trailing-whitespace` hook
> silently corrupted a **syrupy `.ambr` snapshot** (generated output
> legitimately carries trailing whitespace on blank lines), breaking 3
> tests — so `tests/__snapshots__/` is now excluded (byte-exact
> fixtures, same class as attune-rag's `tests/golden/`). Also: this
> repo sets `core.hooksPath = .githooks`, so `pre-commit install`
> doesn't wire into local commits (CI enforces it regardless). The
> UP038 reformat dragged a pre-existing partial branch into codecov's
> patch report → follow-up coverage PR #75.

9. Repeat Phase 1 for `attune-author`. Watch for: the polish
   pipeline's `_anthropic.py` and the regeneration scripts —
   these have long string literals (LLM prompts) that ruff
   may complain about. Likely needs `noqa` or
   per-file-ignores.

## Phase 3 — attune-help ✓ complete 2026-06-20 ([#19](https://github.com/Smart-AI-Memory/attune-help/pull/19))

> **Landed.** The predicted template trailing-whitespace risk was real
> and **load-bearing** (634 generated `.md` files) — the
> `templates/**/*.{md,json}` + `demos/` exclusion held perfectly
> (`git diff --stat` showed zero changes under those paths). This repo
> has **no `[tool.ruff]` config**, so ruff ran with defaults
> (`E4/E7/E9/F` only) — far fewer findings; ruff auto-fixed one unused
> import, the rest was black. 4 E402s from the deliberate
> `pytest.importorskip("attune_author")`-before-import shim pattern →
> per-line `# noqa: E402`.
> **Bonus:** surfaced a separate, pre-existing failure — the RAG P@1
> regression gate had been red on `main` since inception (overall P@1
> 71.4% < 0.73). Fixed honestly in **[#20](https://github.com/Smart-AI-Memory/attune-help/pull/20)**
> (strengthened 4 owner summaries → 73.5%, zero regressions), not by
> lowering the threshold.

10. Repeat Phase 1 for `attune-help`. Watch for: the manifest
    YAML files have stable schemas; check-yaml should
    validate them. The `.help/templates/` content is markdown
    — trailing-whitespace fires on every multi-line LLM-
    generated paragraph. Exclude or tune.

## Phase 4 — attune-gui ✓ complete 2026-06-20 ([#78](https://github.com/Smart-AI-Memory/attune-gui/pull/78))

> **Landed.** The predicted committed-frontend-asset risk was real:
> `end-of-file-fixer` rewrote the generated **Vite bundle**
> (`sidecar/attune_gui/static/`) — excluded alongside `editor-frontend/`.
> This repo has the **strictest** ruff `select` of the four
> (`["E","F","I","N","W","UP","B","S","BLE001"]` — adds `N` naming + `S`
> bandit); whole-tree ruff surfaced 10 `S` findings, all in dev tooling
> (`.claude/hooks/`, `scripts/`) → per-file-ignores (`"S"` for those
> dirs), matching the repo's existing test S-ignore idiom. No shipped
> `sidecar/` code changed. Matched this repo's `@v4`/`@v5` **tag**
> convention for the lint workflow (the other three SHA-pin). Frontend
> prettier/eslint left out of scope (its own `npm` toolchain runs in CI).

11. Repeat Phase 1 for `attune-gui`. Watch for: any committed
    frontend assets (HTML, CSS, JS) — pre-commit's
    trailing-whitespace and EOF rules apply but black/ruff
    don't. May want a follow-up to add prettier; out of
    scope here.

## Phase 5 — close ✓ complete 2026-06-20

12. ☐ **Daily briefing carryover update** — mark the carryover item ✓
    in the next briefing. (Pending the next briefing cycle; all four
    PRs have landed, so it's ready to tick.)

13. ✓ **Spec status → complete.** Done in this PR. No CHANGELOG entry —
    pre-commit additions are dev-loop changes, not user-facing.

---

## Outcomes & lessons

All four siblings shipped one mergeable PR each (plus two follow-ups in
attune-help). Cross-cutting lessons for the next time we replicate a
config across sibling repos:

- **CI lint scope is narrower than pre-commit's.** Every sibling lints
  only its shipped surface in CI (`src/ tests/`, or `sidecar/`), so
  turning the hooks loose on the whole tree reliably surfaces
  pre-existing debt in `scripts/`, `docs/`, `.claude/hooks/`. Budget
  for it — attune-rag alone had 21 latent issues (one a real F821).
  Fix the genuine ones; use each repo's own per-file-ignore idiom for
  legitimately-exceptional code rather than excluding whole files.
- **Byte-exact generated content must be excluded, and it's repo-
  specific.** Each sibling had a different flavor: attune-rag
  `tests/golden/`, attune-author syrupy `tests/__snapshots__/`,
  attune-help's 634 `templates/**/*.md`, attune-gui's committed Vite
  bundle. The hygiene hooks (trailing-whitespace / EOF / check-json)
  will silently rewrite these and break things if not excluded.
- **Match each repo's existing conventions, don't impose attune-ai's.**
  Action-pin style differed (three SHA-pin, attune-gui tags); ruff
  `select` ranged from defaults-only (attune-help) to the strict
  `N`+`S` set (attune-gui). The lint workflow and any ignores should
  look native to the repo.
- **The starters paid off but weren't exhaustive.** Per-repo predicted
  watch-fors were mostly right; the misses were the snapshot-exclusion
  (attune-author) and `core.hooksPath` (attune-author). Fold those
  back into the playbook for any future sibling.
- **Reformatting can dent codecov.** A pure formatting/UP038 reformat
  pulled a pre-existing partial branch into codecov's patch report
  (attune-author) — expect a possible coverage follow-up after a
  whole-tree reformat.

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
