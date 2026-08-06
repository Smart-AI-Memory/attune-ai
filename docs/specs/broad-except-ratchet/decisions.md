# broad-except-ratchet — decisions

## D1 — APPROVED; the three open questions ruled

**Date:** 2026-08-06 · **Status:** approved (chair: Patrick, via the
three-question approval form; Q2 answered with an explicit request
for the lead's judgment and pushback)

| Q | Ruling |
|---|---|
| Q1 — `# noqa: BLE001` sites | **Counted.** The annotation is not an exemption. |
| Q2 — scope | **`src/attune` + `attune_redis` + `backend`.** |
| Q3 — fires-on-violation receipt | **At implementation** — seeded and proven in the build PR. |

### Measurement taken before ruling (2026-08-06)

| Tree | Broad-except sites | Files | Of which `# noqa: BLE001` |
|---|---|---|---|
| `src/attune` | 586 | 247 | 580 |
| `attune_redis` | 31 | 7 | 30 |
| `backend` | 7 | 5 | 3 |

**Q1 — the measurement invalidates the question's own premise, and
the chair's answer is the one the data supports.** Q1 offered
"treat the annotation as the documented-contract marker" as a
plausible reading. It is not tenable: **580 of 586** `src/attune`
sites carry `# noqa: BLE001`. The annotation records that ruff was
satisfied, not that a contract was documented — it is what the lint
made people write, applied near-universally. Excluding annotated
sites would have left the ratchet policing **6 sites out of 586**,
a guard in name only. Counting everything keeps the scan mechanical
(R4's stated principle) and makes the baseline the sole escape
hatch (R2/R3). Recorded because a future reader will otherwise
re-litigate Q1 from the annotation's nominal meaning rather than
its actual distribution.

**Q2 — the lead was asked for judgment and has no pushback to
offer; the widest scope is correct.** Reasons, in order of weight:

1. **`backend/` is where a swallow costs most and the baseline
   costs least.** It carries auth and subscription code
   (`backend/api/auth.py`, `backend/services/auth_service.py`,
   `backend/services/database/auth_db.py`) with its own security
   suite (`tests/backend/test_auth_security.py`) — a silently
   swallowed exception in an auth path is the worst instance of
   the class the spec exists to police. And it is **7 sites**: the
   entire tree costs less baseline than a single busy module in
   `src/attune`.
2. **`attune_redis` is the same product surface.** It ships
   bundled in the `attune-ai` wheel, so excluding it would let debt
   accumulate in shipped code purely because of a directory
   boundary.
3. **A shrink-only ratchet has no per-file carrying cost.** Wider
   scope adds baseline entries, not maintenance; the only recurring
   cost is on files someone edits, which is exactly where the guard
   should fire.

No counter-case survives contact with the numbers, so none is
manufactured here. The one caveat worth recording rather than
arguing: `backend/`'s last substantive commit is 2026-06-21 (a
dependabot bump). If that tree is later retired, its baseline
entries retire with it — the ratchet is not a reason to keep it
alive. That question belongs to the subsystem-value gate, not here.

**Q3 — receipt at implementation.** The acceptance criteria already
require a fires-on-violation receipt; ruling it "at implementation"
means the build PR must both seed the baseline AND demonstrate that
adding one new `except Exception` fails the guard. Approval grants
implementation authority; it does not waive the receipt.

### Effect

`requirements.md` moves draft → approved, with Q1–Q3 folded in as
ratified clauses (R5–R7). Implementation may proceed. Seeding
baseline: **624 sites across 259 files** at approval time — the
build PR re-measures from its own commit rather than trusting this
number.
