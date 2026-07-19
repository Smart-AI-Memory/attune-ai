# Usage Signals — Decisions

**Status:** R6 spend alarm shipped (2026-06-20) · Phase 2b live (D8) ·
Phase 2 scoped (2026-06-15) · Phase 0 complete (2026-06-11)

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

## D4 — Phase 2 opt-in ping: BUILD (2026-06-15)

The question D2 left open is decided: **build the opt-in
phone-home ping.** Full design in
[phase2-design.md](phase2-design.md). Locked choices:

- **Sync-layer architecture** over the existing local `usage.jsonl`
  (not a parallel pipeline) — reuses the local buffer, offline
  resilience free, honors the "don't replace local telemetry"
  non-goal.
- **Backend:** Vercel `/api/usage` function → Vercel Postgres
  (Neon). Relational store for retention / per-workflow / per-version
  queries; AMS Redis untouched.
- **Identity:** rotating anonymous install-ID — a recorded,
  deliberate softening of R2's "no identification ever" to unlock
  retention (the highest-value signal). Anonymous, resettable, no
  PII; see phase2-design Privacy note.
- **Consent:** ships OFF; first-run Socratic prompt + env +
  `attune telemetry enable/disable`; `DO_NOT_TRACK` honored.
- **Transport:** fire-and-forget, 2 s timeout, all errors swallowed.

Payload frozen at schema v1 (package, version, install_id,
event, outcome, os, py, ts) — no paths/code/prompts/args ever; a
regression test asserts the exact key set. ~3 days, three PRs
(2a client / 2b endpoint / 2c dashboard Reach panel = R3).

Status moves Phase 0 complete → **Phase 2 scoped** (implementation
pending an explicit go).

## D5 — Phase 2a implemented: opt-in client (2026-06-15)

The client half of the opt-in ping is built (PR pending). New
`src/attune/telemetry/usage_ping.py` (frozen payload, enablement
precedence, install-id, cursor, fire-and-forget `sync`/`run_sync`),
`TelemetryConfig` gains `usage_ping` / `install_id` /
`usage_ping_consented`, and `attune telemetry status|enable|disable`
ship. 45 unit tests, 92% module coverage; dogfooded end-to-end.

Two design adjustments surfaced while building (code is the contract):

- **`outcome` dropped from v1.** The local `UsageTracker` records
  LLM-call cost/token data, not a success/error outcome — emitting it
  would fabricate data. v1 sends only what's real (workflow + ts);
  `outcome` deferred to a `schema:2` bump. phase2-design.md updated.
- **Opt-in state writes the USER config, never a discovered project
  config.** First implementation wrote `./attune.config.json` (first
  in discovery order), which would let a user commit their install-id
  / `usage_ping=true`. Fixed: `enable/disable/reset` target
  `~/.attune/config.json` explicitly.

Deferred to 2b (no value until the endpoint exists): wiring `run_sync`
into an atexit/Stop trigger. `DEFAULT_ENDPOINT` is empty, so even an
opted-in user transmits nothing yet — intentional double-safety.

## D6 — Phase 2b implemented: endpoint + client go-live (2026-06-16)

The collection endpoint and the client's go-live wiring are built
(branch `claude/usage-signals-phase2b`). What landed:

**Endpoint (website / Next.js):**

- `website/app/api/usage/route.ts` — `POST`, public/unauth, returns
  204. Validates against frozen schema v1, **rejects unknown fields**,
  size-caps the body (256 KB), best-effort per-IP rate-limits, and
  **drops IP + all headers** (read only transiently for the rate-limit
  key, never stored).
- Validation + rate-limit extracted to testable libs
  (`website/lib/usage/{validate,rate-limit}.ts`).
- `usage_events` table + indexes added to `website/lib/db.ts`
  `initializeDatabase()`, plus a `recordUsageEvents()` bulk insert.
- 28 vitest tests green (added `website/vitest.config.ts` with a
  scoped `@/` alias so API-route tests resolve `@/lib/*`).

**Client (attune-ai):**

- `DEFAULT_ENDPOINT` set to `https://smartaimemory.com/api/usage`.
- `usage_ping.run_sync_at_exit()` added — cheap env/endpoint/no-config
  short-circuits before any disk load, then defers to `run_sync`.
- Registered in `UsageTracker.get_instance` BEFORE the local flush so
  it runs AFTER it (atexit is LIFO) and sees freshly-flushed events.
