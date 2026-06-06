# Per-decision log — Self-truthing spec status

Append-only log. Resolutions for the three DECIDEs in
[requirements.md](./requirements.md). Each decision marks the spec
ready to advance to Phase 2 (Design).

---

## Phase 1 approval (2026-05-31)

Three DECIDEs resolved in a single session. Spec status flips from
`draft (awaiting approval)` to `approved`. Phase 2 (design) can be
authored after this lands on `main`.

The author's recommendation was already stated for each DECIDE in
the requirements; Patrick accepted all three as-recommended. The
internal consistency was high — the Edge Cases table in requirements
already encodes these answers.

---

### DECIDE-1 — Precedence when header and checklist disagree

**Decision:** **Terminal signal wins.** A closed checklist or a
terminal status line marks the spec done over a stale
`draft` / `approved` / `in-progress` header.

**Rationale:** the spec's origin observation (architecture-realignment
reported as `draft` while its checklist said `closed 2026-05-08`) is
itself the evidence: the drift we observe in practice is always
*header lags reality*, never the reverse. There is no real-world
case where a header says "closed" while the work is genuinely
in-flight — authors don't proactively mark specs closed.

**Alternatives considered:**

- **Header wins** — preserves the "header as canonical" model, but
  is exactly the bug we're fixing. Rejected by premise.
- **Configurable per-consumer** — adds knobs without a use case.
  Defer until two consumers actually disagree.

**Implementation note for Phase 2 design:**

- `_is_in_flight()` consults the reconciled verdict, not the raw
  header.
- When terminal wins over a non-terminal header, set
  `status_conflict = True` on the `SpecInfo` record so the source
  drift gets surfaced (see DECIDE-3).

---

### DECIDE-2 — What counts as "terminal"

**Decision:** **Either** an explicit terminal status line **or** a
fully-checked non-deferred completion checklist. Both signals carry
equal weight; either one triggers the terminal verdict.

**Terminal lines recognized:**

- `Spec status: closed`
- `Status: complete`
- `Status: closed`
- `Status: retired`
- `Status: superseded`

(Case-insensitive; matched anywhere in the file, not just the
header.)

**Checklist completion:**

- A `## Completion checklist` section (or template equivalent).
- All `- [ ]` rows checked, **ignoring deferred rows**: a `- [ ]`
  line is NOT counted as outstanding when it is struck through
  (`~~…~~`) or annotated `deferred` / `N/A` / `won't do`.

**Rationale:** the project's specs use both conventions. Some end
with a terminal line in the body; others rely on the checklist
state. A reader walking the spec for ground truth must accept
either signal — restricting to one would force authors into a
single convention they haven't agreed to.

**Alternatives considered:**

- **Terminal line only** — simpler regex, but ignores the
  checklist-driven specs (the architecture-realignment case the
  spec was authored around uses both).
- **Checklist only** — fragile across template variants; some
  early specs don't have a checklist section at all.

**Implementation note for Phase 2 design:**

- Phase 2's design.md will lock the exact regex patterns for the
  terminal-line scan (case-insensitive, multiline anchor).
- Deferred-row detection: `re.search(r"~~|deferred|N/A|won't do",
  line, re.I)` — Phase 2 confirms the exact list.
- A terminal verdict from either signal short-circuits the rest.

---

### DECIDE-3 — Surface conflicts or silently reconcile

**Decision:** **Surface conflicts.** When the reconciled verdict
disagrees with the raw header status, append a short hint to the
SessionStart line so the stale header gets fixed at the source.

**Example output:**

```
docs/specs/architecture-realignment — closed
  (closed per checklist — header still says "draft", worth fixing)
```

**Rationale:** matches the project's "surface signals, don't
silence them" discipline (see CLAUDE.md memory:
`feedback_dont_enable_fatigue_push`, `feedback_proactive_persistence`,
the various lessons about silent failures). Silently reconciling
fixes the immediate read but leaves the underlying drift in place;
next time someone clones the repo or opens the file in a different
tool, the wrong status is what they see. Surfacing the conflict
puts a one-line nudge in front of Patrick so the source gets fixed.

**Alternatives considered:**

- **Silent reconcile** — the read is correct but the spec file
  stays wrong. Drift accumulates.
- **Hard fail on conflict** — too aggressive; would block sessions
  over header lag that's already being correctly reconciled.

**Implementation note for Phase 2 design:**

- `SpecInfo` gains `status_conflict: bool` (additive field).
- `spec_orient` reads it and appends the parenthetical hint to the
  SessionStart line when True.
- Hint format: stays under one line; describes what the verdict
  was derived from and what the header currently says.

---

## Cross-cutting note

The three DECIDEs form a single coherent design:

- DECIDE-1 establishes the verdict rule.
- DECIDE-2 names the signals the verdict can read.
- DECIDE-3 establishes the visibility discipline for when the
  verdict overrides the header.

Phase 2's design.md will translate these into concrete regexes,
exact `SpecInfo` field shapes, and the precise `spec_orient`
output format. No further user-facing decisions are required
between this approval and Phase 2 authoring.

---

## Close-out (2026-06-05)

Implementation + tests shipped in **#567** ("feat(hooks): self-truthing
spec status (impl + tests)"): the `_TERMINAL_LINE` / `_CHECKLIST_*` /
`_DEFERRED_MARKERS` regexes, `_completion_signal()`, `_reconcile_status()`,
the additive `SpecInfo` fields (`effective_status` / `status_source` /
`status_conflict`), `_is_in_flight(effective_status)`, and the
`spec_orient` conflict-hint rendering — all per design.md. 8
`TestStatusReconciliation` cases pass. Verified live: the reconciler
runs clean over the 39-spec corpus.

Status flipped to **complete** here on 2026-06-05. Fittingly, this
spec's *own* header was the last stale one — it read "approved" while
the work had landed in #567. The reconciler couldn't auto-catch it
because this spec has no `tasks.md`, no completion checklist, and no
terminal status line in its body, so there was no in-file completion
signal to read (the reconciler reads a spec's own files; it doesn't
cross-reference merged PRs — a known scope boundary). The fix was a
human marking it done — exactly the "header lags reality" drift the
spec was written to surface.
