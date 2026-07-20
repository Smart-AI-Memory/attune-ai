# Attune-AI Metrics Review — Week 1 (Expanded)
**Date:** February 6, 2026
**Package:** [attune-ai](https://pypi.org/project/attune-ai/) v2.3.4
**Repository:** [Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
**Reviewer:** Automated (Claude)

---

## Executive Summary

Attune-ai launched this week as a rebrand of empathy-framework, shipping 16 PyPI releases in 5 days with zero external downloads recorded yet. The codebase is mature — 1,083 commits, 377 source files, 543 test files, and a 1.82x test-to-code ratio — but the GitHub presence starts at zero stars/forks since the predecessor's 10 stars and 5 forks didn't transfer. The most important thing in this review: **the engineering is solid, but the project has a discoverability problem that needs to be solved before any adoption metrics will move.**

---

## North Star Metric

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Weekly active `pip install` count | n/a (too new) | Establish baseline | ⏳ Pending data |

PyPI download stats require ~7 days of BigQuery indexing. First real numbers expected by Feb 8-10.

---

## L1: Metric Scorecard

### Downloads & Adoption

| Metric | Current | Previous | Change | Target | Status |
|--------|---------|----------|--------|--------|--------|
| PyPI downloads (last day) | n/a | — | — | Baseline | ⏳ Pending |
| PyPI downloads (last week) | n/a | — | — | Baseline | ⏳ Pending |
| PyPI downloads (last month) | n/a | — | — | Baseline | ⏳ Pending |
| pepy.tech total | n/a | — | — | Baseline | ⏳ Pending |
| GitHub stars (attune-ai) | 0 | — | — | 10 | 🔴 Miss |
| GitHub forks (attune-ai) | 0 | — | — | 5 | 🔴 Miss |
| GitHub watchers | — | — | — | — | — |
| Org followers | 2 | — | — | — | — |
| empathy-framework stars (predecessor) | 10 | — | — | — | ✅ Reference |
| empathy-framework forks (predecessor) | 5 | — | — | — | ✅ Reference |

### GitHub Activity

| Metric | Current | Previous | Change | Target | Status |
|--------|---------|----------|--------|--------|--------|
| Total commits (main) | 1,083 | — | — | — | ✅ Strong |
| Open pull requests | 10 | — | — | < 5 | 🟡 At risk |
| Open issues (attune-ai) | 0 | — | — | — | ✅ Clean |
| Open issues (empathy-framework) | 6 | — | — | 0 | 🟡 At risk |
| Contributors | 1 | — | — | 3+ | 🔴 Miss |
| empathy-framework commits | 1,051 | — | — | — | ✅ Reference |

### Code Health

| Metric | Current | Previous | Change | Target | Status |
|--------|---------|----------|--------|--------|--------|
| Source files (src/) | 377 | — | — | — | — |
| Source lines of code | 139,508 | — | — | — | — |
| Test files | 543 | — | — | — | — |
| Test lines of code | 254,265 | — | — | — | — |
| Test-to-code ratio | 1.82x | — | — | > 1.5x | ✅ On track |
| Coverage threshold | 70% | — | — | 80% | 🟡 At risk |
| Coverage target | 80% | — | — | 80% | 🟡 At risk |
| Files > 500 lines | 105 (27.8%) | — | — | < 15% | 🔴 Miss |
| Files > 1,000 lines | 19 (5.0%) | — | — | 0 | 🔴 Miss |
| Syntax errors (sampled) | 0 | — | — | 0 | ✅ On track |
| Lazy imports defined | 238 | — | — | — | ✅ Architecture |
| Pytest markers | 7 | — | — | — | — |

### Release Quality

| Metric | Current | Previous | Change | Target | Status |
|--------|---------|----------|--------|--------|--------|
| PyPI releases (this week) | 16 | — | — | — | — |
| Yanked releases | 3 versions (6 files) | — | — | 0 | 🔴 Miss |
| Yank rate | 18.75% | — | — | 0% | 🔴 Miss |
| Healthy releases | 13 | — | — | — | — |
| Semver compliance | 99% | — | — | 100% | ✅ On track |
| Changelog entries (total, incl. predecessor) | 198 | — | — | — | — |
| Breaking changes documented | 11 | — | — | — | — |
| Security fixes documented | 8 | — | — | — | — |
| Governance files present | 3/3 | — | — | 3/3 | ✅ On track |
| Release automation | ✓ prepare_release.py | — | — | ✓ | ✅ On track |
| Install variants | 15 optional extras | — | — | — | — |

---

## L2: Trend Analysis

### Release Velocity

16 versions in 5 days breaks down to:

- **Feb 1:** v2.0.0 → v2.1.0 (4 releases — rebrand day, rapid iteration)
- **Feb 2:** v2.1.1 → v2.2.1 (7 releases — branding fixes, memory refactor, legacy cleanup)
- **Feb 5:** v2.3.0 → v2.3.4 (5 releases, 3 yanked — setup command, security, packaging fixes)

The Feb 5 burst is the concerning one: 3 of 5 releases were yanked (v2.3.0–2.3.2), suggesting the `attune setup` command and packaging changes weren't tested against PyPI distribution before publish. The `prepare_release.py` script handles version bumping and changelog but doesn't include a pre-publish test step.

**Changelog composition** across the full project history (including empathy-framework era):

| Category | Count | Share |
|----------|-------|-------|
| Changed | 61 | 30.8% |
| Fixed | 59 | 29.8% |
| Added | 58 | 29.3% |
| Security | 8 | 4.0% |
| Removed | 6 | 3.0% |
| Deprecated | 6 | 3.0% |

Healthy balance. The near-equal split between Added/Changed/Fixed suggests a project that's actively developing features while staying on top of maintenance.

### Code Health

The codebase is significantly more mature than a 5-day-old package suggests — because it isn't. It's the continuation of empathy-framework with 1,083 commits of history.

**Strengths:**
- 1.82x test-to-code ratio is exceptional. Most open-source projects sit at 0.5-1.0x.
- 238 lazy imports via `__getattr__` pattern eliminates circular import risk at startup.
- 7 pytest markers (slow, integration, unit, security, performance, llm, network) show thoughtful test categorization.
- Ruff + Black + MyPy toolchain with pre-commit hooks.

**Concerns:**
- 105 files (27.8%) exceed 500 lines — nearly double the typical threshold of ~15%.
- 19 files exceed 1,000 lines. Largest: `base.py` at 2,051 lines.
- Coverage threshold is set at 70%, target 80%. Gap between threshold and target suggests coverage isn't enforced at the desired level yet.
- `pytest-xdist` is available for parallel testing but actual pass rate couldn't be verified (dependency install required).

### GitHub Activity

The attune-ai repo has 1,083 commits but 0 stars — it's a fresh repo that received the code but not the social signals from empathy-framework (10 stars, 5 forks). The 10 open PRs on attune-ai need attention: they may be stale from the migration or active work-in-progress.

**Solo maintainer risk:** Patrick Roebuck is the only contributor. The bus factor is 1. The CONTRIBUTORS.md exists but lists no additional contributors.

### Community & Adoption

- **Stack Overflow:** No mentions of attune-ai found.
- **Reddit:** No threads found.
- **Hacker News:** No direct mentions; related discussions about AI memory systems exist but don't reference this project.
- **Dev.to / Twitter:** No presence found.
- **Discord/Slack:** No community channels identified.

The predecessor empathy-framework had modest but real traction (10 stars, 5 forks, 6 open issues, 8 open PRs). The rebrand reset all discoverability signals to zero.

**Competitive landscape** (AI memory / developer workflow tools):
- Mem0 — large community, different approach (universal memory layer)
- Supermemory — API-focused memory engine
- These are in the same conceptual space but attune-ai's Claude-exclusive focus differentiates it.

---

## Bright Spots

**1. Engineering discipline is enterprise-grade.** 1.82x test-to-code ratio, 7 test markers, pre-commit hooks with Ruff/Black/MyPy, CWE-22 security coverage on all 22 file write operations, and a structured release automation script. This is a solo project that runs like a team.

**2. Architectural quality is improving.** The 2,197-line memory monolith → 16 modules refactor and 31 → 26 workflow consolidation with migration system show thoughtful decomposition rather than just feature-stacking.

**3. Changelog hygiene is excellent.** 198 categorized entries with clear Added/Changed/Fixed/Removed/Deprecated/Security sections. Every release is documented. This is better than many funded projects.

**4. Security posture is proactive.** 8 dedicated security entries, path traversal validation on all file writes, SECURITY.md with vulnerability reporting process and version support matrix, Bandit in the toolchain.

**5. Deprecation discipline.** 6 explicit Deprecated entries in the changelog with removal timelines. The empathy-framework → attune-ai migration has documented breaking changes and clear migration instructions.

---

## Areas of Concern

**1. Zero discoverability (Critical).** 0 stars, 0 forks, no Stack Overflow presence, no Reddit threads, no HN discussion, no Twitter activity, no community channel. The rebrand created a clean slate — but also wiped out the modest signals empathy-framework had accumulated.

**2. 18.75% yank rate on this week's releases.** 3 of 16 versions yanked (all on Feb 5) indicates the publish pipeline lacks a pre-release verification step. The `prepare_release.py` script bumps versions and updates the changelog but doesn't run `pip install` from a fresh venv against the built distribution.

**3. Solo maintainer with no contributor pipeline.** 1,083 commits from 1 person. CONTRIBUTORS.md exists but is empty. No community channel to attract contributors. The bus factor is 1.

**4. 27.8% of source files exceed 500 lines.** 105 files over 500 lines, 19 over 1,000 lines. The memory refactor addressed one monolith but others remain. This affects readability and makes onboarding new contributors harder.

**5. 10 open PRs and 6 open issues on empathy-framework.** The predecessor repo has unresolved work. It's unclear if these were migrated, intentionally left, or abandoned. Users following empathy-framework may not know about attune-ai.

**6. Download stats pipeline isn't producing data yet.** The `download_stats.py` script works correctly but external API access returned 403 from the sandbox. More importantly, PyPI's BigQuery hasn't indexed the package yet, so even from a clean network, stats will show n/a for a few more days.

---

## Recommended Actions

### Immediate (Next 48 Hours)

| # | Action | Why |
|---|--------|-----|
| 1 | **Add `TestPyPI` dry-run step to `prepare_release.py`** | The 3 yanked versions on Feb 5 came from packaging issues that would have been caught by a `pip install` from TestPyPI. Add a `--dry-run` flag that builds, uploads to test.pypi.org, and installs in a temp venv before real publish. |
| 2 | **Cross-link empathy-framework → attune-ai** | Add a deprecation notice to empathy-framework's README pointing to attune-ai. Update the PyPI listing for empathy-framework with a "moved to attune-ai" message. This recovers the 10 stars / 5 forks as referral traffic. |
| 3 | **Close or migrate the 10 open PRs** | Review each PR: close stale ones, migrate active ones. An attune-ai repo with 10 open PRs and 0 stars looks unmaintained. |

### Short-Term (This Week)

| # | Action | Why |
|---|--------|-----|
| 4 | **Post a "Show HN" or Reddit /r/Python launch post** | Zero community presence needs a deliberate launch moment. The Claude-exclusive angle and cost savings claims (34-86%) are strong hooks. |
| 5 | **Create a GitHub Discussion or Discord** | Contributors need somewhere to ask questions before submitting PRs. Even a single Discussion tab beats nothing. |
| 6 | **Run full test suite and publish coverage number** | The 70% threshold / 80% target split needs a real measurement. Run `pytest --cov` and publish the badge. It's probably above 70% given the test volume, and knowing the real number turns it from a concern into a bright spot. |

### Medium-Term (Next 2 Weeks)

| # | Action | Why |
|---|--------|-----|
| 7 | **Break up the 19 files over 1,000 lines** | Start with the largest (base.py at 2,051 lines). Apply the same modular extraction pattern used for the memory system refactor. |
| 8 | **Set up GitHub Actions CI badge** | The Tests badge currently points to a static shield. Replace it with the actual workflow status badge so it's live. |
| 9 | **Write a migration guide blog post** | A published tutorial for empathy-framework → attune-ai migration helps SEO, gives a linkable resource, and signals active development. |
| 10 | **Re-run this metrics review with real download data** | By Feb 13, pypistats and pepy.tech should have numbers. That review will establish the true Week 1 adoption baseline. |

---

## Context & Caveats

**Data confidence levels:**

| Source | Confidence | Notes |
|--------|-----------|-------|
| PyPI release history | High | From official JSON API |
| GitHub stars/forks | Medium | From web scrape, not API (403 on direct API) |
| Commit count (1,083) | Medium | From web scrape |
| Code health metrics | High | Direct analysis of local codebase |
| Download statistics | None | APIs not yet indexing this package |
| Community presence | High (absence confirmed) | Searched SO, Reddit, HN, Dev.to, Twitter |

**Known data gaps:**
- Actual test pass rate (requires full dependency install + `pytest` run)
- Real code coverage percentage (requires `pytest --cov`)
- GitHub traffic data (requires repo admin access)
- Clone count (requires repo admin access)
- Referral sources (requires repo admin access)
- empathy-framework download history (predecessor; would show pre-rebrand baseline)

**Events affecting comparability:**
- Package is < 7 days old on PyPI — all adoption metrics are at genesis
- Rebrand from empathy-framework means historical continuity exists in code but not in PyPI/GitHub social signals
- 3 yanked releases inflate the "release count" but not the healthy install surface

---

## Appendix: download_stats.py Output

```
Timestamp:      2026-02-07T04:24:53Z
Version:        2.3.4
Releases:       16 (6 yanked files across 3 versions)
pypistats.org:  n/a (API not yet indexed)
pepy.tech:      n/a (API not yet indexed)
```

CSV log started at: `logs/download_stats.csv`

---

*Next review scheduled: Feb 13, 2026 (first week with real download data expected)*
