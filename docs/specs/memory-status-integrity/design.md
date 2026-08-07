# memory-status-integrity — design

**Status:** draft (2026-08-07) — P1 implemented; not yet reviewed by the
chair
**Requirements:** [requirements.md](requirements.md) — R1–R6
**Decisions:** [decisions.md](decisions.md) — D1 (label, never suppress),
D2, D3

Full ladder below; **P1 is the shippable unit** and is specified to
implementation depth. P2/P3 are specified to the depth needed to prove
P1 doesn't paint them into a corner.

---

## Architecture

Per D3, the mechanism is a path-parameterized library over "a directory
of frontmattered markdown memories," with both corpora as callers.

```
                    ┌─────────────────────────────────┐
                    │ attune.memory.curated_audit     │
                    │  scan_corpus / audit / annotate │
                    └───────────────┬─────────────────┘
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
     ~/.claude/**/memory/   ~/.attune/memory/   scripts/audit_
        (266 files,            (16 files,       curated_memory.py
     personal hook calls in)  attune-shipped)      (CLI / receipt)
```

No corpus path is hardcoded in the library. Callers supply roots. This
is what lets the same logic serve a product store and a personal corpus
that lives outside every repo.

---

## The ranking model — the one non-obvious part

D1 established that **age is anti-correlated with wrongness**: the
oldest memories are `feedback` and `user`, which are settled and stable,
while the memories that actually rotted were `project_*`.

That finding constrains ranking as well as suppression. Ranking review
attention by age alone would repeat the same sign error one notch
weaker: it would march a reviewer through 30 correct process rules
before reaching the one stale CI claim.

**Risk is age scaled by the volatility of the memory's type.** Type is
already a required frontmatter field, so this costs nothing to compute.

| `type` | Volatility | Rationale |
|---|---:|---|
| `project` | 1.00 | asserts mutable state — CI status, PR state, in-flight work |
| `reference` | 0.60 | external resources drift without local signal |
| `lesson` | 0.40 | technical findings; decay as the code moves |
| `feedback` | 0.15 | process and relationship rules; settled by nature |
| `user` | 0.10 | profile; near-static |

```
risk = unverified_age_days × volatility(type)
```

Worked against the real cases:

| Memory | Age | Type | Risk |
|---|---:|---|---:|
| `project_pip_audit_broken` | ~56d | project | **56.0** |
| oldest `feedback_*` files | ~66d | feedback | 9.9 |
| `project_rag_gate_corpus_stale` | ~0d (hours) | project | **0.0** |

This produces the acceptance outcome directly: the pip-audit case ranks
top, the 2026-06-02 `feedback` bulk ranks low despite being *older*, and
the rag-gate case is not flagged at all — which is the boundary the
acceptance test pins.

Weights are a table constant, not a tuned model. Changing them is a
decision.

---

## P1 — display unverified-age + advisory sweep

Scope: R2, R4, R5, and the staleness half of R6. No schema change, no
writes to any corpus.

### Module: `src/attune/memory/curated_audit.py`

```python
@dataclass(frozen=True)
class CuratedMemory:
    path: Path
    name: str | None
    description: str | None
    mem_type: str | None              # user|feedback|project|reference
    verified: date | None             # P2 field; None until P2 ships
    mtime_date: date
    unknown_keys: tuple[str, ...]     # schema violations, e.g. node_type
    links: tuple[str, ...]            # [[slug]]
    deferred_links: tuple[str, ...]   # [[?slug]] — legal unresolved form


def scan_corpus(roots: Iterable[Path]) -> list[CuratedMemory]
def unverified_age_days(mem: CuratedMemory, today: date) -> int
def risk_score(mem: CuratedMemory, today: date) -> float
def audit(memories, index: CorpusIndex) -> AuditReport
def format_age_annotation(days: int) -> str      # "⟨61 days unverified⟩"
```

`AuditReport` carries: `ranked` (desc by risk), `schema_violations`,
`broken_links`, `orphans` (file with no `MEMORY.md` pointer),
`dangling_pointers` (pointer with no file).

### The mtime stopgap, stated honestly

Until P2 lands `verified:`, `unverified_age_days` falls back to file
mtime. **mtime is a known-bad proxy** — it is the exact defect the
principle section of the requirements names, and it under-reports risk
for the 63 bulk-migrated files whose mtime records a reformat rather
than a confirmation.

