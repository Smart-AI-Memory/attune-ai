# Decisions: ops session discovery via `claude agents --json`

> Records the adopt-or-defer evaluation for replacing (or
> augmenting) attune-ops' filesystem-based session discovery with
> a structured CLI source. Research Preview — this doc is a
> snapshot; the decision matrix below was committed **before** the
> conclusion was asserted so the evidence routes the call.

**Status:** complete (recommendation: DEFER)
**Last updated:** 2026-06-08
**Author:** autonomous session (model-migration follow-up triage)

---

## Question

Should attune-ops' `/sessions` page derive its session list from
`claude agents --json` (a structured CLI source) instead of — or
in addition to — the current walk of
`~/.claude/projects/<encoded>*` JSONL files?

The weekly report flagged this as worth investigating, noting that
a `waitingFor` live-status field reportedly landed in CLI
**v2.1.162**.

---

## Decision matrix (pre-committed, before probing)

These thresholds were written down before running `claude agents
--help`, so the result couldn't move the goalpost:

| If the probe shows… | Then… |
| --- | --- |
| `claude agents --json` exists **and** emits structured session records (id, status, `waitingFor`, timestamps) in the installed CLI | **ADOPT** behind a feature flag; keep the filesystem walk as fallback for headless/cron. |
| The subcommand exists but has **no `--json`** (interactive TUI only), or the installed version predates the `waitingFor` field | **DEFER**; record the version + absence; design the adapter seam but don't build it. |
| The subcommand doesn't exist at all | **DEFER**; record absence; revisit at GA. |

---

## Evidence (probed 2026-06-08)

**Installed CLI version:** `2.1.144 (Claude Code)` — *below* the
v2.1.162 that reportedly introduced `waitingFor`.

**`claude agents` exists but is an interactive TUI**, not a data
source. `claude agents --help` describes it as "Manage background
agents" with an "agent view"; every flag configures *dispatching*
sessions (`--model`, `--permission-mode`, `--cwd`, `--mcp-config`,
…). There is **no `--json` flag**.

**`claude agents --json` is rejected:**

```
$ claude agents --json </dev/null
error: unknown option '--json'
```

So in the installed version there is no structured-output mode to
adopt, and even the `waitingFor` signal the report mentioned isn't
present (version is below where it reportedly landed).

---

## What the current filesystem discovery provides

Pure-filesystem, no CLI dependency. Lives in
[`src/attune/ops/data.py`](../../../src/attune/ops/data.py) and is
consumed by
[`src/attune/ops/routes/sessions.py`](../../../src/attune/ops/routes/sessions.py).

- `enumerate_project_encoded_keys()` resolves the project root to
  the encoded key (`path → path.replace('/','-')…`) and globs
  `~/.claude/projects/<encoded>*` — including per-worktree keys.
- `_parse_session()` reads each `<session-id>.jsonl` line-by-line
  (malformed lines skipped, never fatal) into a frozen `Session`.

`Session` fields derived from the JSONL:

| Field | Source |
| --- | --- |
| `id` | JSONL filename stem |
| `started_at` / `last_activity` | first / last event `timestamp` |
| `duration_seconds` | last − first timestamp |
| `message_count` | count of events carrying `content` |
| `starter_prompt` | heuristic truncation of first user prompt (S3 adds Haiku/cached) |
| `source` | `"heuristic"` (badge field reserved for future) |

It has **no live status** and **no `waitingFor`** — it can only
describe sessions as they were last written to disk.

---

## Comparison

| Dimension | Filesystem walk (current) | `claude agents --json` (hypothetical) |
| --- | --- | --- |
| Availability today | Works now, no deps | **Not available** (`--json` unknown at v2.1.144) |
| Live status / `waitingFor` | No — disk snapshot only | Would add it (at ≥ v2.1.162) |
| Structured fields | Derived/heuristic | Structured, first-class |
| Headless / cron runs | Robust (pure FS read) | Risky — CLI may be absent or unauthenticated in headless runs (existing repo lesson: interactively-authed surfaces can be missing in headless/cron) |
| Stability | Stable on a documented on-disk layout | **Research Preview** — output shape can change without notice |
| Cross-worktree coverage | Handled (`enumerate_project_encoded_keys`) | Depends on `--cwd` semantics; unverified |
| New dependency | None | Hard dep on a specific CLI version + its TUI/output contract |

---

## Recommendation: DEFER

The pre-committed matrix routes cleanly to **DEFER**: the installed
CLI has no `--json` mode for `claude agents`, and the version is
below where the `waitingFor` field reportedly appeared. There is
nothing to adopt today, and the filesystem walk remains the only
source that works in headless/cron runs regardless.

Re-evaluate when **both** hold:

1. `claude agents --json` (or an equivalent structured-output
   subcommand) ships in a **GA** (non-Research-Preview) CLI, and
2. the installed CLI is **≥ the version exposing `waitingFor`** (the
   live-status signal that is the actual reason to switch).

### Adapter seam to add when ready (do not build now)

Keep the filesystem walk as the default and authoritative source.
When the CLI source is GA, add it behind a feature flag without
ripping out the existing path:

- A `SessionSource` protocol with two methods (`list_sessions`,
  `get_session`) — the filesystem walk becomes
  `FilesystemSessionSource` (the default).
- A `ClaudeCliSessionSource` that shells `claude agents --json`,
  gated on an env flag (e.g. `ATTUNE_OPS_SESSION_SOURCE=cli`) and a
  CLI-version probe; it **falls back** to the filesystem source on
  any failure (non-zero exit, unknown flag, parse error, missing
  CLI), so headless/cron runs degrade gracefully.
- The CLI source enriches `Session` with the live fields
  (`status`, `waitingFor`) the filesystem walk can't see; the
  `source` badge field already reserved on `Session` surfaces which
  path produced each row.

This keeps the switch a small, reversible, flag-gated addition when
the upstream contract stabilizes — rather than a rip-and-replace
against a Research-Preview surface.
