# Adaptive session interactions — T4 protocol (preregistered)

**Status:** FROZEN 2026-09-05 (decisions D10). Amending this file after
freeze requires a new decisions entry naming what changed and why;
occurrences collected under the earlier text stay attributed to it.
**Freeze identity:** the SHA-256 of this file at the freezing commit is
recorded in [`evidence.md`](evidence.md) under "T4 preregistration".

This is the ASI-6 preregistration for the bounded comparative trial
(ladder T4). It fixes the scenarios, conditions, order, sample, host,
outcomes, exclusions, missing-data rules, and falsification rule BEFORE
the first occurrence is collected. It authorizes no provider call and no
paid operation; every occurrence is a real interaction that would have
happened anyway.

## Question

On the named host, is the automatic default presentation for the `spec`
review choice (widget, per the T2 guidance) more useful than the
session-preference alternative (`conversation`, Markdown lane), measured
by what the user does, not by how fast anything paints?

## Unit of analysis

One **occurrence** = one real `/spec` run reaching the `review` stage
(the `spec` adapter's `redo_plan` / `approve_plan` choice) on the named
host, whose choice is answered and accepted through
`command_workspace_collect_action`. Not a session, not a spec. A spec
that returns to review after `redo_plan` yields a new occurrence.

## Conditions

| Code | Condition | What the agent does |
| --- | --- | --- |
| **A** | Automatic default | Present the returned widget HTML through the host's `show_widget`; the user answers by clicking; the posted payload is submitted unchanged. |
| **B** | Session preference `conversation` | Set `interaction_preference = conversation` for the session (`context_set`); present the returned Markdown verbatim; the user answers in words; the agent transcribes into the bound payload and submits it. |

Both conditions use the same canonical collector, binding grammar, and
acceptance semantics (established by T3). Nothing else about the review
stage changes. The condition governs presentation only.

## Order (counterbalanced, fixed in advance)

Occurrences are assigned in this order and no other:

| Occurrence | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Condition | A | B | B | A | B | A | A | B |

The next unfilled slot in [`t4-record.md`](t4-record.md) is the assigned
condition. An occurrence cannot be skipped to reach a preferred
condition; a skipped occurrence is recorded as an exclusion with its
reason.

## Sample

Eight occurrences, four per condition. This is a **within-user pilot on
one host** (ASI-6: supports a local default decision, not a population
claim). Collection closes at eight or on the falsification rule below,
whichever comes first.

## Host and runtime (recorded per occurrence)

Named host: Claude desktop app, Code tab, with the attune-ai plugin MCP
server. Each row records the attune-ai source or distribution the
serving MCP process imports, the attune-forms version it loads, and the
Python version — read from the serving process's environment, never
inferred from a ref (T1's method). An occurrence on any other host is
recorded and excluded.

## Primary outcomes (per occurrence, all recorded; none may be dropped)

| Outcome | Definition | Source |
| --- | --- | --- |
| Completed | the choice was accepted canonically (revision advanced) | `workspace_accepted` telemetry row joined on workspace, revision, instance |
| Corrections | count of collector rejections before acceptance (stale, invalid, mismatched payloads) | `command_workspace_collect_action` results |
| Clarification turns | count of agent-to-user turns between render and acceptance that asked something about the choice itself | transcript, counted by the agent at record time |
| Override | the user asked for the OTHER lane after the assigned one was presented (either direction) | transcript |
| Authority failure | any acceptance that did not match the rendered view, or any double execution | collector + telemetry; **any occurrence suspends collection (ASI-6)** |

## Secondary (descriptive only; never a criterion — D8)

Render-to-acceptance dwell in seconds from the telemetry join. Paint
timing is **unmeasured on this host** and recorded as `null`, never
estimated from tool-return or arrival times.

## Exclusions (recorded, then excluded from the comparison)

- Synthetic or manufactured review moments, including T3's two receipts.
- An occurrence where the user named the alternative in words BEFORE
  the presentation was rendered (ASI-5: no control is presented; record
  as "pre-chosen" and do not count against the slot).
- An occurrence on a host other than the named host.
- An occurrence where the assigned condition could not be honored (for
  example the host failed to render the widget under A) — record the
  reason; the slot stays open.

## Missing data

A missing value is `null`, reported as such. No zero is imputed. An
occurrence with a missing primary outcome still counts as an occurrence
but is flagged in the record.

## Falsification rule (preregistered)

The automatic default is judged NOT useful, and T5 opens early to record
that, if either holds before the eighth occurrence:

- overrides away from A in two or more of A's occurrences, or
- corrections plus clarification turns summed over A's occurrences exceed
  the same sum over B's occurrences by three or more at any point where
  both conditions have at least two occurrences.

An authority failure in either condition suspends collection immediately
regardless of counts (ASI-6) and returns the pilot to a verified
fallback pending review.

## Promotion criteria (what T5 needs to see to keep the default)

All of: eight completed occurrences; zero authority failures; at most one
override away from A; A's corrections-plus-clarifications not greater
than B's. Anything less is reported as-is; there is no post-hoc metric
selection.

## Where the record lives

[`t4-record.md`](t4-record.md), one row per occurrence, appended by the
agent that served it, in the same session, before any other spec work
continues. Rows carry counts, labels, and telemetry identifiers only —
never the user's answers, never action nonces, never contract hashes.

## Operating instruction (how an occurrence is collected)

At a real `/spec` review stage on the named host:

1. Read the next unfilled slot in `t4-record.md`; that is the condition.
2. Apply it (A: widget; B: `context_set interaction_preference
   conversation`, then the Markdown lane). Do not tell the user which
   slot it is before they answer; do tell them, if asked, that the
   review presentation is under the T4 trial.
3. Serve the choice exactly as the T2 guidance says for that lane.
4. After acceptance, append the row from the telemetry join and the
   transcript. Reset the session preference to `default` after a B
   occurrence unless the user set it themselves.
5. Check the falsification rule. If it trips, stop collecting and open
   T5 with the record as it stands.
