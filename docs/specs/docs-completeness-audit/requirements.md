# Spec: Documentation Completeness Audit

> The `doc-fiction-cleanup` spec triaged the 30-doc cohort tracked
> in `.help/features.yaml` `doc_paths` and the `attune_llm` dead-import
> sweep. That work shipped Phase 1–3 RETIRE and queued the remainder.
> This spec covers the **complementary surface**: docs under `docs/`
> that were never enrolled in `features.yaml`, never appeared in
> `attune-author status`, and were therefore never systematically
> checked against current source. A "strong release" requires that
> the **unknown-unknown** docs are triaged with the same discipline
> as the tracked cohort — or the next reader still hits fiction,
> just in a different aisle of the store.

**Status:** draft
**Created:** 2026-05-30
**Owner:** TBD
**Related:** [`doc-fiction-cleanup`](../doc-fiction-cleanup/) (sibling — tracked-cohort triage);
[`docs-wiring-audit`](../docs-wiring-audit/) (sibling — mkdocs nav / inbound link integrity);
[`docs-release-prep`](../docs-release-prep/) (sibling — release-gate composition);
[`sdk-error-message-fidelity`](../sdk-error-message-fidelity/) (why `doc-audit` workflow can't be used for triage)

---

## Problem statement

`.help/features.yaml` only enrols **24 docs** under `doc_paths`. A
`find docs/ -name '*.md'` (excluding `docs/archive/` and `docs/specs/`)
returns **203 files** — so **~179 docs sit outside the tracked cohort**.
Subtracting the ~30 docs already touched by `doc-fiction-cleanup`
PRs #506–#510 leaves on the order of **~145 untracked, never-triaged
docs** whose claims against current `src/` are unverified.

Spot-checks of this surface keep turning up fiction:

- `docs/ORCHESTRATION_API.md` self-identifies as **"Version 4.0.0"**
  while the real package is `attune-ai 7.2.0`; describes a
  meta-orchestration API surface that needs verification against
  `src/attune/orchestration/meta_orchestrator.py`.
- `docs/PROJECT_OVERVIEW.md` claims **"Version 5.1.1"** and "15
  multi-agent workflows" — both unverified, both contradicted by
  `pyproject.toml` (`version = "7.2.0"`) and the actual workflow
  count under `src/attune/workflows/`.
- `docs/BLOG_CLAUDE_OPTIMIZATION.md` and `docs/EXCEPTION_HANDLING_GUIDE.md`
  received **partial** cleanup in PR #508 — neither has been
  re-verified end-to-end against current source.
- `docs/SKILLS_REFERENCE.md`, `docs/FEATURES.md`, `docs/CLAUDE_NATIVE.md`,
  the entire `docs/architecture/` tree, and most of `docs/blog/`
  are wholly untouched by this session's triage.

### Why this slipped past `doc-fiction-cleanup`

`doc-fiction-cleanup` was scoped to the surface its detector
**could see** — the `features.yaml` `doc_paths` enrollment plus a
grep for `attune_llm` / `coach_wizards` / `attune.webhooks` markers.
Docs that drift in *other* directions (wrong version numbers, stale
class names, retired CLI flags, invented module structure) without
tripping those specific markers stay invisible. The completeness
gap is structural, not accidental.

### Why `doc-audit` couldn't do this triage either

Same reason as `doc-fiction-cleanup`: `attune workflow run doc-audit`
is currently unrunnable from inside a Claude Code session because
`claude_agent_sdk.query()` exits code 1 on teardown. See
[`sdk-error-message-fidelity`](../sdk-error-message-fidelity/) and
the memory note `project_sdk_workflows_blocked_nested`. This spec
will use the same in-harness subagent triage shape that worked for
the tracked cohort.

---

## Scope

**In scope** — every doc under `docs/` that satisfies ALL of:

- Is **not** listed in `.help/features.yaml` `doc_paths` (the
  24-doc tracked cohort handled by `doc-fiction-cleanup`).
- Is **not** under `docs/archive/` (mkdocs excludes it; readers
  don't see it).
- Is **not** under `docs/specs/` (specs are project artifacts,
  not user-facing docs — they have their own truthing model).
- Was **not** the subject of a doc-fiction-cleanup PR (PRs
  #506, #507, #508, #509, #510) OR was only **partially** cleaned
  by one of those PRs (`BLOG_CLAUDE_OPTIMIZATION.md`,
  `EXCEPTION_HANDLING_GUIDE.md` are explicit re-verify targets).

**Out of scope:**

- The 30-doc tracked cohort — owned by `doc-fiction-cleanup`.
- Docs under `docs/archive/` — already excluded from the build.
- Docs under `docs/specs/` — covered by spec-truthing workflow,
  not user-doc accuracy.
- Cosmetic frontmatter drift (hashes, timestamps) where the
  prose still verifies — the regular `.help` regen cycle owns this.
- mkdocs nav-wiring / inbound-link integrity — owned by sibling
  spec `docs-wiring-audit`.

---

## Acceptance criteria

- Every in-scope doc has been **read against current `src/`** and
  classified into exactly one bucket:
  - **MECHANICAL** — concrete claims drift (version numbers, class
    names, import paths, CLI flags) but the doc still describes a
    real feature; fix in place.
  - **REWRITE** — doc describes a real feature through a
    substantially fictional surface; rewrite the affected sections.
  - **RETIRE** — doc describes a feature that no longer exists or
    never existed as written; remove + update inbound links.
  - **CLEAN** — verified accurate as-is; no action needed.
- A `completeness-audit-triage.md` artefact exists in this spec
  directory listing every in-scope doc with its bucket, the
  evidence trail (which `src/` files were read to verify), and a
  one-line justification.
- Every MECHANICAL and REWRITE doc has either landed in a PR or
  been explicitly deferred to a follow-up phase with reasoning
  recorded in `decisions.md`.
- Every RETIRE doc is removed from the working tree, removed from
  any mkdocs nav references, and inbound links are repaired (or
  the cross-spec `docs-wiring-audit` is updated to cover them).
- A final `mkdocs build --strict` passes after all PRs land.
- `pyproject.toml` `version` and any version string in retained
  docs agree, or the doc deliberately uses unversioned phrasing.

---

## Coverage areas

### 1. Problem statement
Captured above — ~145 untracked-untriaged docs with confirmed
spot-check fiction (wrong version numbers, unverified surface
claims, partial earlier cleanup).

### 2. Scope
Captured above — defined positively (in) and negatively (out),
with explicit handoff to sibling specs.

### 3. Acceptance criteria
Captured above — triage artefact + per-doc bucket + PRs landed
or deferred-with-reasoning + clean `mkdocs build --strict`.

### 4. Approach

Mirror the shape that worked for `doc-fiction-cleanup`:

**Stage A — Scout (parallel subagents).** Produce
`completeness-audit-triage.md` by fanning out subagents over
batches of ~15 docs each. Each subagent reads its batch against
current `src/` (using `pyproject.toml` version, the
`src/attune/workflows/` inventory, and any class/CLI claims) and
assigns a bucket + evidence.

**Stage B — Bucket-shaped PRs.** One PR per bucket-cluster, not
one PR per doc. RETIRE PR removes a batch of doc files and
patches inbound links. MECHANICAL PR sweeps version strings and
class-name drift across the cluster. REWRITE PRs are
doc-by-doc because rewrites can't be safely batched.

**Stage C — Verification.** `mkdocs build --strict` + a final
grep-sweep for the same fiction markers `doc-fiction-cleanup`
used (`attune_llm`, `coach_wizards`, `attune.webhooks`) plus any
version strings that disagree with `pyproject.toml`.

### 5. Risks

- **Scope inflation.** If the audit reveals 40+ MECHANICAL docs,
  the work blows past "strong release" budget. Mitigation: cap
  Stage B at one weekend; anything not landed by then defers to
  a follow-up release cycle with the triage artefact preserved
  so future-Patrick has the inventory.
- **Hidden inbound links.** RETIRE-ing a doc that's referenced
  from an external source (PyPI README, blog index, marketing
  site) breaks discoverability silently. Mitigation: before any
  RETIRE PR, grep the workspace for inbound references AND check
  the `attune-ai` PyPI long-description for cross-references.
- **Partial-cleanup regression.** `BLOG_CLAUDE_OPTIMIZATION.md`
  and `EXCEPTION_HANDLING_GUIDE.md` already had partial PR #508
  cleanup — re-verifying without rolling back PR #508's
  improvements requires reading PR #508 first.
- **Triage subagent drift.** A subagent classifying 15 docs at
  once may rubber-stamp CLEAN to finish faster. Mitigation:
  require evidence (specific `src/` file:line) for every CLEAN
  verdict, not just for MECHANICAL/REWRITE/RETIRE.

### 6. Cross-spec impact

- **`doc-fiction-cleanup`** — this spec is the strict complement.
  Boundary: `features.yaml doc_paths` membership. If `doc-fiction-cleanup`
  Phase 3 REWRITE/Phase 4 changes the enrolled-cohort definition,
  this spec's "in scope" set shifts; we re-pull the diff before
  Stage A executes.
- **`docs-wiring-audit`** (sibling, in-flight) — handles
  mkdocs nav consistency and broken inbound links. Our RETIRE
  bucket hands off to `docs-wiring-audit` for nav cleanup; we
  don't duplicate that work.
- **`docs-release-prep`** (sibling, in-flight) — assembles the
  release gate. This spec must complete (or formally defer
  remainder) before `docs-release-prep` can declare a strong
  release.

### 7. Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Exhaustive vs sampling | Exhaustive | 20% sample with statistical inference | "Strong release" requires no hidden landmines; sampling leaves them in. |
| Per-doc rewrite vs batch retire-default | Per-doc within buckets | Default-retire anything not actively maintained | Some docs (e.g. `PROJECT_OVERVIEW.md`) are evergreen-shaped and should be rewritten, not retired. |
| One PR per doc vs one PR per bucket | One PR per bucket-cluster (RETIRE/MECHANICAL); one per doc for REWRITE | One mega-PR | Bucket PRs are reviewable; mega-PR is not. REWRITEs each need substantive review. |
| Inventory now vs as-discovered | Full triage artefact first | Pull-request as you find | The artefact is the deliverable even if PRs defer; without it the gap re-opens silently. |

### 8. Rollback

Specs don't roll back, but PRs can:

- **MECHANICAL PRs** — `git revert <sha>`; the doc returns to its
  fictional state but builds still pass.
- **RETIRE PRs** — `git revert` restores the file; inbound-link
  patches in the same PR also revert. Risk: if a downstream
  blog/marketing post linked the retired path during the window
  between merge and revert, that link 404s. Mitigation: grep the
  workspace for inbound references **inside the PR** before
  merge, and include a 30-day "no surprise RETIRE" review window
  before `docs-release-prep` declares the release strong.
- **REWRITE PRs** — `git revert` restores the prior (fictional)
  version. Acceptable because the prior version was the active
  source of confusion.

If a RETIRE turns out to break a discoverability path, recovery
is: restore from `docs/archive/` (which is where retired docs
go before deletion is final) rather than a full revert.

---

## Open questions

These are deliberately *not* answered in Phase 1 — they're
flagged for Patrick to resolve before approval so the scope
definition is honest:

1. **Blog-shaped docs (`docs/blog/*.md`, `docs/BLOG_*.md`) — in
   or out?** Blog posts are inherently dated artefacts; a 2026
   post describing v3.x behaviour isn't "fiction," it's history.
   Options: (a) all blog docs OUT — they're history, not docs;
   (b) all blog docs IN — they're discoverable from the site and
   should be accurate; (c) date-cutoff IN — anything dated within
   N months of release is treated as docs, older is archived.
   Recommendation pending Patrick.

2. **`docs/PROJECT_OVERVIEW.md` — primary candidate or evergreen?**
   It's high-visibility (top-level project narrative) and currently
   carries a wrong version number. Options: (a) treat as MECHANICAL
   — sweep version + workflow counts; (b) treat as REWRITE — the
   whole framing may be stale; (c) treat as evergreen with version
   stripped — rewrite to be version-agnostic so it stops drifting.

3. **Counting / sizing** — preliminary numbers (203 total ÷ 24
   tracked ÷ ~30 PR-touched ≈ 145 in scope) are from a
   workspace-cwd `find`. Before Stage A spawns subagents, do a
   final `git ls-files docs/` pass to be sure no untracked
   local files are inflating the count, and to be sure the
   triage budget (~145 / 15-per-subagent ≈ 10 subagents) is
   right-sized.

---

## Gaps

This is a draft. Until the three open questions are resolved and
the in-scope set is finalised, the artefact stays at `draft`
status. No code or doc changes happen on the basis of this spec
until Phase 1 is `approved`.

---

## Phase 2: Design

See Phase 1 first. To be written after Phase 1 approval.

## Phase 3: Tasks

See Phase 1 first. To be written after Phase 2 approval.

## Phase 4: Implementation

See Phase 1 first. To be written after Phase 3 approval.
