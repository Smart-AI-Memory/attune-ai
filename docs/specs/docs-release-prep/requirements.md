# Spec: Docs Release Prep

> The final integrator for the documentation-cleanup arc. Three
> sibling specs (`doc-fiction-cleanup`, `docs-completeness-audit`,
> `docs-wiring-audit`) bring the project's prose back into line
> with its source. This spec ships that work as a single coherent
> attune-ai release — CHANGELOG entry, version bump, regenerated
> help templates, and PyPI publish — so users see the corrected
> docs in one cut rather than across a string of inconsistent
> intermediate states.

**Status:** approved (2026-05-31; see [decisions.md](./decisions.md))
**Created:** 2026-05-30
**Owner:** TBD
**Related:** [`doc-fiction-cleanup`](../doc-fiction-cleanup/),
[`docs-completeness-audit`](../docs-completeness-audit/),
[`docs-wiring-audit`](../docs-wiring-audit/);
`attune-release-check` pre-release skill;
`project_pypi_publish_flow` (GitHub Releases → OIDC trusted
publishing with `pypi` env approval gate)

---

## Problem statement

After the doc-cleanup arc lands — fiction corrected
(`doc-fiction-cleanup`), gaps closed (`docs-completeness-audit`),
internal links and navigation clean (`docs-wiring-audit`) —
attune-ai needs a coherent release that ships those corrected
docs to users.

Four artifacts have to land together or users see a confused
intermediate state:

1. **PyPI release** with the new source (docs are packaged
   alongside the wheel via mkdocs-pypi build).
2. **GitHub Release notes** that explain what changed and why
   (the dead-import cluster, the fictional-surface cluster, the
   wiring fixes).
3. **`.help/templates/` regeneration** so the in-product help
   surface matches the new docs. The regen pipeline lives in
   `attune-author` (it's a consumer of attune-ai, not part of
   this release); this spec just orchestrates running it.
4. **CHANGELOG entry** that summarizes the whole arc in one
   place — keep-a-changelog format, semver-disciplined.

Doing these ad-hoc — say, tagging PyPI first, then noticing
`.help/templates/` is stale a day later — leaks an intermediate
state where the wheel says one thing and the help corpus says
another. That's exactly the kind of "fiction vs. reality" gap
the cleanup arc was meant to close, so re-opening it during the
ship would be self-defeating.

---

## Scope

**In scope:**

- CHANGELOG entry covering all three sibling specs' work, written
  as a single user-facing narrative (not a PR list).
- Version bump in `pyproject.toml` + `plugin.json` + `uv.lock`
  (cross-project rule: three files always move together, enforced
  by pre-commit lockfile-drift hook).
- `.help/templates/` regeneration via `attune-author` against the
  new source, with a clean diff committed before the tag.
- PyPI publish via the existing GitHub Releases → OIDC trusted
  publishing flow (`.github/workflows/publish-pypi.yml`, triggered
  by `v*.*.*` tag push). The `pypi` environment approval gate
  stays in place — Patrick approves the publish step manually.
- GitHub Release notes generated from CHANGELOG + the PR list
  across the three sibling specs.
- Pre-release verification via the `attune-release-check` skill
  (version not already on PyPI, working tree clean, CI green,
  pyproject version matches the tag, CHANGELOG entry exists).

**Out of scope:**

- Any code changes. This is a docs-only release; new behavior
  belongs in its own spec + release.
- The three sibling specs' execution itself — they're
  prerequisites, not part of this spec's tasks.
- `attune-redis` release coordination (separate repo,
  independently versioned — see open question below).
- JetBrains plugin and React dashboard releases (separate repos).
- Updating the `attune-release-check` skill itself; if it needs
  fixes, surface them as separate spawned tasks rather than
  bundling.

---

## Dependencies — block release until each is met

The release cannot tag until every item below is true. Listed
here so the spec's first task is a checklist, not an investigation.

| # | Dependency | Definition of "met" |
|---|------------|---------------------|
| 1 | `doc-fiction-cleanup` Phase 3 + Phase 4 | Merged to main; tasks.md status = done; no follow-up issues blocking |
| 2 | `docs-completeness-audit` Phase 1 | Requirements approved + execution merged to main |
| 3 | `docs-wiring-audit` Phase 1 | Requirements approved + execution merged to main |
| 4 | attune-ai `main` is green | Latest commit on main has a green `tests.yml` + `docs.yml` + (waived) `pip-audit.yml`. Note: pip-audit is currently broken with an editable-distribution error per `project_pip_audit_broken`; if not yet fixed, document as a known waiver in CHANGELOG |
| 5 | `attune-release-check` skill green | Run locally on the release branch; all checks pass |
| 6 | No flaky-test debt blocking | If any test is on the "ignore" list, it must have a tracking issue + reason — not a silent skip |

