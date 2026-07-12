# Freeze-Week Plan — 2026-07-13 → 07-27

**Derived from:**
[assessment-2026-07-12.md](assessment-2026-07-12.md)'s
outstanding-work ledger, continuing the pattern that closed N1:
*non-repo-shaped work expressed as a repo artifact with a
scorecard* (see [weekend-plan-2026-07-12.md](weekend-plan-2026-07-12.md)).
**Forks resolved 2026-07-12 (Patrick):** publish the assessment
(go), trap-battery pilot approved, fable-premium-tier proceeds
capped.
**Rule for the fortnight:** every hour either watches the door
(channel, download curve), closes a decision in writing, or
executes an already-made decision. No new specs, no new gates,
no inventing an item 10.

---

## Block 0 — Unblock the enforcement (30 min, browser, Patrick-only, FIRST)

- Set `ANTHROPIC_ADMIN_API_KEY` in attune-ai repo secrets
  (Settings → Secrets → Actions) → DEC-8 gate goes live
  (fails open until then — verified unset 2026-07-12).
- Set the Anthropic Console spend limit (account setting).
- Create `ATTUNE_WORKSPACE_RO_TOKEN` (fine-grained PAT,
  resource owner Smart-AI-Memory, repos attune + layers,
  Contents read-only, **1-year expiry**), then
  `gh secret set ATTUNE_WORKSPACE_RO_TOKEN -R Smart-AI-Memory/attune`.

**Done when:** `ci_spend_gate.py` runs enforcing (not fail-open)
on its next scheduled run; umbrella spec-audit CI green.

## Block 1 — Watch the door (10 min/day, every day)

- Check Discussion #1325; reply same-day to anything substantive.
- Log each substantive thread in
  [user-conversations.md](user-conversations.md) toward the
  DEC-2 count (async text threads count).

**Done when:** zero replies older than 24h at any point in the
window. Silence through 07-27 gets *recorded* as data, not
ignored.

## Block 2 — N5 paragraph (30 min, once)

One paragraph in `../usage-signals/decisions.md`: the attune-rag
27,410/month download figure is uninterpreted noise pending
evidence — never quote it as traction.

**Done when:** committed.

## Block 3 — DEC-3 visible: README reorder (2h, hard stop)

Memory first; workflows / RAG grounding / verification demoted to
a single "also ships" line. Reorder, don't build. Two caveats:

- README is the PyPI `long_description` — the reorder reaches
  GitHub immediately but **PyPI keeps the old copy until the
  first post-freeze release** (07-28+). Acceptable; it rides
  that tag.
- Broad `grep -rn` sweep across `website/app/` in the same PR —
  pillar copy spreads wider than one file.

**Done when:** README + website agree memory is pillar #1; no
four-pillar framing survives the grep.

## Block 4 — trap-battery pilot (approved 2026-07-12)

Decision recorded in `../trap-battery/decisions.md` and the spec
status flipped to approved. Build sequence: **after Block 0**
(pilot spend runs under live enforcement). Scope: 3 classes ×
2 arms × 5 repeats, deterministic scoring only. The ~$30–60 run
gets a stated-cost go at execution time.

**Done when:** discrimination-gate results exist (each trap
fires ≥2/5 OFF-arm) or the run is consciously deferred past
07-27 with a dated note.

## Block 5 — fable-premium-tier tasks 3–8 (capped at 2 sessions)

Proceed (Patrick, 2026-07-12). In-flight spec — DEC-1-compatible.
Checkout `~/attune-ai-fable`; next is task 3
(`src/attune/llm/fable_call.py`). **Task 9 (release) is parked
hard until ≥07-28** — no tags through 07-27; calendar it so
momentum doesn't break the freeze. First block to drop if
Block 1 produces conversations needing follow-through.

**Done when:** tasks 3–8 done, or the drop is recorded with a
reason.

## Block 6 — Close the experiment (1h, on 07-27)

Keep the usage-signals snapshot cadence through the window; on
07-27 write the interpretation into usage-signals — does the
download curve track releases or users? The freeze lifts with a
data point instead of a vibe.

**Done when:** interpretation committed dated 2026-07-27.

---

## Scorecard (fill as blocks close)

| Block | Target | Actual |
|-------|--------|--------|
| 0 | 3 secrets/caps live, gate enforcing | |
| 1 | 0 replies >24h; threads logged | |
| 2 | N5 paragraph committed | |
| 3 | Memory visibly pillar #1, sweep clean | |
| 4 | Pilot discrimination results (or dated deferral) | |
| 5 | fable tasks 3–8 done OR consciously dropped | |
| 6 | Freeze interpretation written 07-27 | |

Success = Blocks 0, 1, 2, 6. Blocks 3–5 are ride-along repo
work; 5 drops first.
