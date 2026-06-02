# The Discipline of Agent Collaboration

> A counter-thesis to vibe coding, from someone shipping real work
> this way.

"Vibe coding" is the shorthand the discourse has settled on for
AI-assisted development — and it's a real thing, useful for
prototypes, exploration, and the bottom of the experience curve.
This piece is about the other 80%: the work that needs to ship,
persist across sessions, coordinate across packages, and not break
under multi-month load. That work isn't vibing. It's a discipline.
The good news: it's a learnable one.

---

## §1 — The Premise: Why Discipline, Why Now

Most "AI-assisted development" stops at suggestion and accept. The
agent finishes a sentence. The human keeps the architectural
picture. Code gets written faster than it would otherwise. The
relationship is real and useful — autocomplete on a better
autocomplete model — but it's a tiny fraction of what's possible.
The interesting space is the work that lives between sessions,
across files, and across packages: specs the agent helps scope and
revise, releases coordinated across multiple PyPI packages with pin
chains, decision matrices committed before measurement so the data
can route the call, memories that persist what was learned across
days, dashboards surfacing live state from sibling sessions you
couldn't otherwise see. That space requires a different posture
from both sides. This piece is the field manual for that other
space.

The thesis in one line: collaboration with an AI agent is not a
*tool* problem (find a better model, write better prompts) — it is
a *discipline* problem. A mutual contract, a shared vocabulary,
agreed artifact shapes, named failure modes. The disciplines are
individually boring. They compound.

And the posture isn't exotic — it's ordinary team management
applied to a teammate who happens to be an agent: an explicit
contract, clear handoffs, named boundaries. Practiced together,
the disciplines produce synergies tied to the discipline
itself; the compounding is the point, not a bonus.

Here is what that looks like on a real morning. The ops dashboard
is up in a browser tab. The family snapshot shows five PyPI
packages tracked. Telemetry shows yesterday's spend and today's.
The workflow runner lists twenty workflows with their recent green
chips. The dashboard surfaces things that would otherwise stay
invisible: a sibling session's spec status edits sitting unstaged
in the main checkout's working tree; a workspace-versus-account
spend anomaly worth a flag but not a block; four PRs in flight,
each showing its CI state. Surfacing is the dashboard's job.
Recognizing what to do with the surfaced state — that's the
discipline.

Two-layer judgment runs the cycle. The agent reads the surfaced
state, synthesizes options, recommends one, waits for the human's
call. "Commit the spec edits as their own PR" — yes, that — the
parallel session put real intentional work into those files and
they're at risk of loss if no one acts. Human approves. Agent cuts
the PR, runs verification, surfaces CI cleanly. Human green-lights
admin-merge once at the start of the batch. That authorization is
durable within the session: the agent treats it as standing
approval for similar future merges of the same shape, removing the
friction of re-asking on every nearly-identical decision. The cycle
repeats. Dashboard surfaces → agent recommends with options → human
approves at the decision point → agent executes the mechanical
work → CI lands → admin-merge under the durable authorization →
next surfacing.

The numbers from one morning: eight PRs handled to resolution.
Three PyPI releases (attune-author 0.14.1, attune-gui 0.8.0,
attune-ai 7.1.2). Five follow-ups (a publish-trigger sync, a
lockfile catch-up, a dep-cap widen, a spec-status persist, and one
dependabot PR closed and replaced when its lockfile had drifted
past the version it was bumping to). Two held without shame for
low-priority bootstrap reasons. Two real judgment calls (a minor
version bump instead of a patch when an unreleased MCP bundle was
queued in CHANGELOG; the dependabot replacement). One in-session
pushback on the agent's own plan (running code-review on a
config-only PR produces no signal — skip it, save the budget). One
proactive memory write that did not exist that morning.

What made this efficient was not magic. Five mechanisms compound.
**Clean small PRs** — each one single-purpose, easy to scope, easy
to review, no mega-PRs that bundle six unrelated concerns.
**AskUserQuestion at real decision points only** — scope expansion,
version-bump shape, release-trigger choice, admin-merge
authorization. Never at mechanical points like "should I now run
pytest?" The agent does not interrupt the human to ask permission
to do its job. **Admin-merge authorization durability** — granted
once at the top of a batch, persists for similar future merges,
zero re-asking friction within the session. **Parallel work while
CI runs** — the agent moves to the next surfaced thing while a
twelve-platform matrix cycles, never serializing waiting time,
because waiting is wasted human attention. **The dashboard as live
state** — surfacing what changed, what's ready, what's anomalous,
so the agent doesn't have to ask the human to re-explain context
that is visible on screen. None of these is clever in isolation.
The compounding is the discipline.

The rest of this piece names the six disciplines that produce
mornings like that. Each gets its own section. Each is something
you can adopt incrementally. §2 covers **the mutual contract** —
what each side owes the other, including the PR-and-approve cycle
as the middle path between agent-acts-alone and
human-approves-every-line. §3 covers **pacing** — sustainability as
a skill, the agent's role in honoring it, why this lives in a
discipline doc and not a wellness doc. §4 covers **artifact
discipline** — how specs nest XML-enhanced prompts which nest
implementation, and how pre-committed decision matrices route
choices that would otherwise drift into goalpost-moving. §5 covers
**memory discipline** — what persists, what doesn't, and why stale
memory is dangerous in a way new agent users do not yet feel. §6
covers **multi-agent coordination** — when you're not the only one,
with the failure shapes named (parallel push, worktree contention,
stranded live-state writes) and the patterns that prevent them. §7
covers **verification** — quality is not optional, dogfooding
catches what unit tests cannot, and the dashboard is also a quality
lens. §8 closes with a longer case study expanding the morning
above into a full twenty-four-hour arc.

---

## §2 — The Mutual Contract

A working contract between collaborators is not a new idea.
High-functioning engineering teams have used explicit working
agreements for decades — when the team will pair, how reviews work,
what counts as a blocker, when interrupts are okay. What we are
doing in this section is applying the same shape to human-agent
collaboration. The asymmetries between the two parties force a more
explicit version of the contract than human-only teams usually
need: one party never tires; one party cannot read past sessions
natively; one party owns all the side effects (commits, pushes,
releases, merges); one party can be replaced wholesale at any
moment without warning. The contract has to do more work because of
those asymmetries, not less.

The contract has two halves.