- 138 telemetry unit tests green (2 existing endpoint-default tests
  updated for the now-non-empty default).

**Two implementation decisions worth recording:**

- **DB reuse, not a fresh Neon project.** D4 assumed a new Vercel
  Postgres. In fact the website already has a provisioned Postgres
  (`DATABASE_URL`, the Stripe/license store) behind `lib/db.ts`. 2b
  reuses it — `usage_events` is a new, isolated, PII-free table in
  that DB. This removed the "provision Neon" blocker entirely.
  Trade-off to weigh at deploy: anonymous usage data co-locates in
  the same database as customer-PII tables (separate tables, but one
  DB). Acceptable given the data is anonymous; a separate DB is the
  alternative if clean isolation is preferred — the route code is
  identical either way.
- **Domain = `smartaimemory.com`** (current canonical Next deployment;
  `attune-ai-dev/` is static, no API routes). Overridable via
  `ATTUNE_USAGE_ENDPOINT`. Revisit if the attune-ai.dev consolidation
  moves the Next app; add a redirect or update `DEFAULT_ENDPOINT`.

## D7 — post-merge fix: endpoint trailing slash (2026-06-16)

Probing the live endpoint after #920 merged surfaced a bug `DEFAULT_
ENDPOINT` shipped with: the site runs `trailingSlash: true`, so
`POST /api/usage` returns a 308 redirect to `/api/usage/` and `urllib`
does not reliably re-issue a redirected POST. Verified live:
`GET /api/usage/` → 405, malformed `POST /api/usage/` → 400 (route
deployed + validating), but `/api/usage` (no slash) → 308. Fix:
`DEFAULT_ENDPOINT` now points at the canonical `…/api/usage/`. Only
local tests with arbitrary URLs ran pre-merge, so the mismatch was
invisible until the live probe — a verify-against-the-real-surface
catch. (Follow-up PR off main.)

**Remaining before this is end-to-end live (deploy-time, owner: Patrick):**

1. ~~Apply the `usage_events` DDL to the prod DB~~ — DONE (table live).
2. ~~Deploy the website so `/api/usage` is live~~ — DONE (see D8). THEN
   ship the attune-ai release carrying `DEFAULT_ENDPOINT` (client
   swallows errors if the order slips, but endpoint-first is cleanest)
   — still pending the next PyPI release.
3. Phase 2c — dashboard "Reach" panel (R3) reading `usage_events`.
4. R5 telemetry watchdog + R6 spend alarm (separate PRs).

## D8 — Phase 2b end-to-end live, verified (2026-06-20)

The deploy-time blocker (D7 item 1+2) is cleared: `DATABASE_URL` is set
in the **website** project's Production env and a redeploy since the
06-16 pause picked it up. Verified directly against the live surface:

- `POST https://smartaimemory.com/api/usage/` with a valid schema-v1
  batch → **HTTP 204** (a missing/broken `DATABASE_URL` would 500 in
  the `recordUsageEvents()` catch). Confirmed in Vercel runtime logs:
  `POST /api/usage/ 204` on production deploy
  `dpl_AT9f3wQbdhTZSgyDRUnoPRdjaZ9s` (commit `ff9472e4`, current `main`).

So the ingest chain — client → validate → rate-limit → drop envelope →
insert → 204 — is proven live end-to-end. The ONLY thing gating real
signal now is the next attune-ai PyPI release shipping the
`DEFAULT_ENDPOINT` client (item 2, above).

**Verification test row left in place.** The probe inserted one sentinel
row (`install_id = '00000000-0000-4000-8000-000000000000'`,
`version = '0.0.0-verify'`, `event = 'workflow.verification_test'`).
Deleting it now would require pulling the full production env (Stripe
keys, `ADMIN_SECRET`, the PII-DB connection string) to local disk to
reach the DB for one harmless, trivially-filterable row — not worth the
secret exposure. It is excluded by any real query
(`WHERE version <> '0.0.0-verify'`). Drop it from the Neon console when
convenient:

```sql
DELETE FROM usage_events
WHERE install_id = '00000000-0000-4000-8000-000000000000';
```

