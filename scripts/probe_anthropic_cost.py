#!/usr/bin/env python3
"""Phase 0 probe — hit Anthropic's admin cost_report endpoint.

Reads the admin API key from one of these (in order):

1. ``$ANTHROPIC_ADMIN_API_KEY`` env var
2. ``~/.attune/anthropic-admin.env`` containing either:
   - ``ANTHROPIC_ADMIN_API_KEY=sk-ant-admin01-...`` (canonical), OR
   - a bare key on a single line (tolerated for convenience)

Prints:
- Total MTD (month-to-date) cost in USD
- Today's cost in USD
- Last 7 days' cost in USD
- Breakdown by ``cost_type`` for the full 30-day window (tokens vs
  session_usage vs web_search vs code_execution) — this is the key
  signal for whether ``session_usage`` captures Claude Code spend.

NEVER prints the admin key. Errors surface only the HTTP status and
the response body's ``error`` field (if any) — both safe to echo.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print(
        "ERROR: httpx not installed. Run with the dashboard venv:\n"
        "  /Users/patrickroebuck/attune-ai/.venv/bin/python scripts/probe_anthropic_cost.py",
        file=sys.stderr,
    )
    sys.exit(1)


ADMIN_ENV_PATH = Path.home() / ".attune" / "anthropic-admin.env"
COST_REPORT_URL = "https://api.anthropic.com/v1/organizations/cost_report"


def _load_admin_key() -> str | None:
    """Return the admin key, or ``None`` if unavailable. Never logs the key."""
    env_value = os.environ.get("ANTHROPIC_ADMIN_API_KEY", "").strip()
    if env_value:
        return env_value

    try:
        raw = ADMIN_ENV_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(f"ERROR: cannot read {ADMIN_ENV_PATH}: {exc}", file=sys.stderr)
        return None

    if not raw:
        return None

    # Canonical form: KEY=VALUE on one line (possibly with quotes).
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("ANTHROPIC_ADMIN_API_KEY="):
            value = line.split("=", 1)[1].strip().strip("\"'")
            if value:
                return value
        # Bare-key form: a single line that LOOKS like a key.
        elif line.startswith("sk-ant-"):
            return line

    return None


def _cost_usd(amount_cents_str: str) -> float:
    """Convert Anthropic's cents-as-decimal-string to USD float."""
    try:
        return float(amount_cents_str) / 100.0
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    key = _load_admin_key()
    if key is None:
        print(
            f"ERROR: admin key not found in $ANTHROPIC_ADMIN_API_KEY or " f"{ADMIN_ENV_PATH}",
            file=sys.stderr,
        )
        return 2

    # 30-day window ending now.
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=30)
    end = today + timedelta(days=1)  # inclusive of today

    params = {
        "starting_at": datetime.combine(start, datetime.min.time()).isoformat() + "Z",
        "ending_at": datetime.combine(end, datetime.min.time()).isoformat() + "Z",
        "bucket_width": "1d",
        "group_by[]": "description",  # so cost_type / model show up
        "limit": 31,
    }

    headers = {
        "X-Api-Key": key,
        "anthropic-version": "2023-06-01",
        "accept": "application/json",
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(COST_REPORT_URL, params=params, headers=headers)
    except httpx.HTTPError as exc:
        print(f"ERROR: network: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    if resp.status_code != 200:
        # Surface only status + sanitized body (NEVER headers — they
        # contain X-Api-Key).
        body: str
        try:
            body = json.dumps(resp.json(), indent=2)
        except ValueError:
            body = resp.text[:500]
        print(
            f"ERROR: HTTP {resp.status_code} from cost_report\n{body}",
            file=sys.stderr,
        )
        return 4

    payload = resp.json()
    buckets = payload.get("data", [])

    # Tallies.
    mtd_total = 0.0
    today_total = 0.0
    seven_day_total = 0.0
    by_day: dict[str, float] = {}
    by_cost_type: dict[str, float] = {}
    by_model: dict[str, float] = {}

    seven_days_ago = today - timedelta(days=7)
    first_of_month = today.replace(day=1)

    for bucket in buckets:
        bucket_start = bucket.get("starting_at", "")
        # Parse just the date portion; bucket_width=1d means buckets
        # snap to UTC day boundaries.
        bucket_date_str = bucket_start[:10]
        try:
            bucket_date = date.fromisoformat(bucket_date_str)
        except ValueError:
            continue

        bucket_day_total = 0.0
        for row in bucket.get("results", []):
            amount_usd = _cost_usd(row.get("amount", "0"))
            bucket_day_total += amount_usd

            cost_type = row.get("cost_type") or "(none)"
            by_cost_type[cost_type] = by_cost_type.get(cost_type, 0.0) + amount_usd

            model = row.get("model") or "(none)"
            by_model[model] = by_model.get(model, 0.0) + amount_usd

        by_day[bucket_date_str] = bucket_day_total

        if bucket_date == today:
            today_total += bucket_day_total
        if bucket_date >= seven_days_ago:
            seven_day_total += bucket_day_total
        if bucket_date >= first_of_month:
            mtd_total += bucket_day_total

    print("=" * 60)
    print(f"Anthropic cost_report probe — {today.isoformat()}")
    print("=" * 60)
    print(f"Window: {start.isoformat()} → {today.isoformat()} (30 days)")
    print(f"Buckets returned: {len(buckets)}")
    print(f"has_more: {payload.get('has_more', False)}")
    print()
    print("Totals (USD):")
    print(f"  Today:           ${today_total:>10.2f}")
    print(f"  Last 7 days:     ${seven_day_total:>10.2f}")
    print(f"  Month-to-date:   ${mtd_total:>10.2f}")
    print()

    print("By cost_type (30d):")
    for cost_type, total in sorted(by_cost_type.items(), key=lambda kv: -kv[1]):
        print(f"  {cost_type:<24} ${total:>10.2f}")
    print()

    print("By model (30d, top 10):")
    for model, total in sorted(by_model.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {model:<40} ${total:>10.2f}")
    print()

    print("Last 14 days:")
    for day in sorted(by_day.keys())[-14:]:
        print(f"  {day}  ${by_day[day]:>10.2f}")

    print()
    print("Compare to Anthropic Console:")
    print(
        "  https://console.anthropic.com/settings/billing  → "
        "Usage tab → 'This month' total should match MTD above."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