The human's half is *make the agent's job possible*. Concretely:
declare the working mode at session start — advancing a measurable
scope, executing a planned spec, firefighting a CI issue, or
meta-reflection with no code changes expected. State the project
(the cwd is often not the project being worked on, especially with
worktrees). State the outcome in one sentence — what should be true
at the end of this session that isn't true now. State the done-when
criteria — the acceptance condition that lets either side say the
session has finished its scoped work. None of this is performative.
Each line saves the agent from inventing wrong context and lets the
agent push back when the work begins drifting.

The agent's half is *make the partnership durable*. Neutral
curiosity over yes-and energy — the agent is not a cheerleader.
Full attention to the prompt — no skimming, no answering what the
human almost asked. Correction without ego — when wrong, admit and
adjust without theater. Honesty about limits — when a memory is
stale, say so. When a claim isn't verified, say so. When a
recommendation is informed by guesses about an API the agent hasn't
read, say so before producing the code that depends on it.

Either side ignoring its half makes the whole arrangement collapse
into transactional autocomplete. The human who treats the agent as
a vending machine — no working mode, no outcome, no done-when, just
requests one after another — does not get collaboration; they get
a slow autocomplete with a personality. The agent that treats the
human as an oracle — no recommendation, no opinion, just "what do
you want me to do" — does not get good direction; the human ends up
doing the agent's synthesis work and resents it. The contract
closes both of those failure modes.

One small rule inside the contract carries more weight than its
size suggests: **ask one question at a time**. When the agent
bundles "do you need a break?" with "what direction next?" the
human's answer to one collapses the other. The questions interact
and corrupt each other. The discipline is to separate them,
sequence them, ask the load-bearing one first, and use a structured
decision-point surface (AskUserQuestion in our tooling) as the
default form. Number the options A/B/C, label A as Recommended
where applicable, keep alternatives short. This is mechanical — not
deep — but mechanical things compound.

> **Pattern: shorthand as vocabulary primitive.** A human
> collaborator says "give me feedback" — singular phrase, no
> parameters. The agent reads it as a request for the full
> discovery kit: opportunities, options, next steps, pros and
> cons, anything load-bearing the agent noticed but didn't
> surface. Re-specifying the kit each time would waste the
> primitive — the shorthand IS the contract. The pattern
> generalizes: any phrase the human uses repeatedly should be
> readable by the agent as a structured invocation, not as a
> literal-string request. The agent's job is to learn the human's
> vocabulary, not to demand it be re-specified. The agent also
> owes a memory write the first time it notices the shorthand
> pattern — so future sessions inherit the vocabulary instead of
> relearning it from scratch.

The PR-and-approve cycle is where the contract lives at the
day-to-day level. There are two failure modes flanking it. On one
side, **agent acts alone** — the agent has line-by-line freedom and
produces wrong-scope PRs, wrong-shape version bumps, wrong release
sequences. On the other side, **human approves every line** — the
human becomes a bottleneck on every keystroke and the agent reduces
to autocomplete. Between them sits a discipline shape: the agent
does mechanical work between named decision points; the human
approves at the decision points.

