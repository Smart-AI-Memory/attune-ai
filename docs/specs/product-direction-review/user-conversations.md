# User Conversations — DEC-2 Evidence Log

**Bar (from [assessment.md](assessment.md)):** 5 conversations with
humans who ran attune-ai on a real repo. Count: **0 of 5 VERIFIED**
(downgraded 2026-07-17 — conversation 1 likely did not meet the bar;
see its entry).

Record each conversation here within a day of having it. Unrecorded
signal doesn't compound (assessment-2026-07-11, N1).

**Inbound channel (weekend-plan Block 5, live 2026-07-12):**
[GitHub Discussion #1325](https://github.com/Smart-AI-Memory/attune-ai/discussions/1325),
"Did setup fight you? Tell me where." Linked from the README
quickstart, the CLI's bare `attune` welcome screen, and all three
setup-related error paths (no-auth preflight, `attune validate`,
the no-signal-stderr SDK failure). Any substantive reply counts
toward the 5.

---

## Channel measurement — 2026-07-17 (interim, not the 07-27 verdict)

Recorded per N1 (unrecorded signal doesn't compound) — this is data
now, 10 days before the verdict, not only on 07-27.

| Measure | Value | As of |
|---|---|---|
| Discussion #1325 comments | **0** | 2026-07-17 |
| Discussion #1325 upvotes | 1 | 2026-07-17 |
| Days live | 5 (since 07-12) | 2026-07-17 |
| Repo stars / forks / watchers | **9 / 0 / 1** | 2026-07-17 |
| Conversations logged | **0 of 5 verified** (1 recorded, downgraded) | 2026-07-17 |

**Interpretation (agent, kept separate from the data):** the channel
is not underperforming — it is fishing a pond of ~9, most of whom
likely never ran attune-ai on a real repo. Zero-contact inbound was a
sound bet given the cost (near-zero), but it cannot arithmetically
produce 4 more conversations by 07-27. Waiting is not a plan that
reaches the bar; it is a plan that reaches the verdict.

This is not yet the F1 answer. Silence from a channel nobody has been
pointed to is weaker evidence than silence after a direct ask —
outbound first would make the 07-27 silence *mean* something.

**Open decision (Patrick):** outbound (LinkedIn — the only audience
with demonstrated engagement — plus the 9 stargazers), or let 07-27
arrive and read the silence as the answer to F1.

---

## Outbound — 2026-07-17: LinkedIn ask POSTED (the DEC-2 decision, executed)

Patrick posted the direct ask to LinkedIn on 2026-07-17.
**URL (captured same day — gap not repeated this time):**
https://www.linkedin.com/posts/patrick-roebuck-attune-ai_ive-been-building-attune-ai-in-the-open-share-7483920107094810624-FuCy/ Final angle was Patrick's
own: setup-has-been-a-challenge / "if pip installing attune-ai gave
you trouble, I'd appreciate your help" — grounded in the verified
F1–F5 frictions and pointing the same direction as Discussion #1325.
The interview bar stays in the post's body: pip installed it AND
pointed it at a real repository; bounce stories explicitly invited.

This closes the "outbound vs read-the-silence" fork: **outbound,
chosen and executed.** From here, the 07-27 verdict reads the
RESPONSE to a direct ask, which means something — unlike silence from
a channel nobody was standing in.

**New population datum (Patrick, 2026-07-17, recorded same day):**
he has talked to **3 people** about attune-ai over the project's
life; **none ever got back to him** about running it. Whether Jacob
is among the 3 is unresolved (asked; pending). So the funnel to
date: 3 personal-network conversations -> 0 follow-throughs; product
channels -> 0 contacts; confirmed run-reports -> 0. The ask is now
public; replies get logged here within a day (N1), against the
four-question checklist kept under draft 1.

---

## Conversation 1 — 2026-07-08/09 — DOWNGRADED 2026-07-17: likely below the bar

**Recorded:** 2026-07-11 (verbal report from Patrick; two-day lag).
**Downgrade (2026-07-17, Patrick's recall):** the conversation was
almost certainly the **2026-07-08 phone call with Jacob** (calendar:
"jacob about apprentice", 1:00–2:00 PM) — an apprenticeship discussion
that ended with a mutual decision not to work together. Patrick: "I
don't think he ran it," and there was no other early-July candidate.
The bar requires a human who RAN attune-ai on a real repo, so this
conversation **does not count toward the 5**. The "setup issues"
signal below was therefore talk ABOUT the product, not a report from
running it — softer than this log originally implied. (The 07-11
fresh-machine reproduction stands on its own receipts: F1–F5 were
real, independently verified frictions regardless of this downgrade.)
**Sourcing datum that survives:** the one near-miss came through
Patrick's personal network by phone; the product channels (README,
CLI error paths, #1325) have produced zero. That is where 2–5 live.

### What the user said

- **Setup issues were the primary concern.** First and dominant
  product signal. Not a pillar complaint — a front-door complaint.
- General industry-trends discussion; shared conclusion that
  **architectural skills are core to working with AI coding tools
  successfully**.

### Not captured (ask next time)

- Which pillar(s) they actually touched, if setup let them get
  that far.
- What specifically broke or confused them in setup.
- Whether they would run it again unprompted.
- How the conversation was sourced (the repeatable part for
  conversations 2–5).

### Clarification — 2026-07-17 (Patrick, from memory)

Asked to discriminate, Patrick's recollection: the user's complaint was
that **workflows were broken**, and **"the problem with the workflows
stemmed from a setup problem."**

This closes the attribution question. One event, three vocabularies:
the user experienced *"your workflows are broken"*; the relay compressed
it to *"setup issues"* (as logged above); the friction log inferred
*"almost certainly F1."* All three are the same thing — a keyless
`attune workflow run` returning a 25-line traceback reading
`Exception: Claude Code returned an error result: success`.

**So F1's fix addresses this user's actual complaint**, and it is
shipped + verified (post-fix table, [setup-friction-log.md](setup-friction-log.md),
`fix/setup-friction` 6a628f2). Conversation 1's product finding is
CLOSED — not "probably F1", confirmed F1-class by the relayer.

**What this rules out:** the complaint was NOT dependency width, the
extras menu, or install weight. The log's own timeline records the
install as clean and fast (72 packages, ~40 s, no build errors). Any
packaging change (e.g. collapsing 22 extras to `attune-ai` +
`attune-ai[all]`) must be justified on its own merits — conversation 1
does not support it.

**Still unasked (needs the user, not the relayer):** whether they'd run
it again unprompted, and **how they found it** — the sole lead on where
conversations 2–5 come from. Both are blocked: no name, handle, or
channel was ever recorded.

### Interpretation (agent, kept separate from the data)

- One datum, but it lands squarely on the width critique (F4/June
  F4): ~402 dependency lines, optional extras, multi-package
  surface — the cost is paid at setup, by the first real user to
  report anything.
- Half the conversation was industry trends. Useful personally
  (see action below), but the DEC-2 bar is product evidence — the
  four questions above are the checklist for the next four calls.

### Action taken by Patrick

- Prioritize the Anthropic architecture course — personal skill
  investment prompted by the shared conclusion above.

---

## Conversation 2 — *(open)*

## Conversation 3 — *(open)*

## Conversation 4 — *(open)*

## Conversation 5 — *(open)*
