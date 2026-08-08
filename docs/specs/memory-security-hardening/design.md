# memory-security-hardening — design

**Status:** draft (2026-08-07) — grounded in the code investigation; decisions
ratified in [decisions.md](decisions.md). Covers R1-followup, R2, R3, R5.
**Requirements:** [requirements.md](requirements.md) · **Tasks:** [tasks.md](tasks.md)

R4 is out of scope here (owned by `memory-status-integrity`). Ordering follows
the ratified ranking; R1-followup and R2 are highest-leverage / lowest-cost and
independent of R3/R5.

---

## R1 follow-up — envelope coverage across model-context recall surfaces (D1)

**Current state.** `render_recall_for_context` is the R1 boundary. Coverage today:

| Surface | file:line | Enters model context? | Framed today |
|---|---|---|---|
| SessionStart recall | `plugin/hooks/session_recall.py:184` | yes | **yes** (wraps) |
| MCP `personal_memory_recall` | `src/attune/mcp/memory_handlers.py:344` | yes (tool result) | no — raw + stamped |
| MCP `memory_retrieve` | `src/attune/mcp/memory_handlers.py:127` | yes (tool result) | no — no provenance at all |
| `PersonalMemory.query` | `src/attune/memory/personal.py:239` | via consumers | stamped, not rendered |
| `recall_digest` widget | `src/attune/memory/recall_digest.py:127` | no (elicitation form) | flag-annotated |

**Target.** The two MCP recall tools render through the envelope before returning:
each hit's model-facing text becomes `provenance.context_block` (already stamped
for `personal_memory_recall`; `memory_retrieve` gets stamping + wrapping added).
Return the framed text in the field the client shows the model; keep structured
fields (id, score, source) as siblings for programmatic use. `PersonalMemory.query`
grows a thin `render_for_context()` helper (or documents that every in-repo
consumer must render) so no caller re-stringifies raw bodies. The digest widget
keeps flag-annotation (D1 — not a chat-channel injection).

**Behavior contract.** Fail closed: if `provenance` is unavailable, the tool
returns structured data with NO raw body echoed into the model-facing field
(mirrors the SessionStart hook's `("", [])` degradation).

---

## R2 — secret-scan at every write path (D2, D3)

**Current state.** Fail-closed secret gate present on raw stash
(`session_stash.py:326`) and curated `/remember` (`personal.py:223`) via
`DataSanitizer(secrets_detection_enabled=True)`. Gaps:

1. **Wiring bug — `short_term/facade.py:187`:** `DataSanitizer(self._base)` puts
   the base in the first positional (`pii_scrub_enabled`), so
   `secrets_detection_enabled` defaults **False**. The Redis short-term tier
   scrubs PII but does **not** scan secrets. Fix: construct with explicit
   keyword args (`DataSanitizer(pii_scrub_enabled=True, secrets_detection_enabled=True)`)
   and the correct base wiring. This is a live security hole, not a new feature.
2. **`long_term` pipelines** (`long_term_integration.py:99`, `long_term_pipelines.py`,
   `long_term.py`) construct `SecretsDetector` but the call-site on the write
   path is unconfirmed — verify it actually runs before persistence; wire if not.
3. **Hydration path** (out-of-repo `~/.attune/memory/hydrate.py`): no gate.
   Machine-gated (D6) — add a scan before it writes to Redis / regenerated cards.
4. **One-time sweep:** the ~271 curated `.md` files + `~/.attune/session_stash/findings.jsonl`.
   A new advisory sweep script (in-repo, hermetic-testable; runs against a path
   arg, defaults documented) reports detections; **rotation is manual** (D3).

**Behavior (D3).** Detected secret → refuse the write (raw drops, curated raises).
No redact-preview path. Amend requirements.md R2 text accordingly.

---

## R3 — disposable authenticated Redis + epoch-trusted recall (D4, D5)

**Current state.** No auth anywhere (local mode hard-codes `password=None`,
`redis_config.py:212`); readers bypass the central factory with ad-hoc
`from_url` (`recall_digest.py:64`, `priors.py:138`, `ops/memory_data.py:86`, …).
Recall trusts any `attune:memory:*` key — no schema/tier/digest validation on
read; `hydrated_at` is a display-only stamp (`memory_data.py:399`), never a trust
gate. AOF persistence ON + no auth in `docker-compose.yml:26` and
`.devcontainer/docker-compose.yml:24`.

**Target.**
1. **Auth + posture (machine-gated, D6):** `requirepass` (random local secret,
   stored where the hydration hook + MCP server can read it), bind loopback /
   Unix socket, `rename-command` the dangerous verbs. Disable AOF (`--appendonly no`)
   in both compose files + document the bundled attune-redis posture.
2. **Central client (in-repo):** route the ad-hoc `from_url` readers through one
   auth-aware factory so `requirepass` isn't bypassed. Enumerated in tasks.md.
3. **Epoch trust (in-repo read-side, D4/D5):** stamp a hydration epoch +
   schema-version on hydration; recall (`recall_digest`, `priors`, `memory_data`)
   serves a record only if it carries the current epoch, a known schema version,
   tier, canonical source path, and content digest — else it is ignored (not an
   error). A raw record injected directly into the keyspace fails the check.
   Because the live hydrator is out-of-repo, the read-side validation ships
   in-repo and the epoch-stamping half is machine-gated with it.
4. **Quarantine (D5):** delete the dead `auto_promote_threshold` field; document
   that promotion is human-gated only.

**Disposable-cache guarantee (D4).** File-of-record (curated `.md` + TTL JSONL)
is source of truth; a wiped/rebuilt cache re-hydrates. Accepted cost: short-term
working memory does not survive a Redis restart.

---

## R5 — extractor output hardening (D2-adjacent)

**Current state.** `plugin/hooks/session_stash.py:220` `_extract_via_ollama`
appends the transcript with no delimiter; only `_normalize` (`:311`) validates
(type coercion + 500-char truncation + max 5). No rejection of control chars,
`---`, or role-override tokens. No `confidence`/`source_refs` fields.

**Target.**
1. **Discard-on-malformed** in `_normalize` / extraction: reject a finding whose
   content contains control characters, frontmatter delimiters (`---`), or
   role-override / tool-call tokens (reuse `provenance` pattern set where it fits).
   Fail closed — a rejected finding is dropped, not truncated-and-kept.
2. **Typed schema:** parse the extractor output into a typed structure with an
   explicit `confidence` and optional `source_ref`; discard on schema mismatch.
   Keep the heuristic fallback.
3. Raw findings stay TTL-bound + visibly machine-generated (already true) and
   quarantined per R3/D5.

---

## Cross-layer & dependency order

1. **R2 wiring-bug fix** (in-repo, isolated, ships first — closes a live hole).
2. **R5 discard-on-malformed** (in-repo, isolated).
3. **R1 MCP-tool wrapping** (in-repo).
4. **R3 read-side epoch trust + central client + dead-field delete** (in-repo).
5. **R3 machine-infra** (requirepass, AOF-off, compose, `~/.attune` epoch-stamp,
   hydration secret-scan) — **gated on chair confirmation + backup (D6)**, last.
6. **R2 one-time sweep** — advisory run, rotation manual.

Each in-repo step lands with hermetic tests (no real home-dir / corpus reads —
`project_test_isolation_home_dir_leaks`). Machine-infra steps produce a receipt.

## Rollback

In-repo steps are additive/config and revert cleanly. Machine-infra: back up the
Redis config + `~/.attune` scripts before editing; `requirepass`/AOF changes are
config toggles; a leaked secret found by the sweep is remediated by **rotation**,
which a revert does not undo.
