---
name: recall
description: "Pull relevant findings stashed from past sessions — on demand. Triggers on: recall, remember, what did I learn, prior session, past findings, did I hit this before, what do we know about."
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

## How To Run It

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

Each session-finding hit is a dict with `text`, `topics` (carrying
`type:<kind>` and `cwd:<path>`), `cwd`, and `session_id`; each
lesson hit has `title`, `score`, and a `body` excerpt. Render them
in two labeled groups — findings first, lessons after:

```
- [decision] <text>
- [bug] <text>
- [lesson] <title> — <one-line gist from the body>
```

**Always name the answering backend** (from `status.backend`) in one
short line, e.g. "(searched via AMSMemoryBackend)". If
`status.unreachable_upgrade` is set, lead with a warning before any
results: the named upgrade backend (e.g. Redis AMS) is down, recall is
degraded to the local file tier, and findings stored in the upgrade
tier are unreachable until it's restarted.

## When Nothing Comes Back

An empty `hits` list means no matching findings yet (the store fills as
the Stop hook stashes findings over sessions), or no searchable backend
is installed. Say so plainly — do **not** invent findings, and do name
the backend that answered: "no hits" from the file tier while
`status.unreachable_upgrade` is set means the real store may simply be
dark, not empty. Suggest the user keep working; the soak fills the
store over time.

## Review / Drop Findings

The stash chip (`🧠 Stashed N session finding(s)…`) shows each
finding with a short id like `` `3f2a9c1b` ``. Two correction modes:

**`/recall drop <id> [<id> ...]`** — delete specific findings by
short id prefix. Run:

```bash
IDS="3f2a9c1b,77bd0e21" python -c "import os; from attune.memory.session_stash import forget_by_prefix; print(forget_by_prefix(os.environ['IDS'].split(','), cwd=os.getcwd()))"
```

Report how many were deleted. A prefix matching zero or multiple
records is skipped (deletion never guesses) — tell the user which
ids were skipped and show the candidates via the recent-findings
snippet so they can retry with a longer prefix.

**`/recall review`** — interactive pruning. Fetch the recent
findings (snippet above), then present ONE multi-select question —
via the `elicitation_render_form` MCP tool when available (a single
`multi_select` field; map to `AskUserQuestion` with
`multiSelect: true`), else directly via `AskUserQuestion` — where
each option is one finding: label = short id + `[type]`, description
= the finding text (truncated ~100 chars). Question: "Which findings
should be deleted?" Then delete the picked ids with the
`forget_by_prefix` snippet and report the count. If the user picks
nothing, delete nothing.

## Promote A Keeper

If a recalled finding is worth keeping permanently, the user can
promote it into curated memory with `/remember` — the durable,
human-curated tier above this raw cross-session stash.
