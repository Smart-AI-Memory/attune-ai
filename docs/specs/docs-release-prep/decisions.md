# Per-decision log — Docs release prep

Append-only log. Resolutions for the open questions enumerated in
[requirements.md](./requirements.md#open-questions). The release
ceremony itself remains unscheduled — it executes only after the
two prerequisite specs (`docs-completeness-audit` Phase 1 and
`docs-wiring-audit` Phase 1) land on `main`.

---

## Phase 1 approval (2026-05-31)

Three open questions resolved in one session. Spec status flips
from `draft` to `approved`. Phase 2 (the release ceremony itself)
runs only after dependencies in
[requirements.md → Dependencies](./requirements.md#dependencies-block-release-until-each-is-met)
are met.

---

### Q1 — Version bump policy: 7.3.0 minor vs 7.2.1 patch?

**Decision:** **7.3.0 minor.** Signals "user-visible improvement"
and matches the scale of the corpus change.

**Rationale:** Strict semver requires a minor bump when a `feat`
commit ships, and main already has PR #500 (`feat(hooks): discover
specs under docs/specs`) since 7.2.0. Patch undersells what's
shipping. Additionally, the doc-cleanup arc is substantial
(~120-135 files audited and corrected per
[docs-completeness-audit/decisions.md Q3](
../docs-completeness-audit/decisions.md#q3--counting--sizing-verify-the-math-before-subagent-spawning))
— calling that "patch" reads as understated to users glancing at
release notes.

**Alternatives considered:**

- **7.2.1 patch** — Technically correct for a docs-only change
  IF docs were the only thing landing. But PR #500's `feat` makes
  patch semantically wrong.
- **7.3.0 minor framed as 'docs release'** — Same version,
  different release-notes framing. Release notes will lead with
  the doc cleanup (primary value) but version stays minor for
  semver correctness.

**Implementation note for Phase 2:**

- Release notes lead-in: "v7.3.0 — Docs cleanup release.
  Fictional and out-of-date documentation removed or rewritten
  across ~135 files; new feature: hooks now discover specs under
  `docs/specs/`."
- CHANGELOG entry under `## [7.3.0]` aggregates the
  doc-fiction-cleanup arc PRs (#499, #506-510), the
  docs-completeness-audit execution PRs, the docs-wiring-audit
  execution PRs, PR #500, PR #512 (wizard entry-point fix), and
  any chips that happen to land in time.
- See [CLAUDE.md "Version bumps touch 7+ files"](../../../.claude/CLAUDE.md)
  lesson for the version-bump checklist.

---

### Q2 — Do the 4 spawned chips block this release?

**Decision:** **Don't block. Ship as docs-cleanup release; chips
ride the wave if they happen to land in time.**

**Chip inventory:**

| # | Chip | Status |
|---|------|--------|
| 1 | Wizard entry-point group fix | **DONE** — PR #512 merged 2026-05-30 |
| 2 | `create_wizard` docstring fix | Pending; small fix |
| 3 | `attune-frameworks` CLI spec | Pending; weeks of new-spec work |
| 4 | Team-coordination-on-shared-redis spec | Pending; weeks of new-spec work |

**Rationale:** Chips 3 and 4 are net-new specs that haven't even
been scoped yet — blocking on them pushes the release out
indefinitely while the doc fixes sit unshipped, which is exactly
the inconsistent-intermediate-state the spec was authored to
prevent. Chip 2 is a small docstring fix; if its session lands
before tag, great; if not, it goes in 7.3.1 or 7.4.0. The
doc-cleanup arc shipping is higher value than waiting for any
individual chip.

**Alternatives considered:**

- **Block only on chip 2 (small docstring fix), defer 3+4** —
  Marginally better discipline; requires chip 2 to actually land
  before tag (if its session stalls, the release stalls too).
- **Block on all 3 remaining chips** — Strongest discipline
  signal but impractical given 3+4 are unscoped spec work.

**Implementation note for Phase 2:**

- Phase 2's first task checks chip status. Chip 2 status will be
  recorded in release notes either way: "fixed in this release"
  or "deferred to next release."
- Chips 3+4 are explicitly NOT release prerequisites; they're
  release-notes mentions only ("spawned during cleanup arc;
  shipping separately").

---

### Q3 — `attune-redis` coordinated bump?

**Decision:** **No coordinated bump.** attune-ai 7.3.0 ships
independently of any attune-redis activity.

**Finding (verified 2026-05-31):**

- attune-redis is **not on PyPI** — confirmed via
  `https://pypi.org/pypi/attune-redis/json` returning no `info`
  field. Pairs with the existing
  [redis-decoupling spec finding](../redis-decoupling/decisions.md)
  that attune-redis as an external package never shipped.
- attune-ai docs reference "attune-redis" in only three shapes:
  (1) a Docker container name (`docker run --name attune-redis`)
  — cosmetic, not a package reference;
  (2) `pip install 'attune-ai[redis]'` — that's attune-ai's own
  optional extra, not the separate plugin;
  (3) sibling-list mentions in
  `docs/MULTI_PACKAGE_RELEASE_PATTERNS.md` — informational.
- **Zero version-pinned cross-repo references.**
  `grep -rEn "attune.redis[\>\<=]" docs/` returns empty.

**Implication:** The premise of the question (cross-repo doc
coherence depends on coordinated bumps) doesn't hold for the
current state. Independent-versioning discipline can carry this
release without any attune-redis activity.

**Rationale:** No coupling exists to coordinate around. If
attune-redis is ever revived as a separate plugin, this question
re-opens — but that's a future-spec concern, not a 7.3.0
blocker.

**Alternatives considered:**

- **Paired bump required** — Adds attune-redis to release
  checklist. Currently impossible (no package to bump) and
  unjustified by the doc surface.

**Implementation note for Phase 2:**

- No attune-redis step in the release checklist.
- If during release prep someone proposes "shouldn't we also bump
  attune-redis," reference this decision.