P1 ships it anyway because a wrong-in-one-direction signal beats no
signal, and the direction is safe: mtime makes memories look *fresher*
than they are, so P1 under-warns rather than over-warns. The fallback is
a single function with an explicit `# P2: prefer mem.verified` marker,
and the report header states which basis it used. No caller branches on
it.

### Surfaces (R2)

| Surface | Change | Delivered |
|---|---|---|
| `personal.py` recall | append annotation to each returned entry | #1975 |
| `recall_digest.py` | age suffix on digest cards, from the node's `updated_at` (Redis nodes carry no file path) | review follow-up |
| SessionStart hydration line | count of memories above a risk floor | **external** — see below |
| sweep CLI | full ranked report | #1975 |

Annotation is a pure function of `(days)`, so a surface that renders
plain text and one that renders HTML share the same signal.

**Hydration-line status (recorded at the 2026-08-07 review):** the
`[memory-hydrate]` emitter is `~/.attune/memory/session_hydrate.py` in
the attune-agent-memory checkout — personal infra, not tracked in this
repo (its fail-open test, `tests/unit/memory/test_session_hydrate_fail_open.py`,
documents exactly this split and runs the real script only where it
exists). The repo therefore ships the capability, not the wiring: the
hook's summary line can add staleness with
`attune.memory.curated_audit.format_age_annotation` over each node's
`updated_at`, the same way `recall_digest._age_suffix` does. Wiring it
is a one-line change in the attune-agent-memory repo, deliberately not
made from here — one layer per commit applies across repos.

### CLI: `scripts/audit_curated_memory.py`

Follows the existing `audit_*.py` convention. `--roots` (repeatable),
`--json`, `--top N`. Exit 0 always in P1 — advisory, never a gate.
Turning it into a gate is a P3 decision that needs the review loop
working first.

### Tests

Hermetic, `tmp_path` only. Real-corpus assertions in CI would violate
the home-directory isolation guard
(`project_test_isolation_home_dir_leaks`), and the 266-file corpus is a
**receipt**, not a fixture.

Golden set pins both directions, per requirements § Acceptance:

| Fixture | Assertion |
|---|---|
| stale `project` memory (56d) | ranks first |
| bulk `feedback` memories (66d) | rank below it despite greater age |
| hours-old `project` memory | risk ≈ 0, absent from the flagged set |
| file with `node_type:` | reported as a schema violation |
| `[[?slug]]` | accepted, not reported as broken |
| corpus after sweep | byte-identical (hash before/after) |

The third row is the D1 boundary marker: if a later change starts
machine-verifying or age-expiring curated claims to catch the hours-old
case, this test fails.

---

## P2 — the `verified:` field and the verdict loop

R1 and R3. Per D2 this is one file (`~/.claude/hooks/memory_lint.py`)
plus its co-located test, not a cross-repo closure.

- Schema gains an optional `verified: <ISO date>`. Absent reads as
  "never verified" — the honest default for all 266 existing files, and
  backward compatible by construction.
- `unverified_age_days` prefers `verified:`, falls back to mtime for
  files that predate it.
- Verdicts (`keep` / `wrong` / `sharper`) are recorded per R3. `keep` is
  the load-bearing one: it is the only way a true-but-old memory becomes
  fresh without an edit.
- `wrong` deletes the file **and** its `MEMORY.md` pointer atomically —
  the existing atomic-write rule already requires the pair to move
  together.

P1's report is what makes P2's review loop finite: without ranking, a
verdict loop over 266 files is a wall, which D6 warns drowns the loop.

---

## P3 — recall-frequency ranking

Full R6. `risk = age × volatility × recall_frequency`. Requires recall
telemetry that may not exist yet; **measure before building**, per the
same discipline that retired R3 in the sibling spec.

A memory nothing ever recalls is near-zero risk however stale. This is
the term that converts the report from "what is old" to "what is
actually being served to sessions," and it is the last piece needed
before the sweep could reasonably become a gate.

---

## Rollback

P1 is additive: a new module, a new script, and annotation strings on
existing surfaces. Rollback is reverting the commit — no migration, no
schema change, no state to unwind. The corpus is never written to, so
there is nothing to restore.

The one exception is outside this repo and outside P1's rollback story:
the authorized one-off normalization of 7 schema-violating files in the
live corpus (2026-08-07). That is backed up separately before the edit
and is not part of the PR.
