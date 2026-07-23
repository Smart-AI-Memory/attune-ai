# Dynamic Forms Demo Script — rehearsal + releasable (Patrick's voice)

**Written:** 2026-07-23. **Status:** draft — this is the Thu/Fri
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

**Screen:** Claude Code, real repo. Ask for something genuinely
ambiguous — "help me test this module."

The agent asks a question. One button row. Answer it. It asks the
next. Answer that. A third appears.

**Narration:**

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
>
> And the honest part, because it's the part that makes this
> good: there's a rule about when NOT to do this. If one answer
> changes the next question, it stays sequential. If I already
> said it, it's not asked. If only one thing is unknown, one
> question is correct. The form never invents fields — it batches
> exactly what Socratic judgment would have asked anyway.

**Production:** hold on the rendered form long enough to read
every field. This is the product shot of the video.

**Narration, over the answered form:**

> Under the hood this is data, not code — a declarative form,
> validated on the way in and the way out, rendered through the
> same tools any MCP client can call.

## The pushback form (1:45–2:45) — disagreement as a decision

**Screen:** a real fork: tell the agent to do something where it
has a better alternative (use the day's genuine example — there
is always one). The disagreement renders AS A FORM: my approach
labeled "your approach," its alternative badged "I'd suggest
instead," a one-line "why I'd push back."

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
promoted report it produced.

**Narration:**

> This isn't a feature I built and forgot. Every ruling in this
> repository — which findings get promoted, which work ships,
> which plans get overruled — runs through these forms. The demo
> you're watching was scoped with one this morning.

## Close (3:30–4:00)

**On-screen caption:**

> Ask everything at once — when the questions are independent.
> Ask one thing — when they're not.

**Narration:**

> Socratic discovery that respects your time. It ships in the
> plugin today.

**Screen:** `pip install attune-ai` · attune-ai.dev

---

## Social cut (~60s)

- 0:00–0:10 — the form, cold: `/elicit` rendering three
  dimensions in one turn. Caption: "Every question at once —
  when that's correct."
- 0:10–0:25 — the interrogation it replaced (compressed, three
  quick question-turns).
- 0:25–0:45 — the pushback form + one-click overrule. Caption:
  "Pushback you can click."
- 0:45–1:00 — install line.

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
