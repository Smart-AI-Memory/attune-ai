# Spec: Sibling-Package Pre-commit Parity

**Status**: ✓ complete 2026-06-20
**Created**: 2026-05-12
**Approved**: 2026-05-12
**Completed**: 2026-06-20 — all four siblings shipped (attune-rag #187,
attune-author #74 + #75, attune-help #19, attune-gui #78)
**Origin**: Daily briefing carryover item — attune-ai ships a
mature `.pre-commit-config.yaml` (black, ruff, bandit, detect-
secrets, custom freshness checks). Its four sibling packages
(`attune-rag`, `attune-author`, `attune-help`, `attune-gui`)
have none. Every quality concern attune-ai's pre-commit catches
locally currently has to be caught by CI or human review in the
siblings — slower, noisier, easier to miss.

---

## Phase 1: Requirements

### Why

1. **Quality regressions in siblings are caught later than in
   attune-ai.** attune-ai's pre-commit fails fast on:
   - unformatted code (black) — caught at commit time
   - lint violations (ruff) — caught at commit time
   - obvious security smells (bandit) — caught at commit time
   - committed secrets (detect-secrets) — caught at commit time
   - trailing whitespace, EOF newlines, YAML/JSON validity —
     caught at commit time

   In siblings, all of these surface in CI (15+ min round
   trip) or PR review. The asymmetry is real and increases
   in cost every time a sibling repo grows.

2. **Patrick already maintains these tools in his local
   environment.** The dev-loop tools (`uv run black`,
   `uv run ruff`) are installed via attune-ai's dev extras
   and used routinely. Sibling-package work currently bypasses
   them because there's no hook to enforce it.

3. **Claude Code plugin hooks DON'T fill this gap.** attune-ai's
   `plugin/hooks/format_on_save.py` fires on Edit/Write tool
   use *during a Claude session*. It does nothing for direct
   `git commit` invocations from the user's shell. Pre-commit
   is the git-layer enforcement; plugin hooks are the
   Claude-Code-session enforcement. Both are needed, neither
   replaces the other.

4. **Each sibling repo has different sensitivities.** A
   uniform copy-paste is wrong:
   - `attune-rag` ships golden fixtures and benchmarks —
     pre-commit must not auto-modify those.
   - `attune-author` ships generated template content — black
     should skip generated dirs.
   - `attune-help` has structured `.help/` content with strict
     formatting requirements.
   - `attune-gui` has a FastAPI sidecar + frontend assets.

### What — high-level scope

- **In scope**: a `.pre-commit-config.yaml` in each of the
  four sibling repos with a baseline set of hooks tuned to
  that repo's content. "Baseline" = the subset of attune-ai's
  hooks that are universally beneficial:
    - black (100-char line length, matching attune-ai)
    - ruff (with the repo's existing pyproject.toml config)
    - detect-secrets (with a per-repo baseline)
    - trailing-whitespace
    - end-of-file-fixer
    - check-yaml / check-toml / check-json
    - check-added-large-files
    - check-merge-conflict

  Bandit is **deferred**, not in baseline — it's noisy in
  small libraries and needs per-repo tuning that's better
  done in a follow-up.

- **Also in scope**: a `pre-commit install` step documented
  in each repo's `CONTRIBUTING.md` (or `README.md` dev
  section if no CONTRIBUTING) so contributors actually opt
  in. Plus a CI workflow that runs `pre-commit run --all-files`
  on PRs — belt and suspenders, since not everyone installs
  the local hooks.

- **Out of scope**:
    - Bandit (deferred, see above).
    - Custom freshness checks (attune-ai's
      `check-docs-freshness`, `attune-help` template freshness
      hooks). Those are highly attune-ai-specific.
    - mypy. Disabled in attune-ai pre-commit already; no
      reason to add it in siblings.
    - Auto-formatting the entire backlog of legacy code as
      part of this spec. The hook fires on changed files
      only; legacy formatting drift is a separate cleanup.

### Done when

- Each of the four sibling repos has a working
  `.pre-commit-config.yaml`.
- Each repo's CI runs `pre-commit run --all-files` on PRs
  and fails on hook violations.
- Each repo's first pre-commit installation completes
  cleanly — i.e., running `pre-commit run --all-files` on
  the current main branch passes (or any violations are
  fixed in the same PR that introduces the config).
- Contributor docs in each repo point at the install step.

### Non-goals

- Identical hook lists across all four siblings. Per-repo
  tuning is the point.
- Migrating attune-ai's pre-commit config. It's mature; this
  spec is purely about extending the pattern to siblings.
- Replacing existing CI test workflows. Pre-commit-on-CI runs
  alongside, not instead of, the test matrix.

### Open questions (resolve in design phase)

1. Per-repo exclusion lists — what stays unformatted in each
   repo? (golden fixtures, generated content, etc.)
2. Should the four PRs land in a specific order? attune-rag
   first probably (it's the API contract source of truth);
   attune-gui last (it has a frontend dimension that may need
   extra hooks like prettier eventually).
3. Whether the existing `.secrets.baseline` from attune-ai
   should seed the sibling baselines, or each one starts
   from a fresh scan. Per-repo fresh scan is cleaner;
   confirm in design.
