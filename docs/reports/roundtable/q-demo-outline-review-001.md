# Round table — demo outline review (q-demo-outline-review-001)

**Thread:** `q-demo-outline-review-001` · **Date:** 2026-07-23 ·
**Roster:** claude, antigravity, codex · **Rounds:** 1 (halted on
convergence, D3) · **Promoted items:** #2 #3 #4 #5
(chair-approved; ruling #6).

Chair ruling (2026-07-23): apply the full amendment set A1–A8 +
the conditional-Antigravity contingency to
`docs/process/DEMO_10_6_0_outline.md` (revised in the same PR);
promote this report. Unanimous: keep the demo's subject and
structure — every seat's output was amendment-level. The one
structural finding, hit by all three seats from different angles:
the title promises three agents, the script delivered two — now
resolved by the conditional third-seat beat + pre-written
two-provider fallback.

## #1 — question (chair)

Review docs/process/DEMO_10_6_0_outline.md and suggest concrete
improvements — or argue for a different demo subject if it would
do a strictly better job. (Seats received the full outline text
and the binding launch constraints: receipts gate, cut-don't-fake,
single-provider-leads order, first-touch-installer audience.)

## #2 — position (claude, 55s)

POSITION: keep subject and structure; five improvements in value
order. (1) ADD THE MISSING REPRODUCIBILITY BEAT: the outline shows
Codex already wired between Acts 1-2 — the viewer never sees how
Codex got the session_memory_* tools; a reveal you can't reproduce
reads as staged. 20-30s beat at the top of Act 2: the one
command/config stanza that registers attune in Codex, on screen; if
the real path is longer, showing that honestly is MORE valuable.
(2) REPLACE THE COLD-OPEN LINE — "the provider boundary is where
context dies" is insider language; use "Every new AI session starts
from zero. You are the only thing carrying context between them."
(3) ACT 1'S 80s CAN'T HONESTLY HOLD install + real workflow —
pre-commit the compression mechanic: jump-cut with persistent
on-screen 4x badge + "full unedited run linked below"; pick the
genuinely fastest workflow. (4) SHRINK THE META-BEAT TO A STINGER —
it sits at the retention nadir (7:00+) and requires reading a doc
on screen; one spoken line over a 3s flash of the report header,
give the reclaimed ~40s to cross_review showing an ACTUAL finding.
The self-planning story belongs in the article. (5) SOCIAL CUT:
payoff in the first 5 seconds — open cold on Codex recalling
Claude's finding, caption "Codex just remembered something Claude
learned," context after. RISK: optimizes first-touch retention at
the cost of the most press-worthy moment (meta-beat), and the new
setup beat adds a receipt dependency that could force a cut if the
marketplace sync misbehaves. QUESTION: what IS the real
second-provider onboarding path today — demoable under 30s with a
receipt, or does Act 2 need an honest "setup takes N minutes"
caption?

## #3 — position (antigravity, 43s)

### POSITION: Antigravity Seat

I support keeping the overall subject and chair-ratified narrative structure ("One Plugin, Three AI Coding Agents", single-provider quick win leading into the multi-LLM reveal). However, to maximize conversion for first-touch installers and ensure the demo honors its headline promise, I propose four concrete beat improvements:

---

#### Improvement 1: Fulfill the "Three Agents" Title in Act 2
* **Current Beat (Act 2):**
  > `- The reveal: open Codex — codex lists the same session_memory_* tools; session_memory_recall returns the finding Claude stashed. [RECEIPT: post-lift Codex canary transcript — R8 #4]`
* **Replacement:**
  > `- The reveal: open Codex and Antigravity side-by-side — show both agents querying the shared MCP layer (`session_memory_recall`) to pull the exact finding stashed by Claude Code. [RECEIPT: post-lift Codex canary transcript — R8 #4 & Antigravity probe]`
* **Rationale:** The title promises *three* agents, but Act 2 currently only demonstrates a two-agent handoff (Claude → Codex) and relegates Antigravity to a post-publish probe mention in the close. Showing Codex and Antigravity concurrently inspecting Claude's stashed memory fulfills the core promise visually and unequivocally.

---

#### Improvement 2: Pin Act 1 to a Single High-Signal Command
* **Current Beat (Act 1):**
  > `- One real workflow on a real repo (bug-predict or security-audit), receipt on screen.`
* **Replacement:**
  > `- Run zero-setup CLI command: attune security-audit . — show the instant terminal output (rich security report with 0 API keys configured) and state: "Zero setup, immediate security audit on your existing repo."`
* **Rationale:** Leaving the Act 1 command ambiguous ("bug-predict or security-audit") risks script drift during recording. `security-audit` produces an immediate, high-contrast visual report that communicates tangible value to first-touch installers in under 30 seconds.

---

#### Improvement 3: Highlight Git-State Safety in Act 3 Handoff
* **Current Beat (Act 3):**
  > `- In Codex: handoff_resume — the second provider verifies the handoff against the working tree before continuing, then picks up the task. [RECEIPT: live round-trip transcript]`
* **Replacement:**
  > `- In Codex: handoff_resume — show the `collaboration_preflight` verification receipt on screen as Codex validates clean Git refs and branch alignment before resuming: "Handoffs aren't loose prompt copies — they are Git-verified session contracts."`
* **Rationale:** Demonstrating explicit pre-flight verification reassures senior developers that switching providers mid-session won't corrupt branch state or silently lose context.

---

#### Improvement 4: Preserve the On-Ramp in the 2-Minute Social Cut
* **Current Beat (Social Cut):**
  > `No Act 1, no meta-beat — one boundary-crossing miracle per minute.`
* **Replacement:**
  > `Flash 10-second Act 1 install at 0:15 (`pip install attune-ai`) → Act 2 memory reveal (0:45) → Act 3 handoff (0:40) → receipts flash + call to action (0:25).`
* **Rationale:** Social feed scrollers lack context. Stripping Act 1 entirely leaves viewers amazed by cross-provider memory but oblivious to how effortlessly they can `pip install attune-ai` to try it themselves.

---

### MAIN RISK OF THIS POSITION

* **Screen Density & Pacing:** Showing three active terminal/agent windows (Claude, Codex, Antigravity) in Act 2 risks visual clutter on smaller screens and adds ~15–20 seconds to the recording length, creating tighter pressure on the 9-minute target duration.

---

### FOLLOW-UP QUESTION FOR THE TABLE

* **Question:** If Monday's post-publish Antigravity probe encounters latency during the recording window, should Act 2 fall back to a two-provider live split (Claude + Codex) with Antigravity showing as an active MCP client in the `/memory` ops view, or do we strictly trigger the cut-don't-fake rule to reduce Act 2's scope?

## #4 — position (codex, 25s)

POSITION

1. Make the cold open demonstrate loss, not merely assert it.

Change:

“Split screen: a Claude Code session rich with project context; beside it a fresh Codex session that knows nothing.”

To:

“Claude identifies a specific repo fact: ‘The failure is in X because Y.’ Cut to fresh Codex and ask, ‘What did Claude just learn?’ Codex cannot answer. On screen: ‘The provider boundary is where context dies.’ Then: ‘Let’s cross it.’”

This creates an observable before/after receipt and gives Act 2 a clean payoff.

2. Replace installation footage with a first-touch success check; reduce Act 1 to 60 seconds.

Change:

“`pip install attune-ai` … One real workflow … receipt on screen.”

To:

“Show the install command completing in a short jump cut, then immediately invoke one discoverable workflow from the host UI. Show one useful finding and its transcript location. Voiceover: ‘One plugin, no API key for subscription-backed use, and a useful result in under a minute.’”

Watching package installation is dead time. The audience needs to see: install → discover → useful result. Only say “no API key required” if the visible path proves the narrower subscription-backed claim.

3. Make Acts 2 and 3 one continuous task, with the human explicitly authorizing every boundary crossing.

Replace the separate examples with:

“Claude finds the bug cause and captures it. Codex recalls that exact finding, receives a handoff tied to the current branch and diff, verifies the tree, and performs the stated next action. The operator triggers capture, recall, handoff, and resume on screen.”

This turns two feature tours into one causal story and avoids implying invisible autonomous coordination. Use a persistent task card showing Finding → Branch → Changed files → Next action so viewers can track continuity.

4. Demote the round-table meta-story and spend the recovered time on an Antigravity receipt.

Change:

“Zoom out to the round table … The product plans itself; the human stays the chair.”

To:

“Ask one concrete judgment question about the live diff. Show Claude’s recommendation, Codex’s objection, and Antigravity’s independent response; then show the human choosing the ruling. Close the act with: ‘The models advise. You decide.’”

“The product plans itself” is both less honest than the surrounding outline and less valuable to a first-touch installer. More importantly, the headline promises three agents while the actual narrative substantially demonstrates only two. If Antigravity cannot complete a meaningful live operation, rename the demo around cross-provider Claude/Codex collaboration and mention broader adapter support only in the receipt matrix.

5. Replace the rapid receipt flash with a readable claim-to-evidence close, and shorten the main cut to roughly 7:30.

Change:

“Flash the receipts trail … Every claim you just watched has a transcript.”

To:

“Hold a three-row evidence card long enough to read: Cross-provider recall — passed, Handoff/tree verification — passed, Independent review — passed; each row names provider pair, timestamp, version, and transcript link/QR. End on one CTA: ‘Install the plugin. Run one workflow. Cross providers when the task needs another seat.’”

A nine-minute first-touch demo is expensive, and flashing receipts makes them decorative rather than auditable. Keep the full transcripts in companion material, but make the close legible.

RISK

A tighter, single-task narrative may underrepresent the breadth of 10.6.0 and could fail spectacularly if one live dependency breaks. Record each boundary as a continuous, independently usable segment so a failed Antigravity or marketplace beat can be cut without destroying the Claude→Codex story.

FOLLOW-UP QUESTION

Is Antigravity guaranteed to perform a meaningful memory, handoff, or review operation on screen by Tuesday, or is its current receipt only registration/probe?

## #5 — synthesis (moderator)

SYNTHESIS (moderator, 1 round — halted on convergence; critiques
are complementary, no decidable split).

UNANIMOUS: keep the subject and act structure — no seat proposed a
different demo. All improvements are amendments, not rewrites.

THE ONE STRUCTURAL FINDING (all three seats, different angles):
**the demo's title promises three agents but the script delivers
two.** Antigravity: show Codex AND Antigravity querying the shared
memory side-by-side. Codex: if Antigravity cannot perform a
meaningful on-screen operation by Tuesday, RENAME the demo around
Claude/Codex collaboration and carry Antigravity in the receipt
matrix only — more honest than a probe mention posing as
participation. Claude seat (the reproducibility angle): the second
provider appears pre-wired; the viewer never sees HOW Codex got the
tools, which reads as staged. MODERATOR FACT (from the T5' probe
record): Antigravity's receipt 6 is register+probe, sequenced
post-publish — a meaningful live operation Tuesday is PLAUSIBLE but
unproven until the probe runs. Resolution consistent with
cut-don't-fake: script the Antigravity beat CONDITIONAL (record if
the probe is green), with Codex's rename-fallback pre-written; add
Claude's 20-30s Codex-setup beat with its own receipt (the
marketplace re-sync canary covers it).