**Second sentinel row (2026-06-20 release dogfood, D10).** Pre-release
readiness dogfood transmitted through the *shipped 8.6.0 wheel* (built,
installed in a clean venv) to confirm the real client network path works
end-to-end against the live endpoint — server logged `204`. It inserted
one more sentinel row (`install_id =
'11111111-1111-4111-8111-111111111111'`, `event =
'workflow.release_dogfood_860'`). Drop both together:

```sql
DELETE FROM usage_events
WHERE install_id IN (
  '00000000-0000-4000-8000-000000000000',
  '11111111-1111-4111-8111-111111111111'
);
```

**Cleanup status: PENDING (deferred 2026-06-20).** Attempted the
console-only `DELETE` but the Neon SQL editor was not readily
reachable — the store does not appear under the Vercel
`empathy-framework` team's Storage tab, and console.neon.tech showed
no projects (wrong Neon account). Since both rows are harmless and
already excluded from every real query (`version <> '0.0.0-verify'`),
chasing the right account was not worth the time. Cleanup deferred
until console access is sorted. To finish: read the `DATABASE_URL`
host in the website project's Vercel env (the `ep-*.neon.tech`
endpoint identifies the project), sign into the Neon account that
owns it, and run the two-row `DELETE` above.

## D9 — default stays OFF; first-run consent prompt is the opt-in lever (2026-06-20)

Question raised at release time: to maximize signal, should the usage
ping default to ON (`ATTUNE_USAGE_PING=1` / config-enabled by default)?

