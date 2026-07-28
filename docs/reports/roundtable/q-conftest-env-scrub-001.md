# Round table — conftest env scrub review (q-conftest-env-scrub-001)

**Thread:** `q-conftest-env-scrub-001` · **Date:** 2026-07-28 ·
**Roster:** claude, antigravity, codex · **Rounds:** 1 (halted on
convergence, D3) · **Promoted items:** #2 #4 #7 #8 (chair-approved).

## Question (chair)

Today's session shipped a test-isolation fix (`tests/conftest.py`
scrubs ambient `ATTUNE_*` at conftest import time and per test, plus a
drift guard) after a `clean-run` routine reported
`keyless-unit-suite: FAIL` on a healthy tree. Is scrubbing env at
conftest import time the right fix, or does it hide a design problem in
reading env at import time? What breaks that we haven't considered?

## Unanimous (3/3, unprompted)

- **Keep the scrub.** No seat argued to revert. All three accept that a
  fixture cannot undo values already captured by module globals, so
  import-time scrubbing is NECESSARY given current module semantics.
- **It is not the complete fix** — a guardrail over an unfixed `src/`
  defect.
- **Import-time env resolution (`release_models.MODEL_CONFIG`) is a
  real design problem**, not merely a testing inconvenience.
- **Hermeticity costs override coverage.** All three named this without
  being asked to weigh it: the suite can no longer observe the override
  paths at all, and all three proposed explicit override/contract tests
  as the replacement. The strongest signal in the round — a work item
  nobody was prompted toward.

The sharpest framing (claude seat): *the import-order defect that
FORCED the import-time scrub is now the exact bug the suite can never
catch again.* Before the scrub, a developer with the var set gave
accidental coverage of that read.

## Split — where the PRIMARY fix belongs

| Seat | Primary fix | Reasoning |
|---|---|---|
| claude | the RUNNER (env allowlist) | generalizes to non-`ATTUNE_` vars AND to non-pytest checks; explicitly de-prioritizes its own `src/` suggestion if budget is one unit |
| antigravity | `src/` lazy evaluation | import-time resolution is an anti-pattern; the whitelist disappears once `src/` is lazy |
| codex | keep scrub + contract tests; `src/` verdict CONDITIONAL | `MODEL_CONFIG` is a defect only if overrides are meant to be observable after import — a lifecycle question, not a code question |

Codex is the only seat that refuses to rule on `src/` without first
settling the lifecycle contract. That reframing converts a code-review
disagreement into one chair decision.

## Moderator verification (probes run against the real system)

Seat positions are reasoning, not receipts (R1 — members never touch
shell). The moderator probed the three checkable claims:

| Claim (seat) | Verdict |
|---|---|
| The check battery inherits the dev shell (claude, Defect 1) | **CONFIRMED** — `routine.py` `run_command`'s check branch is `env = {**os.environ, "ANTHROPIC_API_KEY": ""}`; everything else passes through, so `REDIS_URL` / `TZ` / `LANG` / proxies all reach pytest |
| `load_dotenv` inversion opens a hole (claude) | **CONFIRMED AS A LIVE MECHANISM, currently LATENT** — see below |
| Repo-root `conftest.py` loads first, defeating Part 1 (claude) | **REFUTED** — no repo-root `conftest.py` exists. The entry-point-plugin half is unverified |

### The dotenv inversion, in detail

`load_dotenv()` runs at MODULE level in `src/attune/workflows/base.py:34`,
and both `~/attune-ai/.env` and `.env.local` exist. Dotenv only injects
names that do not already EXIST — so by DELETING the vars, the
import-time scrub makes those files injectable where a shell export
previously shadowed them. The scrub can therefore OPEN a hole rather
than close one.

**Currently latent:** no dotenv file defines any `ATTUNE_*` var today.
A single `ATTUNE_*` line added to `.env` would defeat the import-time
scrub for import-time consumers. This is the same shape as the
documented `env -u` vs `KEY=""` lesson, pointed the other direction.

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
