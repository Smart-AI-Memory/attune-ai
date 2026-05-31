# Spec: Self-truthing spec status (derive from completion state, not the header line)

**Status**: approved (2026-05-31; see [decisions.md](./decisions.md))
**Created**: 2026-05-29
**Layer**: attune-ai plugin — session hooks (`plugin/hooks/_state.py`, `spec_orient.py`)
**Origin**: 2026-05-29 session. The spec-orientation hook reported
`architecture-realignment` as `draft (awaiting approval)` at SessionStart
while its `tasks.md` completion checklist said **closed 2026-05-08, all 8
PRs landed**. That stale status seeded an ungrounded daily-briefing
recommendation ("approve architecture-realignment") for work already
done — the session's root miss. The fix is to make status *self-truthing*
so neither the model nor the human works off a drifted header.

---

## Phase 1: Requirements

**Status**: approved

### Problem statement

`plugin/hooks/_state.py` derives a spec's status from the **first
`**Status**:` line** in its highest-priority phase file:

```python
_STATUS_LINE = re.compile(r"^\s*\*\*?Status\*\*?\s*:\s*(.+?)\s*$", re.I | re.M)

def _read_status(path):                      # header line, lowercased
    match = _STATUS_LINE.search(text)
    return match.group(1).strip().lower() if match else ""

def _is_in_flight(phase, status):            # only this one terminal case
    if phase == "tasks" and status == "complete":
        return False
    return True                              # everything else → in-flight
```

So a spec whose `tasks.md` **header** says `draft` but whose **completion
checklist** says closed/all-done is reported as in-flight `draft`. The
header is the single source of truth, and headers drift — authors update
the checklist and the PRs as work lands, but forget the line at the top.

Consumers of this stale status:
- the **SessionStart orientation** paragraph (`spec_orient.py`) the model
  reads first each session;
- the **`attune-monday-briefing`** skill, which builds recommendations
  from in-flight specs (now patched to grep completion checklists — this
  spec removes the need for that patch);
- any future tooling reading `discover_specs`.

### Scope

**In scope:**
- A status reader that **reconciles the header line with the spec's
  completion signal** (completion checklist + terminal status lines) and
  reports the stronger signal.
- Correct handling of **deferred / struck-through** checklist items so
  they don't block "closed" (architecture-realignment had
  `- [ ] ~~…~~ deferred` rows).
- A **conflict flag** when header and checklist disagree, so a stale
  header gets *surfaced* (and fixed) rather than silently overridden.
- Wiring the reconciled status into `_is_in_flight`, `SpecInfo`, and the
  `spec_orient` SessionStart output.

**Out of scope:**
- Rewriting spec authors' headers automatically (we *read* truthfully;
  we don't mutate spec files).
- Changing the phase-priority order (tasks > design > requirements).
- The `attune-monday-briefing` grep patch added 2026-05-29 — it stays as
  belt-and-suspenders until this lands, then can be simplified separately.
- Non-attune spec formats; this targets the SDD `requirements/design/tasks`
  + completion-checklist convention.

### User stories

1. As the model at SessionStart, I want a spec's reported status to match
   its actual completion state, so I don't recommend work that's done.
