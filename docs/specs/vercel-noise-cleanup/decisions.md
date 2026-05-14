# Decisions — Vercel Noise Cleanup

**Status:** draft — DECIDE callouts need Patrick's input before
design.md can be written

Context, investigation findings, and the resolution option set. See
`requirements.md` for user stories and acceptance criteria.
`design.md` and `tasks.md` are intentionally omitted from this draft
PR — they will be written after Patrick approves this file.

> **DECIDE callouts** mark choices that need Patrick's input before
> the implementation phase. Search this file for `**DECIDE:**`.

---

## Why this exists

Every pull request on `Smart-AI-Memory/attune-ai` carries a
permanently-failing `Vercel – attune-ai` commit status. This has been
the case long enough that the CLAUDE.md lessons section explicitly
instructs agents to ignore it (see verbatim excerpt below).

**Noise quantification (sampled 2026-05-14):**

| PR | Merged | Vercel – attune-ai | Vercel – website |
|----|--------|-------------------|-----------------|
| #343 | 2026-05-14 | failure | success |
| #342 | 2026-05-14 | (not sampled) | — |
| #320 | 2026-05-13 | failure | success |
| #306 | open | failure | success |
| #303 | 2026-05-13 | failure | success |

All 30 most-recent closed PRs (the full page returned by
`gh pr list --state closed`) carry this failure because the commit
status fires on every push to the repository.

**Impact:**

- `gh pr view <N> --json statusCheckRollup` returns `state: FAILURE`
  for 100% of PRs, making the rollup useless as a merge-readiness
  signal.
- Agents querying the rollup must hard-code a name-based ignore list,
  creating ongoing maintenance burden (see lesson below).
- Contributors see a red check on every PR and either ignore it
  (correct but confusing) or investigate it (wasted effort).
- The `auto-approve-owner` workflow uses CI status to decide when to
  approve; the permanent failure does not block it only because
  `Vercel – attune-ai` is not a required check — but this is an
  invisible dependency on that fact remaining true.

---

## What `Vercel – attune-ai` actually is

### Investigation findings

The commit status is posted by the Vercel GitHub App
(`github.com/apps/vercel`, avatar ID `8329`). It originates from
the Vercel project named **`attune-ai`** inside the Vercel team named
**`empathy-framework`**.

```
context:     "Vercel – attune-ai"
target_url:  https://vercel.com/empathy-framework/attune-ai/<deploy-id>
description: "Deployment has failed — run this Vercel CLI command:
             npx vercel inspect dpl_<id> --logs"
```

The working check is:

```
context:     "Vercel – website"
target_url:  https://vercel.com/empathy-framework/website/<deploy-id>
description: "Deployment has completed"
```

### Team name artifact

The Vercel team is still named `empathy-framework` — the project's
original name before it was rebranded to Attune AI. This confirms the
`attune-ai` Vercel project predates the current `website/` directory
layout.

### Root cause hypothesis (high confidence)

The repo's Next.js app was originally at the repo root. At some point
it was moved into the `website/` subdirectory, and a **new** Vercel
project (`website`) was created pointing at `website/`. The **old**
Vercel project (`attune-ai`) was left connected to the repository,
still trying to deploy from the root, where there is no longer a
`package.json` or Next.js app. Every push triggers a deployment
attempt that fails immediately at the build step.

Evidence:

- `website/vercel.json` exists (Next.js config for the `website`
  project); no `vercel.json` or `package.json` exists at the repo
  root.
- `Vercel – website` succeeds on every PR; `Vercel – attune-ai`
  fails on every PR with the same "Deployment has failed" error.
- The `empathy-framework` team name is a rebranding artifact — same
  timeline as when the code was reorganised.

**DECIDE-1:** Can Patrick log into the `empathy-framework` Vercel
dashboard and confirm the `attune-ai` project's root directory /
build settings? This would confirm or refute the hypothesis before
design.md proposes a specific fix step. If the project has custom
build settings that point at a deleted path, that is also
confirmatory.

---

## The four resolution options

### Option A — Disable GitHub checks/comments for the failing project

