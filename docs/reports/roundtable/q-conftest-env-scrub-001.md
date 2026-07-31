# Round table — conftest env scrub review (q-conftest-env-scrub-001)

**Thread:** `q-conftest-env-scrub-001` · **Date:** 2026-07-28 ·
**Roster:** claude, antigravity, codex · **Rounds:** 1 (halted on
convergence, D3) · **Promoted items:** #2 #4 #7 #8 (chair-approved).

## Promoted items

### 1 — This report (msg 8)

The synthesis, recorded. Thread is TTL'd (7 days); this file is the
durable record.

### 2 — Runner-level env containment (msg 2, VERIFIED)

The `clean-run` check battery inherits the developer's interactive
shell, emptying only `ANTHROPIC_API_KEY`. The conftest scrub fixes
pytest ONLY; the collaboration preflight in the same battery remains
exposed, as will every check added later, and the unnamespaced vars
(`REDIS_URL`, `TZ`, `LANG`, `HTTP(S)_PROXY`, `XDG_CONFIG_HOME`,
`GIT_*`) are untouched by a prefix-scoped fix.

**Direction:** launch the battery under an explicit allowlist and emit
the env delta as part of the seat brief, so the table can see what
environment produced the numbers it is reasoning over. Conftest then
becomes defense in depth rather than the only line.

### 3 — The dotenv inversion (msg 2, VERIFIED LATENT)

Guard the latent hole. Cheapest form: assert no dotenv file defines an
`ATTUNE_*` name, so the day someone adds one it fails loudly instead of
silently defeating the scrub.

### 5 — Lifecycle contract for `ATTUNE_*` overrides (msgs 4 + 7) — **UNRULED, chair**

> Are `ATTUNE_*` overrides contractually "read once at process
> startup", or should any library API observe changes made after
> import?

**This is promoted as an OPEN question, not a decision.** It is
upstream of the seats' disagreement: answering it either makes
antigravity's `src/` refactor correct or makes it moot, and leaves
claude's runner-level work unaffected either way. Recording it here so
it is not re-derived; the ruling is the chair's and has not been made.

## Not promoted

- **Override-contract test shape** (claude's follow-up: subprocess
  table / targeted / accept blindness) — deferred; depends on item 5.
- **`_SUITE_MANAGED_ENV` inversion to deny-all-then-set** — churn
  against a currently-passing guard; the proposing seat flagged that
  risk against its own proposal.

---

*Curated stub (local-first reports, `docs/specs/local-first-reports/`): the sections above are the
chair-promoted content. The full deliberation transcript is
machine-local at `~/.attune/reports/roundtable/q-conftest-env-scrub-001.md` and is
not distributed with the repository.*
