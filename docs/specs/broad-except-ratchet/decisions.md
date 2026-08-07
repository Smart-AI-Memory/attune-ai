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

## D2 — BUILT; guard seeded and fires-on-violation receipted (R7)

**Date:** 2026-08-07 · **Status:** built (lead: Claude)

Guard lives at `tests/unit/gates/test_broad_except_ratchet.py`,
three tests: no-new-or-raised, baseline-not-stale (the half that
makes it actually ratchet), and an R6 scope drift guard on the
baseline keys themselves.

**Detection is AST-based, not textual** — a deliberate departure
from the sibling `test_no_new_sys_modules_patch.py` regex model.
This repo's prose, `.claude/lessons.md`, and docstrings mention
`except Exception` constantly; a regex would count them and the
baseline would churn on every docs commit. One `ExceptHandler`
counts once however many names its tuple carries, and the
attribute form (`builtins.Exception`) is caught too.

### Seeded baseline — RE-MEASURED, and it differs from D1

| Tree | Sites | Note |
|---|---|---|
| `src/attune` | 577 | |
| `attune_redis` | 30 | |
| `backend` | 6 | |
| **Total** | **613 across 253 files** | |

D1 recorded 624/259 from a `grep -c` line count; the AST scan
finds **613/253**. The delta is a measurement-instrument
difference, not drift: grep counts LINES matching the pattern
(including a handful in strings/comments), the gate counts
`ExceptHandler` NODES. D1 anticipated exactly this and instructed
the build to re-measure — the gate's own scanner seeded the
baseline, so the number and the enforcement can never disagree.

### R7 fires-on-violation receipt — three shapes, all live

Each probe was applied to the real tree, the gate run, and the
probe reverted (`git status` clean after each):

| Probe | Result |
|---|---|
| Raise the count in an already-baselined file (`src/attune/discovery.py`, +1) | **FAILS**: `src/attune/discovery.py: 2 > baseline 1` |
| Brand-new file with a broad except | **FAILS**: `New file(s) use except Exception…: src/attune/_ratchet_probe.py (1)` |
| Convert a site (baseline goes stale) | **FAILS**: `src/attune/discovery.py: baseline 1 but now 0 — lower it` |

**R5 confirmed live:** the Case-A probe carried
`# noqa: BLE001` and was counted anyway — the annotation is not an
exemption, as ruled.

**Process note worth recording.** The first probe run used
`-p no:xdist`, which collides with `-n auto` in `pytest.ini`;
pytest exited on argument parsing and my filtered grep matched
nothing, so all three probes reported *silence* that I briefly
read as success. The receipt above is from the re-run with a valid
invocation. Silence is not a receipt — the filter has to be able
to show a failure before an empty result means anything.

Seeding commit is green on the full `tests/unit/gates` suite
(199 passed). AC bullets 1 and 3 (guard exists + seeded + green;
shrink-only documented in the docstring) are satisfied by this
commit; AC bullet 2 is the receipt table above.
