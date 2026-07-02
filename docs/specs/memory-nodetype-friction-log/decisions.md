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

## 2026-07-02 — Alignment pause + Frictions A and C fixed

**Alignment (Patrick's answers, batched decision form):**

- **Goal framing:** attune memory is the product; the harness
  auto-memory files are scaffolding. Judge the curated graph against
  "could this carry the agent's continuity." (A complementary
  routing-rule framing was discussed as the *transition* protocol —
  proposal pending Patrick's reaction, not yet a decision.)
- **Fix order:** Friction A now, then Friction C. Friction B (edge
  direction) deliberately stays open as R4 evidence.
- **Read-side wiring:** scope it soon — R4 should judge a living
  read/write loop, not a write-only log (see scope below).
- **Verdict posture:** negative findings are acceptable but carry a
  fix-first bias — propose "what would make it earn its keep" before
  removal talk.

**Friction A — FIXED.** `MemoryGraph.curated()` classmethod opens the
graph at `~/.attune/memory/curated_graph.json` (the same durable home
`personal.py` already uses as `_GLOBAL_ROOT`), leaving the constructor's
cwd-relative default untouched for per-project workflow findings.
Round-trip test across fresh instances included
([graph.py](../../../src/attune/memory/graph.py),
[test_graph.py](../../../tests/unit/memory/test_graph.py)).

**Friction C — FIXED.** `find_similar` now accepts `dict | str`: a node
ID builds the query from that node's fields and excludes it from
results (mirroring `find_related`'s id-based signature); any other
string is free text matched against name and description. Default
`threshold` lowered 0.5 → 0.25 so natural paraphrases match (the
observed 0.301 paraphrase score now clears the default). The one
production caller (`agent_factory/memory_integration.py`) passes an
explicit threshold, so the default change is additive. Regression
guard asserts a paraphrase scoring < 0.5 matches at the default.

**Read-side wiring — SCOPED (no engine work yet):** a session-start
surface that queries the curated graph and injects relevant `active`
nodes into agent context, so curated memory is READ under real
conditions before the R4 verdict. Shape: reuse the existing
SessionStart-hook pattern (the stash/recall hook), query
`MemoryGraph.curated()` via `find_similar`/`find_by_type`, cap the
injection (~5 nodes), and label provenance per node type. Acceptance:
a fresh session surfaces at least the USER_CONTEXT priority node and
any PROJECT_CONTEXT nodes relevant to the working repo without a
manual query. Open question for the spec pass: relevance signal at
session start (no query text yet — recency + type-weighting vs. cwd/
repo tags). **Prototyped 2026-07-02** (Patrick's fuller vision:
git long-term → Redis short-term → widget recall): the private repo
`silversurfer562/attune-agent-memory` (= `~/.attune/memory/`, so
`MemoryGraph.curated()`'s path is unchanged) carries its own
`hydrate.py` (rebuilds `attune:memory:*` hashes/sets + a RediSearch
index) and `functions.lua` (`recall_digest` stored procedure via
FCALL). Measured: FCALL median 86μs, FT.SEARCH median 181μs; the
digest rendered live through `form_from_dict` →
`form_to_widget_html` (progress construct, pure-display sub-state).
Widget-shape evidence: memory facts aren't "done tasks" — the
strikethrough styling reads wrong, which is early evidence for a
dedicated recall-digest grammar primitive rather than reusing
`progress`. Productionization (SessionStart hook registration,
git-pull-before-hydrate, targeted FT.SEARCH procedures, the new
primitive) goes to a spec written from this evidence.

---

## 2026-07-02 — Second real captures: 2 nodes via the NEW curated() path

**What was recorded** (via `MemoryGraph.curated()` — dogfooding the
friction-A fix itself, receipt-verified from a fresh instance):

- `USER_CONTEXT` — the alignment decisions (goal framing: attune
  memory is the product; fix-first verdict bias; read-wiring scoped)
- `PROJECT_CONTEXT` — Frictions A+C fixed (PR #1212), B open by choice
- Two `RELATED_TO` edges, including one linking the new goal-framing
  node to the prior standing-priority node.

**Clean fits:** `curated()` resolved the right path with no explicit
path argument; both nodes round-tripped with `status="active"`; the
taxonomy again matched without forcing.

**New friction (found by the receipt, FIXED in-PR):** free-text
`find_similar` queries scored by Jaccard topped out at ~0.06–0.17
against these verbose curated nodes — a realistic question-shaped
query ("what fixes shipped for the memory frictions") returned `[]`
even at the new 0.25 default, because the union term grows with node
text length. No threshold fixes that class. Fix: the free-text form
(new in PR #1212, so no back-compat) scores by **containment** — the
fraction of query words found in the node's name or description. The
same query now returns 5 hits; "goal framing memory product" ranks the
goal-framing node top at 0.50.

**Remaining evidence for R4 (not fixed):** (a) no stemming —
"fixes"/"fixed" and "friction"/"frictions" still count as misses, and
containment ranking mildly favors verbose nodes (the dead query's top
hit is the wordy priority node, not the frictions node); (b) Friction
B's `direction="both"` read-time workaround still in use for the edge
follow-up. If either keeps biting, they're the adjust/extend evidence.

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

---

## 2026-07-02 — First human review pass: 6 keep / 1 sharper / 0 wrong

**What happened (the R4 core event):** the full 7-node curated graph
was rendered as a widget review form through the production pipeline
(`form_from_dict` -> `form_to_widget_html`, one `single_select`
keep/wrong/sharper per node with the node's description as
`help_text`). Patrick submitted verdicts; the payload validated clean
through `collect_form_response` (`resp-20260702-100356`). Verdicts:
**6 keep, 1 sharper** (the architecture-vision node; note: "7 just
needs refinement and work and it seems you are doing that"), 0 wrong.

**Applied via the real API:** `MemoryGraph.curated()` +
`update_node()` — review provenance merged into every node's
`metadata` (`reviewed_at`, `review_verdict`, `review_response_id`),
and the sharper node's `description` rewritten (vision / method /
receipts / open items separated; marked "refining as prototype
evidence lands"). Redis re-hydrated (7 nodes, 5 edges); memory repo
committed and pushed (`6aba3ff`).

**Clean fits:** `update_node`'s metadata **merge** (not replace)
carried review provenance without a schema change — the graph itself
now records that a human judged it, which is R4 evidence in the data.
The review-form shape (verdict enum + one notes textarea) was
sufficient; no per-node notes field was missed in practice.

**Friction:** none new in the NodeType taxonomy this pass. The
first-review outcome itself is R4 signal: zero "wrong" verdicts on
nodes written by the agent without templates or prompting.

## Adjacent observation (stash/recall subsystem, 2026-07-02)

The Stop-hook auto-stash captured a `[pattern]` finding carrying a
hypothesis ("matches #930 fork-Pool execnet-fd-leak") that the SAME
session's evidence had just superseded — alongside a `[bug]` finding
correctly recording the new conclusion. The stash now holds a
contradictory pair, and recency-ranked recall would surface both with
equal confidence. Auto-extraction has no in-session supersession
awareness; the curated path (human-reviewed, status-bearing) is the
mechanism that catches this class. Same subsystem caveat as the
2026-07-01 cross-project-noise entry: not `add_finding()` scope,
logged as adjacent evidence.

---

## 2026-07-02 — Transition protocol ratified (closes the open
"talk to me more about 2" discussion)

Patrick ratified the two-layer protocol after an explicit
amnesia-centered deep dive: **curated graph = durable-only** (nodes
must pass the 30-day test), **operational handoff = short-term
memory** (separate artifact; starter file today, Redis-native TTL'd
records as the evolution path), bridged by handoff items citing
curated node IDs. Full rationale and the named future R-item
(crash-safe continuous handoff) recorded in
`docs/specs/curated-memory-productionization/decisions.md` D6.
Consequence for THIS log: R1's "real usage" bar now has a sharper
admission filter — a candidate curated node that fails the 30-day
test is routed to the handoff layer, and that routing decision is
itself loggable evidence here.
