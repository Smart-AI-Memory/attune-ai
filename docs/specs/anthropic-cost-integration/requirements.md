# Requirements — Anthropic Cost Integration

**Status:** Draft 2026-05-18
**Owner:** Patrick

---

## Problem

The ops dashboard's "7-day spend" KPI on the Home page is the user's primary signal for "what did I spend lately?" Today it reads from `~/.attune/telemetry/usage.jsonl` — a file written by `UsageTracker.record()` inside the attune workflow runner. This captures **only** workflow runs that route through the attune pipeline.

Patrick reported (2026-05-18) that the dashboard shows $0 for 7-day spend while his Anthropic Console shows $400+ this month. Two independent issues are mixed in:

1. **Stale local telemetry.** Last `usage.jsonl` event is 2026-05-09 — something stopped writing 9 days ago. (Separate spec — `docs/specs/telemetry-rethink/` may already cover.)
2. **Coverage gap.** Even when telemetry IS writing, `usage.jsonl` totals are far below the actual account spend because:
   - Direct Claude Code conversations (`claude` CLI, IDE extension) don't hit `UsageTracker.record()`.
   - MCP tool calls don't hit it either.
   - Direct API calls from other tools (sibling repos, scripts) don't hit it.
   - Subscription / session usage (Claude Code Pro/Max) isn't tracked anywhere locally.

This spec addresses **issue 2** by adding Anthropic's official admin-API cost endpoint as a second data source for the dashboard.

## Goals

- Home page shows **real account spend** for today, the last 7 days, and current month.
- A new panel on `/telemetry` shows the per-day breakdown sourced from Anthropic.
- The existing `usage.jsonl`-based panels stay where they are — they're still useful for "which attune workflows spent the most" — but they no longer claim to represent total spend.
- Admin API key is stored once, in a path the user controls. No automatic discovery from environment scraping or filesystem walks.
- Network calls are cached aggressively. Home page must not hit `api.anthropic.com` on every refresh.
- Graceful degradation: if the admin key is missing, unset, or rejected, the dashboard renders cleanly with a small "Set up Anthropic cost reporting" CTA instead of erroring.

## Non-Goals

- **Replacing** the existing `usage.jsonl` panels. They cover a different question ("which attune workflow spent the most"); the admin API can't answer that.
- **Real-time** data. Anthropic's cost report has a documented delay (lookback-window for finalization). We're not building a live stream.
- **Per-feature attribution.** The admin API doesn't know about attune features. We get model-level, workspace-level, and cost-type breakdown only.
- **Multi-organization support.** One admin key, one organization, current month/7d/today views. Switching orgs requires re-running setup.
- **Storing fetched cost data on disk.** In-memory caching with TTL only. No persistence — Anthropic's API is the source of truth and we shouldn't accumulate a local copy of billing data.

## Data Source

Anthropic Admin API:

- **Endpoint:** `GET https://api.anthropic.com/v1/organizations/cost_report`
- **Auth:** `X-Api-Key: <ANTHROPIC_ADMIN_API_KEY>`, `anthropic-version: 2023-06-01`
- **Granularity:** Daily buckets (`bucket_width=1d`)
- **Cost format:** Decimal string in lowest currency unit (cents). Must divide by 100.
- **Cost types in response:** `tokens`, `web_search`, `code_execution`, `session_usage`
  - **Open question (Phase 0):** Does `session_usage` cover Claude Code subscription usage? If yes, this single endpoint gives us the full picture. If not, we need a different approach for the "$400 / month" figure.

## Constraints

1. **Admin key handling.** The admin key is distinct from a regular API key (per docs, format and permissions differ). It must NEVER appear in:
   - Logs (including debug-level)
   - Error messages surfaced to the UI
   - HTTP request audit trails
   - Process command lines (no `subprocess` calls that include the key as an arg)
2. **Storage:** Reuse the existing `~/.attune/anthropic.env` pattern OR introduce a separate `~/.attune/anthropic-admin.env` to keep blast radius small. Decision deferred to design phase.
3. **Cache:** TTL must be short enough that "I spent $50 in the last hour" shows up the same day, but long enough that 10 home-page refreshes don't fire 10 API calls. Suggested: 15 min default, configurable.
4. **Failure modes:** Network timeout, 401 (bad key), 403 (key lacks org access), 429 (rate-limited), 5xx (Anthropic outage). All must render the existing dashboard untouched and surface a small inline error on the affected panel.
5. **No background polling.** Fetch on-demand when a page renders, miss the cache, and the user has a key configured. No daemon, no scheduled task.

## Acceptance Criteria

- [ ] Phase 0 probe confirms `session_usage` coverage (or surfaces the gap).
- [ ] Home page shows three new KPI values: **Today (account)**, **7d (account)**, **MTD (account)**. Sourced from Anthropic cost_report.
- [ ] `/telemetry` gains a "Account spend (Anthropic billing)" panel with per-day breakdown for the last 30 days.
- [ ] Without an admin key configured, home and `/telemetry` render exactly as before, plus a "Connect Anthropic billing" callout linking to setup docs.
- [ ] CLI command `attune ops setup-billing` (or similar) walks the user through admin-key registration: prompt for key, validate against the API, save to `~/.attune/anthropic-admin.env` with mode 0600.
- [ ] Caching: a forced refresh (`?refresh=1`) and an Anthropic 429 are both handled cleanly.
- [ ] Tests cover: missing key, invalid key (401), valid key + happy path, network timeout, 429 retry, cache hit/miss, currency unit conversion.

## Out of Scope (Parking Lot)

- Comparing attune-workflow telemetry against admin-API spend to compute "% of spend visible to attune."
- Per-workspace breakdown (we'll group by description first; workspace_id breakdown can come later).
- Cost forecasting / projections.
- Slack / email notifications when spend crosses a threshold.
- Web search request cost breakdown.
