# Spec: Ops Specs Completion Candidates — Decisions
**Status:** complete
> Pre-committed decisions captured 2026-05-15/16. Triggered by
> Patrick's observation that approved specs accumulate stale
> status because manual completion-marking has no nudge surface.
> Original framing was "let Claude mark approved specs complete";
> reframed during brainstorm to "surface completion candidates
> with evidence; human keeps the write authority."

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Auto-write vs propose-and-confirm | **Propose-and-confirm** | Asymmetric cost: false negative = 10s manual flip; false positive = lost trust in panel + possibly forgotten work. The existing `(unknown)` drift in the in-flight specs list already shows automated tracking degrades silently. Human keeps the write authority. |
| Default-on vs default-off | **Default-off** | Patrick initially proposed default-on; pushback was the same trust-cost asymmetry. Opt-in via `--specs-candidates`. |
| Q1 — Host-repo discovery | `git remote get-url origin` from the spec root's enclosing repo | Cheapest path. Works for the dominant case (attune-ai monorepo + sibling-package monorepos). `--specs-host-repo owner/name` per-root flag deferred until a real cross-repo case appears. |
| Q2 — Detector cadence | **Page load with 5-min in-memory cache** keyed by spec-roots tuple | ~15 candidate-eligible specs × ~1 `gh api` call each = ~3s worst case, ~0s cached. Cron adds infra + freshness/immediacy tradeoff that doesn't pay off at this scale. |
| Q3 — Confirm-failure UX | **Inline error banner on the row, manual retry, row stays visible** | Matches existing status-pill PUT-failure pattern so users learn one error model. Don't auto-dismiss (loses the candidate); don't auto-retry (masks the cause). |
| Q4 — `partial` / `paused` as candidates | **Out of scope for V1** | Those statuses are explicit human signals ("I know this isn't done"). Re-surfacing them would feel pushy and erode trust. Cost of missing a partial-that-finished = one manual flip. Revisit only if usage shows a pattern. |
| Q5 — PR-ref regex scope | **`decisions.md` + `tasks.md` only** | Discursive files (`_sequencing.md`, audit notes) reference PRs for context more often than for closure. If a real shipping claim lives only in a non-canonical file → manual flip (the cheap failure). |
| Q6 — Persist `--specs-candidates` toggle | **Yes**, to `~/.attune/ops/config.json` | One-time enable per machine, survives restarts. `--no-specs-candidates` clears the persisted state. |
| Candidate-set narrowness | **Only `approved` → `complete`** | The full status vocabulary has 6 values; the only auto-detectable transition with low false-positive risk is `approved → complete`. Other transitions stay manual. |
| Signal-check policy | **Zero false positives, accept many false negatives** | Five strict checks; all must pass. Any parser ambiguity falls toward "not a candidate." The cost asymmetry of trust loss drives this. |
| Detector ordering | **Cheapest local checks first**, network checks last, dismiss filter last | Status / edit-age / tasks-parse short-circuit ~80% of specs before any `gh` call fires. Dismiss filter runs last so dismissed candidates still benefit from the short-circuit. |
| Snapshot hash inputs | **Sorted PR numbers + tasks.md mtime + last_modified .md mtime** — explicitly EXCLUDES PR merge state | When a referenced PR transitions open→merged, the candidate should re-surface even though local snapshot inputs didn't change. The hash matches; the PR check sees new state; `is_active` condition 2 fails; re-surface. Correct by design. |
| Dismiss-store location | `~/.attune/ops/spec_completion_dismissed.json` (one file, atomic writes) | Small file, single user, atomic via temp file + `Path.replace()` per existing cross-platform lesson. No DB; no per-request cache. |
| Dismiss TTL | **14 days, signal-aware** | Re-surface immediately on new signal (PR merge, tasks.md edit) regardless of TTL. TTL is the floor for "nothing changed and the user said no." |
| Tasks.md interpretation | All-`- [x]` OR table rows marked `**done**` / `**complete**` → pass; ANY `- [ ]` → fail; missing → pass with "no tasks.md" evidence; empty → fail | Decisions-only specs are common in the corpus — they shouldn't be excluded. Skeleton tasks files shouldn't auto-complete. |
| Read-only mode behavior | **Hide section entirely**; GET endpoint returns `enabled: false` | The section presupposes the user can flip statuses; read-only mode forbids that. No degraded-mode UX worth designing. |
| Empty / no-candidates state | **Hide the section header entirely**; do not render "no candidates right now" | Removes visual clutter when there's nothing to act on. Section appears only when ≥1 candidate exists. |
| Server-render gating | **Section shell rendered server-side behind the enabled+allow_run gate**; JS only loads if shell present | When feature is off, zero JS runs and zero API calls fire. No client-side feature flagging. |
| Shipping shape | **One PR** | ~1.2k LoC including tests; opt-in default-off; bounded review surface. Splitting creates dead-code intermediate states for no benefit at solo-dev pace. Tasks T1–T7 ordered by dependency; intermediate states compile. |
| E2E audit before flip-on | **Manual review by Patrick** of `scripts/audit_completion_candidates.py` output against the live `docs/specs/` corpus — zero false positives required before enabling | The acceptance criterion in requirements ("zero false-positive completion suggestions across the current spec corpus during a 1-week trial") collapses to a one-time audit before flip-on. |

---

## Open questions (none)

All Q1–Q6 are resolved. Post-merge follow-ups (eviction
policy, `partial → complete` revisit, multi-repo flag) are
deferred explicitly in the tasks file, not open.

---

## References

- Brainstorm transcript: 2026-05-15 session
- Phase 1 (Requirements), Phase 2 (Design), Phase 3 (Tasks):
  [requirements.md](requirements.md)
- Existing status PUT endpoint:
  [src/attune/ops/routes/specs.py](../../../src/attune/ops/routes/specs.py)
- Predecessor spec for the Specs page surface:
  `docs/specs/ops-specs-features/`
