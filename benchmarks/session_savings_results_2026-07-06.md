# session_savings — first measured run (2026-07-06)

First live run of `benchmarks/session_savings.py`: 5 default read-only
analysis tasks × 2 arms × 1 repeat = 10 headless `claude -p` sessions
against this repo (CLI-default model, API-key billing; run total
$6.59). Arms toggled `ATTUNE_JIT_RECALL` / `ATTUNE_LESSON_RECALL`;
raw per-session data in `session_savings_results_2026-07-06.json`.

## Result: on this task profile, memory is measured OVERHEAD

| Metric (median/task) | Memory on | Memory off | Δ on vs off |
|---|--:|--:|--:|
| uncached input tok | 56,552 | 51,921 | +8.9% |
| cache-read tok | 404,097 | 250,088 | +61.6% |
| output tok | 3,155 | 2,404 | +31.2% |
| turns | 6 | 4 | +50.0% |
| wall-clock s | 52.0 | 38.6 | +34.8% |
| API s | 49.4 | 36.4 | +35.7% |
| cost USD | 0.6544 | 0.5096 | +28.4% |

Arm totals: on $3.60, off $2.99 (+20% run cost).

## Read this honestly

- **Do NOT quote "memory saves N%" from anything currently measured.**
  On one-shot analysis tasks the injections add context with nothing
  to save — no cross-session re-derivation avoided, no trap hit. The
  harness docstring predicted exactly this outcome for such a set.
- The memory-on arm did *more work* (6 vs 4 median turns), which
  inflates every downstream metric. Answer quality was not scored;
  broader exploration may be better or just more expensive.
- n=1 per (task, arm), single repeat → directional. The harness
  itself prints the <5-runs-per-arm warning for percentages you'd
  publish.

## What a savings claim still needs

A task profile where memory's design should pay: multi-step tasks
resuming prior-session work, and tasks whose known trap a recalled
lesson prevents (failed approach avoided = turns saved). Run with
`--tasks <continuity-set>.json --repeats 3` and quote medians. Until
then, the defensible public framing remains the scaling claim:
budget-capped ≤3k-token recall from a 300k-token store (67× fewer
tokens per recall, P@3 96%) — cost flat as memory grows.
