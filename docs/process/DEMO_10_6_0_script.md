# 10.6.0 Demo Script — expanded draft (Patrick's voice)

**Written:** 2026-07-23. **Status:** draft — records Tuesday
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

---

## The journey

| Segment | Time | What the viewer sees |
|---------|------|----------------------|
| Cold open | 0:00–0:45 | Context dying at the boundary, live |
| Day one | 0:45–1:45 | Install → one useful result |
| One task, two agents | 1:45–5:15 | Memory + handoff, one story |
| The second opinion | 5:15–6:45 | A real finding from a rival model |
| The receipts | 6:45–7:45 | Evidence card, one ask |

---

## Cold open (0:00–0:45)

**Screen:** Claude Code session on the attune-ai repo, mid-task.

**Narration:**

> I run three AI coding agents on the same repository. Watch what
> happens at the boundary between them.
>
> Claude just worked something out — [reads the actual finding,
> whatever it is that day, e.g. "the projector was importing the
> wrong package because of where Python puts a script's
> directory"]. That took real work to learn.

**Screen:** fresh Codex session, same repo. Type: *"What did the
last session learn about this repo?"* Codex answers honestly: it
has no idea.

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

Real output on the real repo. Point at one finding, not the
report.

**Narration:**

> That's day one: install, run, get something useful back. Fine.
> Every tool demo you've ever seen stops here. Everything from
> this point is what 10.6.0 adds.

## One task, two agents (1:45–5:15)

**Production:** persistent task card in the corner from here on —
Finding / Branch / Changed files / Next action. Every boundary
crossing is me typing a command on screen. Nothing moves on its
own, and I say so.

### Wiring the second agent (1:45–2:15)

**Screen:** the actual Codex config — the marketplace entry /
MCP stanza, however many lines it really is.

**Narration:**

> First, the honest part: here's how Codex gets these tools.
> [If it's one stanza: "One config block. That's the whole
> setup."] [If it's more: walk it, at real speed. A reveal you
> can't reproduce at your desk is a magic trick, and I'm not
> selling tickets.]

`[RECEIPT: marketplace re-sync canary — R8 #4]`

### The finding crosses (2:15–3:30)

**Screen:** back in Claude Code. The session captures the finding
from the cold open — I trigger the capture, on screen.

**Screen:** Codex.

```text
> use session_memory_recall to check what's known about <topic>
```

The exact finding comes back. Hold on it.

**Narration:**

> Codex just remembered something Claude learned. Not a summary I
> pasted — the finding itself, PII-scrubbed on the way in, pulled
> from the same store.
>
> One honest caveat, on screen because it stays true: Claude gets
> automatic capture through lifecycle hooks. Codex and Antigravity
> get the same memory surface through MCP — but automatic hooks
> are not promised there. Same memory, different reflexes.

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

on a real diff from this repo. Show the actual finding the second
provider caught — read it out.

**Narration:**

> A different vendor's model just reviewed my actual diff — not a
> summary of it — and caught something. Different model, different
> blind spots. It's advisory, and it stays advisory until
> dogfooded quality earns it more. I don't let it block a merge
> and neither should you, yet.

**Screen:** 3-second flash of the promoted roundtable report
header.

**Narration:**

> One more thing, quickly: the features you just watched were
> chosen by a round table of these same three models — ruling
> linked below.
>
> The models advise. You decide.

## The receipts (6:45–7:45)

**Screen:** hold a three-row evidence card, long enough to read:

| Claim | Providers | When | Transcript |
|-------|-----------|------|------------|
| Cross-provider recall | Claude → Codex | `[ts]` | `[link]` |
| Handoff, tree-verified | Claude → Codex | `[ts]` | `[link]` |
| Independent review | `[pair]` | `[ts]` | `[link]` |

**Narration:**

> Every claim in this video has a transcript, and they're linked
> below — including the unedited runs behind the jump cuts. That's
> the rule this project runs on: no claim without a receipt.
>
> Install the plugin. Run one workflow. Cross providers when the
> task needs another seat.

**Screen:** `pip install attune-ai` · attune-ai.dev

---

## Social cut (~90s)

- 0:00–0:10 — the miracle, cold: Codex recalling Claude's finding.
  Caption: "Codex just remembered something Claude learned."
- 0:10–0:20 — the loss beat, compressed: "every new session starts
  from zero — until now."
- 0:20–0:30 — `pip install attune-ai` flash.
- 0:30–1:10 — the handoff round-trip, verification held on screen.
- 1:10–1:30 — evidence card + "The models advise. You decide." +
  install line.

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
