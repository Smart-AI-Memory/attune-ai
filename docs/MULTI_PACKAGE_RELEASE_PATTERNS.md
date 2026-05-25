# Multi-package release patterns

Patterns for coordinating releases across the attune-* family (attune-ai, attune-rag, attune-author, attune-help, attune-gui, attune-lite, attune-redis) without locking releases into "all at once" cycles.

---

## Pattern: Widen the consumer's dep range *before* the upstream releases

**Problem.** Two packages, downstream pins upstream tight (e.g. `attune-author>=0.6.2,<0.12`). Upstream is about to bump (e.g. attune-author 0.14.0). If we ship them on the same day with the tight pin, we need a coordinated cut: bump upstream, publish, bump downstream's range, publish. One side slipping blocks the other.

**Pattern.** **Widen the downstream's dep range as its own PR, *before* the upstream releases.** Each side then ships on its own schedule with no coordination.

**Worked example (2026-05-24).**

| When | Who | What |
|---|---|---|
| Days before release | attune-ai | PR #429 widens `[author]` extra: `attune-author>=0.6.2,<0.12` → `>=0.6.2,<0.14`. Lands on main. attune-ai still uses whatever attune-author version is installed locally. |
| Morning of release day | attune-author | Ships v0.14.0 to PyPI. No coordinating attune-ai work needed. |
| Same day | attune-ai | Ships v7.1.0 to PyPI. `pip install attune-ai[author]` resolves attune-author 0.14.0 cleanly. |

**Why it works.** Widening the range is a no-op at runtime as long as the installed version still satisfies the old range. It pre-authorizes the upstream bump without requiring it. When the upstream finally ships, no downstream code changes.

**Anti-pattern: keep the tight pin and chase.** Tight pin (`==0.13.x` or `<0.14`), upstream ships 0.14.0, downstream now MUST cut a coordinating PR (range bump) before it can release. Worst case: downstream's release goes out the door pinned to a version PyPI no longer recommends, OR it gets blocked behind a five-minute fix that should have been a five-second non-event.

**When to apply.**
- Always when the upstream package has a known imminent bump
- Always when widening doesn't introduce a real API risk (i.e. semver-minor on a 0.x dep with no breaking changes is safe to pre-authorize; semver-major might warrant testing first)
- Useful as a routine grooming task — periodically widen ranges on dev-extras that drift conservative

**When NOT to apply.**
- Production-critical dep on a fast-moving API surface where you genuinely want to gate on testing each new upstream version
- When the upstream has an established history of breaking minor bumps

**Implementation shape.**

Single-line PR in `pyproject.toml`:

```diff
 [project.optional-dependencies]
-author = ["attune-author>=0.6.2,<0.12"]
+author = ["attune-author>=0.6.2,<0.14"]
```

Optional title hint: `chore(deps-dev): widen [author] extra to accommodate upstream 0.13.x+`. Squash-merge fine.

---

## Pattern catalogue (this doc grows)

When you spot another reusable pattern from a release cycle, add it above with the same structure: **Problem / Pattern / Worked example / Why it works / Anti-pattern / When to apply / Implementation shape.**

Likely future entries:
- The parallel-audit-during-siesta pattern (5 read-only agents, per-package reports + verdict table)
- The release-prep PR pattern (release/vX.Y.Z branch + PR instead of direct-to-main)
- The CHANGELOG `[Unreleased]` discipline (lint + PR-template guard)
- The lockfile/version-stamp consistency check (uv.lock, `__version__.py`, pyproject all match)
