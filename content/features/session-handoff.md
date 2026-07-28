---
feature: session-handoff
summary: Cross-provider session handoff — verified packet create/resume so any agent can pick up a branch mid-flight
tags: [handoff, collaboration, multi-llm, memory]
source_globs:
  - src/attune/handoff/__init__.py
  - src/attune/handoff/packet.py
  - src/attune/handoff/verify.py
  - src/attune/handoff/memory_link.py
nav:
  help: session-handoff
  mkdocs:
    how-to: how-to/session-handoff
    architecture: architecture/session-handoff
    reference: reference/session-handoff
---

## Overview

Session-handoff lets one agent session hand a branch's in-flight work
to another — including a session run by a *different provider* — with
the claims and the facts kept separate. `handoff_create` assembles a
packet for the current branch: the git-derived fields (branch, head
SHA, merge base, changed files) are read from git at call time and
recorded as **verified**; the caller's prose (goal, acceptance
criteria, current state, next action) is recorded verbatim as
**asserted**. `handoff_resume` reads the packet back and re-checks
every verified field against the current tree, reporting drift as
warnings.

The receiving side gets a **report, not a go signal**: resume never
checks out branches, never writes, never runs tests. It tells the
next session what was claimed, what is still true, and what moved —
the session decides what to do with that.

Both operations are exposed as MCP tools on the attune server, so any
MCP client — Claude Code, Codex, Antigravity — can create or resume a
packet. There is deliberately no CLI wrapper yet (MCP-only at ship;
a CLI waits for a usage signal).

## Concepts

### The packet: verified frontmatter, asserted body

A packet is one markdown file per branch at
`docs/handoffs/<branch-slug>.md` (slug = branch name with `/` as
`-`). YAML frontmatter carries the machine-verified fields —
`branch`, `head_sha`, `merge_base`, `changed_files`, `created_at`,
`provider`. The markdown body holds the asserted prose sections. This
keeps the file human-readable while making verification mechanical:
resume re-derives the frontmatter facts from git and surfaces the
body untouched under `asserted`.

### Verification rows never claim what was not run

The packet's verification table records claims and probes. A row's
`result` defaults to **"not run"** — a caller cannot fabricate a
passing probe through the create surface. The receiving session
re-runs probes itself and updates its own record.

### The drift report

Resume compares the packet against the live tree and emits report-only
warning codes — never blocking, never auto-fixed:

- `branch_missing` — the packet's branch is absent from the repo
- `head_moved` — current HEAD differs from the packet's `head_sha`
- `files_diverged` — the actual diff set differs from
  `changed_files`
- `packet_stale_days` — the packet is older than 7 days
- `dirty_tree` — uncommitted changes are present at resume time

Report keys come in authority order: `verified`, `warnings`,
`asserted`, `memory`.

### Caps and overwrite semantics

Packets are terse by contract: 2048 bytes per field, 8192 bytes per
rendered packet. Oversize input is rejected with
`{ok: false, reason: "field_over_cap", field, limit}` — never
silently truncated. Re-creating a packet for the same branch
overwrites in place (one packet per branch); the previous packet's
`created_at` is preserved as `superseded_at` so staleness stays
honest.

### Memory linkage, degrade-silent but stated

Create stashes a topic-`handoff` pointer through the session-stash
helpers (the same sanitized path `session_memory_capture` uses);
resume recalls pointers for the slug. When no memory backend is
reachable, the report says so instead of erroring or omitting:
`memory: {status: "skipped", reason: "no_backend"}`. An empty recall
is honestly `{status: "recalled", count: 0}` — a skip and a miss are
different facts.

## Quickstart

From any MCP client with the attune server connected, on the branch
you want to hand off:

```json
{
  "tool": "handoff_create",
  "arguments": {
    "goal": "Ship the retry-loop fix with a regression test",
    "next_action": "Run the failing test, then re-run the full suite",
    "provider": "claude-code"
  }
}
```

The receiving session — any provider — resumes with no arguments
(defaults to the current branch):

```json
{ "tool": "handoff_resume", "arguments": {} }
```

Or from Python:

```python
from attune.handoff import handoff_create, handoff_resume

created = handoff_create(".", goal="Ship the retry-loop fix", provider="claude-code")
report = handoff_resume(".")
print(report["warnings"], report["asserted"]["goal"])
```

## Tasks

### Create a handoff packet for the current branch

```python
from attune.handoff import handoff_create

result = handoff_create(
    ".",
    goal="What should be true when this work is complete",
    acceptance_criteria="Concrete completion conditions",
    current_state="Status, decisions, risks",
    next_action="One concrete ordered action",
    provider="claude-code",
)
assert result["ok"], result
print(result["path"])  # docs/handoffs/<branch-slug>.md
```

### Resume a packet and read the drift report

```python
from attune.handoff import handoff_resume

report = handoff_resume(".")
if report["ok"]:
    for warning in report["warnings"]:
        print(warning["code"], warning["detail"])
```

### Record verification claims without fabricating results

```python
from attune.handoff import handoff_create

handoff_create(
    ".",
    goal="Land the fix",
    verification=[{"claim": "unit suite green", "probe": "pytest -q tests/unit"}],
)
# The stored row's result is "not run" — the receiver re-runs probes.
```

## Reference

### Python API (`attune.handoff`)

