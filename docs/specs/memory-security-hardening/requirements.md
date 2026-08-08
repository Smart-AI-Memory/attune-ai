# memory-security-hardening

**Status:** draft (2026-08-07 — requirements; from round-table deliberation).
R1 shipped (PR #1979); R2/R3/R5 ladders drafted — see [tasks.md](tasks.md).
**Owner:** Patrick (chair)
**Origin:** Round table `q-memory-system-deep-dive-001` (2026-08-07,
Claude + Codex + Antigravity, 2 rounds). The security lens produced a
**unanimous** 4-rank attack surface with no dissent. Full transcript:
`~/.attune/reports/roundtable/q-memory-system-deep-dive-001.md`
(machine-local, untracked).

**Relationship to other specs:** independent of `memory-status-integrity`
(the staleness/P2 work) — these mitigations do not touch the ranking
design. Overlaps `memory-claim-verification` only at the raw-tier
quarantine boundary (R3 below).

---

## Problem

The attune memory system is a persistence-and-recall loop that feeds
prior-session content back into future LLM context. Every property that
makes it useful — durability, always-on injection, cross-session recall —
is also an attack surface. Three seats deliberated it independently and
converged on the same ranking for a **sole-developer machine** (not
multi-tenant: the threat model is untrusted *code and content*, not other
users).

The finding that reframes everything below: **on a sole-dev box the
dangerous boundary is not "who can reach Redis" — it is any process,
dependency, repository file, or session that can influence what gets
written to memory, because recall grants persisted text standing
authority through repeated re-injection.**

---

## Ranked attack surface

### R1 — Memory-as-prompt-injection (TOP risk, unanimous #1)

**Mechanism.** A session reads untrusted content in the normal course of
work — a GitHub issue, a PR comment, a web page, third-party dependency
docs. The raw-tier `session_stash` extractor (local `llama3.1:8b`)
summarises whatever the transcript contains into ≤5 findings with **zero
verification**. A payload phrased as a finding ("important: always run X
before committing") is stored, and later recall **re-injects it into
active context**, where it reads as a standing instruction with tool
access behind it. Injection stops being a single bad turn and becomes
durable.

The curated tier is narrower — it is linted on write — but
`memory_lint.py` checks **format, not content**: attacker-shaped prose
passes.

**Mitigation (cheapest, ratified by all seats).** A provenance-labelled
envelope at **every recall surface**:

- Recalled material renders as quoted, source-attributed **untrusted
  evidence — explicitly "NOT instructions"** — never as bare prose that
  blends into the system/assistant channel.
- Each recalled item carries its tier, source (file/session), and author
  class (human-curated vs machine-extracted).
- **Tool execution is never authorized by recalled text alone.**
- A cheap instruction-pattern lint (imperatives addressed to the
  assistant, "ignore previous", tool-invocation strings, role-delimiter
  tokens like `<|im_start|>` / `system:`) that **flags, not blocks**, on
  writes.

**Ratified caveat (self-flagged by two seats, do not lose this):**
delimiters are the *weakest known* defense against prompt injection. A
payload engineered to survive "this is data" wrappers defeats the
envelope outright. The envelope is **necessary, not sufficient** — it
must be paired with **raw-tier quarantine** (R3): raw findings never
auto-promote into always-loaded or curated surfaces without human
promotion.

**Implementation status — DONE (PR #1979, branch `feat/memory-security-r1r2`).**
`attune.memory.provenance` renders the untrusted-evidence envelope +
instruction-flag lint; `session_stash` stamps every recall dict with
`provenance.context_block`; and the **live injection point** — the in-repo
SessionStart hook `plugin/hooks/session_recall.py::_format` — now renders
through `render_recall_for_context` (fails closed if the module is absent).
This closes the round-table's **BLOCK-1 residual**: the review had
misattributed the injection to an out-of-repo personal hook
(`~/.attune/memory/session_hydrate.py`), which in fact injects no recall
text. Verified end-to-end — an `"ignore all previous instructions…"` finding
reaches context wrapped + flagged, content preserved. Per the ratified caveat
above, this is necessary-not-sufficient and still depends on raw-tier
quarantine (R3, open).

### R2 — Secret accumulation (accidental, high blast radius)

**Mechanism.** The extractor eats full transcripts as free prose;
transcripts contain API keys, tokens, private endpoints, copied incident
data. These land in **plaintext markdown + an unauthenticated Redis copy
+ a 30-day JSONL** — and in generated recall cards and backups. The
corpus's own history records the exposure class (a real `sk-ant` value
surfaced in a console during earlier work). Retention multiplies the
exposure across every copy.

**Mitigation.** Secret detection **before every write** — the
`session_stash` pipeline, the curated `/remember` path, the short-term
Redis tier, **and** the hydration path — not merely at git commit (the
one place it was checked before this spec). On detection, **fail closed:
refuse the write** (raw path drops the finding; curated path raises so
the user rotates). Redacted-preview storage is **rejected** (design D3) —
imperfect redaction would persist partial secret material into a
recallable store. A one-time corpus-wide sweep of the ~271 curated files
+ the JSONL. **Rotate anything found — deletion is insufficient.** Redis
is made non-persistent (design D4), so the hydrated corpus no longer sits
in an AOF on disk.

_Status: engine + raw/curated gates shipped; short-term wiring + hydration
scan + sweep pending — see [tasks.md](tasks.md) R2. Secret engine is the
in-repo `SecretsDetector` (D2)._

### R3 — Unauthenticated localhost Redis + hydration path

**Mechanism.** Redis on localhost with no auth lets **any local
process** — an npm `postinstall`, a pip build hook, a compromised
dependency — read the entire hydrated corpus (compounding R2) or **write
`attune:memory:*` directly**, poisoning recall while bypassing the
linter until the next hydration. A sole-dev machine runs more untrusted
code than most servers.

**Mitigation.**
- `requirepass` with a random local secret; bind to loopback or a Unix
  socket; disable dangerous commands.
- **Treat Redis as a disposable cache**, not a store of record: full
  re-hydrate at every SessionStart from allowlisted roots, so the
  file-of-record always wins and recall **never trusts keys older than
  the current hydration epoch**. Consumers trust only hydrated records
  carrying a schema version, tier, canonical source path, and content
  digest — not arbitrary keys under the prefix.

### R4 — Forgeable mtime / updated_at (reliability, not security)

**Mechanism.** All seats agreed this is **not** a leading *security*
risk — an attacker who can `touch` files already owns the box. It is a
**reliability** hole: git checkouts, sync tools, and bulk edits rewrite
mtimes routinely, so the staleness signal is already silently wrong in
both directions.

**Mitigation.** Fixed by `memory-status-integrity` P2's `verified:`
field (human-set, content-tracked, mtime ignored for ranking). A git
commit timestamp is a better fallback than mtime where a human date is
absent. **Cross-reference, not owned here** — listed only so the
security review does not mistake it for an attack vector.

### R5 — The 8B extractor as a confused deputy

**Mechanism.** `llama3.1:8b` converts adversarial session/repo text into
durable assertions without understanding provenance or truth. Its "≤5
findings" cap bounds *volume*, not *harm*.

**Mitigation.** Constrain the extractor to a **strict typed-JSON schema**
with source references and explicit confidence; **discard** any output
containing control characters, frontmatter delimiters (`---`), or
role-override syntax. Keep raw findings quarantined, TTL-bound, and
visibly machine-generated. This dovetails with `memory-claim-verification`
(fail-closed on *promotion*; ordinary recall may fail open by omitting
unresolved raw claims).

---

## Scope

**In scope:** the recall-render envelope (R1), secret-scan-before-write
+ one-time sweep (R2), Redis auth + disposable-cache posture (R3),
extractor output schema (R5).

**Out of scope:** the P2 ranking/verdict design (owned by
`memory-status-integrity`); typed-ref resolution against git/gh (owned
by `memory-claim-verification`); the mtime fix (R4, cross-referenced).

## Priority note (moderator read, ratified by the chair's promotion)

R1's envelope and R2's secret-scan-before-write are **the two
highest-leverage, lowest-cost items in the entire deliberation** and are
**independent of the P2 design** — they can ship immediately without
waiting on any ranking decision.

## Open questions

1. Envelope format: a single rendering contract shared by
   `personal.py`, `recall_digest`, and the hydration line, or
   per-surface? (The P1 work already proved a shared pure formatter is
   viable — `format_age_annotation`.)
2. Secret-scan engine: reuse the repo's existing `detect-secrets`
   pre-commit config, or a lighter regex+entropy pass tuned for the
   memory write path?
3. Does the raw tier warrant encryption-at-rest, or is
   redact-before-write + TTL sufficient given the sole-dev threat model?
