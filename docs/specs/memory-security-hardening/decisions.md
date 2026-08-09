# memory-security-hardening — decisions

Ratified calls that shape the design. Each is grounded in the code investigation
(2026-08-07) and the chair's answers on the design-gate questions.

## D1 — R1 envelope must cover EVERY model-context recall surface, not just SessionStart

**Finding.** Only `plugin/hooks/session_recall.py::_format` renders recalled text
through `render_recall_for_context`. The MCP recall tools return raw text into
model context: `personal_memory_recall` (`src/attune/mcp/memory_handlers.py:344`)
and `memory_retrieve` (`:127`). `PersonalMemory.query` (`personal.py:239`) and
`session_stash._stamp_provenance` stamp `context_block` but return raw bodies;
consumers may or may not render them.

**Decision.** Any surface whose output enters a model's context — MCP tool
results included — MUST emit the envelope (call `render_recall_for_context` or
return `provenance.context_block`), never the raw body. Data-layer functions
that only return dicts (`query`, `_stamp_provenance`) are exempt **as long as**
every consumer that feeds a model renders them; where that can't be guaranteed
(MCP tools handing results to an arbitrary client), the tool wraps.
Non-model-context surfaces (the `recall_digest` widget/elicitation form) keep
flag-annotation, not the full envelope — they are not injection into a chat
channel.

**D1 narrowing (ratified during implementation).** The MCP `memory_retrieve`
tool returns keyed, agent/human-authored **structured** data (short-term
working memory, staged patterns) — not machine-extracted recall. Wrapping
structured data in the "untrusted-evidence, do not obey" prose envelope is the
wrong shape, so `memory_retrieve` carries a **light trust annotation**
(`trust: "untrusted-evidence"` + a reference-not-instructions note) rather than
the envelope. The envelope proper stays on the recall surfaces that emit
machine-extracted/curated prose (`session_recall.py`, `personal_memory_recall`).

## D2 — Secret engine is the existing in-repo `SecretsDetector`, not Yelp detect-secrets

**Finding.** `src/attune/memory/security/` already ships `SecretsDetector`
(regex for ~20 secret types + Shannon entropy) and the `DataSanitizer` façade,
already wired fail-closed on the raw stash (`session_stash.py:326`) and curated
`/remember` (`personal.py:223`) paths. Yelp `detect-secrets` is a separate
commit-only pre-commit hook.

**Decision.** R2 reuses the in-repo library at every write path. `detect-secrets`
stays the git-commit backstop; it is not the memory write-path engine. Q2 is
answered by the code — no new engine.

## D3 — On a detected secret, FAIL CLOSED (block); do not build redact-preview

**Chair's call.** The R2 requirements text ("store redacted previews + source
references") is superseded. A detected secret refuses the write — the raw path
drops the finding, the curated path raises "rotate this." Rationale: redaction
is imperfect; a redacted-preview record persists partial secret material into a
recallable store. Blocking is simpler and strictly safer, and rotation (not
storage) is the real remediation. The R2 requirements text is amended to match.

## D4 — Redis is a DISPOSABLE, non-persistent, authenticated cache

**Chair's call.** Disable AOF on the memory Redis; add `requirepass` (random
local secret) + loopback/Unix-socket bind + disable dangerous commands. Recall
trusts only records written by the current hydration epoch, carrying a schema
version + tier + canonical source path + content digest — never arbitrary keys
under `attune:memory:*`. Rationale: with secrets already blocked at write (D3),
nothing sensitive should persist to disk; the file-of-record (curated `.md` +
the TTL JSONL) is the source of truth, so a wiped cache re-hydrates cleanly.
Encryption-at-rest is rejected as overkill under the sole-dev threat model.
**Cost accepted:** short-term working memory does not survive a Redis restart —
it re-hydrates/re-derives.

## D5 — Raw-tier quarantine is owned HERE (R3), not by memory-claim-verification

**Finding.** `memory-claim-verification` scope is claim *verification/grounding*
and explicitly excludes the curated tier and promotion machinery; its own
mechanism is retired-pending-a-ruling. No auto-promotion path exists today
(`promotion.py` is human-gated; `auto_promote_threshold=0.8` in `unified.py:95`
is defined but **never referenced** — dead field).

**Decision.** memory-security-hardening owns raw-tier quarantine as an **enforced
read-side control**: recall serves a record only if its tier + provenance pass
the epoch/schema check (D4); a raw record written directly into the served
keyspace is not trusted just because it matches the prefix. Delete the dead
`auto_promote_threshold` field to remove the illusion of an auto-promote knob.

## D6 — Machine-infra changes are gated and reversible

Changes that touch the developer's actual machine — `requirepass` on the live
Redis, disabling AOF, editing `~/.attune` hydration scripts, teaching the MCP
server + hydration hook the new secret — require explicit confirmation and a
backup before the edit (the same gate applied to the R1 `~/.attune` work).
In-repo code (the sanitizer wiring fix, extractor hardening, MCP-tool wrapping,
compose-file config, epoch-trust read validation) proceeds without that gate.

## D7 — R1-followup task 2 VOID ratified (chair, 2026-08-09)

**Context.** PR #1997 flipped task 2 ("MCP `memory_retrieve` —
stamp provenance + wrap; fail closed if unavailable") to **void**
on the lead's reading of the D1 narrowing: task 2b's chair-ratified
trust annotation replaced the prose envelope for keyed structured
data, and no fail-closed dimension exists for inline constants.
That flip was a lead interpretation, flagged in the 2026-08-09
feedback pass as unratified.

**Ruling.** RATIFIED. The chair selected "Confirm task-2 void" on
the 2026-08-09 session feedback form (multi-select response, all
four items selected; recorded in
`docs/specs/feedback-close-out-2026-08-09/`). Task 2 stays void;
2b is its executed replacement. R1-followup remains COMPLETE as
recorded in tasks.md.