| Function | Signature (keyword-only after `repo_root`) | Returns |
| --- | --- | --- |
| `handoff_create` | `repo_root=\".\"`, `goal`, `acceptance_criteria`, `scope_assumptions`, `current_state`, `next_action`, `verification`, `provider`, `base_ref=\"origin/main\"` | `{ok, path, slug, packet, memory}` or `{ok: False, reason}` |
| `handoff_resume` | `repo_root=\".\"`, `slug=None` (defaults to current branch) | `{ok, slug, path, verified, warnings, asserted, memory}` or `{ok: False, reason}` |

### MCP tools

| Tool | Required args | Notes |
| --- | --- | --- |
| `handoff_create` | `goal` | Optional: `acceptance_criteria`, `scope_assumptions`, `current_state`, `next_action`, `verification` rows, `provider` |
| `handoff_resume` | none | Optional `slug`; defaults to the current branch |

### Constants

| Constant | Value | Meaning |
| --- | --- | --- |
| `attune.handoff.packet.PACKET_CAP_BYTES` | 8192 | Max rendered packet size |
| `attune.handoff.packet.FIELD_CAP_BYTES` | 2048 | Max per-field size |
| `attune.handoff.verify.STALE_AFTER_DAYS` | 7 | Age before `packet_stale_days` fires |

### Failure reasons

| Reason | Surface | Meaning |
| --- | --- | --- |
| `field_over_cap` | create | A prose field exceeded 2048 bytes |
| `git_read_failed` | both | Git state could not be read |
| `packet_not_found` | resume | No packet exists for the slug |
| `invalid_slug` | resume | Slug failed path validation |
| `packet_unreadable` | resume | File unreadable or malformed |

## Comparison

- **vs. the handoff *contract* file alone** — the collaboration
  contract already tracks `docs/handoffs/<branch-slug>.md` as a
  hand-written file. Session-handoff keeps that location and template
  but makes the facts machine-derived and re-checkable: a receiving
  agent no longer has to trust that the listed SHA or file set is
  current.
- **vs. session memory (`session_memory_*`)** — the stash carries
  small cross-session findings; a handoff packet carries one branch's
  full working state. They link: create stashes a pointer so recall
  surfaces the handoff, but the packet file is the artifact.
- **vs. `/spec` documents** — a spec captures multi-session design
  intent; a packet captures a moment: this branch, this HEAD, this
  next action.

## Failure modes

- **Resume warns `head_moved` / `files_diverged` on your own
  branch** — someone (possibly you, in another session) committed
  after the packet was created. Read the diff before trusting the
  packet's `current_state`; re-create the packet after material
  changes.
- **`memory: skipped` with `no_backend`** — the memory tier is
  unreachable from this process. The packet itself is unaffected;
  recall-based discovery of the handoff just will not fire.
- **Cap rejections on create** — the packet is a pointer, not a
  design doc. Move long prose into the spec or the branch's docs and
  reference it from the packet.
- **A stale packet (`packet_stale_days`)** — packets outlive their
  usefulness fast; treat one older than a week as archaeology, not
  instruction.

## FAQ seeds

- **Q:** Does resume switch me to the packet's branch?
  **A:** No. Resume performs no side effects — no checkout, no
  writes, no test runs. It reports; you act.
- **Q:** Can I hand off between different AI providers?
  **A:** Yes — that is the point. Any client of the attune MCP
  server can create or resume: Claude Code, Codex, and Antigravity
  all reach the same tools, and the packet's `provider` field
  records who authored it.
- **Q:** What happens if I create a packet twice on one branch?
  **A:** The second create overwrites in place, and the first
  packet's `created_at` is preserved as `superseded_at` in the
  frontmatter.
- **Q:** Is there a CLI command?
  **A:** Not yet, deliberately — the surface is MCP-only until real
  usage justifies a wrapper.

## Notes & tips

- Delete the packet when its branch merges — the file is branch-scoped
  working state, not documentation.
- Fill `verification` rows with the probes you actually intend the
  receiver to run; the "not run" default keeps everyone honest.
- Both tools emit one structlog event each (`handoff_create`,
  `handoff_resume`) with the slug, warning codes, duration, and the
  memory outcome — provider-boundary usage shows up in telemetry
  reads.

## Design & extension

The module splits on the authority seam. `attune.handoff.verify` owns
every git read — read-only subprocess calls (`branch
--show-current`, `merge-base`, `diff --name-only`, `rev-parse`) with
validated paths and no mutating commands, so resume works in
read-restricted sandboxes. `attune.handoff.packet` owns
render/parse/caps for the packet file. `attune.handoff.memory_link`
owns the degrade-silent memory linkage; every failure path returns a
stated `{status: "skipped", reason}` rather than raising. The public
API (`handoff_create` / `handoff_resume`) is pure functions returning
dicts with no MCP imports — the MCP layer is a thin adapter, which is
what makes the tools equally reachable from every provider's client.

Extension points deliberately deferred: a CLI wrapper (waits for MCP
usage signal), auto-invocation hooks (non-goal — handoffs are
deliberate acts), and cross-repo packets (a packet is branch-scoped
within one repo).

Spec: `docs/specs/cross-provider-session-handoff/` — requirements
R1–R6, design D1–D6, and the receipts ledger.
