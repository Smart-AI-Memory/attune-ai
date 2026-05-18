# Design — Anthropic Cost Integration

**Status:** Draft 2026-05-18

---

## Component layout

```
src/attune/ops/
├── anthropic_cost.py             # New — HTTP client + cache + key loader
├── routes/dashboard.py           # Modified — home + telemetry pulled from new module
├── templates/home.html           # Modified — three new KPI tiles, conditional CTA
├── templates/telemetry.html      # Modified — new "Account spend" panel
└── cli.py                        # Modified — `setup-billing` subcommand
```

## Module: `anthropic_cost.py`

Single module owns:

1. **Admin key loader** — reads `~/.attune/anthropic-admin.env`, returns `None` if missing or unreadable. Never raises.
2. **HTTP client** — `httpx.Client` with 10s timeout, single retry on connection errors, no retry on 4xx. Uses the `anthropic` SDK only if it already supports admin endpoints; otherwise raw `httpx`.
3. **Cache** — process-lifetime `dict[<query-key>, (fetched_at, payload)]` with TTL (default 900s = 15min). Cache key includes the date range + bucket_width so different views don't pollute each other.
4. **Domain transforms** — convert the API's `data[].results[].amount` (cents-as-string) into a `CostSummary` dataclass with `today_usd`, `seven_day_usd`, `month_to_date_usd`, `by_day: list[(date, float)]`.

```python
@dataclass(frozen=True)
class CostSummary:
    """Account-level cost data from the Anthropic admin API.

    All amounts in USD (converted from the API's lowest-unit decimal strings).
    `last_fetched_at` is the wall-clock time of the underlying API call,
    not when the dashboard last rendered.
    """
    today_usd: float
    seven_day_usd: float
    month_to_date_usd: float
    by_day: list[tuple[date, float]]  # last 30 days
    last_fetched_at: datetime
    source: Literal["live", "cached"]

@dataclass(frozen=True)
class CostFetchError:
    """Distinguishes "no key configured" from "key rejected" from
    "Anthropic is down" so the UI can render the right CTA."""
    kind: Literal["no_key", "auth_failed", "rate_limited", "network", "unknown"]
    message: str  # Safe to render — never contains key material
```

## Configuration

`~/.attune/anthropic-admin.env` contains a single line:

```
ANTHROPIC_ADMIN_API_KEY=sk-ant-admin01-...
```

File mode forced to 0600 on write. Loaded lazily on first request, then cached in memory. Refresh requires restart (matches `ANTHROPIC_API_KEY` convention).

Why a separate file from `anthropic.env`? Admin keys grant org-wide read access; regular keys are scoped per workspace. Keeping them in distinct files makes accidental leaks (e.g. copying a config into a sibling repo) less likely to cross-contaminate.

## Caching strategy

In-memory TTL:

- Default 15 min (`ANTHROPIC_COST_CACHE_TTL_SECONDS=900`).
- Cache key: `(start_date.isoformat(), end_date.isoformat(), bucket_width)`.
- A user-forced refresh via `?refresh=1` bypasses cache for that single render. The cache entry IS still updated with the fresh payload (so the next un-forced render benefits).

No on-disk caching. Billing data is sensitive and the in-memory layer is sufficient given the access pattern (one user, occasional refresh, not a high-traffic dashboard).

## Route changes

### `home.html` flow

```python
@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    cfg = request.app.state.config
    # ... existing telemetry summary, workflows, etc. ...

    # New — best-effort Anthropic cost fetch
    cost_summary, cost_error = anthropic_cost.fetch_summary(cfg)

    return _render(
        request,
        "home.html",
        # ... existing fields ...
        cost_summary=cost_summary,   # None when fetch failed
        cost_error=cost_error,       # None when fetch succeeded
    )
```

Template branches on `cost_summary`:
- Present → three new KPI tiles next to the existing "Workflow telemetry" tiles.
- `cost_error.kind == "no_key"` → small "Connect Anthropic billing →" callout (link to setup docs).
- Other error kinds → an "Anthropic billing temporarily unavailable" muted notice.

### `/telemetry` flow

Same pattern: fetch summary, pass to template, conditional render of the new panel.

## Setup command

`attune ops setup-billing` (new subcommand in `cli.py`):

```
attune ops setup-billing

→ Visit https://console.anthropic.com/settings/admin-keys to create an admin API key.
  (Admin keys give read-only access to organization usage and cost reports.)

Enter your admin API key: ********

✓ Key validated against Anthropic admin API
✓ Saved to /Users/.../.attune/anthropic-admin.env (mode 0600)
✓ Cached cost data: $42.18 today, $387.45 last 7 days

Done. Restart the ops dashboard to see the new data.
```

Validation = a single `GET /v1/organizations/cost_report?starting_at=<today>&limit=1` call. If it returns 2xx, the key is valid and has cost-read scope. If 401/403, the key is rejected with a clear error.

## Failure handling

| Failure | UI behavior |
|---|---|
| No key file | Callout: "Connect Anthropic billing →" |
| Key file present but unreadable | Same as no_key, log at WARN with path (not contents) |
| Network timeout | KPI tiles render as `—` with hover tooltip "Anthropic API unavailable" |
| 401 (key rejected) | Notice: "Anthropic admin key was rejected — run `attune ops setup-billing` to refresh" |
| 429 (rate limited) | Use cached value if available; otherwise show `—` |
| 5xx Anthropic outage | Same as network timeout |

## Privacy / logging

- The admin key is never logged. The key loader returns the key as a `str` only to the HTTP client; intermediate functions take it by reference, not value.
- HTTP error messages from `httpx` are sanitized before surfacing — the standard format includes the URL but not headers, so no key leakage there. We still scrub `X-Api-Key` from any string we pass to a logger or render.
- Cached payloads contain cost data but no key material. Safe to render in tracebacks (we don't, but if we did, it wouldn't leak the key).

## Drift guards

- Test: `anthropic_cost.fetch_summary` with a missing key returns `(None, CostFetchError(kind="no_key", ...))` — never raises.
- Test: Home page renders cleanly with no key (key error → callout, not 500).
- Test: Currency conversion — "12345" cents → $123.45, not $12345.
- Test: Cache hit increments only the cached counter; subsequent calls within TTL don't hit `httpx.Client.get`.
- Test: `?refresh=1` bypasses cache.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Admin key leakage via logs / error pages | High | Single key-loading function, scrub all log lines, no env-var-based key passing |
| `session_usage` doesn't actually cover Claude Code | Medium | Phase 0 probe confirms before building Phase 1+ |
| API schema changes | Low | Cost report endpoint is stable per docs; pin `anthropic-version: 2023-06-01` |
| Caching staleness confuses users | Low | Show `last_fetched_at` next to each KPI tile (faint, on hover) |
| `httpx` adds dependency weight | Low | Already a transitive dep of `anthropic` SDK |

## Phasing

See `tasks.md`.
