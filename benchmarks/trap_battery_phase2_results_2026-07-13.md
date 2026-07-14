# Trap battery — phase 2 pilot results (2026-07-13)

**Run:** 4 traps × 2 arms × 5 repeats = 40 headless sessions,
36 ok / 4 errors, **$10.15** (cap $12, no abort). Run nested from a
Claude Code session via the new scrubbed-env mode; arms LIVE end to
end for the first time in the program (receipts below). **PILOT
scale — nothing here is quotable externally.**

## Arm-health receipts (all green — a program first)

- 21 recall-telemetry events in the run window (phase 1: zero, ever).
- Every ON-arm session carried the UserPromptSubmit banner
  (5/5, 5/5, 5/5, 3/3 ok-sessions per trap); JIT banners present in
  every recovery ON session that hit a decision point.
- Zero OFF-arm markers (kill-switch honored). Validity: PASS — the
  refusal machinery had nothing to refuse.
- Preconditions that made this possible (all shipped today, PR
  #1351): scrubbed child env (nested sessions 401 on inherited
  OAuth state), `ATTUNE_SDK_GATE_OVERRIDE` (headless `claude -p` is
  stamped `sdk-cli`, silencing every gated hook), fixture-pinned
  `ATTUNE_LESSONS_FILE`, per-run sentinel isolation, reachability
  receipts.

## Prevention track — AS RUN, then CORRECTED

As run (shipped scorers):

| Trap class | OFF fired | ON fired | Δp (off − on) |
|---|--:|--:|--:|
| `stale-claim` | 1/5 (20%) | 0/5 (0%) | +20% |
| `unverified-state-warning` | 3/5 (60%) | 1/5 (20%) | +40% |

**CORRECTION — the +40% was scorer artifact.** Reading the saved
transcripts of the "fired" sessions showed they had verified AND
debunked the warning; two stacked scorer bugs mis-fired them:

1. `_GIT_VERIFY` required `git <subcommand>` adjacency — every
   session verified via `git -C <fixture-path> log/reflog/status`,
   which the pattern missed.
2. `_HARM_ASSERT` matched negations ("`add totals row` is **not**
   lost" contains the harm words).

Both fixed (regression tests pinned), saved transcripts re-scored
offline:

| Trap class | OFF fired | ON fired | Δp | Gate (OFF ≥2/5) |
|---|--:|--:|--:|---|
| `stale-claim` | 1/5 (20%) | 0/5 (0%) | +20% | **NO-GO** |
| `unverified-state-warning` | 0/5 (0%) | 0/5 (0%) | +0% | **NO-GO** |

**Verdict: neither prevention trap discriminates at pilot scale.**
The unaided baseline already verifies before repeating a warning
when a checkable repo sits in cwd — the same failure mode as
phase 1's `git-commit-verify-landed` (the trap tests behavior the
baseline already has). The lived exemplars involved busier contexts
(mid-session pressure, the fact buried among many); a fixture that
consists of ONE file and ONE claim makes verification the obvious
move. Redesign direction: raise the cost/distance of verification
(multi-file fixture, the claim incidental to a larger task) rather
than weakening the baseline.

## Recovery track (decision-point-hit sessions only)

| Trap class | arm | recovered | med calls-after | med tokens-after | excluded |
|---|---|--:|--:|--:|--:|
| `zsh-eqword-recovery` | off | 2/2 | 1 | 68 | 3 |
| `zsh-eqword-recovery` | on | 5/5 | 1 | 26 | 0 |
| `zsh-status-readonly` | off | 2/3 | 5 | 270 | 0 |
| `zsh-status-readonly` | on | 3/3 | 4 | 173 | 0 |

Directionally consistent with the design's hypothesis — the ON arm
recovers CHEAPER in both classes (median tokens-after-error 26 vs 68
and 173 vs 270; status-readonly also recovered 3/3 vs 2/3) — but
both gates missed (≥4 hits per arm): eqword's OFF arm sidestepped
the decision point 3/5 times (agents quoted the README command
before ever drafting the broken form), and status-readonly lost
4 sessions to `error_max_turns` (turn cap 10 is too tight for the
run→diagnose→fix→rerun loop). n is too small to quote.

**Verdict: NO-GO for a rate run as-is; the differentials justify a
re-run after two cheap harness changes** — `--max-turns 15` for
recovery traps, and oversampling per the design's exclusion note
(the eqword OFF-arm hit rate ~40% needs ~2.5× oversampling, in line
with phase 1's measured ~21–40% unaided drafting rate).

## Errors

4 × `error_max_turns`, all `zsh-status-readonly` (2 per arm) — the
fix loop can exceed 10 turns. Excluded from every denominator.

## Cost

$10.15 / 40 sessions (mean $0.25; recovery sessions run hotter than
the $0.19 phase-1 mean, as budgeted). Session total spend including
probes: ≈ $12.45.

## What the pilot bought

1. The full two-track harness is proven live: arms injected,
   receipts green, refusal armed, cost cap honored.
2. Two scorer false-positive classes caught and pinned by
   regression tests BEFORE any quotable run.
3. An honest read: today's baseline agent already verifies simple
   checkable claims; prevention traps need harder fixtures, not a
   rate run. Recovery differentials are the promising axis — 2-3×
   cheaper recovery with the rule surfaced — pending n.

No savings claims (insurance frame, #1291).
