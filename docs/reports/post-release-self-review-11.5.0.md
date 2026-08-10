# Post-release self-review — 11.5.0 (2026-08-08)

Step-16 runs, dashboard-launched on the shipped tree (main at
v11.5.0, merge SHA 5cf38b3e7):

- **bug-predict** run `a28a402d4920` — 42/100 (moderate), $3.26, 367s.
- **code-review** run `031085bf659a` — 74/100, $5.64, 355s; full
  26-finding report captured to the session scratchpad and mirrored
  below in triaged form.

Truncation note (known class): bug-predict's "one concrete latent
bug" was never named in the stream or the persisted record
(suggestions/sections empty, 19 lines total) — unrecoverable,
recorded honestly. code-review DID persist its 5 sections.

## Triage — verified act-now candidates (small, safe, high value)

Each verified against the tree before classification.

1. **[Medium/security] hooks/executor.py:150 — argv/flag injection.
   CONFIRMED**: `command.format(**context)` runs BEFORE
   `shlex.split`, so a context value containing spaces becomes
   extra argv tokens (no shell, but flag injection is real).
   Fix: tokenize first, substitute per-token.
2. **[Medium/security] hooks/executor.py:255 — webhook DNS-rebinding
   TOCTOU. CONFIRMED**: `_validate_webhook_url` validates by
   resolved IP, then aiohttp re-resolves at connect;
   `resolve_pinned_ip` exists and is unused here. Fix: connect to
   the pinned IP.
3. **[Medium/quality] memory/config.py:55 — URL helpers typed
   `object`. CONFIRMED** (introduced by rct-1, mine): callers
   access `.hostname/.password` on `object`, defeating type
   checking at the credential seam. Fix: `urllib.parse.ParseResult`.
4. **[Low/quality] memory/redis_auto_detect.py:32 — module cache
   mutated without a lock. CONFIRMED**: `_cached_result/_cached_at`
   bare; features.py's warn-once set (rct-2) is the cited locked
   analog. Trivial fix.
5. **[Low/security] ops/runner.py:645 — run_id not validated against
   `_RUN_ID_RE` before filesystem lookup** (sibling loaders do).
   Spot-checked plausible; verify inline when fixing.

## Already tracked — do NOT double-file

- **Redis config duplication/drift** (High quality
  memory/config.py:263 + High architecture redis_config.py:164 +
  Low redis_config.py:1): this is EXACTLY redis-config-truth
  **rct-4** (15-file consumer migration, drift guard). The review
  independently endorses the ladder's next rung. No new tracking.

## Structural — needs its own spec/chair read (not act-now)

- **[High] config/__init__.py:28 — config.py shadowed by config/
  package, loaded via `spec_from_file_location` + `exec_module`.
  CONFIRMED verbatim**: AttuneConfig's module identity is
  `attune_config_legacy` (isinstance/pickle/registry hazard).
  Fix shape per review: rename to config/legacy.py + normal import.
- **[High] core→ops upward dependency** (ops/config.py:108,
  `attune_home()` imported by core) — extract attune/paths.py.
- **[High] BaseWorkflow name clash. CONFIRMED**: plugins/base.py:33
  (ABC) vs workflows/base.py:169 (14-mixin) — rename the plugin
  variant.
- **[Medium] Empathy vestiges on live surfaces** (EmpathyMCPServer,
  empathy_level) — brand-retirement follow-through; wide blast
  radius (tests fixture-typed), needs its own PR.
- **[Medium] god files** (ops/data.py 1862 LOC, agent_sdk_adapter
  1774, mcp/server 1585) + 14-mixin BaseWorkflow + config sprawl —
  refactor-plan fodder, matches bug-predict's hotspot cluster 3.

## Performance cluster (act-now-adjacent, one coherent PR)

- **[High ×2] ops/help_data.py:185/:340** — list_features computed
  3× per help-home request (grep-confirmed 3 call sites); nested
  get_template N+1 file reads.
- **[Medium] ops/data.py:862** — usage.jsonl fully re-parsed per
  dashboard request. **[Medium] pattern_review.py:289** — per-key
  Redis retrieve loop (MGET/pipeline; #1982 shipped the same fix
  class elsewhere). **[Medium] dashboard.py:279** — sync I/O on the
  event loop.
- [Low ×2] simple_storage list_keys full-parse;
  compaction.load_state_by_session linear scan.

## Dismissed / advisory

- security_guard.py regex bypassability (Low): stated purpose IS
  advisory defense-in-depth; not a boundary. No action.
- 0.0.0.0 bind info-disclosure (Low): default is loopback;
  warn-on-bind is a nice-to-have, fold into act-now PR if touched.
- tests/memory vs tests/unit/memory duplication (Medium): real but
  janitorial; fold into test-quality program, not urgent.
- models↔workflows import cycle behind 52 inline imports (Low):
  backlog; refactor-plan input.

## bug-predict cross-read

Hotspot clusters align with code-review: (1) SDK/subprocess
boundary, (2) Redis config path (= rct-4), (3) god files. No
independent actionable finding beyond the unnamed (lost) latent
bug.

## Recommendation

Two PRs mirror the #1982 precedent: (a) **act-now security+quality**
(items 1–5 above, ~small diff each, D11 lane required — security
surface); (b) **help/dashboard perf** (the High N+1 pair + optional
Mediums). Structural items go to a refactor-plan run or a spec;
rct-4 proceeds as planned and subsumes the Redis-config findings.
