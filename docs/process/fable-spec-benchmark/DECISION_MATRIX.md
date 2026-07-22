# Fable 5 Spec-Generation Decision Matrix

**Source:** FABLE_SPEC_WORKFLOW_TODO.md item 1 — "Measure before
setting the generation budget."
**Harness:** `scripts/benchmark_fable_spec.py` (streaming, beta
namespace + fable fallbacks, `max_retries=0`).
**Raw data:** [results-20260722T120248Z.json](results-20260722T120248Z.json)
(one run per packet, 2026-07-22, API-key path).
**Status:** measured; latency budget RATIFIED (Patrick, 2026-07-22,
PR #1590 review — approved as proposed).

## Measured results (n=1 per packet)

| packet | files | TTFE (s) | TTFT (s) | total (s) | in tok | out tok | markers | failure | cost ($) |
|---|---|---|---|---|---|---|---|---|---|
| one | 1/1 | 3.03 | 4.03 | 65.5 | 401 | 4,994 | ok | none | 0.25 |
| four | 4/4 | 2.88 | 7.64 | 205.6 | 545 | 16,473 | ok | none | 0.83 |
| five | 5/5 | 2.93 | 8.04 | 210.6 | 592 | 17,678 | ok | none | 0.89 |

TTFE = time to first stream event; TTFT = time to first text delta
(the gap is the adaptive-thinking lead-in, which emits stream events
— so a streaming consumer sees progress from ~3s even while the
model is still thinking).

## What the data says

1. **First-event latency is flat (~3s) regardless of packet size.**
   The >150s silent stall that motivated the todo is a property of
   non-streaming/whole-block consumption, not of Fable 5. Any runner
   that streams gets a progress signal in seconds.
2. **Whole-spec five-file generation completes reliably in ~3.5 min**
   with perfect marker compliance (5/5) and `end_turn` — no
   truncation at a 64k cap, no refusal, no fallback engagement.
3. **Marker discipline held at every size** — `=== FILE: path ===`
   validation is a workable materialization gate.
4. **Cost is modest**: a full five-file spec draft ≈ $0.89; the whole
   three-packet benchmark ≈ $1.97.

## Routing matrix (default strategy selection)

| Condition | Strategy |
|---|---|
| Default (any packet ≤5 files) | **Whole-spec, streaming** — evidence shows no reliability or latency penalty vs splitting, and one call preserves cross-document coherence |
| First-event gate trips once | Switch to **per-document** generation; never re-attempt the same whole-spec call (todo item 2 rule) |
| Marker validation fails | Re-request ONLY the missing/malformed document(s) per-document; never regenerate the whole packet |
| >5 documents requested | Split into ≤5-file packets (unmeasured territory — extrapolation not licensed by this data) |

## Latency budget — RATIFIED 2026-07-22

Derived from measurements with stated multipliers; ratified as
proposed by Patrick in PR #1590 review (todo item 1 forbids invented
thresholds — these are anchored, but n=1, so the margins are
deliberately generous):

| Bound | Proposal | Derivation |
|---|---|---|
| Time-to-first-event gate | **30 s** | ~10× measured TTFE (3.0s); far below the 150s pain threshold that triggered the todo |
| Inter-event gap gate | **90 s** | streaming read timeout; adaptive thinking emitted events continuously in all runs — a 90s silence indicates a stall, not thinking |
| Total-run budget, ≤1 file | **180 s** | ~2.7× measured 65.5s |
| Total-run budget, 4–5 files | **480 s** | ~2.3× measured ~210s |

## Limitations

- **n=1 per packet** — no variance data; tail latency under pool
  saturation (where the server-side opus-4-8 fallback engages) is
  unmeasured. The generous multipliers compensate; re-run the
  harness to accumulate samples if a budget trip is ever disputed.
- Prompts carried a compact brief (~500 input tokens); packets with
  heavy repo context will raise TTFT modestly (input processing) but
  TTFE should stay transport-bound.
- Measured on the direct API-key path; the Codex-mediated path that
  exhibited the original stall adds its own orchestration overhead
  not captured here.