**Decision: No. The ping stays default-OFF.** Silently defaulting it ON
would contradict the stance already shipped in the README, SECURITY.md,
CHANGELOG, and R2 ("ships OFF, requires explicit consent, privacy by
construction"), and developers are the audience most hostile to surprise
telemetry — the reputational downside of default-ON dwarfs the signal
upside, and it is a one-way door. It also wouldn't yield much: the
privacy-conscious slice opts out immediately, leaving a noisy
self-selected sample.

**The lever instead:** a first-run consent prompt (ask once, explicitly,
default No) — the Homebrew / .NET CLI / Next.js-notice pattern. An
explicit friendly ask converts far better than passive opt-in (~0) while
keeping consent intact. Tracked as a Phase 2c follow-up, NOT bundled
into the 8.6.0 release; the client ships default-OFF as already built.

No copy changes needed — existing telemetry text remains accurate.

## D11 — first-run consent prompt shipped (the D9 opt-in lever) (2026-06-20, 8.6.1)

D9 kept the ping default-OFF and named a first-run consent prompt as the
opt-in lever, deferred to a follow-up. After 8.6.0 shipped the client,
the gap was concrete: nothing *asked*, so opt-in ≈ 0 (users won't run
`attune telemetry enable` for a feature they were never told about).

**Shipped in 8.6.1:** `usage_ping.maybe_prompt_consent()`, called from
`cli_minimal.main()` before dispatch. It asks once, default-No. Design:

- **Interactive only.** Gated on `sys.stdin.isatty() AND sys.stdout.isatty()`
  (`_is_interactive`) — never hangs or nags CI / pipes / scripts.
- **Asks at most once.** Gated on `TelemetryConfig.usage_ping_consented`
  (the field already existed). "Yes" → `enable()`; anything else →
  `disable()`. Both set `consented=True`, so it never re-appears.
- **Respects prior signals.** Skips entirely (and does NOT record
  consent) when `DO_NOT_TRACK` or `ATTUNE_USAGE_PING` is set — those are
  already an explicit choice.
- **Skips meta commands** (`telemetry`/`setup`/`version`/`doctor`/`auth`)
  so the prompt fires on real first use, not while managing telemetry.
- **Transient skips don't burn the one-shot.** Non-interactive runs and
  an aborted prompt (EOF/Ctrl-C) leave `consented=False`, so a later
  interactive run can still ask.
- **Best-effort.** Never raises into the CLI (config-load and persist
  failures are swallowed) — and it's pure stdlib, so it stays out of the
  [ops]/fastapi base-CLI crash class (#945).

Default stays OFF; this only adds the *ask*. Wording reviewed and
approved by Patrick. Remaining: Phase 2c Reach dashboard, R5/R6.

## D12 — consent ask also reaches the plugin/MCP channel (2026-06-20)

D11's prompt fires only from `cli_minimal.main()` in an interactive
terminal. But the dominant channel is the **Claude Code plugin + MCP
tools**, which never call `main()` — yet their workflows still write
local `usage.jsonl` records. So plugin users generate the data but were
never offered the choice: the exact "nobody was ever told" gap D11 closed
for the CLI persisted verbatim for the larger audience.

**Constraint:** hooks run as piped subprocesses (no TTY) and the MCP
server is a JSON-RPC stdio server, so neither can reuse D11's
`input()`-based prompt — `_is_interactive()` would always skip.

**Shipped:** a SessionStart hook `plugin/hooks/usage_consent_notice.py`
that surfaces a short `## Anonymous usage sharing` block to context,
asking **Claude** to put the choice to the user via `AskUserQuestion`
(the Socratic surface D9 always intended). The user's answer is persisted
by the existing `attune telemetry enable` / `disable` commands — no new
persistence path. Design:

- **Delegated ask, not a prompt.** The hook can't prompt; it instructs
  Claude to ask. `AskUserQuestion` is the native conversational surface
  and matches the project's core Socratic rule.
- **Quiet by default.** Emits nothing once `usage_ping_consented` is set
  (opt-in OR opt-out), when `DO_NOT_TRACK`/`ATTUNE_USAGE_PING` is set,
  on the `compact` source, or when `ATTUNE_CONSENT_NOTICE` is falsey.
- **Anti-nag cap.** A `~/.attune/telemetry/.consent_notice_count` marker
  caps the notice at 3 sessions, so an ignored ask stops nagging instead
  of reappearing forever. Consent itself still lives only in the config.
- **Best-effort, pure stdlib.** Reads `~/.attune/config.json` directly;
  never raises into the session; carries the `_sdk_gate` so it never
  poisons SDK-subprocess streams.

Default stays OFF; this only widens *where the ask reaches*. Remaining:
Phase 2c Reach dashboard, R5/R6.

## D13 — R6 spend alarm shipped (2026-06-20)

R6 ("the $1,200-night class of event must be visible within a day") is
implemented and surfacing on the ops dashboard home page. New code in
`src/attune/ops/data.py`: a pure `spend_alarm()` verdict, a
`read_daily_spend()` local reader, and a `build_spend_alarm()` source
selector; an "API spend watch" panel in `home.html` (CSS in `main.css`);
wired into the home route. Tests: `tests/unit/ops/test_spend_alarm.py`
(18 tests, full ops suite green).

**Two triggers, either raises the alarm:**

1. **Daily anomaly** vs a trailing baseline of prior *active* (non-zero)
   days — comparing today against a typical *active* day, not against
   quiet days whose zeros would make any normal day look anomalous.
   - `stddev > 0` → z-score; flag at `z >= 3.0`.
   - **`stddev == 0` (flat history) → the spec's explicit multiplier
     fallback:** flag when `today > baseline_mean * 3`. A variance-free
     baseline yields no z-score, so the multiplier stands in. Below
     3 active prior days → `insufficient_data` (anomaly judgment skipped;
     the panel still shows today + the ceiling gauge).
2. **Ceiling approach** — month-to-date `>= 80%` of the `$350` monthly
   API ceiling (org 7edead08; see the `user_monthly_spend_budget`
   memory). Fires independently of baseline history, so it makes
   "approach to the cap" visible even on a fresh install.

**Source precedence — a deliberate refinement of the task's named
source.** The session brief pointed at local `usage.jsonl` (the
`scripts/ci_report_api_cost.py` cost field, bucketed by `ts`). But the
$1,200 burn lived on **CI**, whose spend never reaches Patrick's local
`usage.jsonl` (confirmed: local telemetry showed only ~$126/mo that
month). Building R6 *only* on local telemetry would be structurally blind
to the exact event class R6 exists to catch. So `build_spend_alarm()`
**prefers the account-level admin cost-report** (`anthropic_cost.py`'s
`by_day` + `month_to_date_usd`, already fetched on the home route — no
extra API call), which captures everything billed to the org including
CI, and falls back to local `usage.jsonl` (the named source) when no
admin key is configured. The verdict carries `source` ("account" /
"local") and the panel says so; the local path appends a "CI spend not
counted" note so the blind spot is explicit, not silent.

The `ts`-not-`timestamp` field discipline (the #867 bug that made Home
read zero) is honored in `read_daily_spend()` with a `timestamp` legacy
fallback. Remaining: Phase 2c Reach dashboard, R5 telemetry watchdog.

**Correction — 2026-07-12 (Patrick):** the "$1,200-night" figure named
above and in `product-direction-review/assessment-2026-07-11.md`'s N2
finding understated the actual amount — the real figure was over
$1,700. Separately, Anthropic has acknowledged Patrick is owed a
refund related to this spend; the exact mechanism (billing/metering
error vs. real usage refunded as goodwill) isn't confirmed yet, so
the root-cause narrative (a mismarked-tests bug causing real API
calls) should be treated as provisional pending that explanation. The
R6 alarm and its design rationale in this entry are unaffected by
either correction.

## Signal check — 2026-07-11 (agent, Vercel runtime logs)

Three weeks after D8 go-live, first read of what the ingest has
actually received. Method: Vercel observability aggregates for the
`website` project (no DB/secret access needed).

- Last 7 days, all `/api/usage` traffic: **6 × HTTP 405** (GETs —
  scanners/browser pokes), **zero 2xx ingests**.
- Last 24h by request path: `/api/usage/` absent from all 260
  distinct paths.
- Only known rows in Neon remain the two 2026-06-20 sentinels
  (D8/D10). Raw log-line retention is shorter than the window, but
  the 7-day aggregate is fully silent.

Reading: the pipe works; the signal is zero — D9's prediction
("opt-in default-off transmits ~nothing") confirmed empirically.
Corollary for the reach question: 2,316 downloads/week alongside
zero pings is further evidence the download curve is CI shadow, not
humans at the CLI. This system cannot answer "do users exist" on
any useful timescale; the product-direction-review instruments
(user conversations, inbound friction channel) are the working
ones. No further investment here recommended until a conversation
or inbound report proves a human population to measure.

## D11 — attune-rag download figure declared uninterpreted noise (2026-07-12)

The 2026-07-12 snapshot shows attune-rag at **27,410
downloads/month — 5× attune-ai's 5,501** — for a sub-package with
no announcement, no badge prominence, and no known users. Per the
third product-direction assessment (N5): this figure is
**uninterpreted noise pending evidence** and MUST NOT be quoted as
traction on any surface (README, website, posts, changelogs). The
D1 finding ("our CI is the biggest user") and the 07-11 signal
check (zero pings alongside thousands of weekly downloads) both
predict exactly this artifact — mirror/scanner amplification on a
freshly-tagged dependency chain. Standing rule extended: no
download number for ANY attune-* package is quotable until a
recorded interpretation in this file says otherwise. The DEC-7
release-freeze window (2026-07-13 → 07-27, no tags) is the live
experiment; its 07-27 interpretation supersedes this entry's
"pending evidence" clause either way.

## DEC-7 amendment — 2026-07-17: mid-window tag, reframed as the experiment's sharpest probe

**Decided by Patrick 2026-07-17** (form pick: "Release now, AS the
experiment"). The no-tags window (07-13 → 07-27) is amended: v10.5.0
tags on 2026-07-17, deliberately, four days into the window — same day
as the LinkedIn direct ask (URL in `product-direction-review/
user-conversations.md`). Rationale: a tag whose download spike arrives
with zero human responses alongside it is the cleanest CI-shadow
evidence the experiment can produce — sharper than an undisturbed
quiet window. The 07-27 interpretation must therefore read THREE
series together: the download curve, the tag date, and the
LinkedIn-response count. Not a violation; an instrumented probe.

## D14 — requirements refreshed by the round table (2026-07-19)

The 2026-06-11 requirements froze at approval while D1–D13 shipped
most of them; the spec had no honest done/remaining split and no
termination condition. The round table's third spec-authoring loop —
the FIRST under armed rotation (thread `us-refresh-001`, codex
drafted per `next_owed`, claude + antigravity critiqued 12 + 6 cited
items, dissent register attested empty and moderator-verified) —
authored the replacement; the chair approved all seven items
(US-1..US-7) per-item, 2026-07-19.

Headline outcomes: US-1/US-2/spend marked DONE with regression-pin
requirements; US-3 = bounded direct outreach (the real remaining
work); US-4 = reach-capture strategy (pre-tag before-snapshots,
completeness manifest — kills the 10.5.0 silent-0/5 class); US-6 =
R3 closes only on a three-panel receipt; US-7 = D11a/D11b ledger
disambiguation + the refreshed done-when. `requirements.md` replaced
(prior text in git history).
