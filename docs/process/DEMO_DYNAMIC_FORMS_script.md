# Dynamic Forms Demo Script — rehearsal + releasable (Patrick's voice)

**Written:** 2026-07-23. **Amended:** 2026-07-24, per roundtable
thread `q-demo-scripts-review-002` (chair-ruled; caption-carried
caveats per amended ruling). **Re-cut:** 2026-07-25, per roundtable
thread `q-forms-default-vs-latency-001` and decisions.md D21 —
the arc changed because the product changed (see "Why this was
re-cut" below). **Status:** draft — this is the Thu/Fri CAPTURE
REHEARSAL subject (chair-ruled): it exercises the full recording
pipeline before Tuesday's 10.6.0 shoot, and the footage is
releasable in its own right after the chair's honesty-gate pass.

> **Version gate — READ BEFORE CAPTURE.** This script now shows
> **10.6.0 behaviour, which is NOT on PyPI yet** (10.5.0 is
> current). The forms-by-default routing and keyboard mode land in
> 10.6.0. Capture against the branch/local build, and do not
> publish the main cut until 10.6.0 is live. The previous version
> of this script claimed "everything shown is live on PyPI 10.5.0
> today" — that claim is now false and has been removed rather
> than quietly left standing.

**Format:** ~4 min main cut + 60s social cut. Stage geometry:
record on screen 1 per the
[10.6.0 script's](DEMO_10_6_0_script.md) Stage geometry section —
same rules, same set.

## Why this was re-cut (2026-07-25)

The old arc was **"3 turns → 1 turn"**: cold-open on the agent
asking three sequential button questions, then `/elicit` collapsing
them into one form. That arc no longer reproduces. D21 flipped the
default — a multi-dimension ask now renders as one form
*immediately*, without `/elicit`, because the Socratic rule was
rewritten to batch independent dimensions. The three-question
interrogation the cold open depended on is the behaviour we
removed.

Rather than lose the visual proof, the re-cut makes it
**deterministic**: keyboard mode reproduces the sequential
experience on demand, so the same prompt gives both takes from one
machine. This is strictly better than the old approach, which
needed a specimen "rehearsal-verified to reliably yield ~3
sequential questions" and could still misfire on the day.

The demo's claim also gets stronger and more honest: the good
behaviour is no longer a move the user has to know to ask for — it
is what the product does by default.

Pre-record checklist:

- [ ] Screen Studio mic toggle flipped + 2-second audio-track
      test (the pending receipt from the 07-23 walkthrough)
- [ ] Both takes and one pushback form rehearsed once, unrecorded
- [ ] Cold-open prompt PRE-SELECTED (one prompt, two takes — see
      "The two-take method" below). The specimen is picked before
      the take, not during it (table ruling,
      q-demo-scripts-review-002 — curation of a live run, never
      simulation). Candidates locked 2026-07-24, method re-cut
      2026-07-25; the unrecorded live pass is what remains before
      ticking this.
- [ ] Keyboard-mode toggle verified BOTH directions on the capture
      machine: `ATTUNE_KEYBOARD_MODE=1` yields sequential button
      turns, unset yields one form, on the SAME prompt. This is the
      re-cut's load-bearing mechanism — if it doesn't flip cleanly,
      the cold open doesn't work.
- [ ] Running against a build that HAS D21 (forms-by-default). Check
      with `python -c "from attune.elicitation import
      select_form_surface; print('ok')"` — an ImportError means the
      stage is on 10.5.0 and the whole arc reverts to the old one.
- [ ] Pushback example LOCKED: a rehearsed, real, low-context
      disagreement whose two options fit on screen and whose
      consequence reads in one sentence. Specimen locked and
      render-verified 2026-07-24 — see "Locked specimens" below.
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

## Locked specimens (2026-07-24)

### Cold-open candidates (primary first)

**Re-cut 2026-07-25:** these are now the prompt for BOTH takes, not
just the interrogation take. Each candidate's dimensions map onto
the same scope/focus/depth wording, so "same questions, one form"
is visually provable across the cut.

The reliability problem the old note worried about is gone.
Previously the specimen had to be "rehearsal-verified to reliably
yield ~3 sequential questions" — a hope, since the agent chose the
shape. Now take A gets the sequential shape because
`ATTUNE_KEYBOARD_MODE=1` *makes* it sequential, and take B gets one
form because that is the default. Both takes are deterministic; the
rehearsal pass is confirming wording and pacing, not fishing for a
behaviour.

The candidates are still drawn from the repo's own Socratic
Interaction Rule examples — note that rule was rewritten by D21, and
its worked example (`"security audit" → path + focus + depth → ONE
form`) is now the *batching* instruction rather than the sequential
one.

1. **"help me test this module"** (primary — typed verbatim in
   BOTH takes). Take-A sequence, under keyboard mode:
   Q1 scope — "Which module should we test?"; Q2 focus —
   "What's the focus?" (run existing tests / find coverage
   gaps / generate new tests / coverage of changed code);
   Q3 depth — "How deep?" (quick smoke pass / full unit
   suite / full suite + coverage report).
2. **"review my recent changes"** — Q1 scope (branch diff,
   staged, or last N commits); Q2 focus (security / quality /
   performance / tests); Q3 depth (quick pass vs multi-pass
   deep review).
3. **"clean up this code"** — Q1 scope (which path); Q2 focus
   (simplify / refactor / dead code); Q3 depth (safe-only vs
   structural).

Whichever candidate is used, take B types the SAME words with no
flag and no slash command — that identity is the whole proof.

### Act-1 form (primary specimen)

Dogfood-verified 2026-07-24 through the live
`elicitation_render_form` MCP tool — validates clean and batches
all three fields into a single turn. **Re-cut note:** this is now
what take B renders *by default* from the plain prompt; the
`/elicit` command is no longer needed to produce it, and the
verification must be re-run against a D21 build (the 10.5.0 run
proved the form validates, not that it is the default).

```json
{
  "title": "Scope this testing work",
  "fields": [
    {"id": "scope", "text": "Which module should we test?",
     "type": "single_select",
     "options": ["src/attune/elicitation/",
                 "src/attune/workflows/",
                 "src/attune/hooks/", "attune_redis/"]},
    {"id": "focus", "text": "What's the focus?",
     "type": "multi_select",
     "options": ["run existing tests", "find coverage gaps",
                 "generate new tests",
                 "coverage of changed code"]},
    {"id": "depth", "text": "How deep?",
     "type": "single_select",
     "options": ["quick smoke pass", "full unit suite",
                 "full suite + coverage report"]}
  ]
}
```

### Pushback specimen (LOCKED) — "Scope of the fix"

Setup: Patrick says "just fix the failing test and let's ship";
the agent has found the same unvalidated call in four sibling
modules and pushes back with a one-sweep alternative. Patrick
clicks OVERRULE (keeps "Fix only the failing test") — the
overrule reads as smallest-unit-of-work discipline, not
recklessness, which is why this fork was chosen. The agent
acknowledges, executes the focused fix, and files the sweep as
a follow-up. Low-context: any developer reads the fork cold,
and the consequence is one sentence.

```json
{
  "title": "Scope of the fix",
  "fields": [
    {"id": "fix_scope",
     "text": "How much of this do we fix now?",
     "type": "pushback",
     "options": ["Fix only the failing test",
                 "Fix the pattern in all five modules"],
     "user_position": "Fix only the failing test",
     "recommended": "Fix the pattern in all five modules",
     "rationale": "The same unvalidated call exists in four sibling modules — fixing one leaves four known-broken.",
     "option_notes": {
       "Fix only the failing test": "Small, reviewable, ships today",
       "Fix the pattern in all five modules": "One sweep, no repeat visits"}}
  ]
}
```

Receipts (2026-07-24, live on the installed 10.5.0 plugin, no
API credits spent): the widget render returns the exact demo
shot — "I'd suggest instead" badged and ordered first, "your
approach" tag on Patrick's option, "Why I'd push back" callout —
and the overrule answer round-trips
`elicitation_collect_response` cleanly (resp-20260724-091558).

---

## The journey

| Segment | Time | What the viewer sees |
|---------|------|----------------------|
| Cold open | 0:00–0:30 | Question-by-question interrogation (take A, keyboard mode) |
| One form | 0:30–1:45 | Same prompt, one form, no command (take B, the default) |
| The pushback form | 1:45–2:45 | Disagreement as a decision, not an argument |
| Dogfood | 2:45–3:30 | This repo's own rulings ran on these forms |
| Close | 3:30–4:00 | The rule + the install line |

---

## The two-take method (production note — read first)

Both opening acts use **one prompt and one flag**. Record take A,
flip the flag, record take B, cut them together. Same repo, same
prompt, same session shape — the only variable is the mode, which
is exactly what makes the comparison honest and repeatable.

```bash
ATTUNE_KEYBOARD_MODE=1 claude    # take A — sequential button turns
```

```bash
claude                            # take B — one form (the default)
```

Nothing is staged or simulated: take A is a real, shipping,
user-selectable mode, not a re-enactment of an old version. That
distinction is what keeps this inside the table's
"curation of a live run, never simulation" ruling.

## Cold open (0:00–0:30) — the interrogation

**Screen:** Claude Code, real repo, **take A**. Use the
PRE-SELECTED prompt (see checklist) — a genuinely ambiguous ask,
e.g. "help me test this module."

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

**Screen:** **take B** — the identical prompt, typed the same way,
with no flag and no slash command.

```text
help me test this module
```

One form renders immediately: the independent dimensions of the
decision — scope, focus, depth — batched into a single turn,
multi-select where it fits, a recommended option marked. Fill it
in one pass. Work starts.

**Narration:**

> Same prompt. Same questions. One form. I didn't ask for this —
> I didn't type a command, I didn't opt in. The dimensions of a
> decision I was going to make anyway, asked together, because
> they're independent. That's just what it does now.

**Production:** hold on the rendered form long enough to read
every field, with MINIMAL narration over the hold. This is the
product shot of the video — the viewer cannot read fields and
parse policy by ear at the same time. The scope/focus/depth
wording is identical across both takes, so "same questions, one
form" is visually provable; a "3 turns → 1 turn" caption
punctuates the cut.

**Caption (burned in over the cut between takes):**

> same prompt · no command · the default changed

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

- 0:00–0:05 — sequential-question friction, compressed (take A):
  three quick question-turns with the turn-counter. Caption:
  "Three decisions. Three round trips."
- 0:05–0:20 — smash-cut to take B: the SAME prompt, no command,
  the same three dimensions as one form, with a brief
  3-turns-vs-1-form contrast frame (split or before/after).
  Caption: "Same prompt. Every question at once — when that's
  correct."
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
