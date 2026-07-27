# 10.6.0 Demo Script — expanded draft (Patrick's voice)

**Written:** 2026-07-23. **Amended:** 2026-07-24, per roundtable
thread `q-demo-scripts-review-002` (chair-ruled; caption-carried
caveats per amended ruling). **Status:** draft — records Tuesday
07-28 after the lift and live receipts; every `[RECEIPT]` beat
must exist before its segment records (cut-don't-fake, binding).
**Structure:** expands
[DEMO_10_6_0_outline.md](DEMO_10_6_0_outline.md) (v2, amendments
A1–A8 applied) into narration + on-screen text + commands.
**Voice note:** narration deliberately echoes the launch article's
language — one campaign, one voice.

Pre-record checklist:

- [ ] PyPI serves 10.6.0 (a 200, not a promise)
- [ ] Codex canary green (marketplace re-synced)
- [ ] Antigravity probe ruled go/no-go — no-go = two-provider cut
- [ ] Every command below rehearsed once, unrecorded, same machine
- [ ] Cold-open FINDING pre-selected the day before, from
      candidates passing a one-sentence stranger-legibility test;
      the read is rehearsed (table ruling,
      q-demo-scripts-review-002)
- [ ] VERBATIM-RECALL receipt: rehearsal confirms whether
      `session_memory_recall` returns the stored finding verbatim
      or a ranked digest — if a digest, the "not a summary — the
      finding itself" narration is REWRITTEN before recording,
      not softened in the edit
- [ ] TASK FIXTURE built: one prebuilt task supplies the finding,
      branch, changed files, handoff next-action, and
      cross-review diff — every Act 2 beat draws from it
- [ ] Cross-review diff pre-selected from 2–3 rehearsed
      candidates where the second model demonstrably surfaces
      something real

---

## The journey

| Segment | Time | What the viewer sees |
|---------|------|----------------------|
| Cold open | 0:00–0:45 | Context dying at the boundary, live |
| Day one | 0:45–1:45 | Install → one useful result |
| One task, two agents | 1:45–5:15 | Memory + handoff, one story |
| The second opinion | 5:15–6:45 | A real finding from a rival model |
| The receipts | 6:45–7:15 | Evidence card, one ask |

---

## Cold open (0:00–0:45)

**Screen:** Claude Code session on the attune-ai repo, mid-task.

**Narration:**

> I run three AI coding agents on the same repository. Watch what
> happens at the boundary between them.
>
> Claude just worked something out — [reads the PRE-SELECTED
> finding (see checklist): chosen the day before, rehearsed, and
> short enough to compare verbatim when recall succeeds in Act
> 2. It must pass the stranger-legibility test — one sentence a
> viewer who has never seen this repo understands]. That took
> real work to learn.

**Screen:** fresh Codex session, same repo. Ask a
TOPIC-SPECIFIC question about the finding — e.g. *"What do we
know about <the finding's topic> in this repo?"* — not the
generic "what did the last session learn?" (a question no tool
answers reads as a straw man; a specific question Codex SHOULD
answer, and can't, is the honest failure). Codex answers
honestly: it has no idea.

**On-screen caption:**

> Every new AI session starts from zero.
> You are the only thing carrying context between them.

**Narration:**

> Until this week, I was the transport layer. Copy, paste, hope.
> 10.6.0 deletes that job. Let's cross the boundary.

*(No title card yet — the title lands after the cold open, so the
first 20 seconds are all demonstration.)*

## Day one (0:45–1:45)

**Screen:** empty terminal.

```bash
pip install attune-ai
```

**Production:** jump-cut the install; persistent `4×` badge in the
corner; caption "full unedited run linked below." The compression
is visible because hiding it would be a claim.

**Narration:**

> One install. No API key for subscription-backed use — if you
> already pay for Claude, you're done configuring.

**Screen:**

```bash
attune security-audit .
```

Real output on the real repo. Point at ONE finding — and it is
not a throwaway: this finding is the task fixture's seed, the
exact artifact the rest of the video carries across every
boundary (Act 2's capture, recall, handoff, and the cross-review
all trace back to it). One artifact, one story — a Day-one
finding that disappears would make Acts 1 and 2 two disconnected
demos. Keep this whole segment tight (~30–40s): install and
audit are commodity beats; the differentiated product starts at
the boundary.

**Narration:**

> That's day one: install, run, get something useful back. Fine.
> Every tool demo you've ever seen stops here. Everything from
> this point is what 10.6.0 adds — and it's all about THIS
> finding.

## One task, two agents (1:45–5:15)

**Production:** persistent task card in the corner from here on —
Finding / Branch / Changed files / Next action, all drawn from
the ONE task fixture (see checklist). Every boundary crossing is
me typing a command on screen. Nothing moves on its own, and I
say so. **Agent-seat distinction:** across 3.5 minutes of
boundary crossings viewers lose track of whose terminal is on
screen — give each seat an unmistakable look (distinct terminal
theme or a color-coded header/border per agent; cheapest variant
that survives 1080p). For the cold open's failure beat, prefer
the two sessions side-by-side so the boundary is visible in one
frame.

### Wiring the second agent (1:45–2:15)

**Screen:** the actual Codex config — the marketplace entry /
MCP stanza, however many lines it really is.

**Production:** cap this segment at ~30 seconds regardless of
config length. Show the FULL config on screen for one readable
pause (nothing hidden), narrate only the two lines that matter,
caption "full config linked below." A 60-second config read
sits exactly where the drop-off curve is steepest; honesty is
preserved by the full-frame pause plus the linked receipt.

**Narration:**

> First, the honest part: here's how Codex gets these tools.
> [If it's one stanza: "One config block. That's the whole
> setup."] [If it's more: "It's this block — the whole thing is
> on screen and linked below."]

`[RECEIPT: marketplace re-sync canary — R8 #4]`

### The finding crosses (2:15–3:30)

**Screen:** back in Claude Code. The session captures the finding
from the cold open — I trigger the capture, on screen.

**Screen:** Codex.

```text
> use session_memory_recall to check what's known about <topic>
```

The finding comes back — the fixture finding, the same one from
the cold open and the Day-one audit. **Hold 4+ seconds, zoomed
or highlighted on the matched text, composed CENTERED** (this is
the social cut's opening beat; it must survive the vertical
crop — center-stage compose ruling, no dedicated vertical take).

**Narration (scoped to what the verbatim-recall receipt proved
in rehearsal — if recall returns a digest, this line was already
rewritten at the checklist stage, not here):**

> Codex just remembered something Claude learned. Not a summary I
> pasted — pulled straight from the shared store. Let the reveal
> breathe.

**Honesty card (on-screen caption, AFTER the reveal has landed —
chair ruling, amended 2026-07-24: caveats live on screen, not
over the payoff):**

> Captured with PII scrubbed on the way in.
> Claude: automatic capture via lifecycle hooks.
> Codex / Antigravity: same memory surface via MCP —
> automatic hooks not promised there.
> Same memory, different reflexes.

`[RECEIPT: post-lift Codex canary transcript]`

### The task crosses (3:30–5:15)

**Screen:** Claude Code, mid-task on a real branch.

```text
> handoff_create
```

**Narration:**

> The handoff packet's git facts — branch, changed files, HEAD —
> come from git at call time, never from what the model says it
> did. Claims without receipts get recorded as exactly that:
> "not run."

**Screen:** Codex.

```text
> handoff_resume
```

**Hold on the verification output** — refs checked, tree checked,
drift reported.

**Narration:**

> Before Codex continues the work, it re-checks the packet against
> the actual tree. Handoffs are git-verified session contracts,
> not loose prompt copies. Our collaboration contract said "a
> handoff is context, not authority" for months. Now it's
> mechanical.

Codex performs the stated next action. The task card updates.

`[RECEIPT: create-in-Claude → resume-in-Codex round-trip
transcript]`

### Conditional third seat (inside 3:30–5:15, if probe green)

**Screen:** Antigravity querying the same shared memory.

**Narration:**

> And it's not a two-vendor trick — Antigravity reads the same
> store.

`[RECEIPT: Antigravity register+probe — R8 #6]`

*(Probe not green by record time → this beat does not exist, the
title becomes the Claude/Codex story, and Antigravity appears in
the evidence matrix only. Decided before recording, not in the
edit.)*

## The second opinion (5:15–6:45)

**Screen:**

```text
/cross-review
```

on the PRE-SELECTED diff (see checklist — the fixture's diff,
chosen from 2–3 rehearsed candidates where the second model
demonstrably surfaces something real). Show what the second
provider surfaced — read it out.

**Narration (say "caught something" ONLY if it is demonstrably a
defect; otherwise it is an independent observation — overcalling
a style note as a catch spends the credibility the receipts
built):**

> A different vendor's model just reviewed my actual diff — not a
> summary of it — and surfaced something I hadn't considered.
> Different model, different blind spots. It's advisory, and it
> stays advisory until dogfooded quality earns it more. I don't
> let it block a merge and neither should you, yet.

**Screen:** 3-second flash of the promoted roundtable report
header.

**Narration:**

> One more thing, quickly: the features you just watched were
> chosen by a round table of these same three models — ruling
> linked below.
>
> The models advise. You decide.

## The receipts (6:45–7:15)

Compressed to ~30s (table ruling): a full minute on a static
table is where a 7-minute video loses its ending.

**Screen:** the evidence card, rows ANIMATING IN as each is
narrated. The card must work as a standalone still (it will be
screenshot-shared and re-embedded, where "linked below" breaks):
one short human-typeable URL on the card itself — a single
receipts index page (e.g. `attune-ai.dev/receipts/10-6-0`) —
instead of dead per-row `[link]` cells. Full links stay in the
description.

| Claim | Providers | When |
|-------|-----------|------|
| Cross-provider recall | Claude → Codex | `[ts]` |
| Handoff, tree-verified | Claude → Codex | `[ts]` |
| Independent review | `[pair]` | `[ts]` |

Card footer: `all transcripts: attune-ai.dev/receipts/10-6-0`

**Narration:**

> Every claim in this video has a transcript — one URL, on
> screen, including the unedited runs behind the jump cuts.
> That's the rule this project runs on: no claim without a
> receipt.
>
> Install the plugin. Run one workflow. Cross providers when the
> task needs another seat.

**Screen:** `pip install attune-ai` · attune-ai.dev

---

## Social cut (~90s YouTube + 45–60s feed variant)

Causal order (problem → payoff, matching the chair's
problem-first ruling on the dynamic-forms cut): the miracle is
unparseable without the loss beat first. All beats carry
burned-in captions — LinkedIn autoplays muted.

- 0:00–0:05 — the loss, cold: Codex not knowing, next to
  Claude's finding. Caption: "Every new AI session starts from
  zero."
- 0:05–0:15 — the recall reveal (centered take). Caption:
  "Codex just remembered something Claude learned."
- 0:15–0:25 — `pip install attune-ai` flash.
- 0:25–1:05 — the handoff round-trip, verification held on
  screen. Caption: "Handoffs are git-verified, not pasted."
- 1:05–1:30 — evidence card + "The models advise. You decide." +
  install line.

Feed variant (45–60s, LinkedIn-native): loss → recall reveal →
verification hold → evidence card; cut the install flash, keep
the final install overlay. 90s is YouTube-Shorts-tolerable but
long for feed retention.

---

## Stage geometry (chair-ruled 2026-07-23 — record on screen 1)

The recording stage is **screen 1 — LG HDR 4K (1), 3840×2160,
native 16:9**. That matches LinkedIn's player aspect exactly, so
the capture is the whole display, no area math:

- **Capture mode: Display, screen 1.** 4K → 1080p export is a
  clean 2× downscale — the crispest text LinkedIn will ever get
  from us. Screen Studio's recorder: Display, pick LG HDR 4K (1).
- **Backstage is the OTHER monitors, by construction:** the
  ultrawide keeps Claude (director/QC + this script as
  teleprompter); System Settings and spillover stay where they
  are. Nothing off-stage can enter frame — no tape lines, no
  drift risk. The only discipline: never drag a backstage window
  onto screen 1 mid-take.
- **Screen 1 is a CLEAN SET:** demo windows only, wallpaper
  neutral, Dock hidden (or untouched if it lives on another
  display), menu bar acceptable (it reads as "real machine").
  Notifications: Do Not Disturb ON for the session.
- **Split-screen beats** (cold open, Act 2): two side-by-side
  panes ~**1900×2000 each**. At half-4K width, **18pt** terminal
  font survives the 1080p export and LinkedIn compression;
  drop below 16pt nowhere.
- **Single-window beats** (Act 1, cross-review): one centered
  ~3200×1900 window, 18pt.
- **The task card** sits ON screen 1 — pinned bottom-right,
  ~700×400 at 4K — or it doesn't exist for the viewer.
- **Vertical-cut discipline:** the 9:16 social crop keeps
  roughly the middle 1215px of the 4K frame. For the two beats
  the social cut reuses (memory-recall reveal, handoff
  round-trip), the payoff output must sit CENTERED at the
  payoff moment — recompose those takes center-stage, or accept
  re-recording them for the vertical.
- **Evidence card / title cards:** author the HTML full-screen
  at 3840×2160 (16:9); recorded full-stage they need no zoom,
  and the three evidence rows stay within the center 1215px so
  the vertical cut keeps them readable.

## What this script refuses to do

Carried from the outline, restated because they're the point:

- No beat records without its receipt. A missing receipt cuts the
  beat; it never simulates it.
- No catalog tour, no dashboard tour, no config surfaces. One
  paved path per act.
- No claim wider than what's on screen ("no API key" is always
  "for subscription-backed use").
- Each boundary crossing records as its own segment, so any beat
  can be cut without re-shooting the story.
