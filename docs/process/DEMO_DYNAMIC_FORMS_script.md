# Dynamic Forms Demo Script — rehearsal + releasable (Patrick's voice)

**Written:** 2026-07-23. **Amended:** 2026-07-24, per roundtable
thread `q-demo-scripts-review-002` (chair-ruled; caption-carried
caveats per amended ruling). **Status:** draft — this is the Thu/Fri
CAPTURE REHEARSAL subject (chair-ruled): it exercises the full
recording pipeline before Tuesday's 10.6.0 shoot, and the footage
is releasable in its own right after the chair's honesty-gate
pass. **Everything shown is live on PyPI 10.5.0 today** — no
receipt slots to wait for; the pre-record check is just "the
commands run on this machine." **Format:** ~4 min main cut + 60s
social cut. Stage geometry: record on screen 1 per the
[10.6.0 script's](DEMO_10_6_0_script.md) Stage geometry section —
same rules, same set.

Pre-record checklist:

- [ ] Screen Studio mic toggle flipped + 2-second audio-track
      test (the pending receipt from the 07-23 walkthrough)
- [ ] `/elicit` and one pushback form rehearsed once, unrecorded
- [ ] Cold-open prompt PRE-SELECTED: 2–3 candidate prompts
      rehearsal-verified to reliably yield ~3 sequential
      questions; the specimen is picked before the take, not
      during it (table ruling, q-demo-scripts-review-002 —
      curation of a live run, never simulation)
- [ ] Pushback example LOCKED: a rehearsed, real, low-context
      disagreement whose two options fit on screen and whose
      consequence reads in one sentence
- [ ] Do Not Disturb on; screen 1 clean set
- [ ] Recorder config verified fresh: mic = G733, system audio
      OFF, camera off (config drifts between sessions)

Capture and export settings (ruled 2026-07-23, dry-run + Patrick):

- Capture: full display, screen 1 (LG HDR 4K) at native 4K —
  identify the stage by a 5s test take + thumbnail check, never
  by display name (names disagree across tools).
- Export, main cut (~4 min): mp4, **1920×1080 (16:9)** — the
  full stage, forms stay readable (the product shot is "read
  every field"), and it is YouTube-native for the article-embed
  path. H.264 + AAC, 10-60 fps, ≤5 GB.
- Export, 60s social cut: mp4, **1080×1350 (4:5 portrait)** —
  best current LinkedIn mobile-feed engagement; its beats each
  fit a portrait crop of a single window. Verify the crop per
  beat in the editor (one-click vertical + auto-zoom reframes,
  but eyeball each form). The 16-18pt terminal font rule is
  even more binding at 4:5.
- Split ruled by Patrick 2026-07-23 (supersedes both the
  dry-run 1080p-everything ruling and the interim
  4:5-everything ruling). Shooting is unchanged: full 16:9
  stage, no record-time portrait framing.
- Hosting: native video upload = FEED POST only. A LinkedIn
  ARTICLE cannot host native video — YouTube/Vimeo embed only.
- After EVERY take: `cp -R` the `.screenstudio` bundle out of
  `~/Screen Studio Projects/` before touching the app again.

---

## The journey

| Segment | Time | What the viewer sees |
|---------|------|----------------------|
| Cold open | 0:00–0:30 | Question-by-question interrogation, live |
| One form | 0:30–1:45 | The same scoping as a single form |
| The pushback form | 1:45–2:45 | Disagreement as a decision, not an argument |
| Dogfood | 2:45–3:30 | This repo's own rulings ran on these forms |
| Close | 3:30–4:00 | The rule + the install line |

---

## Cold open (0:00–0:30) — the interrogation

**Screen:** Claude Code, real repo. Use the PRE-SELECTED prompt
(see checklist) — a genuinely ambiguous ask, e.g. "help me test
this module," chosen because rehearsal showed it reliably draws
~3 sequential questions.

The agent asks a question. One button row. Answer it. It asks the
next. Answer that. A third appears. **Production:** the
interrogation itself holds ~12–15 seconds of screen time —
jump-cut the agent-latency waits (raw footage will run 60–90s)
and burn in a turn-counter caption that makes the compression
honest: "question 1 of 3 · turn 1" → "question 2 of 3 · turn 2" →
"question 3 of 3 · turn 3." Same visible-compression grammar as
the 10.6.0 install jump-cut. Let the visual rhythm land BEFORE
the philosophy narration starts.

**Narration (over the third question appearing):**

> This is Socratic discovery, and it's the right instinct — the
> agent scopes before it executes instead of guessing. But it's
> one question per turn. Three decisions, three round trips, and
> I haven't started working yet.

**On-screen caption:**

> The questions are right. The pacing is wrong.

## One form (0:30–1:45) — the same scoping, one turn

**Screen:**

```text
/elicit testing this module
```

One form renders: the independent dimensions of the decision —
scope, focus, depth — batched into a single turn, multi-select
where it fits, a recommended option marked. Fill it in one pass.
Work starts.

**Narration:**

> Same questions. One form. The dimensions of a decision I was
> going to make anyway — asked together, because they're
> independent.

**Production:** hold on the rendered form long enough to read
every field, with MINIMAL narration over the hold. This is the
product shot of the video — the viewer cannot read fields and
parse policy by ear at the same time. Use the SAME
scope/focus/depth wording the cold-open questions used, so "same
questions, one form" is visually provable; a brief "3 turns →
1 turn" caption may punctuate the transition.

**Narration (after the hold) — captions carry the rules (chair
ruling, amended 2026-07-24: caveats live on screen, narration
stays on the payoff):**

> And the honest part, because it's the part that makes this
> good: there's a rule about when NOT to do this — it's on
> screen. The form never invents fields. It batches exactly what
> Socratic judgment would have asked anyway.

**Caption stack (burned in, cumulative, one line appearing per
beat of the narration pause):**

> one answer changes the next question → stays sequential
> already said → not asked
> one unknown → one question

**On-screen caption (over the answered form, not narrated):**

> Declarative form · validated in and out · rendered via MCP —
> any client can call it.

## The pushback form (1:45–2:45) — disagreement as a decision

**Screen:** the LOCKED pushback example (see checklist) — a
real fork, rehearsed in advance: two options that fit on screen,
a consequence that reads in one sentence. The disagreement
renders AS A FORM: my approach labeled "your approach," its
alternative badged "I'd suggest instead," a one-line "why I'd
push back."

**Production:** click OVERRULE on screen — not accept. Hold ~2
seconds on the agent acknowledging the override and executing
the original plan. The caption's claim ("the human stays the
chair") is only proven by the overrule path; showing only
acceptance reads as the agent still winning arguments.

**Narration:**

> This is my favorite one. When the agent disagrees with me, it
> doesn't write me an essay — it renders the disagreement as a
> decision. My approach, its alternative, why. I overrule with
> one click, or I take the suggestion with one click. Either way
> the argument is over in five seconds and the reasoning is on
> the record.

**On-screen caption:**

> Pushback you can click. The human stays the chair.

## Dogfood (2:45–3:30) — this repo runs on it

**Screen:** a real chair-ruling form from this week's roundtable
work (a promotion ruling — multi-select, per-item). Flash the
promoted report it produced. THEN show the receipt for the
closing line: the actual form that scoped this demo, captured
that morning (it will genuinely exist — screenshot it at scoping
time; the strongest claim in the script gets pixels, not just
voice).

**Narration:**

> This isn't a feature I built and forgot. The rulings that run
> this repository — which findings get promoted, which work
> ships, which plans get overruled — go through these forms. The
> demo you're watching was scoped with one this morning.

## Close (3:30–4:00)

**On-screen caption:**

> Ask everything at once — when the questions are independent.
> Ask one thing — when they're not.

**Narration:**

> Socratic discovery that respects your time. It ships in the
> plugin today.

**Screen:** the answered form from Act 1 flowing into the first
concrete work action — the decision becoming work, not a static
logo. The install line lands as the FINAL OVERLAY over that
motion, not as a separate closing card:
`pip install attune-ai` · attune-ai.dev

---

## Social cut (~60s)

Order ruled 2026-07-24 (problem-first, q-demo-scripts-review-002):
establish the friction, resolve it, END on the pushback click.
LinkedIn autoplays MUTED — every beat carries a burned-in caption
that works with no audio.

- 0:00–0:05 — sequential-question friction, compressed: three
  quick question-turns with the turn-counter. Caption: "Three
  decisions. Three round trips."
- 0:05–0:20 — smash-cut to `/elicit`: the same three dimensions
  as one form, with a brief 3-turns-vs-1-form contrast frame
  (split or before/after). Caption: "Every question at once —
  when that's correct."
- 0:20–0:50 — the pushback form + one-click OVERRULE + the
  agent's acknowledgment (the decision receipt). Caption:
  "Pushback you can click."
- 0:50–1:00 — install overlay over the form-into-work motion.

---

## Rehearsal double-duty (why this subject)

This script exists to prove the Tuesday pipeline: per-segment
takes, live narration, auto-captions off the G733, my QC pass
per segment, the editor pass (zooms, cuts, export), and the
LinkedIn-compression eyeball on the exported mp4. If any step
fights back Thursday, Tuesday absorbs the lesson instead of the
damage. The footage releasing later is the bonus, not the point —
the chair's honesty-gate pass gates any publish, same as
everything else.

## What this script refuses to do

- No mock forms — every form shown is rendered live by the
  installed 10.5.0 plugin on this machine.
- No claim that batching is always right — the batching rule's
  refusals are narrated on screen, because the restraint IS the
  feature.
- No catalog tour, no dashboard, no config. One paved path.
