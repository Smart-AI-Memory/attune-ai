---
name: recall
description: "Pull relevant findings stashed from past sessions — on demand. Triggers on: recall, remember, what did I learn, prior session, past findings, did I hit this before, what do we know about."
argument-hint: "<topic to recall | leave empty for recent>"
---

# Recall

**IMPORTANT: Start your response by telling the user:**

> **Recall** — Searching cross-session memory for findings related to
> your query.

## What It Does

`/recall` is the on-demand companion to the automatic SessionStart
recall. It searches the findings stashed by the Stop hook across past
sessions (file backend by default; Redis AMS when connected) and
surfaces the most relevant ones, formatted for reading.

- **With a query** (`/recall AMS event loop`): keyword + recency search,
  same-project findings ranked first.
- **No query** (`/recall`): the most recent findings for this project.

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

Each hit is a dict with `text`, `topics` (carrying `type:<kind>` and
`cwd:<path>`), `cwd`, and `session_id`. Render them as:

```
- [decision] <text>
- [bug] <text>
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

## Promote A Keeper

If a recalled finding is worth keeping permanently, the user can
promote it into curated memory with `/remember` — the durable,
human-curated tier above this raw cross-session stash.
