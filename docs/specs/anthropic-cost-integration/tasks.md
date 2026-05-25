# Tasks — Anthropic Cost Integration
**Status:** approved
Each phase is independently shippable and reversible.

---

## Phase 0 — Confirm API coverage (no production code)

Empirical probe to answer the open question: does `session_usage` cover Claude Code subscription usage, or only API-key usage?

- [ ] **0.1** Patrick creates an admin API key at the Anthropic Console.
- [ ] **0.2** Write `scripts/probe_anthropic_cost.py` — single curl-equivalent. Hits `GET /v1/organizations/cost_report?starting_at=<today-30d>&group_by[]=description` and dumps the response. Reads the admin key from `~/.attune/anthropic-admin.env` (or `ANTHROPIC_ADMIN_API_KEY` env var). Excluded from the package — script-only.
- [ ] **0.3** Run the script and compare the returned `MTD` total to Patrick's Anthropic Console MTD figure. If they match (or differ only by the lookback delay), Phase 1 is unblocked. If `cost_report` is missing Claude Code subscription costs, decision point: build with the gap documented OR find a different data source.
- [ ] **0.4** Record findings in `docs/specs/anthropic-cost-integration/probe-2026-05-XX.md`.

**Gate to Phase 1:** Phase 0.3 returns a match (or a documented, acceptable gap).

---

## Phase 1 — Backend fetcher + cache

- [ ] **1.1** New module `src/attune/ops/anthropic_cost.py`:
  - `load_admin_key()` — reads `~/.attune/anthropic-admin.env`, returns `str | None`.
  - `fetch_summary(cfg, *, refresh: bool = False) -> tuple[CostSummary | None, CostFetchError | None]` — orchestrates load + HTTP + cache + transform.
  - `CostSummary` and `CostFetchError` dataclasses.
  - Module-level `_CACHE: dict[tuple, tuple[datetime, CostSummary]]`.
- [ ] **1.2** HTTP client uses `httpx.Client` (already transitive via `anthropic`). 10s timeout. Single retry on connection error. No retry on 4xx.
- [ ] **1.3** Currency conversion helper. Anthropic returns cents-as-decimal-string; we want USD float. Edge cases: `"0"`, `"0.00"`, very large numbers, malformed strings → log + skip that bucket.
- [ ] **1.4** Tests in `tests/unit/ops/test_anthropic_cost.py`:
  - Missing key → `(None, CostFetchError(kind="no_key"))`
  - HTTP 200 round-trip → correct `CostSummary` fields
  - HTTP 401 → `kind="auth_failed"`
  - HTTP 429 → returns cached if available, else `kind="rate_limited"`
  - Network timeout → `kind="network"`
  - Currency conversion edge cases
  - Cache hit doesn't re-call the client
  - `refresh=True` bypasses cache

## Phase 2 — Home page integration

- [ ] **2.1** Modify `routes/dashboard.py::home` to call `anthropic_cost.fetch_summary` and pass `cost_summary` / `cost_error` to the template.
- [ ] **2.2** `templates/home.html` — add three KPI tiles ("Today (account)", "7d (account)", "MTD (account)") gated on `cost_summary is not None`. When `cost_error.kind == "no_key"`, show a single-line CTA instead.
- [ ] **2.3** CSS for the new tile cluster — visually distinct from the workflow telemetry tiles (suggest a thin border on the right edge of the cluster) so users can tell at a glance which numbers come from which source.
- [ ] **2.4** Tests:
  - Home page renders with no key → CTA present, no traceback
  - Home page renders with valid `CostSummary` → all three KPI tiles populated
  - Home page with `auth_failed` → friendly notice, dashboard otherwise functional
  - `?refresh=1` → cost fetch happens with `refresh=True`

## Phase 3 — /telemetry per-day panel

- [ ] **3.1** Modify `routes/dashboard.py::telemetry_page` to include `cost_summary.by_day` for the panel.
- [ ] **3.2** `templates/telemetry.html` — new section "Account spend (Anthropic billing)" with a table: Date | Cost. Last 30 days. Empty-state matches the existing pattern.
- [ ] **3.3** Tests for the new panel.

## Phase 4 — `attune ops setup-billing` CLI

- [ ] **4.1** New CLI subcommand. Prompts for admin key (no echo), validates against the API (single `cost_report` call with `limit=1`), writes to `~/.attune/anthropic-admin.env` with mode 0600.
- [ ] **4.2** Validate-only mode (`--validate`) — checks an existing key without re-prompting.
- [ ] **4.3** Tests using a mocked API client.

## Phase 5 — Polish + docs

- [ ] **5.1** Add a panel of "About Anthropic billing data" on `/telemetry` linking to Anthropic's billing docs, explaining the 24h lookback delay, and noting that this is read-only.
- [ ] **5.2** Update `docs/reference/` with a "Setting up cost reporting" page.
- [ ] **5.3** CHANGELOG entry.
- [ ] **5.4** Close spec.

---

## Out of scope (parking lot)

- Per-workspace breakdown
- Forecasting / projections
- Slack / email threshold notifications
- Hourly granularity on the telemetry panel
- Comparing attune-workflow telemetry vs admin-API spend to compute coverage gap
- Multi-organization support

## Rollback plan

Each phase is a single squash-merge. Revert via `git revert <commit>`:

- Revert Phase 2 → no account-spend KPI tiles; rest of home page works
- Revert Phase 3 → no /telemetry account panel
- Revert Phase 4 → no setup CLI (user can manually create the env file)
- Revert Phase 1 → module disappears; no callers exist by definition
