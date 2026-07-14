# Cross-session recall loop — live triage 2026-06-11

**Trigger:** Patrick asked "are the Redis memory enhancements
helping yet?" Answer required receipts; this is the dogfood record.

## Verdict

**Not yet — until today the recall loop had never delivered a real
cross-session finding.** Every individual component works; the
losses come from three specific integration/ops gaps, all fixable
with small PRs. The track itself is right: the quality of what the
extractor pulls from a real transcript is genuinely worth recalling.

## Receipts (all live, 2026-06-11)

1. **`/recall` returned `[]`** for "MCP workflow tool handlers
   integration coverage" — a topic with rich history. Backend had
   silently degraded to `FileStashBackend`.
2. **AMS server was down** (0 processes; died ~Jun 4–5, `nohup`
   doesn't survive reboot). Redis Stack itself was up, holding
   51 long-term records — **all 51 are test/probe residue**
   (`itest-*`, `probe*`, `dogfood` namespaces). Zero real session
   findings had ever landed in AMS.
3. **File tier equally starved**: `findings.jsonl` held 2 entries,
   both from a `/tmp` dogfood fixture; `kv.json` empty, born Jun 9.
4. **Restarted AMS** with the prior env (recovered from
   `~/.attune/ams/server.log`: `EMBEDDING_MODEL=ollama/nomic-embed-text`,
   `GENERATION_MODEL=ollama/llama3.1:8b`,
   `REDISVL_VECTOR_DIMENSIONS=768`, port 8000; index dim 768
   verified matching). Health 200.
5. **Post-restart round-trip passes**: `stash_entry` → AMS →
   `recall_entries` returns the new finding ranked #1.
6. **Extraction quality is good**: `_extract_via_ollama` on a real
   1.2 MB transcript tail returned 5 genuinely useful findings in
   14 s (warm model) — e.g. the pip-extras-drift lesson, the
   CI-watcher SHA-keying pattern.
7. **The cached 8.0.1 Stop hook, run exactly as Claude Code runs
   it, stored ZERO entries** (exit 0, no sentinel) — reproducing
   the historical silent loss on demand.

## Root causes (three, compounding)

1. **Utilization gate miscalibrated.** The 1.2 MB transcript
   scored `estimate_utilization = 0.18` against the 0.30 default
   gate (`ATTUNE_MEMORY_STASH_MIN_UTIL`). Most real sessions never
   stash at all — this is why the store is starved despite weeks
   of sessions. (19 sentinels exist from Jun 6–10, so *some*
   sessions crossed it; most don't.)
2. **The hook's interpreter can't reach AMS.** Hooks run `python`
   → pyenv 3.10.11, which imports attune (editable, 8.3.0) but has
   **no `agent-memory-client`** — so AMS backend construction
   fails and every stash that does happen goes to the FILE tier,
   even with AMS healthy. AMS-side recall then misses them.
3. **AMS has no keep-alive and no surfaced health.** It died on
   (likely) a reboot ~Jun 4–5 and nothing noticed for a week:
   `resolve_backend`'s connectivity gate degraded recall to the
   file tier silently. The degradation is *too* graceful.

Compounding design issue: `_stash_findings` returns 0 on import or
write failure and the sentinel is written whenever findings were
non-empty — so "done" sentinels accumulate while nothing is stored.

## Fix list (small PRs, ranked)

| # | Fix | Where | Size |
|---|-----|-------|------|
| 1 | Recalibrate the utilization gate (lower default and/or fix the estimator's denominator so a 1 MB+ transcript clears it) | `plugin/hooks/session_stash.py`, `plugin/hooks/_transcript_size.py` | S |
| 2 | Surface the resolved backend + AMS reachability in `/recall` output ("file backend; AMS unreachable — N records dark") and as a SessionStart health line | recall skill, `session_recall.py` | S |
| 3 | Get `agent-memory-client` into the hook's interpreter (install into pyenv global, or have the hook prefer the project venv python when present) | env / hook shebang strategy | S |
| 4 | Keep AMS alive: launchd agent (or `brew services`-style) + document the env | ops/setup docs, optional plist | S |
| 5 | Don't write the sentinel when `written == 0` with non-empty findings; emit a stderr warning instead | `plugin/hooks/session_stash.py` | XS |

## State after this triage

- AMS running again (pid in `~/.attune/ams/server.pid`, log in
  `~/.attune/ams/server.log`); recall verified live.
- Store now contains the first real findings (from the
  instrumented hook run, session `pyenv-e2e-0611`, plus one
  `live-diagnosis-0611` probe entry) — the soak starts today.
- **Fixes 1–3 + 5 landed same day** (this PR): gate default
  0.30 → 0.05 with calibration comment; `backend_status()` +
  SessionStart health line + `/recall` backend naming; `stash.log`
  forensic trail beside the sentinels (zero-written runs flagged
  loudly, so fix 5 ships as "sentinel kept, loss logged" — the
  no-sentinel variant would re-run Ollama on every Stop turn);
  `agent-memory-client==0.14.0` installed into the hook's pyenv
  interpreter (machine-level; the version pins to the AMS 0.14.0
  server per the pairing lesson).
- **Fix 4 (AMS keep-alive) still open** — current restart is a
  `nohup` that dies on reboot; a launchd agent is the durable form.
  Mitigated meanwhile by the new health line, which makes the next
  outage visible at the first session start instead of invisible
  for a week.
- Note: marketplace-plugin users get the hook fixes on the next
  plugin release + `claude plugin update`; the locally cached
  8.0.1 hooks keep the old gate until then.
