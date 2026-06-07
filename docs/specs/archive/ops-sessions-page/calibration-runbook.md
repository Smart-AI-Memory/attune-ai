# Calibration runbook

> How to seed and maintain
> `tests/fixtures/ops/session_summaries/snapshot.json` — the
> regression gate for the Haiku starter-prompt summarizer.

---

## Background

The `/sessions` page calls Haiku-4.5 to summarize each session's
opening prompt. The output is sensitive to two things:

1. The exact text of `attune.ops.session_summarizer.SUMMARY_PROMPT`
2. The model itself (Anthropic ships new Haiku revisions
   periodically)

A change to either can quietly regress output quality, length, or
cost. The committed `snapshot.json` is the regression gate — it
holds one row per fixture with the Haiku tokens, cost, and summary
text from the last accepted calibration run.

---

## When to re-run the calibrator

- You edited `SUMMARY_PROMPT` in `src/attune/ops/session_summarizer.py`
- You added or removed a fixture in
  `tests/fixtures/ops/session_summaries/*.jsonl`
- You bumped the Haiku model ID (the snapshot stores the model id,
  so a mismatch fails the test)
- Periodic re-baseline against the current Haiku release (quarterly
  is plenty; the snapshot is a regression gate, not a quality
  benchmark)

You do **not** need to re-run for:

- Pure refactors of `session_summarizer.py` that don't change the
  prompt
- Cache module changes (the calibrator uses a fresh tempdir cache)
- Changes elsewhere in the codebase

---

## Run the calibrator

```bash
# From the repo root, with ANTHROPIC_API_KEY in your env
ATTUNE_OPS_SESSIONS_LLM=1 \
  python scripts/calibrate_session_summary.py
```

Output:

```text
Model:         claude-haiku-4-5-20251001
Prompt hash:   b837f64e77aa
Fixtures:      12 from tests/fixtures/ops/session_summaries
Snapshot:      tests/fixtures/ops/session_summaries/snapshot.json

Fresh totals:  {'fixtures': 12, 'succeeded': 12, 'tokens_in': ...,
                'tokens_out': ..., 'cost_usd': 0.0xxx}

Snapshot written to tests/fixtures/ops/session_summaries/snapshot.json
Total cost:    $0.0xxx

Review the diff and commit when satisfied:
  git diff tests/fixtures/ops/session_summaries/snapshot.json
```

Cost is typically ~$0.02 (12 fixtures × ~$0.001 each). The
calibrator uses a fresh tempdir cache, so every fixture incurs a
real Haiku call — no cache hits inflate the "this seems free"
illusion.

---

## Inspect + commit

```bash
git diff tests/fixtures/ops/session_summaries/snapshot.json
```

Look for:

- **Tokens / cost** — drift past ±20% on `cost_usd` is the
  threshold the `--check` mode flags. A larger drift means
  something material changed (prompt got chattier, fixture got
  longer, model got more verbose).
- **Summary samples** — random-spot-check 2-3 to make sure the
  output still matches decisions.md Decision 2 (one short
  sentence, optional 0-3 bullets, `Resume:` line). If a recent
  prompt edit dropped the structural rules, you'll see it here.
- **Prompt hash** — should match the new `SUMMARY_PROMPT` you
  edited. The test asserts this so a stale snapshot can't sneak
  in.

When you're satisfied:

```bash
git add tests/fixtures/ops/session_summaries/snapshot.json
git commit -m "calib(session-summary): regen snapshot after prompt edit"
```

---

## Check mode (CI-style dry-run)

Use `--check` to verify a fresh run matches the committed
snapshot without overwriting it. Useful as a pre-PR sanity check
or in a nightly cron:

```bash
ATTUNE_OPS_SESSIONS_LLM=1 \
  python scripts/calibrate_session_summary.py --check
```

Per-field tolerances:

| Field | Tolerance | Why |
|-------|-----------|-----|
| `tokens_in` | ±10% | Input is the redacted text; mostly stable |
| `tokens_out` | ±50% | Haiku output length varies more |
| `cost_usd` | ±20% | Per decisions.md Decision 8 |
| `summary_chars` | ±50% | Sanity check; catches empty / runaway |

Exit code is 1 if any fixture drifts past its tolerance; the
report lists every drifting fixture + field + observed ratio.

---

## Dry-run (no API calls)

```bash
python scripts/calibrate_session_summary.py --dry-run
```

Lists the fixture set + prints the current prompt fingerprint
(SHA-256[:12]). Useful for "I just want to know what the prompt
hash is right now" — e.g. to compare against what's in the
committed snapshot before deciding whether a re-run is needed.

---

## CI gate

`tests/unit/ops/test_calibration_snapshot.py` runs on every CI
build. It does **not** make Haiku calls — it asserts the
committed snapshot is:

- Structurally sound (right top-level fields, model id matches,
  one row per fixture on disk)
- Within plausible cost bands (per-fixture ≤ $0.05, total ≤ $0.10)
- Hash-consistent with the current `SUMMARY_PROMPT`

When the snapshot is absent (fresh clone before first
calibration), every test in the file skips — no false failures
during initial setup.

---

## Open boxes the snapshot fills

Once you've run the calibrator and committed the snapshot, the
following items in `decisions.md`'s calibration record stop being
"to fill in" boxes and become reportable facts:

- Average tokens per summary (in / out) — read from
  `snapshot.json` `totals.tokens_in / totals.fixtures`
- Average cost per session summary — `totals.cost_usd /
  totals.fixtures`
- Whether the budget cap ever fires during normal usage — observe
  over the first week of production use; the snapshot's
  per-fixture max cost is the proxy
