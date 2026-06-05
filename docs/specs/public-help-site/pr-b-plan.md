# PR-B Plan — Tutorial / How-To Migration (for review)

> Prepared while you were out. This is a **recommendation to
> approve/prune**, not a commitment. PR-B implements spec tasks T3 +
> T8 (the guides migration + redirects). Nothing here is built yet.

---

## Your two sign-offs, with recommendations

### 1. Migration set — what moves to `/help` vs stays

Audit of all 13 `docs/tutorials/` + 26 `docs/how-to/` files
(read, not guessed). Headline: **almost everything is USER content
and should move**; only 2 files are maintainer-internal.

**MOVE to attune-ai.dev/help (USER content):**

- **11 tutorials** — META_ORCHESTRATION, build-a-workflow, hooks,
  ops-dashboard, release-prep, spec-engine, plugin, refactor-plan,
  bug-predict, rag-grounding, deep-review.
- **23 how-tos** — everything except the two maintainer docs below
  and the stub index.

**STAY in mkdocs (maintainer / contributor):**

- `how-to/help-system-maintenance.md` — `.help/` corpus freshness,
  weekly regen PR, drift checks. Internal maintenance.
- `how-to/learning-and-patterns.md` — session evaluator + pattern
  extractor pipeline. Internal.

**DELETE (stubs / stale, replaced by the generated site):**

- `tutorials/installation.md` — 15-line stale redirect to
  `getting-started/installation.md`.
- `tutorials/index.md` + `how-to/index.md` — hand-maintained landing
  stubs (the how-to one already omits 18 of 26 docs). The generated
  `/help` landing replaces both.

> **Prune freely** — if any of the 34 "move" docs feel
> maintainer-only to you (e.g. agent-factory, project-analysis), say
> so and they stay.

### 2. Install page — recommendation: **both**

- Keep the quick **`pip install attune-ai` chip** on the landing
  page (already there — fastest path for a visitor).
- Migrate `docs/getting-started/installation.md` (171 lines:
  pip + provider config + Redis) into **`/help/installation`** as
  the full guide. Delete the stale `tutorials/installation.md`
  redirect.

So: chip for the 2-second answer, `/help/installation` for the real
setup. The two how-tos that mention prereqs (`prerequisites.md`)
fold into `/help/installation` or sit beside it.

---

## Feature-centric merge map (Model A)

Most guides slug-match a feature and merge into its page; the rest
go to `/help/guides/`. **Exact slug matches auto-merge**; the
*topic* matches (italicized) are judgment calls to confirm:

| Guide(s) | Merges into feature |
|---|---|
| bug-predict, deep-review, hooks, ops-dashboard, plugin, rag-grounding, refactor-plan, release-prep, spec-engine (tutorial + how-to each) | same-named feature (exact match) |
| resilience-patterns | resilience |
| telemetry-and-signals | telemetry |
| *security-architecture* | *security-audit* |
| *unified-memory-system, memory-graph* | *memory* |
| *META_ORCHESTRATION* | *orchestration* |
| *agent-factory* | *agents* |
| *triage-code-quality* | *code-quality* |

**`/help/guides/` catch-all** (no clean feature home):
build-a-workflow, practical-patterns, multi-agent-coordination,
smart-router, auto-chaining, context-management,
project-analysis-and-metrics, discovery-sweep-on-the-dashboard.

---

## Two things the audit surfaced (decide in PR-B)

1. **8 how-tos have stale code examples** — unresolved module
   imports in `bug-predict, deep-review, hooks, plugin,
   rag-grounding, refactor-plan, release-prep, spec-engine`. They
   render fine as markdown, but the import paths may be wrong.
   **Recommendation:** render as-is in PR-B (rendering ≠ content
   fixing), and open a separate content-fidelity pass (the
   attune-author fact-check pipeline, attune-author#27, is built for
   exactly this). Don't block the migration on it — but don't
   silently ship broken examples either; a banner or a tracked
   follow-up.

2. **T3 risk is lower than the spec feared** — the audit found **no
   `!!! note` admonitions or `:::` fenced divs** in the guide
   bodies. Only the two `index.md` stubs use Material card markup,
   and those aren't migrating. So the "strip mkdocs-isms" work is
   light: handle code fences (markdown-it renders them) + a
   defensive check for stray Material syntax. Good news for PR-B
   scope.

---

## Suggested PR-B task order

1. Extend `build_help.py`: second source (tutorials + how-to),
   slug-match + Model-A merge, `/help/guides/` catch-all, defensive
   admonition strip.
2. Migrate `getting-started/installation.md` → `/help/installation`;
   delete `tutorials/installation.md` + the two index stubs.
3. Redirects (T8): old framework-docs guide URLs → new `/help`
   homes (cold traffic, low priority — can be a follow-up).
4. Tests: slug-match correctness, guides catch-all, merged-page
   structure, content-fidelity banner.
5. CHANGELOG + decisions.md log entry.

**Smallest first step when you're back:** confirm/prune the move
list + the install-page call above, then I extend `build_help.py`
for the second source. Everything else follows mechanically.
