# Per-decision log — Enforcement vs Documentation

Append-only log. Decisions recorded 2026-05-31 during the
morning session that surfaced the framing.

---

## D1 — Promotion criteria (2026-05-31)

**Decision:** A lesson is promoted from documentation to
enforcement candidate only when ALL three criteria hold:

1. Recurrence ≥2 times in **distinct** sessions.
2. Cost ≥10 min recovery OR irrecoverable state per occurrence.
3. Mechanical check available (not "be careful").

**Rationale:** prevents the enforcement list from absorbing
every lesson ever written. The three criteria align cost-of-
enforcement with cost-of-recurrence. The "distinct sessions"
qualifier specifically guards against same-session double-hits
masking as "this happens all the time" — they reflect in-flight
forgetting, which is a different problem.

**Alternatives considered:**

- **Recurrence ≥3 across any sessions** — more conservative;
  delays valuable enforcements. Rejected as too slow.
- **Recurrence ≥1 if cost is severe** — handles "shouldn't
  happen even once" cases (security incidents, data loss).
  Implicitly covered by "irrecoverable state" in criterion 2:
  if the first occurrence loses state, the enforcement can be
  built defensively without waiting for a second hit.

---

## D2 — List-size discipline (2026-05-31)

**Decision:** **Soft cap of 10 active enforcements.** When a
new candidate would push past 10, Patrick is notified
explicitly and presented with current retirement candidates
ranked by retirement metrics. He may approve growth OR retire
one.

Patrick's exact framing during the session:

> "I'm not sure about capping the list at 10. We should be
> informed if there are more than 10, which needs approval."

This is the implemented shape: the cap is **attention-
triggering**, not blocking. 10 is the default discomfort
threshold — picked because it's small enough that each member
gets remembered, large enough to cover the genuinely
high-cost recurring patterns.

**Rationale:** unbounded enforcement lists become their own
maintenance burden; each enforcement is code, costs
attention to tune, and risks false alarms that erode trust
in the whole system. Bounding the list forces explicit
trade-offs.

**Alternatives considered:**

- **Hard cap of 10** — would block legitimate additions.
  Rejected per Patrick's direction.
- **No cap, periodic review only** — defers the decision to
  whenever review happens. Rejected because growth without
  attention is the failure mode this discipline addresses.

---

## D3 — Retirement metrics (2026-05-31)

**Decision:** Each active enforcement carries four metrics:

| Metric | Retirement signal |
|---|---|
| **Hit rate** (real saves) | Drops toward zero over rolling window (suggest: 0 hits in 30 days) |
| **False-alarm rate** | Rises above 20% of fires |
| **Override count** | Rising trend (suggest: ≥3 overrides in 30 days) |
| **Days since last hit** | >60 days |

Retirement candidates are surfaced in a periodic review
(weekly or monthly — exact cadence TBD with first review).
Patrick decides retire vs keep. Retired enforcements: code
removed, lesson stays in `CLAUDE.md` as documentation.

**Rationale:** Patrick explicitly asked for "appropriate
metrics that will guide me regarding possible retirement
candidates." These four cover the failure modes an enforcement
can have: (a) no longer needed (low hit rate, high days-since-
last), (b) wrong (high false-alarm), (c) annoying (high
override). Any one trending bad is a retirement signal.

**Implementation note for the first enforcement:**

The pre-Write worktree-path hook will need a metrics
collector. Lightweight: append-only JSONL log at
`~/.attune/enforcement-metrics.jsonl` with `{timestamp,
enforcement, action, outcome}` records. The periodic review
aggregates from this log. Build the metrics scaffolding ALONG
WITH the first enforcement so it's not bolted on later.

---

## D4 — Mechanical-enforcement shape catalog (2026-05-31)

**Decision:** Five appropriate shapes for attune-ai:

1. **PreToolUse hook** — agent-action source.
2. **Pre-commit hook** — commit-source.
3. **Shell wrapper / alias** — CLI-invocation source.
4. **Test as drift-guard** — static drift (file lists,
   counts, configuration).
5. **Env-var gate** — runtime misconfiguration.

**Rationale:** these five cover every action source attune-ai
has surfaces for. Any enforcement should pick the shape that
matches where the dangerous action originates. The wrong
shape means the enforcement misses cases (e.g. a pre-commit
hook can't catch agent actions during a session — they don't
go through commits).

**Implementation note:** when proposing a new enforcement,
the spec should name which shape and why. If the shape
doesn't fit any of the five, that's a signal the enforcement
isn't ready (or the catalog needs a sixth entry — escalate).

---

## D5 — Where this spec leaves us (2026-05-31)

**Decision:** **Ship the framework now, validate with one
concrete enforcement, expand later.** This spec lands as
documentation of the criteria; the first concrete enforcement
(pre-Write worktree-path hook) ships in its own follow-up PR
and proves the framework end-to-end.

If the first enforcement works (hits real cases, false-alarm
rate stays low), the framework is validated. The next two
candidates (`.help` template regen skip, `git pull` wrapper)
can be queued. If the first enforcement fails to add value or
fires too often, the framework needs revision before more
enforcements ship.

**Initial enforced set (after first PR lands):** 1.

**Cap to be respected:** 10. Next addition past 10 triggers
the notification + retirement-candidates surfacing per D2.

---

## Cross-cutting note

This spec is itself a meta-improvement. It doesn't change any
user-facing behavior; it changes how the project decides which
lessons to encode mechanically. Pairs with
[`spec-status-self-truthing`](../spec-status-self-truthing/) —
both make the project's operational discipline more reliable
without shipping new product surface.

The pattern of pairing a documentation-only meta-spec with one
concrete validating implementation (a "framework + first
case") is itself worth noting. It's how this spec ships
honestly: the framework is testable because we ship one real
case alongside it.