---

## Acceptance criteria

The release is considered successful when every line below holds.

1. **Version coherence.** The version on PyPI matches the
   GitHub Release tag matches the CHANGELOG `## [x.y.z]` entry
   header matches `pyproject.toml` matches `plugin.json` matches
   the resolved version in `uv.lock`.
2. **Help corpus is fresh.** `.help/templates/` regen ran against
   the post-merge `main`; `attune-author status` reports zero
   stale features post-tag.
3. **Docs build clean.** `mkdocs build --strict` passes with zero
   INFO-level link warnings — this is the `docs-wiring-audit`
   acceptance criterion and must already be met as a prerequisite,
   but this spec re-verifies on the tagged commit.
4. **Spawned chips dispositioned.** All four open chips from the
   doc-cleanup session — wizard entry-point fix, `create_wizard`
   docstring fix, frameworks CLI spec, team-coordination spec —
   are either landed (and noted in CHANGELOG) or explicitly
   deferred to a later release with reasoning in CHANGELOG. No
   chip is silently dropped.
5. **PyPI install smoke-passes.** A clean-venv
   `pip install attune-ai==<new-version>` followed by
   `attune --version` and `attune help <known-template>` works on
   at least one OS (CI does Linux; do macOS manually).
6. **CHANGELOG narrative reads coherently.** The entry tells a
   single story across the three sibling specs — not a copy-paste
   of three independent sections. A new user should understand
   what changed and why without reading the specs.

---

## Approach (proposed — refine in Phase 2)

A staged checklist, not a script, because the publish step needs
manual approval at the `pypi` environment gate.

1. **Pre-flight (off the release branch).**
   - Confirm all 6 dependencies above are met.
   - Skim the three sibling specs' tasks.md to draft the
     CHANGELOG narrative.
2. **Help regen.**
   - Run `attune-author status` to confirm the staleness state
     before regen.
   - Run the regen against `main`.
   - Commit `.help/templates/` diff with
     `chore: regenerate help templates for docs-release-prep`.
3. **Version + CHANGELOG.**
   - Bump version in three files (pyproject + plugin.json +
     uv.lock).
   - Move `## [Unreleased]` content into a dated `## [x.y.z]`
     block; write the cross-spec narrative.
   - Commit as `chore(release): vX.Y.Z`.
4. **Pre-release check.**
   - Run the `attune-release-check` skill.
   - Resolve any reds before tagging.
5. **Tag + publish.**
   - `gh release create vX.Y.Z --generate-notes` or hand-written
     notes; verify the PR list matches the CHANGELOG narrative.
   - Tag-push fires `publish-pypi.yml` (per current workflow
     comment — release-published doesn't fire on `GITHUB_TOKEN`
     releases, so tag-push is the load-bearing trigger).
   - Approve the `pypi` environment when prompted.
6. **Post-release smoke.**
   - Clean-venv install + `attune --version` + help-template
     sanity check.
   - Verify the GitHub Release notes link to the CHANGELOG entry.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| PyPI publish fails after tag (OIDC misconfig, gh-action-pypi-publish regression) | low | Tag is cheap to add; if publish fails, fix the workflow and re-run via `workflow_dispatch`. PyPI doesn't allow republish under same version, but a failed publish leaves nothing on PyPI to conflict with |
| `.help/templates/` regen consumes API tokens (regen calls Anthropic) | medium | Run with the developer key, not CI eval key; budget a few dollars; if regen reveals deeper drift, treat as a finding and either patch-fix or defer the release |
| Coordination drift with `attune-redis` (its docs may reference attune-ai version) | low | Check `attune-redis` README + CHANGELOG for hard-coded version pins before tagging; if found, coordinate a follow-up patch in that repo |
| `pip-audit.yml` still broken at release time | high (per memory note) | Document as a known waiver in CHANGELOG; don't gate the release on it (it's an infra bug, not a vulnerability). Spawn a separate fix-it if not already in flight |
| One of the three sibling specs slips | medium | This is a serial dependency — if a sibling spec slips, the release slips. Don't release on partial cleanup |
| Spawned chip is actually a regression caused by the doc work | low | If discovered during the release smoke, treat as a blocker — patch and re-tag from a new version |

---

## Cross-spec impact

- **Waits on:** `doc-fiction-cleanup`, `docs-completeness-audit`,
  `docs-wiring-audit`. These are serial — this spec does not start
  Phase 4 until all three are merged.
