# Round table — ops memory page + multi-LLM surface (q-ops-memory-multi-llm-pages-001)

**Thread:** `q-ops-memory-multi-llm-pages-001` · **Date:** 2026-07-22
· **Roster:** claude, antigravity, codex · **Rounds:** 2 (halted on
convergence, D3; chair had authorized 3) · **Promoted items:**
#2 #3 #4 #7 #8 #9 #10 (chair-approved). Notable: a mid-deliberation
chair ruling, an amendment ("keep unless consensus against"), and a
steelman round that MOVED the table 3/3-close → 2/3-keep.

## #1 — question (chair)

Should the attune-ops dashboard have (a) a memory page and (b) a
multi-LLM page? Context given to seats: rebuilt /memory page exists
as held PR #1576 (chair call pending); prior memory/sessions pages
removed as dogfood-dead (#1545); the multi-LLM layer (roundtable
board, session_memory_* transport, handoff packets, cross-review
ledger, provider telemetry) has no ops surface; Health tab is
closest.

## Round 1 (msgs #2 claude, #3 antigravity, #4 codex)

All three: close #1576 — a browse-only memory page repeats the
dogfood-dead pattern; memory facts belong as a Health card
(index count, hydration staleness, drift). On multi-LLM: claude
wanted an "Attention" strip on Health (counts with TTL deadlines;
page only after proven clicks); antigravity and codex each wanted
ONE minimal Collaboration "action inbox" page. Unanimous bans:
transcript viewers, memory CRUD/browsers, per-concern pages,
telemetry vanity charts, archival search of expired threads.
Follow-ups converged on one question: which surface owns the
promotion gesture?

## #5, #6 — chair rulings (mid-deliberation)

Msg 5: memory page STAYS (overrule). Msg 6 AMENDMENT: stays UNLESS
the table consensus is against it; chair elected a round-2 steelman
("design the page that earns opens, or say no such design exists").
Injected fact: promotion is IN-SESSION by design (R4;
`Board.promote` via the moderator) — a dashboard cannot own the
promote action.

## Round 2 — the steelman (msgs #7 claude, #8 antigravity, #9 codex)

- **claude** held: "NO PAGE-SHAPED DESIGN EXISTS" — every
  visit-earning element is alert-shaped (card territory) or needs a
  loop the dashboard is barred from closing. Self-corrected its
  multi-LLM pick from the strip to (B): deciding promote-or-expire
  requires reading the packet body, which a strip cannot render.
- **antigravity** flipped: keep as an "Operational Memory & Recall
  Debugger" — drift header + copyable rehydrate command,
  recall-miss query sandbox, stale-pointer triage, cross-links to
  collaboration items. Multi-LLM as a section ON that page (C).
- **codex** flipped: keep as a "Memory Attention" page —
  EXCEPTIONS-FIRST (hydration age, drift counts, recall misses,
  memory-dependent collab items), C1+C3 browse retained BENEATH the
  action queue; explicit kill clause (collapse alerts into Health
  and close the page if exception-driven opens don't materialize).
  Multi-LLM: (B).

## #10 — synthesis (moderator)

Memory page: no consensus against exists post-steelman (2/3 keep) —
under the amended rule the page stays; both keep votes share a
design core the as-built #1576 lacks: exceptions-first header above
browse. Multi-LLM: converged on (B) — one Collaboration inbox page
at claude's minimum scope (action-first, TTL countdown, read-only
thread body, copyable `/roundtable promote <thread>` line, nav
badge; NO GUI promote) with codex's kill clause. Acceptance signals
offered: inbox-open-precedes-promotion (claude), ≥1/3 deep-link
click-through before expiry (codex), ≥15% surface-originated
commands (antigravity) — all with demote-to-Health clauses ruled at
the usage read.

## Chair ruling (final, 2026-07-22)

- **#1576 MERGES at the Monday lift** — the pending chair call on
  the held queue is RESOLVED (the consensus test came out keep).
- **Work item 1 (FIRST): memory-page exceptions-first evolution** —
  the codex/antigravity shared core: attention header (hydration
  age + rehydrate command, corpus-vs-index drift with expandable
  file list, memory-dependent collaboration items) above the
  existing C1+C3 browse surface. Post-lift build; carries codex's
  kill clause.
- **Work item 2 (SECOND): Collaboration inbox page (B)** —
  claude's minimum scope exactly; display + deep-link only,
  promotion stays in-session. Carries the acceptance-signal ruling
  at the usage read (chair picks among the three offered signals
  then).
- Bans reaffirmed as binding for both surfaces.
- Sequencing: both AFTER the chair-queued binding build slot
  (T4+T2, then P2); they do not reorder it.