What counts as a decision point: scope expansion ("this PR grew to
include X — okay?"), version-bump shape ("patch or minor here?"),
release-trigger choice ("ship the unreleased work bundled or split
into two releases?"), admin-merge authorization ("grant the durable
approval for green-CI low-risk merges, or hold and decide each
one?"), irreversible side effects (force-push to a shared branch,
deletion of a directory tree, posting to a public surface). What is
not a decision point: code formatting, lockfile updates, test runs,
CI polling, mechanical retries after a transient failure, choosing
which subagent to spawn for a research subtask. The agent surfaces
the decision points clearly with the recommendation labeled. The
human picks. The agent executes the mechanical span until the next
decision point. Today's session had roughly twelve decision points
across eight PRs. Each was a discrete surface from the agent, each
got a discrete answer, the mechanical work between was hands-off.

The shape that makes this work is *the agent earning the human's
trust at the mechanical layer*. When the human approves "go ship
these three releases in simplest-first order," they are not
approving every line of every commit; they are approving the *kind*
of work that will happen between this approval and the next
decision point. The agent that uses that approval to smuggle in an
unrelated refactor breaks the contract. The agent that asks for
re-approval at each mechanical sub-step also breaks the contract,
in the other direction — it turns the human into a babysitter. The
middle path is narrow, but it is also the one where actual
collaboration happens.

The contract above is fully compatible with the agent disagreeing
with the human. In fact, that is one of its load-bearing
properties. When the agent has a concrete alternative — not a
hedged "have you considered" but a fully-formed counter-proposal
with the file list, the diff sketch, the measurement plan — the
agent owes the human that pushback before executing. Hedging
without an alternative is cosmetic and creates friction without
value. The contract welcomes real pushback and rejects the
imitation kind.

The contract has an asynchronous mode, too — for when the human
steps away and the agent keeps working. Everything above governs
*interactive* work: decision points, recommend-and-approve. But
agents don't tire, and a known away-window is runway the human can
spend deliberately. The asynchronous contract has the same
two-obligation shape, re-pointed at unattended work.

The human's half is to queue *execution-ready* work — not merely
substantial work. Decisions made, premise fresh, path clear:
roughly, hand off implementation, not design. Decision-ambiguous
work handed to an unattended window either stalls (the agent waits
for an answer that won't come) or guesses wrong (a thousand lines
of correct implementation of the wrong thing). The artifact
altitude is the tell — tasks-level work survives an away-window;
design-level work belongs in the synchronous window where you're
present to answer. A compact invocation helps: in our tooling
`auto: <specs or PRs>` reads as "these are execution-ready, run
them to the boundary" — the same shorthand-as-vocabulary primitive
from earlier in this section.

The agent's half is to narrow to what is genuinely safe and fresh;
hold hard guardrails (no irreversible or outward-facing act — no
merge to a protected branch, no publish, no new repo, nothing
touching credentials — without the human); re-validate a spec's
premise before executing it, because specs go stale in days; and
stop honestly at the real boundary rather than manufacture busywork
or blind-execute a stale plan. The agent that pads an away-window
with low-value churn to look productive breaks the asynchronous
contract exactly as the one that smuggles in a refactor breaks the
synchronous one.

This cuts both ways at the *edges* of the work, not only the
middle. If the human's starting handoff is weak — vague, ambiguous,
or decision-heavy — the agent owes a pushback to firm it into a
strong start before proceeding, the same way it owes a clean
stopping boundary at the end rather than halting mid-edit.
Protecting the quality of the start and the stop is higher-leverage
than executing whatever phrasing happened to arrive.

---

## §3 — Pacing: Sustainability Is a Skill

Sustainable pace has decades of engineering-management evidence
behind it. Brooks's law on adding people to a late project. The
death-march anti-pattern and its predictably brittle output. The
standard expectation in mature teams that velocity must be averaged
over recovery time rather than measured in sprint peaks. The same
evidence applies to human-agent collaboration, even though the
asymmetry has shifted. Agents do not tire. The humans they work
with do. Ignoring that asymmetry produces the downstream quality
cost it always has — but the cost can land later than expected
because the agent's energy masks the human's exhaustion for hours
past where the work should have stopped.

The trap is that long agent-collaboration sessions are seductive in
a specific way. The agent reads context instantly. The agent
doesn't need a recap. The agent doesn't push back on "let's do one
more thing." So a session that should have ended at hour three
keeps going for another two, and the work in hours four and five
is consistently worse than the work in hours one through three —
not in a way that's obvious in the moment, but in a way that
surfaces three days later as a debug session for a bug that
wouldn't have existed if the original session had ended cleanly.

The first move in the discipline is the human naming their own
pattern. This is not optional. The agent cannot honor a
sustainability commitment the human has not made to themselves. The
form of the naming varies. It can be "I'm a morning person and
afternoons get sloppy," or "my polyphasic schedule means I'm
sharpest in the first ninety minutes after a nap," or "after 8pm my
best is reviewing, not writing." What matters is that it is
*named*, in writing, in the agent's memory or the project's
top-of-tree instructions, where future sessions inherit it. The
agent can't honor a commitment it doesn't know you made.

The agent's role is not to nag and not to lecture. Surface the
signal once when it appears. At session start: late hour, "I'm
tired" mentions, back-to-back sessions on something that doesn't
need it. Mid-session: frustration that doesn't match problem
difficulty, "let's just get this done," trading quality for speed
in ways the human normally would not. When the human asks the
agent to skip a safety step "because it's fine." One sentence,
named once. Then defer to the human's call. The agent is not the
supervisor; the agent is the collaborator who notices and says so
once.

The clean-stop pattern is one of the highest-leverage moves in
this discipline. Prefer ending at completion boundaries — PR
merged, spec drafted, commit pushed, decision recorded — over
mid-edit. Resuming mid-edit costs more energy than starting fresh
on a clean unit, every time. A session that ends at "PR #469
merged, dashboard reflects new state, two follow-ups noted for
tomorrow" can be picked up cold by the next session with one
paragraph of context. A session that ends at "halfway through
refactoring the routes module, three of nine files done, tests
partially updated" requires the next session to rebuild the mental
model of where the refactor was going, what's been done, what's
broken, what's intentional-incomplete vs accidental-incomplete. The
cost gap between those two pickup states is large.

The agent supports clean stops by tracking them. When the human
signals fatigue, the agent's recommended next move is not "let's do
one more thing" but "the next natural stopping point is PR #X
landing — about ten minutes of CI — would you like to wrap there?"
That framing trades zero discipline for a real pause; the human
gets to land the in-flight work AND stop cleanly. Both halves
matter.

Why is this in a discipline document and not a wellness document?
Because the shape of the work changes when you optimize for
sustainability over throughput. You write better artifacts when you
write them rested. You make fewer desperate decisions when you have
the option to defer until tomorrow. The agent learns your real
cadence rather than averaging across grinds, which means future
sessions calibrate against the work you do *well* rather than the
work you do *exhausted*. The compounding here is across weeks: the
team (you, the agent, the codebase) gets better-shaped when each
session is optimized for quality-per-hour rather than total hours.

There is also a counterintuitive point worth naming. The discipline
of stopping cleanly does not slow throughput — it raises it. We
have observed this informally across many sessions. The mornings
that started with a clear declaration of mode and outcome, ran for
three to four focused hours, and ended cleanly at a natural
boundary, consistently produced more shipped work *per week* than
the mornings that opened vague and ran until exhaustion. The reason
is that the exhaustion-tail of those longer sessions produced work
that had to be redone, which consumed the next morning's first
hour. The "extra" hours weren't extra. They were borrowed against
tomorrow's best window.

A final note on pacing inside a single session: micro-pacing
matters too. The agent should not interrupt the human at every
mechanical step. The agent should not bury the human in walls of
text when one paragraph would do. The agent should resist the
temptation to over-narrate ("I am now about to read the file…").
The collaboration runs on the human's attention budget. Spend it on
decision points and substance. Mechanical work happens silently.

---

## §4 — Artifact Discipline: Specs Nest XML Prompts Nest Implementation

Spec-driven work, pre-committed decision criteria, and structured
task decomposition are not new ideas. They are well-validated
project-management and engineering hygiene. What we are doing in
this section is naming the *layering* of those artifacts inside
human-agent collaboration, where the surface for amplifying poor
scope is much wider than with a human collaborator who can
independently push back on scope creep without being asked. A bad
spec given to a human gets pushback before any line of code is
written. A bad spec given to an agent gets a thousand lines of code
that exactly implement the bad spec, and the human now has both the
original problem and the cost of unwinding the implementation.

The shape of work the agent can do well has **four nesting
levels**, ranked by how much ceremony the work justifies. Pick the
row that matches the task at hand and adopt its four columns
together — they're calibrated as a set.

| Tier | When | Plan depth | Verify depth | Capture | PR shape |
|---|---|---|---|---|---|
| **Inline edit** | Trivial — one file, no ambiguity, diagnosis shorter than fix | None | Eyeball + existing tests | None | None or part of larger |
| **Structured one-shot** | 1–3 files, single session, no design questions | Goal + constraints + acceptance criteria in turn one | Tests + dogfood at end | Inline lesson if surprising | Single PR |
| **XML-enhanced prompt** | 3+ files, dependencies, subagent handoff plausible | Plan-mode iteration before execution | Tests + dogfood + named failure modes | Dedicated memory write | Single PR or stacked 2–3 |
| **Spec** (`/spec`) | Multi-session, design ambiguity, irreversible choices, multi-PR | Full design phase + pre-committed decision matrix | All of the above + regression guards | `decisions.md` log + memory writes | Multi-PR, often stacked |

Two rules read into this table. *The cost of over-formalizing a
trivial task is real* — a spec for a one-character fix is a
productivity tax on the system. *The cost of under-formalizing a
complex task is much larger* — a spec-shaped problem given inline
becomes wrong-scope work that requires unwinding. Right-sizing
means matching the row to the work and not being precious about
either direction.

The four tiers nest: a spec contains tasks, tasks become XML
prompts when they meet the XML-prompt criteria, XML prompts
contain structured one-shots and inline edits where appropriate.
Mistaking them as competing artifacts produces predictable failure
modes — under-scoped specs with no implementable tasks; over-scoped
XML prompts that should have logged decisions in a `decisions.md`
for posterity; structured one-shots that should have been escalated
to specs because design ambiguity surfaced mid-session.

**Spec.** Right artifact when there is genuine design ambiguity,
when the work spans multiple sessions, when you want the *why*
recorded for the next agent (or the next human reading the
codebase a quarter later), and when irreversible choices are
about to be made. Specs in our setup live in `docs/specs/<topic>/`,
orchestrated by the `/spec` slash-command. The four files aren't
formality for its own sake — each one pays specific rent:

- **`requirements.md` — states what must be true at the end.**
  Not how, not why, not the implementation. The acceptance
  condition. *The benefit:* when the spec is in flight and the
  work starts drifting, this is the document that answers "are we
  still solving the original problem?"
- **`design.md` — names the alternatives considered AND rejected
  with reasons.** A design doc without rejected alternatives is a
  TODO list with formatting. *The benefit:* future sessions
  don't re-litigate decisions you already made; they read the
  reasons and move on.
- **`tasks.md` — decomposes into independently shippable units.**
  If a task can't ship without three others also landing, it's
  the wrong slice. *The benefit:* progress is visible at task
  granularity, and partial completion is a stable state rather
  than a half-finished mess.
- **`decisions.md` — logs irreversible choices with timestamps.**
  The timestamp is the arbiter when later sessions want to
  relitigate. *The benefit:* pre-committed decision matrices stay
  credible because the commit predates the data; future-you can't
  move the goalposts on past-you.

The four-file structure is small and the editing cost is low —
most spec edits touch one or two files at a time. The discipline
is that the files exist *before* implementation starts, not after
as rationalization-of-already-shipped work.

**XML-enhanced prompt.** Right artifact when the work touches
three or more files with dependencies, when the unit will be
executed by a subagent or future session, and when you want a
self-contained executable specification rather than back-and-forth.
The schema is small (`<task>`, `<objective>`, `<context>`,
`<files-to-create>`, `<files-to-modify>` with before/after,
`<validation>`, `<risks>`); the property that matters is
*self-containment* — an XML prompt should be executable cold,
without the executor reading any other document. Paths specific.
Validation steps are concrete assertions, not "make sure it
works." Risks named with severity tags.

**Structured one-shot prompt.** Right artifact when the work fits
inside a single session and a single PR but isn't trivial enough
to skip planning entirely. Three components in the first turn:
*goal* (what success looks like), *constraints* (non-goals,
things not to touch), *acceptance criteria* (how you'll verify
it's done). No XML schema, no formal spec; just a structured
paragraph or two before the agent starts touching code. Most
day-to-day work lives in this tier. Giving it a name turns it
from "improvise the right framing" into "follow the pattern."

**Inline edit.** Right move for trivial work: a single-file edit,
a config tweak, a bug fix where the diagnosis is shorter than the
fix, a one-line documentation correction. The discipline here is
*not over-formalizing*. A spec for a one-character fix is a
productivity tax on the system.

Pre-committed decision matrices are the highest-leverage artifact
inside this discipline. When a spec's value rests on a measurable
claim — "X costs Y bytes or dollars or seconds" — write the
decision matrix *before* running the experiment. Commit the matrix
to the repo. When the measurement lands, the matrix routes the
decision automatically. Goalpost-moving becomes impossible because
the goalposts are version-controlled with a timestamp prior to the
data.

This pattern saved us real work on a recent embeddings decision in
our retrieval pipeline. The matrix was committed: if golden P@1 is
≥70% with the current zero-dependency retriever, defer the
embeddings dependency; if 60–69%, run a small additional experiment
to decide; if <60%, adopt the dependency. The measurement came in
at 73.3%. The matrix routed the decision in one minute without
debate. We had every incentive in the moment to find reasons to
adopt the heavier dependency anyway (it was the more interesting
path, the more "real RAG" path), and the matrix prevented that. The
commit timestamp is the arbiter, not your later preference.

Read first, execute second. For any open-ended task, the agent
reads everything relevant — the spec, the recent commits on
adjacent code, the test suite for the area being touched, the
memories with related tags — before executing the recommendation.
Surface only the genuinely-ambiguous items to the human. Do not
make the human re-explain context that is already in the repo. The
cost of an extra grep is seconds; the cost of executing on a
misread context can be hours and a force-push.

A worked example: the article you are reading was proposed with a
four-phase scope — outline, section drafts, integrate, derive short
forms. That structure is not decorative. It is how the agent can
deliver a meaty artifact without burning context on whole-document
re-reads at each step. Each section is its own XML-prompt-shaped
unit. Each one stands alone (a locked design constraint). When a
future session picks up the derivative-form work (LinkedIn post
from §8, Discord drops from §3/§5/§7, Twitter thread from §6), the
foundation piece is the source-of-truth and the derivative work
reads one section at a time. The structure makes the work
compositional.

One more property to name: artifact discipline is what makes
*handoffs* possible. A session ending at "spec approved, three
tasks queued as XML prompts" can be picked up by a different agent
(or the same agent in a fresh session) and produce work that
matches the original intent. A session ending at "I think we should
probably build something like…" cannot be handed off without losing
fidelity. Artifacts are the protocol that survives the session
boundary.

**The discipline needs a surface to live on.** Specs are markdown
files. XML prompts are shareable text. Memories are
version-controlled. The dashboard is a web UI over disk artifacts.
Pick tools that make these artifacts cheap to create, share, and
revisit — the surface matters less than the discipline running on
it. Our implementation is the
[attune-\* family](https://github.com/Smart-AI-Memory):
`attune-ai` as the tool belt (the plugin that orchestrates the
disciplines), with `attune-author` (authoring help content),
`attune-gui` (the ops dashboard), `attune-help` (the living-doc
help layer), and `attune-rag` (retrieval over the help corpus) as
the specialized tools the belt carries. The patterns above don't
require these specific tools — they require *some* tools that play
these roles. If you'd rather wire your own, the disciplines stand
alone; if you'd rather skip the wiring, the family is on PyPI.

---

## §5 — Memory Discipline: What Persists, What Doesn't

The agent's memory is a curated artifact, not a log. Memory in this
sense is the persistent layer that survives session boundaries —
the files in the agent's auto-memory directory, the project's
top-of-tree lessons section, the cross-linked notes that future
sessions inherit at startup. It is the long-term knowledge layer of
the collaboration. It is not the conversation transcript and it is
not the commit history. Those are logs. Memory is the curated
subset of what those logs surfaced that is worth carrying forward.

Three classes of fact help orient what belongs in memory.

**Worth saving.** Surprising user preferences. Validated approaches
that aren't obvious from the code. Recurring failure modes with
their fix shape (pre-commit's stash conflict with auto-fix hooks;
the YAML colon trap in `run:` blocks). Project-specific gotchas
where the *why* matters as much as the *what*. The common shape is
*non-obvious from the code, won't be re-derivable, has bite if
forgotten*.

**Not worth saving.** Anything `git log` already knows (who changed
what, when, in what commit). Anything the project's top-of-tree
instructions already capture as a project-wide standard.
Conversation context that ends with the session. Generic principles
the model already knows. The test for "not worth saving" is *can
the agent re-derive this in the moment by reading the code or
running a command*. If yes, don't save it; saving it just creates a
maintenance burden as it goes stale.

**Anti-saves.** These look like memory but are actively harmful.
Debugging recipes ("when X breaks, do Y") — the fix is in the code;
the commit message has the context; a recipe in memory rots the
moment the underlying code changes. Per-task state — that belongs
in a task manager, not a memory file. Snapshots of repo state
("here are the files in src/") — these are guaranteed stale within
hours.

Proactive persistence is the rule that makes memory actually work.
When the human teaches the agent something non-obvious —
preference, pattern, validated approach — the agent's job is to
*name the memory type AND implement the write*, in the same
response. "I'll save this as a feedback memory" without the actual
write is performative. The write without the naming leaves the
human guessing whether the agent actually got it. Both halves
required. Both in the same response.

The reason is that the teaching moment is the moment with the
highest fidelity. The human knows exactly what they meant, the
context is fresh, the agent can ask one clarifying question if
needed and get the precise answer. Twenty minutes later, the moment
has degraded. Twenty hours later, the moment is gone and the agent
has invented a slightly-wrong version of the lesson. The discipline
is *write while it's hot*.

Cross-linking and indexing is what turns a pile of memories into a
navigable knowledge base. Each memory references related memories.
The index file is a curated front door, not a log — it's a
one-line-per-entry pointer list, ordered semantically by topic,
kept under a length cap so the agent loads the full index at
session start. When a new memory is added, the index entry is added
in the same write. Stale entries are pruned. Duplicates are merged
into the canonical home. None of this is automatic. All of it is
discipline.

Stale memory is the dangerous category and it deserves its own
paragraph. A memory written six months ago about "the routes module
lives at `src/attune/ops/routes.py`" can be confidently wrong today
because the routes module was split into a package three months
ago. The memory is still there, the agent still recalls it, and an
action taken on the recalled fact ("edit the routes module") opens
a file that no longer exists. The discipline is *verify against
current state before acting on a recalled fact*. The cost of
`grep -r "class RoutesModule" src/` is sub-second. The cost of
executing on a stale memory can be a force-push and an apology.

This applies broadly. Memories that name functions, classes, file
paths, CLI flags, env vars — all of those are claims that *existed
when the memory was written*. They may have been renamed, removed,
or never merged. Before recommending action that depends on the
named entity, verify. "The memory says X exists" is not the same as
"X exists now." The agent that confuses those two breaks the
contract from §2 about honesty about limits.

One more category worth naming: **memories that snapshot state**
(an audit log, an architecture snapshot, a count). These are frozen
in time. If the user asks about *recent* or *current* state, the
right move is `git log` or reading the live code, not recalling the
snapshot. The snapshot tells you what was true on the date in the
frontmatter, not what is true now. Use the snapshot to understand
history; use the code to understand the present.

Finally, the consolidation discipline. Memory grows. The index
grows. Without periodic consolidation, the system silts up with
near-duplicates and stale entries that quietly mislead. The
mechanism is a reflective pass at intervals — merging
near-duplicates, fixing stale facts, pruning index entries that no
longer pay rent for their slot. This is the librarian function of
memory work. The agent is the natural worker for it; the human
approves the consolidation diff. Schedule it like any other
maintenance activity. Without it, the value of memory degrades to
noise inside a few months.

---

## §6 — Multi-Agent Coordination: When You're Not the Only One

The coordination patterns named in this section — don't push
without fetching, the PR-and-approve cycle, durable authorizations,
clear ownership of side effects — are what distributed engineering
teams have used for years. Applying them deliberately to
human-agent collaboration matters more because the failure modes
here (parallel sessions clobbering each other's work, silent
live-state writes from one session that another session can't see,
lost handoffs across worktree boundaries) are harder to spot when
one party can't independently advocate for itself in the way a
human teammate would.

The reality of a serious working setup is that multiple sessions of
the same agent run in parallel. Different worktrees. Different
terminals. Different machines. Sometimes different users. Each
session writes to a shared filesystem, can push to the same PR
branches, can write to the same memory files, can flip status on
the same specs. Coordination is not an edge case — it is the
baseline.

The collision shapes that recur:

**Parallel push to the same PR.** Two sessions push to the same
branch. The slower one runs `git push` and sees "Everything
up-to-date." That message does not disambiguate "already pushed by
me" from "your peer beat you to it." The wall-clock between your
last fetch and your push is not a vacuum; an upstream peer may have
written in the gap. The discipline: after any "up-to-date" message,
run `git fetch origin <branch> && git log HEAD..origin/<branch>`.
If the remote has commits HEAD doesn't, a peer pushed in the gap.
Do not assume "up-to-date" means "your work landed."

**Worktree main-branch contention.** A sibling worktree holds the
`main` branch checked out in the bare repository's tracking. When
you run `gh pr merge` from a non-main worktree, the remote merge
succeeds, but the local post-merge fast-forward of main fails with
a confusing "branch is already used by worktree at…" error. The
exit code is non-zero. The merge looks like it failed. It did not.
Verify state with `gh pr view <PR> --json state,mergedAt,mergeCommit`
and trust the API, not the local exit code. The remote is
authoritative; the local fast-forward is convenience.

**Live-state writes from another session.** This is the failure
mode that drove a real spec this week. The ops dashboard writes
spec status changes directly to disk in the working tree as part of
its UI flow — not as commits. When the session that hosted the
dashboard ends, those writes are stranded: real intentional state
changes that exist only as unstaged modifications in the main
checkout's working tree, invisible until someone runs `git status`
and sees ten modified spec frontmatter files with no commit
attached. Hit this exactly that way today. Ten spec edits, all
real, all at risk of loss.

The general discipline for collision-avoidance is *treat the
wall-clock between your fetch and your write as not-a-vacuum*.
After any "rebase + force-push" cycle on an active main, re-fetch
and re-rebase if upstream moved in the gap. Before admin-merging a
base PR with `--delete-branch`, re-target the stacked PRs first so
they don't auto-orphan. Before assuming you understand the working
tree, run `git status` AND grep for known live-write surfaces
(dashboard-driven status writes, telemetry buffers that haven't
flushed, journal files from in-flight workflows). The rule is
mechanical. The cost of doing it wrong is not.

Admin-merge authorization durability is a named pattern worth
pulling out. The human grants admin-merge authorization once at the
start of a batch — "yes, you can admin-merge the green-CI low-risk
merges as they land." The agent treats that grant as durable for
similar future merges *within the session*. Saves friction across
the next four or eight merges; the human is not re-asked on each
one. The discipline runs in both directions. The agent does not
re-ask on each similar merge (eliminates friction). The human
trusts that the agent's definition of "similar" matches theirs
(eliminates scope creep). When the agent is unsure whether a merge
fits the scope — a merge that touches a different package, a merge
that drops protection for longer, a merge with non-green CI — it
asks. Authorization durability is *not* permission to expand. It is
permission to repeat the same pattern.

> **Before adopting this pattern.** Admin-merge authorization
> durability is an advanced move. It presumes preconditions an
> inexperienced operator may not have, and adopting it without
> them turns a safety mechanism into theater.
>
> - **Trust history.** The human has watched the agent operate
>   over many prior decision points — observed it push back, ask
>   when unsure, decline to act. Trust is earned per-collaboration,
>   not transferred between projects or between models.
> - **CI that's load-bearing.** Green CI must mean the code's
>   non-trivial behaviors were exercised. At 30% coverage, "green"
>   is decoration; auto-merging on it shortcuts a review that
>   wasn't going to happen anyway.
> - **Branch protection that survives the grant.** A code-review
>   requirement the agent cannot silently bypass — only a temporary
>   admin-merge dance lowers it, and only briefly. The dance is
>   friction by design; if your setup makes the dance free, the
>   safeguard is theater.
> - **Recoverable work.** Pre-prod, non-customer-facing,
>   easy-to-revert. Don't auth durably for production deploys,
>   security-sensitive merges, schema migrations, or anything
>   that touches customer-data paths.
> - **The agent's "this doesn't fit" reflex.** When in doubt
>   about whether a PR fits the grant — different package,
>   different risk profile, non-green CI — the agent asks. The
>   agent that smuggles a different-shaped merge into the grant
>   breaks the contract from §2.
>
> If you're advising someone newer to agent collaboration, the
> default is "ask each merge, read each diff." Durable auth is
> what you graduate to once those five preconditions are real,
> not what you reach for to save typing.

The dashboard as a coordination surface is the read-side of this
discipline. When multiple sessions can write to a shared system,
the dashboard becomes the queue where you find out what has
happened. Specs flip status. Sessions list updates. Run telemetry
accumulates. Family snapshots show package versions across the org.
The discipline is to use the dashboard at decision points, not just
at end-of-day. It is the lens that makes coordination judgment
possible.

Two-layer judgment runs the cycle, and it is the same shape as §1.
The dashboard surfaces raw state (telemetry numbers, spec status
flips, recent run chips, family snapshot, anomalies). The agent
synthesizes options and recommends. The human picks. The dashboard
is not the decision-maker. The dashboard is the lens that makes
decision-quality possible. Today's session: the dashboard surfaced
the other session's ten unstaged spec edits (otherwise invisible
from a fresh agent session), a workspace-versus-account spend
anomaly (worth flagging, not blocking), the in-flight PRs' CI
states. Each surfacing routed to an agent recommendation that
routed to a human decision that routed to mechanical execution. The
cycle is the discipline.

The worked example of discipline running on itself: the same
session that surfaced those ten unstaged spec edits also *designed
and shipped a proactive solution* to the underlying class of bug in
the same afternoon. Sequence: the agent named the class of bug —
live-state writes from session-bound services becoming silent debt
when sessions end. The agent enumerated six solution candidates
with a pros-and-cons table. The agent recommended a layered
approach (a durable journal of pending writes, an API for
inspecting them, consumer wiring on the write sites) and named why
each layer addressed a distinct damage mode. The human approved the
design. The agent proposed phasing — Phase 1 today, Phases 2 and 3
deferred — and the human approved that scope cleanly. The agent
wrote the full spec at
[`docs/specs/dashboard-pending-writes-journal/`](../specs/dashboard-pending-writes-journal/),
with requirements, design, and a `decisions.md` logging eight
durable choices. The agent implemented Phase 1 in roughly an hour
and a half — a journal writer, an API endpoint, the spec-status
setter wire-in, and twenty-five tests, all green. An end-to-end
smoke test against the live dashboard confirmed the cycle. The PR
opened as
[attune-ai #469](https://github.com/Smart-AI-Memory/attune-ai/pull/469).

The point of the worked example is the meta-shape. The article's
central thesis — discipline produces better work faster — gets
demonstrated by the act of using the discipline to address the
discipline's own friction. The spec design AND the implementation
AND this paragraph are all products of the same multi-hour session.
No single piece of that work is impressive in isolation. The
compounding *is* the discipline.

---

## §7 — Verification: Quality Is Not Optional

An LLM-driven documentation pass on a real codebase produced six
classes of hallucination in a single page — invented CLI flags,
wrong import paths, fabricated cross-references, wrong route paths,
an insecure example, a fabricated numeric count. The unit tests
caught zero of them. Three of the six would have broken readers who
followed the docs literally. Verification, not taste, is what
closes that gap.

The verification gap is the space between "the code compiles and
the tests pass" and "the work actually does what the work was
supposed to do." An agent that runs tests is not an agent that
verified the work. Tests pass on bad code constantly — when the
test was written from the same misunderstanding as the code, both
sides agree on the wrong thing and the test reports green. Coverage
is green on dead code paths. Type checks pass on functions that no
caller ever invokes. The gap is real and large.

The dogfood principle is the single highest-leverage move in
closing the gap. Before declaring an LLM-generated artifact done,
run the artifact against a realistic input it will actually face in
production. The six-hallucination case from the opening above is
what dogfooding catches that unit tests cannot — the polished help
page passed its unit tests cleanly. Dogfood runs are slower than
unit tests by orders of magnitude, but they operate at the
*meaning* layer, where the hallucinations live. A unit test asserts
that the function returned the expected type; the dogfood run
asserts that the function returned something *true*. Those are
different properties. Both are needed. Neither replaces the other.

Verification beats taste. The temptation to read an agent-generated
artifact and approve it based on prose feel is strong. Discipline:
name the concrete verification step *before* generation starts. For
doc generation, resolve every CLI flag against the live `--help`
output. Parse every Python import. Traverse every markdown link to
confirm the target exists. Verify every numeric claim against its
source. For code generation, run the function against
representative inputs and confirm the outputs match expected. For
spec generation, identify the irreversible decisions and verify
each is logged with rationale. The verification is the artifact.
The prose is decoration.

This is not a counsel of perfection. The verification step does not
need to catch every possible bug; it needs to catch the *named
failure modes* that are known to recur. For LLM-generated
documentation, the failure modes are: fabricated symbol names,
fabricated CLI flags, fabricated cross-references, route-shape
errors, version-mismatched code samples, insecure example code,
fabricated quantitative claims. A six-step automated verification
pass that checks for those six failure modes will catch most of
what slips past taste. The pass is not glamorous. It is
load-bearing.

Decision matrices are also verification. When you commit the "if A
then X, if B then Y" matrix before measurement, the measurement
*automatically* routes the decision. The verification is built into
the artifact's shape. There is nothing to "review" — the matrix
says what to do; the measurement says which branch fires; the
decision follows mechanically. This eliminates an entire class of
post-hoc rationalization where the human (or the agent) finds
reasons to favor the more interesting path against what the data
actually says. The matrix is verification by structure.

The dashboard is a quality lens. Watch for drift over time. Stale
specs that should have moved status weeks ago and didn't. Broken
cross-package pins where a sibling's version moved and the
dependent didn't widen. Telemetry anomalies (today: workspace-local
seven-day spend exceeded account-level seven-day spend by a
non-trivial margin; that is mathematically impossible if the local
counter is the local subset of the account counter; one of the two
is wrong; worth flagging, not blocking; logged for diagnosis
later). Use the dashboard at decision points, not just at
end-of-day. The dashboard is reading what unit tests cannot reach:
the state of the *world* the code lives in, not the state of the
code in isolation.

A specific verification pattern worth naming: **the regression
guard**. After fixing a bug, write a test whose only purpose is to
fail loudly if the bug returns. The test does not need to be
beautiful. It needs to fail when the bug is back. The most valuable
regression guards are the ones that nail a specific past failure
mode by name. We have one that asserts the `Path.endswith("/...")`
pattern is not used in tests because Windows paths break it. We
have one that asserts a specific dataclass field is required at
construction because forgetting it silently shipped wrong telemetry
for ten days. Each guard is mechanical, narrow, and durable. None
of them is glamorous. The collection compounds into a wall that
past failure modes do not get to recur through.

A note on what verification is *not*. It is not asking the agent
"are you sure this is right?" The agent will say yes because the
agent is wired to be helpful. It is not skimming the diff for an
hour because diffs of a thousand lines exceed the human's ability
to spot anomalies. It is not relying on the agent's "I have
verified that…" claim — which is a verbal report, not a
verification artifact. Verification is a thing that *runs* and
*produces an output*. If you cannot name what would have failed if
the bug were present, you have not verified.

The verification discipline is also what makes *trust* sustainable
across sessions. A human who trusts the agent because the agent
claims to be careful is trusting a verbal report. A human who
trusts the agent because the verification pass passed is trusting
a check. The first trust is fragile and erodes the first time a
confident agent ships a confident bug. The second trust accumulates
because the check is doing the work of being trustworthy.
Verification offloads trust from the relationship to the artifact,
which is where it belongs.

The dashboard as quality lens, the dogfood principle, decision
matrices as structural verification, regression guards as durable
failure-mode protection — these are not separate practices. They
are four shapes of the same property: *something runs and tells the
truth about the work, independent of whether anyone wants to
believe it*. The discipline is to wire those checks in before they
are needed and to honor their outputs when they fire.

**The receipt.** Across the attune-\* family — five PyPI packages,
multiple months of agent-collaborated development — test coverage
sits at **93%**. That number isn't a target we aimed at; it's a
byproduct of treating regression guards as non-optional and
dogfood verification as part of the work, not an add-on.
Discipline produces measurable artifacts. The artifact is the
proof.

---

## §8 — What This Looks Like When It Goes Right: A Twenty-Four-Hour Case Study

The morning of 2026-05-25 began with attune-rag 0.2.0 already on
PyPI — shipped overnight in a clean release ceremony. The
downstream pin-widens were the work of the day. Three sibling
packages (attune-author, attune-gui, attune-ai) each carried a cap
on attune-rag that needed to lift to admit the new version. None of
those widens was difficult in isolation. The compounding question
was the sequence and shape.

The session opened with the working mode declared: advancing a
measurable scope (the pin widens), the outcome named (all three
siblings shipping pin-widened versions to PyPI), the done-when
criteria stated (every dependent verifiable on `pip install <pkg>`
from a clean venv). The agent read the relevant CHANGELOG sections,
the lockfile state of each sibling, the open PRs on each. The
dashboard surfaced the family snapshot: five packages, current
versions, who depends on whom.

The first call was simplest-first order. attune-author had the
cleanest cap-widen — single-line bump, no transitive complications.
Ship that. Then attune-gui. Then attune-ai, which had the most
surface area. The agent recommended; the human approved.

attune-author 0.14.1 went smoothly. Cap widened, CHANGELOG bumped,
tag pushed, publish workflow approved, PyPI confirmed within ten
minutes. Clean. Move to attune-gui.

attune-gui surfaced a judgment call. The widen itself was trivial,
but `CHANGELOG.md` showed an unreleased MCP bundle queued under
`## [Unreleased]` that the maintainer had been holding for the next
minor. A patch release here would bundle the bundle without intent
— the maintainer was waiting for the right moment to ship that
work. The agent surfaced the choice with options. Option A: ship as
0.7.5 patch, bundle the MCP work as an unintended ride-along.
Option B: ship as 0.8.0 minor, intentional inclusion of the MCP
work that was already documented as ready. Recommendation: B,
because the work was already documented as `[Unreleased]` and
ready, and a minor bump is the right shape for "new feature
accompanies the pin widen." Human approved. attune-gui 0.8.0
shipped.

attune-ai 7.1.2 hit a different snag mid-flight. A dependabot PR
for the `codeql` action had landed on main two hours earlier with a
lockfile that had drifted past the version it was bumping to — the
action self-bootstrapped during the dependabot run. The PR looked
merged but the lockfile was now wrong. The agent's recommendation:
close the dependabot PR (do not re-bump, the action version was
correct), then manually re-cut a lockfile-only PR to restore
correctness. Human approved. The replacement PR landed clean.
attune-ai 7.1.2 pin-widened and shipped to PyPI under the same
ceremony.

At this point the dashboard surfaced something unexpected: ten spec
status edits in the main checkout's working tree, modified but
unstaged. The signature was a parallel session writing through the
ops dashboard's spec-status setter — live writes that landed on
disk but never made it into a commit. The session that owned them
had ended. The edits were real. The agent surfaced the find with
options. Commit them as their own PR (preserving the parallel
session's work). Stash them and investigate later. Discard them
(deny the parallel session's work). Recommendation: commit, because
the edit pattern (status transitions on currently-active specs) was
unmistakably intentional and at risk of loss. Human approved. A
spec-status persistence PR was cut, reviewed quickly (the diffs
were small and self-consistent), and merged.

That find — ten unstaged spec edits surfaced by the dashboard from
a parallel session — drove the design work of the rest of the
afternoon. The class of bug was named: live-state writes from
session-bound services become silent debt when sessions end. The
agent enumerated six solution candidates with a pros-and-cons table
— a durable journal, a session-end commit hook, periodic
auto-commit, a dashboard-side "stage these" button, a "pending
writes" overlay, a hard "no live writes outside commits" stance.
The recommendation was a layered approach: a durable journal of
pending writes (Phase 1), an API for inspecting and resolving them
(Phase 2), consumer wiring on write sites (Phase 3). Phase 1 was
small enough to ship today; Phases 2 and 3 were deferred to
dedicated future sessions. The human approved the design and the
phasing.

The agent wrote the spec at
[`docs/specs/dashboard-pending-writes-journal/`](../specs/dashboard-pending-writes-journal/).
Requirements, design, decisions with eight durable choices logged,
tasks broken down. The full spec was reviewable in under fifteen
minutes. The agent implemented Phase 1: a journal writer, an API
endpoint, the spec-status setter wire-in, twenty-five tests
covering the happy path and the failure modes. All green on the
first full pass. Smoke test against the live dashboard confirmed
the cycle: a spec status flip now lands in the journal *before*
writing to disk; the journal records the pending write; on next
reconciliation the journal entry is cleared. The PR opened as
[attune-ai #469](https://github.com/Smart-AI-Memory/attune-ai/pull/469).
Admin-merge under the durable session authorization. Done.

Four PyPI releases. One mid-session pivot when the dependabot
anomaly surfaced. One judgment call on minor-versus-patch. One
proactive design and ship-cycle in response to a live-state-write
find. Six end-to-end ships if you count the spec-status persist and
the journal as their own. Two real decision points the agent could
not have made alone. Roughly twelve mechanical decision points
across the session that the agent handled without re-asking. One
in-session pushback on the agent's own initial plan to run
code-review on a config-only PR (no signal; skip; save the budget).
One proactive memory write that did not exist at session start (the
don't-enable-fatigue-push lesson, named after the third fatigue
signal in three days). Test coverage across the family stayed at
**93%** — not because we ran a coverage push but because regression
guards landed alongside the new code. A handful of clean stops at
completion boundaries when the human signaled fatigue.

The point of the case study is not that the morning was
breathtaking. No single decision in that sequence was virtuoso. The
shipped releases were routine. The spec was small. The
implementation was an hour and a half of focused work. What made
the morning unusual was the *absence* of friction: no parallel-push
collisions, no over-formalization on the trivial decisions, no
under-scoping on the substantive ones, no re-explaining context
that was already visible on the dashboard, no fatigue-grinding past
the productive window. Six disciplines, each boring in isolation,
compounding into a morning where the work *moved*.

And that morning wasn't a one-off. Across the two weeks ending
2026-06-02, the same one-developer-plus-agent setup merged
**130 pull requests — roughly nine per calendar day** — into the
attune-ai repository. The composition matters more than the
headline: about fifty were feature and fix code; the rest were
documentation, specs, and release work the discipline keeps
moving in lockstep with the code. That lockstep is the point —
§5's memory and §4's artifacts mean the docs and specs *keep
pace* rather than accruing as debt behind the shipping. The
number is a dated snapshot of what the discipline produced here,
not a multiplier anyone is promised.

The closing point is simple. This is a learnable skill. The
discipline above is six bullet-points worth of vocabulary, not a
worldview, not an ideology, not a stance on AI. Adopt the contract
from §2. Adopt the pacing from §3. Adopt the artifact nesting from
§4. Adopt the memory rules from §5. Adopt the multi-agent awareness
from §6. Adopt the verification gates from §7. Practice each one
boring-ly until they compound. The mornings that result are
unremarkable in any single moment, and remarkable across a week.

There is a tell in how this article got written. The attune-\*
family is these disciplines turned into software — attune-ai
builds and maintains the others — and the disciplines, once
named, keep generating the next thing. Drafting this piece
surfaced a friction none of the six quite covered; naming it
produced a new spec by the end of the session. The discipline
didn't only describe the work. It generated more of it. That is
the synergy — tied to the discipline itself, not to any one
tool.

That is the discipline of agent collaboration. We are still
learning it. We hope this is useful.

---

## A note on the authorship

This piece was written collaboratively. Patrick Roebuck (founder,
Smart AI Memory) drafting, directing, and making every irreversible
call; an AI agent helping to author under the discipline this
article describes. Patrick brings three decades of software
development plus earlier years in coordination-heavy roles outside
engineering — patterns that shape his approach to contracts,
pacing, and multi-party work. The past year-plus has been spent
building the [attune-\* ecosystem](https://github.com/Smart-AI-Memory)
— five PyPI packages (attune-ai, attune-rag, attune-author,
attune-help, attune-gui) that together ship the workflow patterns
described above. The evidence base for the claims here is that
codebase and the multi-month working history that produced it.
