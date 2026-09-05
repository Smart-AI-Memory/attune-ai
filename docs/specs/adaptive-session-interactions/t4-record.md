# Adaptive session interactions — T4 record

Append-only. One row per real `/spec` review-stage occurrence on the
named host, served under [`t4-protocol.md`](t4-protocol.md) (frozen
2026-09-05, decisions D10). The next row with an empty **Date** is the
next assigned slot. Rows carry counts, labels, and telemetry identifiers
only — never answers, nonces, or contract hashes.

Columns: Completed = choice accepted canonically; Corr = collector
rejections before acceptance; Clar = clarification turns about the choice
between render and acceptance; Override = user asked for the other lane;
Auth fail = any acceptance not matching the rendered view or any double
execution; Dwell = render-to-acceptance seconds from the telemetry join
(descriptive); Paint = always `null` on this host.

| # | Cond | Date (UTC) | Spec slug | Workspace id | Runtime (attune-ai src / forms / py) | Completed | Corr | Clar | Override | Auth fail | Dwell s | Paint | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | A | | | | | | | | | | | null | |
| 2 | B | | | | | | | | | | | null | |
| 3 | B | | | | | | | | | | | null | |
| 4 | A | | | | | | | | | | | null | |
| 5 | B | | | | | | | | | | | null | |
| 6 | A | | | | | | | | | | | null | |
| 7 | A | | | | | | | | | | | null | |
| 8 | B | | | | | | | | | | | null | |

## Exclusions (recorded, not counted)

| Date (UTC) | Spec slug | Reason | Notes |
| --- | --- | --- | --- |
| 2026-09-05 | asi-t3-widget-lane | synthetic (T3 receipt) | widget lane; accepted rev 3 → 4 |
| 2026-09-05 | asi-t3-markdown-lane | synthetic (T3 receipt) | Markdown lane; accepted rev 3 → 4 |

## Falsification / suspension log

| Date (UTC) | Rule | Tripped? | Action |
| --- | --- | --- | --- |