2. As Patrick, I want a stale header *flagged* ("closed per checklist;
   header still says draft"), so I notice and fix the drift instead of it
   silently disappearing.
3. As the briefing skill, I want `discover_specs` to already exclude
   closed-by-checklist specs, so I don't re-derive completion myself.
4. As a hook, I must never crash a session over a malformed checklist —
   degrade to today's header-only behavior.

### Current behavior (grounded in code)

- `_PHASE_FILES` priority: `tasks.md` > `design.md` > `requirements.md`.
- `_read_status` → first `**Status**:` header line, lowercased.
- `_is_in_flight`: `tasks` + `complete` ⇒ done; **all else ⇒ in-flight**
  (including empty/malformed status).
- No part of the pipeline reads `- [x]` checkboxes, a `## Completion
  checklist`, or a terminal line like `Spec status: closed`.

### Proposed mechanism

Add a **completion-signal reader** over the chosen phase file (normally
`tasks.md`) and reconcile:

1. **Terminal line scan** — match anywhere in the file (not just the
   header): `Spec status: closed`, `Status: complete`, `Status: closed`,
   `Status: retired`, `Status: superseded`. Case-insensitive.
2. **Completion checklist scan** — if a `## Completion checklist` (or the
   template's checklist block) exists, compute checked vs unchecked,
   **ignoring deferred rows**: a `- [ ]` line is *not* counted as
   outstanding when it is struck through (`~~…~~`) or annotated
   `deferred` / `N/A` / `won't do`. All non-deferred items checked ⇒
   complete.
3. **Reconcile** header status vs the completion signal:
   - either signal says terminal (closed/complete/retired/superseded) ⇒
     spec is **done** (not in-flight), even if the header says draft.
   - else fall back to the header status (today's behavior).
   - if the two disagree, set `status_conflict = True`.
4. `_is_in_flight` consults the reconciled verdict, not the raw header.
5. `SpecInfo` gains additive fields: `effective_status`,
   `status_source` (`"header" | "checklist" | "terminal-line"`),
   `status_conflict: bool`. Existing `status` stays (raw header) for
   back-compat.
6. `spec_orient` shows `effective_status`, and when `status_conflict`,
   appends a short hint, e.g.
   `(closed per checklist — header still says "draft", worth fixing)`.

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Header-only status drifts; derive from completion state. |
| **Interfaces** | addressed | `_state.py` (`_read_status`/`_phase_for_dir`/`_is_in_flight` + new checklist reader); additive `SpecInfo` fields; `spec_orient` output. `discover_specs` signature unchanged. |
| **User-facing behavior** | addressed | SessionStart line shows effective status + conflict hint; closed-by-checklist specs drop out of the in-flight list. |
| **Edge cases** | addressed | See table. |
| **Compatibility** | addressed | Additive fields; no-checklist ⇒ today's behavior exactly; consumers reading `.status` unaffected. |
| **Error handling** | addressed | Any parse failure → fall back to header; hook never raises (existing outer try/except preserved). |
| **Tradeoffs & alternatives** | addressed | See below. |
| **Rollback** | addressed | Revert the PR → header-only behavior returns; no migration. |

### Edge cases & open questions

| Case | Expected |
|------|----------|
| Header `draft` + checklist all-checked + `Spec status: closed` line (the real bug) | **done**, `status_source=terminal-line/checklist`, `status_conflict=True` |
| Header `approved` + checklist partially checked | **in-flight** (`approved`); no conflict |
| No completion checklist, no terminal line | header-only (today's behavior); `status_source=header` |
| `- [ ]` rows that are struck-through / "deferred" / "N/A" | not counted as outstanding; don't block "done" |
| Checklist fully unchecked but header `complete` | terminal header wins ⇒ done; `status_conflict=True` (surface it) |
| Malformed / unparseable checklist | fall back to header; never crash |
| `design.md` chosen (no `tasks.md`) | run the same reconcile on `design.md`; checklists usually live in tasks, so typically header-only |

**DECIDE-1** — precedence when header and checklist disagree.
*Recommend:* **terminal signal wins** (a closed checklist or terminal line
marks done over a stale `draft`/`approved` header), because the drift we
observe is always *header lags reality*, never the reverse.

**DECIDE-2** — what counts as "terminal." *Recommend:* **either** an
explicit terminal line (`closed`/`complete`/`retired`/`superseded`) **or**
a fully-checked non-deferred completion checklist.

**DECIDE-3** — surface conflicts or silently reconcile. *Recommend:*
**surface** a short hint in the SessionStart line so stale headers get
fixed at the source (otherwise the data stays wrong, just invisibly).

### Tradeoffs & alternatives

| Option | Pros | Cons | Pick |
|--------|------|------|------|
| Reconcile header ↔ checklist (this spec) | Truthful; surfaces drift; no author burden | More parsing; checklist-format assumptions | ✅ |
| Header-only + lint that fails CI on header/checklist mismatch | Forces authors to fix headers | Doesn't help at read time; adds CI friction | ✗ (could complement later) |
| Make the briefing grep every time (current patch) | Zero hook change | Per-consumer, repeated, doesn't fix SessionStart | ✗ (patch, not fix) |

### Rollback strategy

Single PR, additive. Revert restores header-only `_is_in_flight`.
`SpecInfo`'s new fields are optional; no persisted state, no migration.

### Testing strategy

Extend `tests/unit/hooks/test_session_continuity_state.py`:
- reconstruct the architecture-realignment case (draft header + closed
  checklist w/ struck-through deferred rows) ⇒ not in-flight, conflict
  flag set;
- header `approved` + partial checklist ⇒ in-flight, no conflict;
- no checklist ⇒ identical to current behavior;
- deferred/struck rows ignored;
- malformed checklist ⇒ falls back, no exception.

### Gaps

None blocking. The three DECIDEs have recommended defaults; design phase
locks them and the exact checklist/terminal-line regexes.

---

## Phase 2: Design — *(not started; awaiting requirements approval)*

## Phase 3: Tasks — *(not started)*
