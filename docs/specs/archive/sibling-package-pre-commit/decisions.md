# Decisions — Sibling-Package Pre-commit Parity

**Status**: phase 0 complete
**Decided**: 2026-05-12

---

## D1 — Locked baseline hook list + versions

Pinned to attune-ai's currently-shipping versions
([.pre-commit-config.yaml](../../../.pre-commit-config.yaml))
so siblings never run newer formatters than the umbrella —
black version drift between attune-ai and a sibling would
cause reformatting churn on every merged PR.

| Hook | Repo | Rev | Notes |
|------|------|-----|-------|
| black | psf/black | `24.10.0` | `--line-length=100` |
| ruff | astral-sh/ruff-pre-commit | `v0.8.4` | `--fix --exit-non-zero-on-fix`, plus `--select=BLE --no-fix` as a second pass to block bare excepts |
| detect-secrets | Yelp/detect-secrets | `v1.5.0` | per-repo `.secrets.baseline` (fresh scan, not seeded) |
| trailing-whitespace | pre-commit/pre-commit-hooks | `v5.0.0` | |
| end-of-file-fixer | pre-commit/pre-commit-hooks | `v5.0.0` | |
| check-yaml | pre-commit/pre-commit-hooks | `v5.0.0` | exclude `^mkdocs.*\.yml$` only if the repo has one |
| check-added-large-files | pre-commit/pre-commit-hooks | `v5.0.0` | `--maxkb=1200` (matches attune-ai's `uv.lock` accommodation) |
| check-merge-conflict | pre-commit/pre-commit-hooks | `v5.0.0` | |
| check-toml | pre-commit/pre-commit-hooks | `v5.0.0` | |
| check-json | pre-commit/pre-commit-hooks | `v5.0.0` | |
| mixed-line-ending | pre-commit/pre-commit-hooks | `v5.0.0` | `--fix=lf` |

**Explicitly excluded from baseline** (attune-ai has them
but they're repo-specific or out of scope):

- bandit — needs per-repo `.bandit` config and source paths;
  deferred per requirements.
- mypy — disabled in attune-ai's pre-commit anyway
  ("removed — duplicate module").
- All `repo: local` hooks (pattern-review, platform-compat,
  docs-freshness, patterns-summary) — attune-ai-specific
  automation, not portable.

---

## D2 — Per-repo exclusion table

Each repo gets its own `.pre-commit-config.yaml`'s top-level
`exclude:` regex tuned to the content below. Common to all:
`\.venv/`, `build/`, `dist/`, `.*\.egg-info/`, `__pycache__/`,
`node_modules/`.

| Repo | Repo-specific excludes | Rationale |
|------|------------------------|-----------|
| **attune-rag** | `tests/golden/` | Golden fixtures for retrieval regression — exact-byte stability is the whole point. Black/ruff/trailing-ws must not touch. |
| **attune-rag** | `src/attune_rag/dashboard/templates/.*\.html$`, `src/attune_rag/editor/template_schema\.json$` | Shipped package data (per pyproject.toml). HTML/JSON aren't Python; black/ruff irrelevant, but the EOF/trailing-ws hooks could rewrite them — exclude to be safe. |
| **attune-author** | `benchmarks/hallucination-v.*/`, `benchmarks/.*\.yaml$` | Hallucination eval baselines + run artifacts; reformatting would invalidate comparisons. |
| **attune-author** | `src/attune_author/meta_templates/.*\.j2$` | Jinja templates (per pyproject.toml package-data); not Python, formatter false positives. |
| **attune-author** | `# Long prompt strings in _anthropic.py / polish.py may need per-file ruff ignores` | Per CLAUDE.md lesson: prompt-string lines can trip ruff. Resolve case-by-case during Phase 2 rather than pre-emptively excluding the files. |
| **attune-help** | `src/attune_help/templates/.*\.(md|json)$`, `src/attune_help/demos/.*\.md$` | LLM-polished template content (per pyproject.toml package-data). Trailing-whitespace + EOF-fixer would silently rewrite generated content; check-json would reject schema variants. Both bad. |
| **attune-gui** | `editor-frontend/` | TypeScript/React frontend with its own toolchain (eslint, prettier, vite). Pre-commit can't usefully lint TS here. |
| **attune-gui** | `__pycache__/`, `dist/` | Build/cache artifacts (matches global excludes; called out because they appear at repo root). |

---

## D3 — Per-repo specifics worth flagging before each Phase

**attune-rag**:
- Has `dist/` at repo root (build artifact); covered by
  global exclude.
- `tests/golden/` is THE critical exclusion — confirmed
  the dir exists.

**attune-author**:
- `pyproject.toml` already has
  `[tool.ruff] line-length = 100` and
  `select = ["E", "F", "W", "I", "UP", "BLE"]` — already
  aligned with attune-ai's enforcement. Pre-commit add is
  pure dev-loop gain.
- Long-prompt-string ruff trips will surface as Phase 2
  noise; resolve with `# noqa` rather than excluding files.

**attune-help**:
- Top-level dirs: `dist/`, `scripts/`, `src/`, `tests/` —
  no surprises.
- The templates package-data is the load-bearing exclusion.
  Without it, every `pre-commit run --all-files` would
  rewrite hundreds of LLM-generated `.md` files and corrupt
  the polished content.

**attune-gui**:
- Hybrid repo: Python sidecar + TypeScript frontend.
  Pre-commit only meaningfully applies to `sidecar/`,
  `scripts/`, `specs/`. The `editor-frontend/` directory is
  out of scope (its own toolchain).
- No `[tool.setuptools.package-data]` in pyproject.toml —
  simpler exclusion surface than the other three.

---

## D4 — Order of execution (refines tasks.md Phase 1-4)

Phase 0 found no surprises that would change the planned
order. Keep:

1. **Phase 1: attune-rag first** — API contract source of
   truth; smallest meaningful diff.
2. **Phase 2: attune-author** — exposed prompt-string ruff
   issue is the only new variable; resolve in-flight.
3. **Phase 3: attune-help** — load-bearing template
   exclusion is the only critical move; otherwise simple.
4. **Phase 4: attune-gui** — hybrid repo, smallest Python
   surface; finish with the easiest.

Each PR independent and individually mergeable.

---

## D5 — Cost (Phase 0)

Zero API cost. Phase 0 was pure repo introspection (file
reads + `pyproject.toml` scans). Total elapsed: ~3 minutes.

This is the right kind of Phase 0 — cheap research that
locks design decisions before any irreversible work.
Contrast with `agent-surface-rebalance` Phase 0 ($8.78 of
real API usage) which was the right cost for a measurement
that hinges on real workflow execution.
