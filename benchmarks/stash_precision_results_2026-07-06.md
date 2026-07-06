# Stash-precision frozen baseline — 2026-07-06

First measured run of `stash_precision.py`, taken the day the
provenance fix (#1269, shipped in 10.0.1) landed. A/B: the pre-fix
extractor (`v10.0.0`) vs the fixed one, identical transcripts,
deterministic extraction (llama3.1:8b, temperature 0, seed 42).

## Broad replay — 8 real session transcripts

| variant | findings | ambient-sourced (auto) | rate |
|---|---|---|---|
| pre-fix (10.0.0) | 39 | 2 | **5%** |
| fixed (10.0.1) | 39 | **0** | **0%** |

Auto-score is a lower bound (shingle overlap against tool-only text);
`unmatched` findings need human labeling. The two pre-fix catches were
textbook #1263: corpus-lesson text a session *read*, promoted to
findings.

## Incident replay — the 2026-07-05 15:23 garbled stash

Transcript truncated at the originating Stop-hook moment (`--anchor`),
so both variants saw exactly the input that produced the original
3-of-5-garbled stash (issue #1263):

| variant | findings | bad (auto + human label) |
|---|---|---|
| pre-fix | 5 | 2 — regenerated the fatigue-file restatement and an inverted admin-merge "decision" |
| fixed | 5 | **0** — all five traceable to actions the session actually took |

## Method notes

- Provenance ground truth is machine-derived: text appearing ONLY in
  tool_result/tool_use blocks was never said by a participant, so a
  finding built from it is ambient by construction.
- Determinism: seed/temperature injected into the extractor's own
  Ollama call — variants differ only in extractor code.
- Transcripts never leave the machine; this file carries aggregates
  only (the two pre-fix garble examples are already public in #1263).

Re-run: `python benchmarks/stash_precision.py --recent 8 --compare-ref v10.0.0`
