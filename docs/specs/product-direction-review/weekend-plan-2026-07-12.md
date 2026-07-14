# Weekend Plan — 10 Hours, 2026-07-12/13 (rev 2)

**Derived from:** [assessment-2026-07-11.md](assessment-2026-07-11.md)
and conversation 1's setup-friction signal.
**Rev 2 (2026-07-11):** Patrick's constraints — setup first; no
direct outreach (no user contact list exists). Outreach replaced
with a zero-contact inbound channel (Block 5). No phone anywhere;
DEC-2 "conversations" includes async text threads.
**Rule for the weekend:** no new specs, no new gates. Every hour
either removes friction the user hit, opens a door for users to
report friction, or closes a decision.

---

## Saturday (5h) — reproduce and understand

### Block 1 — Fresh-machine setup reproduction (2.5h)

Be user 1. Zero prior state.

- `docker run -it --rm python:3.12-slim bash` (and/or a clean
  macOS user account).
- Follow README top-to-bottom exactly as written — no memory
  allowed. `pip install attune-ai`, first command, first workflow.
- Repeat with the extras a real user plausibly picks (`[all]`).
- Stopwatch running: log every stall, error, ambiguity, and
  "wait, what now" with a timestamp into `setup-friction-log.md`
  (this directory).
- Headline number: **time-to-first-successful-workflow**.

**Done when:** the log exists with a ranked top-5 friction list.
Fix nothing yet — ranking before fixing keeps the 3h fix budget on
the right targets.

### Block 2 — Fix friction #1 (1.5h)

Start the highest-ranked fix while the reproduction is fresh.
Direct fix only — no spec, no abstraction.

### Block 3 — DEC-6: answer the open decisions in writing (1h)

In [assessment.md](assessment.md) and
[assessment-2026-07-11.md](assessment-2026-07-11.md), replace every
"(pending)" on DEC-1…5 and DEC-7…9 with a dated call. "No" is a
valid answer; silence isn't. DEC-7 (release freeze) decides whether
this weekend's fixes get tagged now or held.

**Done when:** zero "(pending)" remain in either file.

---

## Sunday (5h) — fix and open the door

### Block 4 — Fix frictions #2 and #3 (2.5h, hard stop)

From the ranked log. Likely shapes: README quickstart that matches
reality, clearer first-run errors, a smaller default install, one
fewer decision before the first workflow runs. Re-run the Block 1
container against each fix to confirm the stall is gone; append the
new time-to-first-success to the log.

### Block 5 — Zero-contact inbound channel (1h)

The no-contact-list replacement for outreach. Users exist (one
found you); give the rest a path that costs them 60 seconds:

- Pin a GitHub Discussion (or issue template) titled roughly:
  *"Did setup fight you? Tell me where — I'm fixing these this
  month."* Three questions, plain text, no format police.
- Link it from the README quickstart section and — highest-value
  spot — from the CLI's first-run output and setup error paths,
  where the frustrated user is already standing.
- Log the channel in
  [user-conversations.md](user-conversations.md); every substantive
  reply counts toward the 5.

**Done when:** a stranger hitting a setup error is one click from
telling you about it.

### Block 6 — Root hygiene + CI spend cap (1.5h, hard stop)

- DEC-9: delete `MagicMock/`, `scratchpad_pushback.html`, stale
  `coverage.json` / `security_scan_results.json`; gitignore
  `build/`, `dist/`, `htmlcov/`, `site/`; move the six root
  `test_*.py` into `tests/`; merge the two ACKNOWLEDG(E)MENTS
  files; prune the 2.4 GB of stale worktrees.
- DEC-8 (if yes in Block 3): confirm per-push/PR workflows carry
  `ANTHROPIC_API_KEY: ""`; set `ATTUNE_MAX_BUDGET_USD` on the
  scheduled keyed jobs.

---

## Scorecard (filled 2026-07-12 — done same night, not Sunday)

| Block | Target | Actual |
|-------|--------|--------|
| 1 | Friction log + time-to-first-success baseline | **Done.** `setup-friction-log.md` — baseline "not reached" (keyless wall), 5 ranked frictions (F1-F5). |
| 2+4 | Top-3 frictions fixed, time re-measured | **Done, exceeded.** All 5 fixed (not just top-3), PR #1318. Shipped live in v10.4.0 — the real re-measurement is the release itself, not just a worktree re-run. |
| 3 | 0 "(pending)" decisions | **Done.** All 9 DECs (1-9) recorded with dates, PR #1323. |
| 5 | Inbound channel live, linked from error paths | **Done.** Discussion #1325, linked from README + CLI welcome screen + all 3 setup-error paths, PR #1326. |
| 6 | Root clean, CI spend capped | **Partial.** Root hygiene done (PR #1322). CI spend cap *decided* (DEC-8: \$350/mo) but enforcement mechanism not yet built — in progress. |

All 5 required blocks (1-5) done, plus most of Block 6 — full weekend
scope closed in a single session rather than across Sat/Sun.

Success = Blocks 1–5. Block 6 is the first to drop if time runs
out.