AMENDMENT LIST (converged, in outline order):
A1. Cold open DEMONSTRATES loss (Codex): Claude states a specific
    repo fact; fresh Codex is asked and cannot answer; THEN the
    caption. Replace the insider line with Claude's plain-language
    version: "Every new AI session starts from zero. You are the
    only thing carrying context between them."
A2. Act 1 pinned + honest compression: pin ONE command (fastest;
    Antigravity votes security-audit), jump-cut with persistent 4x
    badge + "full unedited run linked", narrow the claim to "no
    API key for subscription-backed use". Target 60s.
A3. Act 2 opens with the reproducibility beat: the actual
    command/stanza wiring attune into Codex (20-30s, receipted by
    the canary). If real setup exceeds ~30s, show it honestly.
A4. Acts 2+3 become ONE CONTINUOUS TASK (Codex): find bug → capture
    → recall in Codex → handoff tied to branch/diff → verify tree →
    perform the stated next action; the OPERATOR visibly triggers
    every boundary crossing (no implied autonomy); persistent task
    card (Finding / Branch / Changed files / Next action).
A5. Act 3 shows the git-verification receipt on screen
    (Antigravity): "handoffs are git-verified session contracts,
    not loose prompt copies."
A6. Act 4: meta-beat shrinks to a 3s stinger + one line; reclaimed
    time goes to a CONCRETE cross_review finding on the live diff,
    closing "The models advise. You decide." (Codex's line — more
    honest than "the product plans itself"). Full self-planning
    story stays in the article.
A7. Close: replace the receipts FLASH with a readable three-row
    evidence card (claim → provider pair → timestamp → transcript
    link), one CTA. Tighten total runtime toward ~7:30-8:00.
A8. Social cut: miracle in the FIRST 5 SECONDS (Codex recalling
    Claude's finding, captioned), then context; keep a 10s
    pip-install flash (Antigravity) so scrollers know how to try
    it.
CONTINGENCY (bind into production notes): record each boundary as
an independently usable segment so a failed Antigravity or
marketplace beat cuts cleanly without destroying the Claude→Codex
story; pre-write the two-provider rename fallback.
