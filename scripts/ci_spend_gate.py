#!/usr/bin/env python3
"""DEC-8 enforcement: block a CI job when month-to-date API spend is over budget.

The R6 spend alarm (``attune.ops.data.spend_alarm``) surfaces overspend on
the ops dashboard — visibility only, no matter how loud the alarm, nothing
stops the next keyed workflow run from adding to the bill. This script is
the enforcement half: a pre-flight step for CI jobs that use a real
``ANTHROPIC_API_KEY`` (``integration-auth.yml``, ``help-freshness.yml``,
``windows-payload-capture.yml``). Run it before the keyed step; a nonzero
exit fails the job before any real API call happens.

Requires the ``ANTHROPIC_ADMIN_API_KEY`` secret (org-wide cost-report
read access — distinct from the workspace-scoped ``ANTHROPIC_API_KEY``
used to actually run workflows). Without it, this script cannot see
account-level spend and deliberately does not block: failing closed on
missing configuration would silently break every keyed workflow the day
this lands, before anyone wires up the new secret. The same reasoning
covers transient fetch errors (rate limit, network) — CI flakiness in the
cost-report call is not a reason to lose a real workflow run. Both cases
print a loud warning and exit 0.

The only case that blocks is a *confirmed* month-to-date figure at or
over the ceiling. That matches DEC-8 (“hard-cap CI LLM spend”,
docs/specs/product-direction-review/assessment-2026-07-11.md) and defers
to the account-level ceiling already named in
`user_monthly_spend_budget` and `attune.ops.data.MONTHLY_API_CEILING_USD`.
"""

from __future__ import annotations

import argparse
import sys

from attune.ops.anthropic_cost import fetch_summary
from attune.ops.data import MONTHLY_API_CEILING_USD


def check_budget(ceiling: float) -> int:
    """Return the process exit code for the spend-gate check.

    0: under the ceiling, or the ceiling couldn't be verified (fail-open,
       with a loud warning — see the module docstring for why).
    1: month-to-date spend is confirmed at or over the ceiling.
    """
    summary, error = fetch_summary(refresh=True)

    if error is not None:
        print(
            f"::warning::ci_spend_gate: could not verify CI spend "
            f"({error.kind}: {error.message}). Proceeding without "
            f"enforcement — see scripts/ci_spend_gate.py for why this "
            f"fails open rather than blocking the job."
        )
        return 0

    assert summary is not None  # exactly one of summary/error is set
    if summary.month_to_date_usd >= ceiling:
        print(
            f"::error::ci_spend_gate: month-to-date API spend "
            f"${summary.month_to_date_usd:.2f} is at or over the "
            f"${ceiling:.2f} ceiling (DEC-8). Blocking this job before "
            f"it makes any real API calls."
        )
        return 1

    print(
        f"ci_spend_gate: month-to-date spend ${summary.month_to_date_usd:.2f} "
        f"is under the ${ceiling:.2f} ceiling — proceeding."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ceiling",
        type=float,
        default=MONTHLY_API_CEILING_USD,
        help=f"Monthly USD ceiling (default: ${MONTHLY_API_CEILING_USD:.2f}).",
    )
    args = parser.parse_args(argv)
    return check_budget(args.ceiling)


if __name__ == "__main__":
    sys.exit(main())
