# Decisions: Memory NodeType Friction Log

Running log of friction points (and good fits) observed while using
the 4 curated `NodeType` members (`USER_CONTEXT`, `FEEDBACK`,
`PROJECT_CONTEXT`, `REFERENCE`, PR #1207) for real curated-memory
writes. See `requirements.md` for the graduation criteria (R4).

Entry format: date, what was being recorded, which type/field, fit
(clean / friction), notes.

---

## Fix notes (not friction entries)

Bugs found in the mechanism itself, before any real dogfood usage,
don't belong in the friction log proper (R1 scopes friction to real
curated-memory writes) — logged here instead so future readers don't
mistake a pre-existing implementation gap for a taxonomy-fit problem.

- **2026-07-01 — `add_finding()` dropped `status` entirely.** A
  `/code-review` of PR #1207 found that `MemoryGraph.add_finding()`
  never read `finding["status"]` — every node created through the
  real public API silently got the dataclass default `status="open"`,
  regardless of what the caller passed. This predates #1207, but it
  falsified the PR's stated design (curated-memory nodes get
  `active`/`superseded`/`stale`) for every node actually written via
  `add_finding`, and the new regression test
  (`test_loads_curated_memory_node_via_real_add_finding`) didn't catch
  it because it asserted `.type` but not `.status`. Fixed:
  `add_finding` now passes `status=finding.get("status", "open")`
  ([graph.py](../../../src/attune/memory/graph.py)); the regression
  test now asserts `status == "active"` on reload
  ([test_graph.py](../../../tests/unit/memory/test_graph.py)). Not a
  taxonomy/field-fit signal — a plain implementation bug, caught
  before real usage began.

---

## 2026-07-01 — First real captures: 4 nodes, one per type

**What was recorded** (real session findings, written to
`~/.attune/memory/curated_graph.json` via the real public API, receipt
verified by reloading from a brand-new `MemoryGraph` instance):

- `PROJECT_CONTEXT` — "PersonalMemory recall is file-backed and
  survives process death" (the Run 3 verdict, PR #1209)
- `REFERENCE` — pointer to the canonical benchmark numbers
  (`docs/specs/memory-recall-eval/decisions.md`)
- `FEEDBACK` — "prefer real round-trip tests over mocks when touching
  attune.memory" (Patrick-endorsed, both #1208 bugs were mock-blind)
- `USER_CONTEXT` — Patrick's stated active priority (2026-07-01): make
  the memory system genuinely work for the agent
- Two `RELATED_TO` edges (`REFERENCE → PROJECT_CONTEXT`,
  `FEEDBACK → PROJECT_CONTEXT`)

**Clean fits:** the 4-type taxonomy matched all four captures with no
forcing — nothing needed a fifth type, nothing straddled two types.
`status="active"` persisted and reloaded correctly (the #1208 fix
working live). `severity` staying unset read naturally. Tags carried
fine. `workflow=""` for curated nodes worked as documented.

**Friction A — storage location (the biggest one).** `MemoryGraph`'s
default path is `patterns/memory_graph.json`: **cwd-relative and
git-tracked**. Curated *cross-session* memory written through the
default would either get committed into the repo or stranded inside
whichever worktree the session happened to run in (this repo runs many
parallel worktrees). Workaround: explicit
`path=~/.attune/memory/curated_graph.json`. Signal: curated memory
needs a durable default home outside the repo, distinct from
workflow-findings graphs — the current default is shaped for
per-project workflow state, not cross-session memory.

**Friction B — `RELATED_TO` direction ergonomics.** The natural
`[[link]]` usage — add an edge, then ask the *target* node for related
nodes — silently returns `[]`: `RELATED_TO` is declared symmetric
(`REVERSE_EDGE_TYPES` maps it to itself) but `add_edge` defaults
`bidirectional=False` and `find_related` defaults
`direction="outgoing"`, so symmetry exists only if the writer or
reader remembers to ask for it. Workaround: `direction="both"` at read
time (verified: returns both linked nodes). Signal: for curated
memory, symmetric edge types should traverse both directions by
default; the current defaults quietly drop half the link graph.

**Friction C — `find_similar` signature + threshold (also closes the
session-starter's #3 sanity-check).** Two parts. (a) Signature
inconsistency: `find_related` takes a node id, `find_similar` takes a
finding *dict* — first call attempt passed an id and died with
`AttributeError: 'str' object has no attribute 'get'`. (b) The default
`threshold=0.5` over Jaccard word-overlap mutes realistic queries:
"recall benchmark persistence numbers" scored 0.301 against the
project-context node and 0.125 against the reference node — both
filtered out at the default; only a near-verbatim name clears 0.5
(verbatim self-match = 1.0, so this is NOT the `PersonalMemory.query()`
dead-path class — the mechanism works, the default tuning makes it
effectively silent). Workaround: `threshold≈0.25`, or use
`PersonalMemory.query()` for text recall. Cross-referenced in
`docs/specs/memory-recall-eval/decisions.md`.

**Minor:** `EdgeType` lives in `attune.memory.edges`, not
`attune.memory.nodes` (where the curated-memory docstring pointing at
it lives) — cost one failed import.

---

## Adjacent observations (not R1-scope — different subsystem)

- **2026-07-01 — cross-project recall noise in the stash/recall
  surface.** A session resume in this repo surfaced "recent findings
  from this project" that included precious-metals-conversation
  findings ("silver volatility over 20 years", "consider reinvesting
  dividends") plus one entry too context-free to act on ("Identity
  rewrite may be more done than the memory note implies").
  Recency-ranked recall with no topical/project gate pulls whatever
  was stashed last, and project attribution leaked across sessions.
  This is the stash/recall-hook subsystem, not `add_finding()`, so it
  is logged here as adjacent evidence only — but it is the same
  product question this spec exists to answer (does recalled memory
  read as trustworthy?), and today the answer on that surface was no.