- **Does not block:** other in-flight attune-ai work (curator,
  multi-actor bulletin, ops dashboard). They can land between the
  sibling specs and this release as long as their changes don't
  contradict the doc narrative.
- **Affects downstream:** `attune-redis` consumers who pin
  `attune-ai` — but only at the level of "they get a new minor
  with no API change". The `[author]` extra cap-widening that
  shipped in v7.2.0 is not relevant here.

---

## Tradeoffs

| Decision | Option A | Option B | Chosen? |
|----------|----------|----------|---------|
| Release granularity | Ship all three sibling specs in one cut (this spec's premise) | Ship each sibling spec as its own patch release | A — defer to Phase 2 to confirm. The cluster reads as one user-facing story; three releases would split the narrative |
| Version bump | Minor (7.2.0 → 7.3.0) | Patch (7.2.0 → 7.2.1) | Open — docs-only is traditionally patch, but the doc corpus is large user-facing surface and a minor signals "look at this." Patrick to decide in Phase 2 |
| CHANGELOG style | Single narrative section ("Documentation overhaul") with sub-bullets | Three independent sections, one per spec | A — coherence is the whole point of integrating into one release |
| Help-regen timing | Regen before tag (this approach) | Regen after tag as a follow-up | A — the wheel contains the help corpus; "after" would leak the intermediate state we're trying to avoid |
| Spawned-chip handling | Hard-require disposition (in CHANGELOG) | Soft-allow drop | A — the chips were captured deliberately; silent-drop erodes the spawned-task signal |

---

## Rollback

PyPI does not allow republishing under the same version. The
rollback strategies, in order of preference:

1. **Yank + patch.** If a defect is found post-publish, yank
   the broken version on PyPI (existing installs keep working;
   new installs skip it) and ship a patched version. This is
   the standard path.
2. **Help-corpus-only rollback.** If only `.help/templates/` is
   broken, revert that commit on `main` and re-regen — no PyPI
   action needed, since users get help-corpus refreshes via
   their next `attune-author` run, not via the wheel.
3. **Documentation-only follow-up.** If only the prose is wrong
   (e.g., a fictional surface re-introduced by an editing slip),
   ship a docs-only patch release rather than yanking.

There is **no rollback path for "I changed my mind about a
version bump"** — once tagged and published, the version is
spent. Use a release candidate (`v7.3.0rc1`) if the team wants a
trial run before committing to the version.

---

## Open questions

These are flagged for Patrick's call in Phase 2; this spec does
not pre-answer them.

1. **Version bump policy.** Minor (7.2.0 → 7.3.0) signals "user-
   visible improvement" and matches the scale of the corpus
   change. Patch (7.2.0 → 7.2.1) is technically correct for a
   docs-only change. Which discipline does attune-ai follow?
2. **Do the four spawned chips block this release?** Arguments
   for blocking: they're real bugs / missing features captured
   during the cleanup arc; deferring weakens the signal that
   spawned tasks are taken seriously. Arguments against: the
   chips aren't regressions caused by the doc work, they're
   pre-existing or net-new issues; waiting on them could push
   the release out indefinitely while the doc fixes sit unshipped.
3. **`attune-redis` coordinated bump?** They're independently
   versioned but doc-aligned. Does this release need a paired
   `attune-redis` bump to keep cross-repo doc references coherent,
   or is the independent-versioning discipline strong enough that
   they can drift?

---

## Coverage areas — all 8 addressed

| # | Area | Where addressed |
|---|------|-----------------|
| 1 | Problem statement | Top of doc |
| 2 | Scope | "Scope" + "Dependencies" sections |
| 3 | Acceptance criteria | "Acceptance criteria" — 6 numbered, all objectively verifiable |
| 4 | Approach | "Approach" — 6-step staged checklist |
| 5 | Risks | "Risks" table — 6 risks with mitigations |
| 6 | Cross-spec impact | "Cross-spec impact" — waits-on, doesn't-block, downstream |
| 7 | Tradeoffs | "Tradeoffs" table — 5 decisions, with at least 1 open |
| 8 | Rollback | "Rollback" — three strategies + the explicit no-rollback case for version bumps |

---

## Phase 2: Design

**Status:** stub. Author after Phase 1 approved.

Will cover: exact CHANGELOG draft, version-bump decision,
help-regen command sequence, tag/release commands, smoke-test
procedure.

---

## Phase 3: Tasks

**Status:** stub. Author after Phase 2 approved.

Will cover: ordered task list (dependency check → help regen →
version bump → CHANGELOG → pre-release check → tag → approve
publish → smoke test → close spawned chips).

---

## Phase 4: Implementation

**Status:** stub. Execute after Phase 3 approved. This is the
phase that actually ships the release.
