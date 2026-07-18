---
name: roundtable
description: "Convene the multi-LLM round table — Claude, Antigravity, and Codex deliberate a question; the user chairs promotion. Triggers on: roundtable, round table, convene the table, ask the table, what do the other models think, deliberate."
---
# Round Table

**IMPORTANT: Start your response by telling the user:**

> **Round table** — Convening the fixed roster (Claude, Antigravity,
> Codex). You chair; I moderate. Up to 3 rounds.

## What It Does

A moderated deliberation (Phase 1 of
`docs/specs/agent-round-table`): the user poses a question, each
roster member answers headlessly and independently, the moderator
(this session) posts every message to the Redis board, synthesizes,
and presents the result. Only the chair — the user — promotes
anything into a tracked artifact.

Invariants (ratified — do not improvise around them):

- **R1** Members are text-in/text-out. They never touch Redis,
  files, or shell. All board I/O goes through the moderator via
  the `Board` client (`attune.roundtable`).
- **R3** Board state lives only under `attune:roundtable:*`
  (TTL 7 days). Never write `attune:memory:*`.
- **R4** Nothing reaches a tracked file without explicit per-item
  chair approval. No auto-promotion, ever.
- **D3** Hard ceiling: 3 rounds per question. Halt early when
  positions converge or a round adds no information.

## Step 0 — Intake and the spend gate

Confirm the question with the user (one short exchange if it is
ambiguous; skip if crisp). Derive a thread slug
(`kebab-case`, e.g. `q-cache-invalidation-002`). Then state the
plan — roster, expected rounds (usually 1) — and get an explicit
go before invoking any member. That go is session-durable.

If Redis is unreachable (`Board()` raises on first call): tell the
chair. Offer to deliberate unrecorded (transcript stays in-session;
promotion still writes artifacts) or abort. Never block silently.

## Step 1 — Open the thread

Write the question to a scratch file, then post it:

```bash
T="<slug>" A="chair" K="question" F="/tmp/rt-q.txt" python -c "import os; from attune.roundtable import Board; b=Board(); b.ensure_functions(); print(b.post_message(os.environ['T'], os.environ['A'], os.environ['K'], open(os.environ['F']).read()))"
```

## Step 2 — Brief the members (round 1)

Write one brief per member to a scratch file. Brief template:

```text
You are one seat at a three-model round table (Claude, Antigravity,
Codex). Answer independently; you cannot see the other seats this
round. Reply with: (1) your POSITION on the question, concretely;
(2) the main RISK of your own position; (3) optionally ONE follow-up
question for the table. Text only — do not run tools, write files,
or take actions. Question:

<question text, plus any round-N context — see Step 4>
```

Invoke all three (verified recipes; run the two CLIs in parallel
Bash calls, each with a timeout of ~180s):

- **Claude seat** — Agent tool, `general-purpose`, context-free:
  pass the brief verbatim as the prompt; its final text is the
  reply.
- **Antigravity** — reasoning-only plan mode (shell is auto-denied
  headlessly, which is what R1 wants):

```bash
agy --add-dir "$PWD" -p "$(cat /tmp/rt-brief.txt)" --mode plan
```

- **Codex** — brief on stdin (the arg-prompt form blocks forever on
  non-TTY stdin):

```bash
codex exec --skip-git-repo-check - < /tmp/rt-brief.txt
```

## Step 3 — Post positions with receipts

For each member, write its reply to a scratch file and post it as a
`position` authored by the provider, carrying the R7 receipt fields
(and `round`):

```bash
T="<slug>" A="codex" F="/tmp/rt-codex.txt" DUR="41s" python -c "import os; from attune.roundtable import Board; b=Board(); print(b.post_message(os.environ['T'], os.environ['A'], 'position', open(os.environ['F']).read(), round=1, duration=os.environ['DUR']))"
```

Add token/cost figures as extra kwargs when the CLI reported them.

**Absent seat (R6):** a member whose CLI is missing, unauthenticated,
or times out never blocks the table. Post
`kind='position'`, body `ABSENT — <reason>`, extra `absent=True`,
and proceed. The table degrades to however many seats answered.

**Member-originated items (R9):** if a reply contains a follow-up
question or an unprompted suggestion, post it as its own message
(`kind='question'` or `'suggestion'`, author = that provider,
`reply_to` = the position's id). Origination grants no execution
rights — triage it to the chair in Step 5.

## Step 4 — Further rounds (bounded)

Run another round only if member follow-up questions (R9) need
answers or positions genuinely diverge on a decidable point. The
round-N brief appends the prior round's positions (as plain text,
attributed by seat) and the open follow-ups. Repeat Steps 2–3 with
`round=N`.

Halt early on convergence. At the ceiling (3 rounds) or any budget
the chair set, stop and post the halt (R5):

```bash
T="<slug>" python -c "import os; from attune.roundtable import Board; Board().post_message(os.environ['T'], 'moderator', 'halt', 'round ceiling (3) reached')"
```

## Step 5 — Synthesize and present

Post one `synthesis` message (author `moderator`): where seats
agree, where they split and why, and the moderator's read. Then
present to the chair: a compact per-seat position table, the
synthesis, member-originated items needing triage, and promotion
candidates. Read the thread back any time with:

```bash
T="<slug>" python -c "import os, json; from attune.roundtable import Board; print(json.dumps([vars(m) for m in Board().read_thread(os.environ['T'])], ensure_ascii=False, default=str))"
```

## Step 6 — Chair rules; promote (R4, R10, D2)

Ask the chair per item: promote, decline, or another round. Use
`AskUserQuestion` (or an elicitation form) — never assume. On
promotion:

1. Recommend an artifact tier per the contract's artifact-selection
   table — inline edit / structured one-shot / XML task / spec —
   sized to what the table produced. The chair ratifies the tier.
2. Destination (D2): the owning spec's `decisions.md` when a spec
   exists; else `docs/reports/roundtable/<slug>.md`. The artifact
   records the thread id it came from.
3. Write the artifact, then mark the thread:

```bash
T="<slug>" D="docs/reports/roundtable/<slug>.md" python -c "import os; from attune.roundtable import Board; Board().promote(os.environ['T'], os.environ['D'])"
```

Post the chair's decision as a `ruling` message (author `chair`).
Declined items get no file writes — `git status` stays clean.

Deliberation is TTL'd; only promoted content is durable. If the
chair wants a raw thread kept past 7 days, promotion to a report is
the mechanism — say so rather than extending TTLs ad hoc.

## Arguments

- `/roundtable <question>` — full deliberation (Steps 0–6).
- `/roundtable read <thread>` — read and render an existing thread
  (Step 5's read snippet); no member invocations.
- `/roundtable promote <thread>` — jump to Step 6 for a thread that
  already deliberated.
