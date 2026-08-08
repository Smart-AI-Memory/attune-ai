# memory-security-hardening — tasks

**Status:** active (2026-08-07) — design gate passed; decisions ratified.
R1 shipped (PR #1979) but the envelope does NOT cover all recall surfaces
(R1-followup below). Full pass in flight: R1-followup + R2 + R3 + R5.
**Requirements:** [requirements.md](requirements.md) · **Design:** [design.md](design.md)
· **Decisions:** [decisions.md](decisions.md)

Grounded in the code investigation (2026-08-07). Ordered by the design's
dependency order — in-repo, low-risk items first; machine-infra last (gated).
`machine-gated` = requires chair confirmation + backup before the edit (D6).

## R1 — recall-render envelope — SHIPPED (PR #1979)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | `provenance` renderer + CONSUMER CONTRACT + lint | done | |
| 2 | `session_stash` stamps `context_block` on recall | done | |
| 3 | Live SessionStart injector renders through the envelope | done | `session_recall.py::_format` |
| 4 | Tests + payload verification | done | |

## R1-followup — envelope coverage on the other model-context surfaces (D1)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | MCP `personal_memory_recall` returns framed `context`; bare summary/excerpt stripped from results | attune-ai | done | `memory_handlers.py:344`; fails closed if provenance absent |
| 2 | MCP `memory_retrieve` — stamp provenance + wrap; fail closed if unavailable | attune-ai | pending | `memory_handlers.py:127`; no provenance today |
| 3 | `PersonalMemory.query` — `render_for_context()` helper (or documented consumer contract) so no caller re-stringifies | attune-ai | pending | `personal.py:239` |
| 4 | Tests: each surface frames a payload, content preserved, fails closed | attune-ai | pending | hermetic |

## R2 — secret-scan at every write path (D2, D3) — ~2/3 SHIPPED

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Raw stash gate | attune-ai | done | `session_stash.py:326`, fail-closed |
| 2 | Curated `/remember` gate | attune-ai | done | `personal.py:223`, raises "rotate" |
| 3 | **Fix wiring bug**: short-term Redis tier scans secrets (was silently OFF) | attune-ai | done | `short_term/facade.py:187` — explicit kwargs; regression test added |
| 4 | Verify `long_term` pipelines actually invoke `SecretsDetector` on the write path; wire if not | attune-ai | pending | `long_term_integration.py:99` et al. |
| 5 | Amend requirements.md R2 text: fail-closed block, drop "redacted previews" (D3) | docs | pending | |
| 6 | Hydration-path secret scan before write to Redis / cards | external | pending | **machine-gated** — `~/.attune/memory/hydrate.py` |
| 7 | One-time sweep: ~271 curated `.md` + `findings.jsonl`; advisory, exit 0 | receipt | pending | in-repo script, hermetic-testable; **rotation manual** |

## R3 — disposable authenticated Redis + epoch-trusted recall (D4, D5)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Central auth-aware Redis client; route ad-hoc `from_url` readers through it | attune-ai | pending | `recall_digest.py:64`, `priors.py:138`, `ops/memory_data.py:86`, `ops/collab_data.py:101` |
| 2 | Read-side epoch/schema trust: recall serves a record only with current epoch + schema version + tier + canonical source path + content digest | attune-ai | pending | else ignore (not error); a raw key injected into the prefix fails the check |
| 3 | Delete dead `auto_promote_threshold` field; document human-gated promotion only (D5) | attune-ai | pending | `unified.py:95` — defined, never referenced |
| 4 | Disable AOF in both compose files (`--appendonly no`) | attune-ai | pending | `docker-compose.yml:26`, `.devcontainer/docker-compose.yml:24` |
| 5 | `requirepass` (random local secret) + loopback/socket bind + `rename-command` dangerous verbs | infra | pending | **machine-gated** — hook + MCP server must learn the secret |
| 6 | Epoch-stamp on hydration (writer half) | external | pending | **machine-gated** — out-of-repo hydrator |
| 7 | Tests: recall rejects a record missing epoch/schema/digest; accepts a valid one | attune-ai | pending | hermetic, fakeredis or stubbed reader |

## R4 — forgeable mtime — NOT owned here

Reliability, owned by `memory-status-integrity` P2. No tasks. Listed so the
security review doesn't mistake it for an attack vector.

## R5 — extractor output hardening (D2-adjacent)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Discard-on-malformed in extraction/`_normalize`: reject content with control chars, `---`, role-override/tool-call tokens (drop, not truncate) | attune-ai | done | `plugin/hooks/session_stash.py` `_is_malformed`; keeps injection prose for R1 recall-flagging |
| 2 | Typed-schema parse with explicit `confidence` + optional `source_ref`; discard on mismatch; keep heuristic fallback | attune-ai | pending | `_extract_via_ollama:220` |
| 3 | Raw findings stay TTL-bound + visibly machine-generated | attune-ai | done | already true |

## Testing strategy

Unit tests only, all hermetic — pure functions + `importlib`-loaded hooks, no
live Ollama/Redis/backend, no real home-dir or corpus reads
(`project_test_isolation_home_dir_leaks`). Payload tests assert BOTH: content
preserved AND framed/flagged (a wrapper that drops content fails as loudly as
one that doesn't wrap). The ~271-file corpus is a PR receipt (R2 task 7), never
CI. Redis read-trust tests use a stubbed/fake reader, not a live socket.

## Rollback plan

- **In-repo (R1-followup, R2#3-4, R3#1-4/7, R5):** additive/config; revert
  cleanly. Guarded imports already degrade to safe defaults.
- **Machine-gated (R2#6, R3#5-6):** back up the Redis config + `~/.attune`
  scripts before editing; `requirepass`/AOF are config toggles.
- **Secrets found by the sweep (R2#7):** remediated by **rotation** — a revert
  does not un-expose a leaked key.

## Design questions — RESOLVED (see decisions.md)

1. Envelope coverage → D1 (all model-context surfaces, incl. MCP tools).
2. Secret-scan engine → D2 (in-repo `SecretsDetector`).
3. Secret behavior → D3 (fail-closed block, no redact-preview).
4. Persistence/encryption → D4 (disposable non-persistent + auth, no encrypt).
5. Quarantine ownership → D5 (owned here).