**What:** In the Vercel project settings for `attune-ai`
(empathy-framework team → Project → Settings → Git → "Comments and
Checks"), uncheck the option that posts commit statuses to GitHub.

**Pros:**
- Surgical — the project continues to exist and deploy internally;
  only the GitHub status posting is disabled.
- Reversible in one click.
- No risk of accidentally breaking an unknown dependency on the
  project itself.
- Does not require deleting anything.

**Cons:**
- The project still deploys on every push, consuming Vercel build
  minutes for a deployment no one views.
- The root cause (broken build) persists; it just becomes silent.
- A future developer might re-enable checks and be confused by the
  reappearing failure.

**Surface area:** Vercel project settings UI only. Zero repo changes.

---

### Option B — Disconnect the GitHub repository from the failing project

**What:** In the failing Vercel project's settings
(empathy-framework team → attune-ai → Settings → Git), remove the
GitHub repository connection entirely. This stops Vercel from
receiving push events for that project.

**Pros:**
- Stronger than Option A: the project stops triggering on pushes
  entirely, so no build minutes are consumed.
- Still reversible — the project remains in the Vercel dashboard and
  can be reconnected.
- Does not delete any deployment history or configuration.

**Cons:**
- If the `attune-ai` project was ever serving a staging URL cited in
  documentation or bookmarks, those URLs stop updating (though
  previous deployments remain accessible).
- Slightly more disruptive than Option A (silences builds entirely
  vs. just hiding the check).

**Surface area:** Vercel project settings UI only. Zero repo changes.

**DECIDE-2:** Does the `attune-ai` Vercel project's deployment URL
appear anywhere in documentation, issue templates, or shared
bookmarks? If not, Option B is strictly better than Option A.

---

### Option C — Delete the failing Vercel project entirely

**What:** Delete the `attune-ai` project from the Vercel
`empathy-framework` team.

**Pros:**
- Clean — no vestigial project accruing history and build minutes.
- Removes the source of the problem permanently.

**Cons:**
- Irreversible without recreating the project from scratch.
- Destroys all deployment history for that project (may matter if it
  was ever the canonical production deployment).
- Higher blast radius than needed if the project is genuinely stale.

**Surface area:** Vercel project deletion UI. Zero repo changes.

**When to prefer over B:** If Patrick confirms the `attune-ai`
project has never been the production deployment and has no external
references, deletion is the cleanest option.

---

### Option D — Fix the build so the project deploys successfully

**What:** Configure the `attune-ai` Vercel project to point at the
`website/` root directory (matching the `website` project), or add a
minimal `package.json` at the repo root.

**Pros:**
- Resolves the root cause rather than silencing it.
- Both Vercel projects would deploy successfully, giving two preview
  URLs per PR (potentially useful for staging vs. preview purposes).

**Cons:**
- Creates a second site deployment on every push — doubles Vercel
  build minutes.
- Two identical preview deployments confuse contributors about which
  URL is canonical.
- Unless there is a genuine use case for two separate Vercel
  environments, this is solving the wrong problem.
- A `vercel.json` at the repo root would interfere with tools that
  look for Vercel config at the project root.

**Verdict:** Not recommended. The `website` project already succeeds.
A second deployment of the same site adds cost and confusion with no
benefit.

---

## Recommended path (preliminary)

Based on investigation findings, the recommended path is
**Option B (disconnect)** or **Option C (delete)**, depending on
DECIDE-1 and DECIDE-2.

Decision tree:

```
Does the attune-ai project's deployment URL appear anywhere
in docs, issue templates, or shared bookmarks?
│
├─ YES → Use Option A (disable checks) while auditing usage,
│         then move to Option B or C once usage is confirmed zero.
│
└─ NO → Does Patrick want to preserve deployment history?
        │
        ├─ YES → Option B (disconnect)
        └─ NO  → Option C (delete)
```

**DECIDE-3:** Patrick's preference from the decision tree above.
This is the only input needed before design.md can be written.
design.md for Options B and C is trivially short (one Vercel UI
action + one CLAUDE.md cleanup commit). Stating the preference here
unblocks writing it.

---

## Relevant CLAUDE.md lesson (verbatim)

The following lesson appears in `.claude/CLAUDE.md` under
"Lessons Learned" and is the primary evidence that this problem has
been chronic long enough to require a documented workaround:

> **Admin-merging a deletion PR without checking the `build` docs
> check breaks main**: PR #279 deleted `attune.coordination` and was
> admin-merged with all tests green, but `docs/reference/multi-agent.md`
> had `::: attune.coordination.ConflictResolver` mkdocstrings autogen
> blocks. Main's `mkdocs build` failed immediately, blocking the next
> PR in the stack. The trap: every PR fails Vercel-attune-ai
> permanently (legacy preview), so the "failures" field in
> `gh pr view --json statusCheckRollup` is always non-empty. When
> admin-merging a `feat!:` or any deletion PR, **read each failure by
> name** — `build`, `test (...)`, `Analyze (...)` are fail-real,
> while `Vercel – attune-ai` is fail-ignore. Concrete rule: before
> admin-merging a deletion, also `grep -rn "::: <removed.module>"
> docs/` and `grep -rn "<RemovedClass>" docs/` to catch mkdocstrings
> autogen refs that won't resolve. Fixing main mid-session via a
> hotfix branch (`hotfix/...`) and a focused PR is the right recovery
> path — don't try to bundle the fix into the next stacked PR.

The lesson is correct and useful for the PR #279 scenario. The
vercel-noise-cleanup spec exists to eliminate the permanent-failure
premise so the lesson no longer needs the "Vercel – attune-ai is
fail-ignore" clause.

---

## What this spec explicitly will NOT do

- No changes to `.github/workflows/` files.
- No changes to repo-level branch protection rules.
- No required-check additions or removals.
- No edits to `website/vercel.json` or any repo-tracked Vercel
  config.
- `design.md` and `tasks.md` are not in this draft PR — they are
  intentionally deferred pending DECIDE-3 above.
