---
name: recall
description: "Pull relevant findings stashed from past sessions — on demand. Triggers on: recall, remember, what did I learn, prior session, past findings, did I hit this before, what do we know about."
argument-hint: "<topic | empty for recent | drop <id> | review>"
---

# Recall

**IMPORTANT: Start your response by telling the user:**

> **Recall** — Searching cross-session memory for findings related to
> your query.

## What It Does

`/recall` is the on-demand companion to the automatic SessionStart
recall. It searches TWO stores and labels results by source:

1. **Session findings** — stashed by the Stop hook across past
   sessions (file backend by default; Redis AMS when connected).
2. **The lessons corpus** — the repo's accumulated engineering
   lessons, retrieved via `attune.lessons.LessonsIndex` (query mode
   only; lessons have no recency, so the no-query mode skips them).

- **With a query** (`/recall AMS event loop`): both stores; session
  findings keyword + recency ranked, lessons by retrieval score.
- **No query** (`/recall`): the most recent session findings for
  this project.

## Pick Your Transport First

Route by what YOUR client can actually do — never assume the
universal Python recipe works everywhere (in a sandboxed provider
it selects an unwritable file tier or a blocked socket):

1. **MCP available** — the `session_memory_*` tools appear in your
   tool list (Codex, Claude Code with the attune MCP server, any
   MCP client): use them. They execute host-side, outside your
   sandbox, and carry the full contract (sanitization, cwd scoping,
   TTL). **Never run in-process Python for memory from a sandboxed
   client, and never substitute raw `redis_memory_store` for
   finding capture — capture goes through `session_memory_capture`
   only.**
2. **Trusted host context, no MCP** — you can run repo Python
   directly (Claude Code Bash, the CLI, lifecycle hooks): the
   Python snippets below remain valid.
3. **Neither** — report honestly that cross-session memory is
   unavailable in this client (no MCP tools, no trusted Python).
   Do not fake results and do not claim the backing service is
   down — you cannot know that from here.

## MCP Tools

| Tool | Use |
|------|-----|
| `session_memory_recall` | Semantic search (args: query, optional top_k, cwd) |
| `session_memory_recent` | Newest findings, no query (args: top_k, cwd) |
| `session_memory_capture` | Stash a finding (args: content, type, tags, cwd) |
| `session_memory_forget` | Delete by full record id (args: ids, cwd) |
| `session_memory_status` | Caller-scoped backend status |

Pass the project root as `cwd` so same-project findings rank first.
Every result carries `ok`; a failed write is `{ok: false, reason:
<code>}` — surface the reason (`no_backend`, `file_write_denied`,
`not_found`, …) instead of pretending success. The lessons-corpus
search has no MCP tool — in MCP-only clients skip the lessons
section silently; session findings still render.

## Trusted-Host Python

Recall is exposed through `attune.memory.session_stash`. Run the
appropriate snippet via Bash from the project root, then present the
results as a readable list (newest / most-relevant first), grouped or
annotated by their `[type]`.

**With a query:**

```bash
python -c "import json, os; from attune.memory.session_stash import recall_entries, backend_status; print(json.dumps({'status': backend_status(), 'hits': recall_entries(os.environ['Q'], top_k=8, cwd=os.getcwd())}, ensure_ascii=False))"
```

Pass the user's topic as the `Q` environment variable (avoids quoting
issues), e.g. `Q="AMS event loop" python -c "..."`.

**No query (recent):**

```bash
python -c "import json, os; from attune.memory.session_stash import recent_entries, backend_status; print(json.dumps({'status': backend_status(), 'hits': recent_entries(top_k=8, cwd=os.getcwd())}, ensure_ascii=False))"
```

**Lessons corpus (query mode only — run alongside the findings
search):**

```bash
Q="<topic>" python -c "import json, os; from attune.lessons import LessonsIndex; idx = LessonsIndex(); print(json.dumps([{'title': h.entry.summary, 'score': h.score, 'body': h.entry.content[:600]} for h in idx.retrieve(os.environ['Q'], k=3)], ensure_ascii=False))"
```

If this raises (older install without `attune.lessons`, or
attune-rag missing), skip the lessons section silently — session
findings still render.

## Rendering Results

Each session-finding hit is a dict with `text`, `topics` (carrying
`type:<kind>` and `cwd:<path>`), `cwd`, and `session_id`; each
lesson hit has `title`, `score`, and a `body` excerpt. Render them
in two labeled groups — findings first, lessons after:

```
- [decision] <text>
- [bug] <text>
- [lesson] <title> — <one-line gist from the body>
```

**Always name the answering backend** (from `status.backend`; over
MCP, `session_memory_status` reports it with `transport: "mcp"` and
the Python layer as `backend_transport`) in one short line, e.g.
"(searched via AMSMemoryBackend)".

**Truthful status language** — status is caller-scoped:

- `unreachable_upgrade` set: lead with a warning before any
  results — the named upgrade backend (e.g. Redis AMS) is
  unreachable *from this caller*, recall is degraded to the local
  file tier, and findings stored in the upgrade tier are dark until
  it is reachable again.
- `reachability: "unreachable_local"` (with a `reason` such as
  `file_write_denied`): THIS process cannot write the stash — a
  sandbox denial. Say exactly that. **Never report "Redis is down"
  or "memory is broken" from a local denial** — a sandboxed probe
  proves nothing about the service; route via MCP instead.

## When Nothing Comes Back

An empty `hits` list means no matching findings yet (the store fills
as the Stop hook stashes findings over sessions), or no searchable
backend is available. Say so plainly — do **not** invent findings,
and do name the backend that answered: "no hits" from the file tier
while `status.unreachable_upgrade` is set means the real store may
simply be dark, not empty. Suggest the user keep working; the soak
fills the store over time.

## Review / Drop Findings

The stash chip (`🧠 Stashed N session finding(s)…`) shows each
finding with a short id like `` `3f2a9c1b` ``. Two correction modes:

**`/recall drop <id> [<id> ...]`** — delete specific findings by
short id prefix.

- *MCP path:* fetch candidates with `session_memory_recent`, match
  each prefix against the returned `id` fields, and delete exact,
  UNAMBIGUOUS matches with `session_memory_forget` (full ids only).
  A prefix matching zero or multiple records is skipped — deletion
  never guesses; show the candidates so the user can retry with a
  longer prefix.
- *Trusted-host path:*

```bash
IDS="3f2a9c1b,77bd0e21" python -c "import os; from attune.memory.session_stash import forget_by_prefix; print(forget_by_prefix(os.environ['IDS'].split(','), cwd=os.getcwd()))"
```

Report how many were deleted, and which prefixes were skipped.

**`/recall review`** — interactive pruning. Fetch the recent
findings (either transport), then present ONE multi-select question —
via the `elicitation_render_form` MCP tool when available (a single
`multi_select` field; map to `AskUserQuestion` with
`multiSelect: true`), else directly via `AskUserQuestion` — where
each option is one finding: label = short id + `[type]`, description
= the finding text (truncated ~100 chars). Question: "Which findings
should be deleted?" Then delete the picked ids (same transport rules
as `drop`) and report the count. If the user picks nothing, delete
nothing.

## Promote A Keeper

If a recalled finding is worth keeping permanently, the user can
promote it into curated memory with `/remember` — the durable,
human-curated tier above this raw cross-session stash.
