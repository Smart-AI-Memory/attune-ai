# Usage Signals — Decisions

**Status:** Phase 0 complete (2026-06-11)

## D1 — Phase 0 baseline snapshot (2026-06-11)

R1 executed: inventory of every zero-instrumentation signal, with a
baseline snapshot recorded below. Methods are inline so the snapshot
is reproducible (and scriptable for R4).

### PyPI downloads (pypistats.org `/recent` — mirrors EXCLUDED)

Method: `curl https://pypistats.org/api/packages/<pkg>/recent`.
Empirically these numbers track the `/overall` endpoint's
`without_mirrors` category (attune-ai: 2,836 recent-month vs 2,948
without-mirrors-30d), so `/recent` is already the mirror-corrected
view. Caveat: `last_day` reads 0 for ALL packages early in the UTC
day (ingestion lag — not a real zero).

| Package | last_week | last_month | Latest | Releases | First upload |
|---|---|---|---|---|---|
| attune-ai | 636 | 2,836 | 8.3.0 | 125 | 2026-02-01 |
| attune-rag | 6,271 | 31,602 | 0.7.0 | 27 | 2026-04-18 |
| attune-help | 143 | 770 | 0.11.1 | 15 | 2026-04-04 |
| attune-author | 593 | 2,796 | 0.16.0 | 33 | 2026-04-09 |
| attune-verify | 1,131 | 1,131 | 0.2.0 | 2 | 2026-06-09 |

Mirror split (`/overall`): see the addendum table below. Operational
note for any snapshot script: the pypistats API rate-limits HARD — a
5-request burst triggered a 429 penalty that outlasted both a 4-min
and a 25-s-spaced retry; only a 15-minute quiet period followed by
60-s spacing got through.

### The headline interpretation: our own CI is the biggest "user"

The download shape across packages is explained almost entirely by
attune-ai's CI, not external adoption:

- **attune-rag (31.6k/mo) and attune-verify (1.1k in its FIRST
  week)** are core deps of attune-ai. CI installs them from PyPI on
  every run (attune-ai itself installs editable from source, so it
  does NOT count its own CI). ~12 matrix lanes × dozens of runs/day
  ≈ tens of thousands of dep downloads/month. attune-verify's curve
  is the cleanest proof: it became a core dep on 2026-06-09 (#708)
  and immediately jumped to CI-volume numbers.
- **attune-help (770/mo)** is NOT a core dep — its number is the
  closest thing we have to an organic background level.
- **attune-ai (2.8k/mo, already mirror-free)** = real users + every
  non-editable install path we ourselves exercise: `uvx --from
  attune-ai` MCP-server spawns, `uv run --from` regen invocations,
  publish smoke tests. Attribution between "external user" and "our
  own tooling" is not possible from pypistats alone — that's
  exactly what BigQuery's per-installer/per-version splits would
  answer if the question ever becomes load-bearing.

Implication for any future reach panel: **subtract the CI shadow**
— either read `without_mirrors` AND discount dep-package numbers,
or use per-version curves (CI always installs latest; long version
tails = humans).

### GitHub traffic (14-day window ending 2026-06-10)

Method: `gh api repos/Smart-AI-Memory/<repo>/traffic/{views,clones,popular/referrers,popular/paths}`.
**The window is rolling 14 days and unsnapshotted history is lost —
this is the strongest argument for the R4 release-ritual snapshot.**

| Repo | Views (uniq) | Clones (uniq) | Stars | Forks |
|---|---|---|---|---|
| attune-ai | 662 (24) | 57,451 (2,651) | 5 | 1 |
| attune-rag | 210 (3) | 4,418 (492) | 1 | 0 |
| attune-help | 0 (0) | 58 (19) | 0 | 0 |
| attune-author | 7 (1) | 527 (78) | 0 | 0 |
| attune-verify | 4 (4) | 102 (63) | 0 | 0 |

- **Clones are CI-dominated and unusable as a user signal** for
  active repos: attune-ai's per-day clone counts track our own PR
  activity (9,497 clones on 2026-06-09, the heaviest dev day;
  GitHub Actions checkouts count as clones). Marketplace plugin
  installs also land here, indistinguishable.
- **Views are mostly us** (top path: `/pulls` at 162 views/3
  uniques) — but the unique-visitor floor is real external eyes:
  24 uniques on attune-ai in 14 days.
- **Referrers carry small but clean discovery signal**: Google
  (6 views/3 uniques), attune-ai.dev (2), pypi.org (1), vercel.com.
- **Stars are the cleanest external-interest signal we have**:
  attune-ai has 4 external stargazers arriving ~1/month (2026-03-29
  darphiz, 05-05 michelkro, 05-14 oldschoola, 05-31 hegc-co).
  Timestamps via `gh api .../stargazers -H "Accept:
  application/vnd.github.star+json"`.
- attune-verify got a 31-unique clone burst on 2026-06-02 — days
  before its first release, with zero publicity. New-repo crawler
  bots; calibrates how much of "uniques" is scanners.

### Claude Code marketplace

**No install-count surface exists.** Findings:

- No public Anthropic API exposes plugin install/update counts.
- Marketplace installs clone the GitHub repo — they appear in clone
  traffic, indistinguishable from CI.
- **attune-ai is listed in NEITHER Anthropic plugin directory** —
  `anthropics/claude-plugins-official` ("Anthropic-managed directory
  of high quality Claude Code Plugins") nor
  `anthropics/claude-plugins-community` (community directory;
  submissions at clau.de/plugin-directory-submission). Both were
  code-searched for "attune": zero hits. Today the plugin is only
  discoverable by people who already know the repo slug.
  **Free growth lever, Patrick's call: submit to the community
  directory.** (Listing wouldn't add install counts, but it adds a
  discovery channel whose effect would show up in stars/referrers.)

### Free sources inventoried but not yet pulled

- **BigQuery public PyPI dataset** (`bigquery-public-data.pypi.file_downloads`)
  — per-version, per-installer (pip vs bandersnatch), per-python
  splits; the tool that separates CI (always-latest, ci=true
  installer env) from humans. Needs a GCP project; free tier covers
  it. The right backend if the dashboard panel (R3) gets built.
- **pepy.tech** — aggregated totals; now requires an API key.
- **GitHub dependents graph** — who depends on attune-ai; no API,
  scrape-only. Skipped.
- **Vercel Analytics on attune-ai.dev** — exists, out of scope per
  non-goals (separate surface).

## D2 — Verdict on "is zero-instrumentation enough?" (R1's question)

**Partially — and the gap is exactly the one the spec predicted.**

Zero-instrumentation data answers:

- *How many installs?* Yes, after mirror/CI correction (BigQuery
  per-version curves are the clean instrument; pypistats alone
  over-counts by ~10x on dep packages).
- *Is anyone discovering us?* Yes — stars (~1/month), search
  referrers, pypi.org referrals. All small, all real.

It cannot answer:

- *Which workflows/skills do external users run?* Nothing public
  carries this. The opt-in ping (Phase 2) remains the only path —
  decision stays open per R2, to be made after a release ships with
  a before/after reach pair (R4) and we see whether install-count
  deltas are signal enough.

**Decided now:** build nothing heavier than a snapshot script until
one release-cycle of baseline pairs exists. Concretely: (a) the R4
release-ritual hook records `pypistats /recent` + GitHub
traffic/stars at tag time (a ~30-line script; respect pypistats
rate limits — one request/min, retry-after-15-min on 429);
(b) BigQuery setup is deferred until the first time a real question
needs per-version splits; (c) the marketplace-directory submission
is surfaced to Patrick as a free discoverability lever independent
of measurement.

## Addendum — mirror split (pypistats `/overall`, 2026-06-11)

| Package | Window | with_mirrors | without_mirrors |
|---|---|---|---|
| attune-ai | all-time | 68,382 | 17,678 |
| attune-ai | last 30d | 13,588 | 2,948 |
| attune-ai | last 7d | 3,936 | 656 |
| attune-rag | all-time | 49,772 | 39,945 |
| attune-rag | last 30d | 38,447 | 33,671 |
| attune-rag | last 7d | 9,437 | 8,503 |
| attune-help | all-time | 12,605 | 6,681 |
| attune-help | last 30d | 2,256 | 782 |
| attune-help | last 7d | 459 | 157 |

attune-author / attune-verify splits: the rate limiter cut the run
off after three packages (one 429 even at 60-s spacing following a
15-min cooldown). Their `/recent` rows in the main table are already
mirror-free; the with-mirrors split adds nothing decision-relevant —
fill in opportunistically on the next snapshot.

Reading: attune-rag's volume is ~85% non-mirror — i.e. REAL
downloads, dominated by attune-ai CI dependency installs (it became
a core dep in the 7.x line). attune-ai's own raw counts are ~75%
mirror noise; the mirror-free ~2.9k/month is the number to track.

## D3 — R4 snapshot script shipped (2026-06-12)

`scripts/reach_snapshot.py` automates the D1 method: pypistats
`/recent` for all five packages with 60-s spacing (the D1
rate-limit lesson baked in — a 429 ABORTS with a "wait 15 minutes"
message instead of retrying), plus best-effort GitHub signals
(stars/forks always; traffic clones/views when the token allows).
Writes `docs/specs/usage-signals/snapshots/<date>.json` and prints
a paste-ready markdown table.

Release-ritual hook (R4 proper): the release-execute skill's tag
step now kicks the script off in the background at tag time and
commits the snapshot in close-out, so every release gets its
before/after pair without manual effort.

Tests: `tests/unit/scripts/test_reach_snapshot.py` — network
boundaries mocked; spacing (n-1 sleeps, none before the first),
429-abort short-circuit, table rendering, CLI write/exit paths.
One bug caught at authoring time: a def-time default argument
(`fetcher=fetch_pypistats_recent`) bound the real fetcher and the
first CLI test silently hit the live API — defaults now resolve at
call time.

Remaining in scope: R3 (dashboard Reach panel), R5 (telemetry
watchdog), R6 (spend alarm), and the Phase 2 opt-in ping question.
