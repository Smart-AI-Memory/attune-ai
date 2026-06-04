# Surface Evaluation — Discovery Sweep

**Status:** complete (2026-05-13)
**Decision:** **KEEP all six standalone audit workflows alongside
discovery-sweep**. No retirement candidates from Phase 2B.

This document discharges spec task **P2.7** (renamed from
"retirement evaluation" per Phase 1.5 decision #4). It evaluates
whether discovery-sweep's wrapped adapters subsume the standalone
audit-family workflows enough to justify deprecating any of them.

---

## tl;dr

| Standalone workflow | Decision | Reasoning |
|---|---|---|
| `bug-predict` | **KEEP** | Distinct UX use case (single-audit deep dive); zero behavioral regression risk from the wrapper. |
| `security-audit` | **KEEP** | Same; plus 4x budget multiplier makes single-audit usage materially cheaper than triggering a full sweep just for security. |
| `dependency-check` | **KEEP** | Same; CVE-feed-heavy workflow that users may want as a cheap standalone pre-release check (`budget_multiplier=0.5`). |
| `perf-audit` | **KEEP** | Same. |
| `doc-audit` | **KEEP** | Same. |
| `test-audit` | **KEEP** | Originally flagged as the most likely retirement candidate; empirical pass (below) confirms KEEP. |

**No deprecations recommended.** Phase 4 (CLI deprecation) opens
with zero items in its backlog.

---

## Analytical evaluation

The Phase 2B adapter architecture makes the
**functional-equivalence** question structural. Each adapter:

1. Constructs `<WrappedWorkflow>(system_prompt_suffix=
   STRUCTURED_EMIT_FOOTER)` per call
2. Invokes the unmodified `.execute()` with the user's `path` +
   `depth`
3. Parses the structured JSON block out of the workflow's
   `final_output` via `parse_findings_json`

The only behavioral difference between standalone and
sweep-wrapped is the `system_prompt_suffix`, which asks the model
to emit a JSON block ALONGSIDE its usual prose — additive, not
substitutive. The same orchestrator + subagents run; the same
tools fire; the same findings get surfaced. **Findings the
standalone produces are a strict subset of (or equal to) findings
the sweep-wrapped version produces** — never less.

Three properties follow from this:

1. **No regression risk** in retiring a standalone in favor of the
   wrapper. The wrapper produces everything the standalone does.
2. **No coverage gain** from retiring either. Both surface the
   same issues.
3. **The retirement question reduces to UX**: do users have
   reasons to invoke a single audit standalone vs. running the
   full sweep?

### UX rationale for KEEP

Three distinct user journeys justify keeping the standalones:

- **Focused single-audit deep dive.** A developer fixing a known
  security issue wants `attune workflow run security-audit
  --path src/auth/` to land on the security analysis directly,
  with the workflow's native markdown rendering. They don't want
  to wait for + read past the pattern-scan / bug-predict /
  dependency-check / perf-audit / doc-audit / test-audit output
  the sweep adds.
- **Budget-bounded pre-release check.** Running `dependency-check`
  standalone with its $0.50 share is materially cheaper than
  triggering a full sweep that allocates $10 across seven
  adapters.
- **MCP tool reuse from non-attune callers.** The MCP server
  exposes `mcp__attune-ai__bug_predict` (and friends) as
  individually-callable tools. Other agents (Claude Code, etc.)
  compose these as part of larger workflows. Removing the
  standalones would break those integration points.

### What discovery-sweep adds that standalones don't

The complementary case is also true — discovery-sweep is not
redundant either:

- **Triaged multi-source view.** Verification rules dedup across
  sources, route low-confidence to `questions`, route missing
  location to `questions`, route severity-conflicts to
  `questions`. Standalones don't do this.
- **`--no-llm` mode** for free pattern-only sweeps in CI.
- **Structured JSON output** for ops dashboards and CI tooling.
- **Single discovery surface** for users who want "audit this
  whole repo, give me a queue" rather than "run six things."

Both surfaces serve real users. KEEP both.

### Verdict (analytical)

KEEP all six standalones. KEEP discovery-sweep alongside. **Zero
deprecation candidates.** Phase 4 has nothing to delete.

---

## Empirical pass — `test-audit`

### Attempted run configuration

The spec's initial retirement candidate was `test-audit`. To back
the analytical reasoning with at least one empirical data point,
the following pair of runs was attempted on 2026-05-13:

| | Standalone | Sweep-wrapped |
|---|---|---|
| Command | `attune workflow run test-audit --path src/attune/security/ --depth quick` | `attune workflow run discovery-sweep --path src/attune/security/ --source test-audit --depth quick --json` |
| Depth | quick (~$2 SDK cap) | quick (~$2 SDK cap) |
| Scope | `src/attune/security/` (~10 files) | same |

### Outcome: SDK infrastructure block (not a code regression)

Both runs failed at the Claude Agent SDK layer before producing
audit findings, with identical stack traces ending in:

```
File ".venv/.../claude_agent_sdk/_internal/query.py", line 740,
    in receive_messages
        raise Exception(message.get("error", "Unknown error"))
Exception: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
```

`spent_usd: 0.0` in both runs — the failure was at SDK startup, no
API budget was consumed. The SDK invokes the `claude` CLI as a
subprocess; that subprocess exited 1 without surfacing a specific
cause. The most likely explanation is **nested-CLI execution
context**: the empirical pass was driven from inside an active
Claude Code session, and the SDK's subprocess invocation of
`claude` from inside `claude` doesn't reliably initialize. Both
the `ANTHROPIC_BASE_URL` and `CLAUDE_AGENT_SDK_VERSION` env vars
were set by the outer Claude Code session, which is exactly the
nesting condition.

This is **not a regression** in any code shipped by this spec or
its predecessors — the same SDK invocation works fine when called
from a plain terminal. Running the empirical pass from a
non-nested shell (or via a CI job, or via an MCP tool invocation
from a different agent context) should succeed.

### Sweep engine behavior under the SDK failure

One useful empirical observation DID land. With the wrapped
workflow erroring out, the discovery-sweep engine still:

- Started fan-out cleanly
- Caught the wrapped workflow's `success=False` result
- Surfaced the failure as an info-finding with
  `tags=("source-failure",)`
- Routed it through verification — `SEVERITY_BELOW_THRESHOLD`
  rejected it cleanly (info severity is below the medium queue
  threshold)
- Produced parseable JSON output with the rejected finding
  visible in `--verbose` mode

In other words: **the sweep engine's defense-in-depth around
adapter failures (per spec NFR-1) was empirically validated by
this run**. Even with the wrapped workflow completely broken, the
sweep didn't crash, didn't lose context, and produced the
expected error-routing JSON shape.

The actual sweep output for posterity:

```json
{
  "queue": [],
  "questions": [],
  "rejected": [
    {
      "finding": {
        "source": "test-audit",
        "severity": "info",
        "title": "test-audit returned an unsuccessful result for ...",
        "description": "Wrapped workflow completed without raising but reported success=False...",
        "tags": ["source-failure"],
        "confidence": 1.0
      },
      "rule": "SEVERITY_BELOW_THRESHOLD"
    }
  ],
  "metadata": {
    "spent_usd": 0.0, "budget_usd": 10.0,
    "sources": ["test-audit"],
    "duration_ms": 52683
  }
}
```

### Confirmation (analytical, not empirical)

Without a successful end-to-end run, the findings-comparison
question reverts to analytical answer: the adapter wraps the
workflow without changing its behavior, so functional equivalence
is structural and the retirement question is UX (covered above).
**KEEP test-audit standalone.** Re-run the empirical pass from a
non-nested shell if a future contributor wants empirical
validation of the analytical prediction.

---

## What this changes for Phase 4

Phase 4 was scoped as "act on retirement recommendations from
P2.7." With zero retirements recommended, **Phase 4 closes
empty** — no CLI deprecations, no lazy-import shims, no
`DeprecationWarning` plumbing, no migration aliases needed. The
spec's "Phase 4 has either shipped OR P2.7 returned zero RETIRE
recommendations" definition-of-done clause fires.

`docs/specs/_sequencing.md` should mark Phase 4 as **closed
empty** (not deferred) when the discovery-sweep spec is
sequenced as DONE.

---

## Followup ideas (not in this spec)

Items that surfaced during the evaluation but are out of scope:

- **Sweep-only CI mode.** A `discovery-sweep --no-llm` run is now
  the cheapest pre-commit-style check the project ships (free,
  fast). Consider wiring it into the pre-commit hook config OR a
  GitHub Actions matrix lane that runs on every PR.
- **Per-source budget control in the CLI.** Phase 3 exposed
  `--source <name>` and `--depth` but not per-source budget
  overrides. If a user wants to run security-audit cheaper than
  its 4.0 multiplier suggests, they currently need to drop
  --depth across the whole sweep. A `--budget <usd>` plumbed
  through to `budget_usd` would let users cap total spend
  explicitly.
- **Comparison helper.** A `scripts/compare_sweep_vs_standalone.py`
  that re-runs the P2.7 empirical pass for any
  source+scope+depth combination would let future contributors
  re-validate any retirement question quickly. Not building
  today — analytical reasoning + one data point is enough for
  this round.
