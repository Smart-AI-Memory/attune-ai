# The Discipline of Agent Collaboration — Outline

**Status:** SUPERSEDED — the article this outlined shipped and is
live at attune-ai.dev/discipline (Draft v5, published 2026-07-02,
revision history in
`COLLABORATION_DISCIPLINE_revision_2026-07-02_proposal.md`). Kept
as the historical outline record. (Was: outline APPROVED
2026-05-25 · ready for Phase 3b section drafting.)

**Working title (locked 2026-05-25):**

> **The Discipline of Agent Collaboration**
>
> *— a counter-thesis to vibe coding, from someone shipping real
> work this way*

The title carries the frame; the subtitle does the SEO + positioning
work. We don't mix "vibing" into the title because the piece is its
direct counter-thesis (discipline, persistence, named failure modes)
and that would attract the wrong readers (the ones looking for
permission *not* to have a discipline). Counter-positioning in the
opening + tagging gets the SEO benefit without compromising the
message.

**Opening paragraph (locked) — sets the counter-positioning:**

> "Vibe coding" is the shorthand the discourse has settled on for
> AI-assisted development — and it's a real thing, useful for
> prototypes, exploration, and the bottom of the experience curve.
> This piece is about the other 80%: the work that needs to ship,
> persist across sessions, coordinate across packages, and not
> break under multi-month load. That work isn't vibing. It's a
> discipline. The good news: it's a learnable one.

**Publishing tags (for SEO when published):**

`vibe coding` · `AI agents` · `agentic development` · `Claude
Code` · `AI-assisted development` · `developer productivity` ·
`engineering discipline` · `solo dev` · `multi-package release`

---

## Audience

**Primary:** engineering managers and senior individual contributors
who already have hands-on time with an AI agent (Claude Code,
Cursor, Aider, etc.) and have hit the ceiling of "fancy autocomplete."
They suspect there's a real collaboration shape they haven't
unlocked, but the existing discourse is either evangelism (works
for everything) or dismissal (it's just statistical pattern
matching). They want a discipline they can adopt and a vocabulary
to teach their teams.

**Secondary:** AI product engineers shipping agentic features
who need to understand the human side of the loop they're
designing for.

**NOT for:** people who haven't used an agent yet (this won't
sell them on it), or people looking for prompts (we don't ship
prompts here, we ship discipline).

---

## Length target

8,000–9,500 words. ~7 sections of ~1,100–1,300 words each.
Each section can stand alone as a tutorial or short post (Phase
3d derivative-form roadmap below).

---

## Narrative arc (one sentence)

Working productively with an AI agent isn't about better prompts
or better tools — it's about adopting a small set of mutual
disciplines (each one boring on its own, compounding when
practiced together) that let the agent function as a real
collaborator rather than a sophisticated autocomplete.

---

## Sections

### §1 — The Premise: Why Discipline, Why Now (~1,000 words)

**Open the gap (~200 words).** Most "AI-assisted development"
stops at suggestion + accept. The agent finishes the sentence;
the human keeps the architectural picture. That arrangement is
real, but it's a tiny fraction of what's possible. The
interesting space — specs the agent helps you scope, releases
the agent coordinates across packages, decision matrices the
agent commits to before measurement, memories the agent
maintains across sessions, workflows the agent recommends and
the dashboard surfaces — requires a different posture from both
sides. This piece is the field manual for that other space.

**The thesis in one line (~100 words).** Collaboration with an
AI agent is not a *tool* problem (better model, better prompt)
— it's a *discipline* problem (mutual contract, shared
vocabulary, agreed artifact shapes, named failure modes).
Discipline is boring. Discipline compounds.

**Personal evidence — the vignette (~500 words, REWRITTEN per
2026-05-25 feedback).** Two paragraphs walking through one
concrete cycle from a real session:

*Paragraph 1 — The dashboard surfaces.* Set the scene: the ops
dashboard up in a browser tab, family snapshot showing five
packages tracked, telemetry showing yesterday's spend and
today's, the workflow runner listing 20 workflows with recent
green chips. The dashboard surfaces a state-shaped picture: a
sibling session's spec status edits sitting unstaged in main
checkout's working tree (otherwise invisible); a workspace-vs-
account spend anomaly (worth a flag, not a block); the four
PRs in flight showing their CI state. Surfacing is the
dashboard's job. *Recognizing what to do with the surfaced
state — that's the discipline.*

*Paragraph 2 — Two-layer judgment.* The agent reads the
surfaced state, synthesizes options (commit the spec edits as
their own PR / stash / discard), recommends one ("commit them —
real intentional work from the parallel session, at risk of
loss"), waits for the human's call. Human approves. Agent cuts
the PR, runs the verification, surfaces CI cleanly. Human
green-lights admin-merge once at the start of the batch; that
authorization is durable within the session (a discipline
shape — granted once, persists for similar future merges). The
cycle repeats: dashboard surfaces → agent recommends with
options → human approves at the decision points → agent
executes the mechanical work → CI lands → admin-merge under
the durable authorization → next surfacing.

*The numbers from one morning.* Eight PRs handled to
resolution — three PyPI releases (attune-author 0.14.1,
attune-gui 0.8.0, attune-ai 7.1.2) and five follow-ups (a
publish-trigger sync, a lockfile catch-up, a dep-cap widen, a
spec-status persist, plus one dependabot PR closed and
replaced when its lockfile had drifted). Two held without
shame for low-priority bootstrap reasons. Two real judgment
calls (a minor bump instead of a patch when an unreleased MCP
bundle was queued; the dependabot replacement). One in-session
pushback on the agent's own plan (code-review on config-only
PRs is no-signal; skip it). One proactive memory write that
didn't exist that morning.

*What made it efficient — not magic.* Five mechanisms compound:
(1) **clean small PRs** — each one single-purpose, easy to
scope, easy to review, no mega-PRs; (2) **AskUserQuestion at
real decision points only** — scope expansion, version-bump
shape, release-trigger choice; never at mechanical points
like "should I now run pytest?"; (3) **admin-merge authorization
durability** — granted once, persists for similar future merges,
zero re-asking friction; (4) **parallel work while CI runs** —
the agent moves to the next surfaced thing while a 12-platform
matrix cycles, never serializing waiting time; (5) **the
dashboard as live state** — surfacing what changed, what's
ready, what's anomalous, so the agent doesn't have to ask the
human to re-explain context. None of those mechanisms is
clever on its own. The compounding is the discipline.

**Roadmap (~200 words).** Six disciplines, each in its own
section, named here in advance so the reader has the vocabulary
when it appears in the vignette:

- **§2 The Mutual Contract** — what each side owes the other.
  Where the PR-and-approve cycle lives as a concept (human
  approves at decision points; agent does the mechanical work
  in between).
- **§3 Pacing** — sustainability as a skill.
- **§4 Artifact Discipline** — specs nest XML prompts nest
  implementation. Where decision matrices commit before
  measurement.
- **§5 Memory Discipline** — what persists, what doesn't.
- **§6 Multi-agent Coordination** — when you're not the only
  one. Where admin-merge authorization durability and dashboard-
  as-shared-state live as named patterns.
- **§7 Verification** — quality is not optional. Where the
  dashboard-as-quality-lens completes its concept.
- **§8 What it looks like when it goes right** — the full
  24-hour case study expanding the vignette above.

**Source material:**
[CLAUDE.md](../../.claude/CLAUDE.md) lesson clusters, the
multi-package release narrative from 2026-05-25, the eight
disciplines outlined below (six core + opener + case study).

---

### §2 — The Mutual Contract (~1,100 words)

**Lineage anchor.** The contract concept isn't novel: explicit
working contracts have been standard practice in high-functioning
engineering teams for decades — what we're doing is applying the
same shape to human-agent collaboration, where the asymmetries
between the two sides (one never tires, one can't read past
sessions, one owns all the side effects) force a more explicit
version of the contract than human-only teams usually need.

**The two halves of the contract.**

(a) The human's commitments to the agent: *make the agent's job
possible*. Concretely: declare the working mode at session
start (advancing a measurable scope vs executing a planned spec
vs firefighting vs meta-reflection); name the project, the
outcome, and the done-when criteria; let the agent push back
when the alternative is concrete; surface energy/scope tradeoffs
explicitly rather than pushing through.

(b) The agent's commitments to the human: *make the partnership
durable*. Concretely: neutral curiosity (not yes-and energy);
full attention (no skimming the prompt); correction without ego
(when wrong, admit and adjust without theater); honesty about
limits (when a memory is stale, say so; when a claim isn't
verified, say so).

**Why both halves matter.** Either side ignoring its half makes
the whole thing collapse into transactional autocomplete. The
human who treats the agent as a vending machine doesn't get
collaboration. The agent that treats the human as an oracle
doesn't get good direction.

**The "ask one question at a time" rule.** Surprisingly
load-bearing. When the agent bundles "do you need a break?"
with "what direction next?" the human's answer to one collapses
the other. The discipline: separate the questions, sequence
them, A-is-recommended option labeling, AskUserQuestion as the
default decision-point surface.

**The PR-and-approve cycle as middle path (~200 words to add).**
Between two failure modes:
- *Agent acts alone* (line-by-line freedom; produces wrong
  scope, wrong version-bump shape, wrong release sequence)
- *Human approves every line* (defeats the point of the
  collaboration; agent reduces to autocomplete)

…there's a discipline shape: **the agent does mechanical work
between named decision points; the human approves at the
decision points.** What counts as a decision point: scope
expansion (this PR grew to include X — okay?); version-bump
shape (patch or minor?); release-trigger choice (bundle the
unreleased work or split?); admin-merge authorization (grant
or hold?). What doesn't: code-formatting, lockfile updates,
test runs, CI polling, mechanical retries. The agent surfaces
the decision points clearly (AskUserQuestion with the
recommendation labeled); the human picks; the agent executes
the mechanical span until the next decision point.

Worked example: today's session had ~12 decision points across
8 PRs. Each was a discrete surface from the agent; each got a
discrete answer; the mechanical work between was hands-off.

**Source material:**
[feedback_my_commitments_to_patrick](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_my_commitments_to_patrick.md),
[feedback_collaboration_pace](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_collaboration_pace.md),
[feedback_one_question_at_a_time](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_one_question_at_a_time.md),
[feedback_lead_with_recommendation](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_lead_with_recommendation.md).

---

### §3 — The Pacing Discipline: Sustainability Is a Skill (~1,000 words)

**Lineage anchor.** Sustainable pace has decades of
engineering-management evidence behind it: Brooks's law, the
death-march anti-pattern, the standard expectation that team
velocity must be averaged over recovery time — and the same
evidence applies here, even though the asymmetry has shifted:
agents don't tire, but the humans they work with do, and
ignoring that produces the downstream quality cost it always has.

**The trap.** Long agent-collaboration sessions are seductive.
The agent doesn't tire. The human does. The asymmetry tempts
both sides to keep pushing past the point where work-quality
peaks.

**The first move.** The human names their own pattern. Patrick
explicitly self-identified that pushing through exhaustion
creates downstream debug cost that wouldn't have existed if
he'd rested instead. That self-knowledge is a gift to the
agent — it lets the agent honor a commitment the human is
making to himself.

**The agent's role.** Not nag. Not lecture. Surface the signal
once when it appears: at session start (late hour, "I'm tired"
mentions, back-to-back sessions), mid-session (frustration that
doesn't match problem difficulty, "let's just get this done",
trading quality for speed), or when the human asks the agent
to skip a safety step "because it's fine." One sentence. Defer
to the human's call.

**The clean-stop pattern.** Prefer ending at completion
boundaries (PR merged, spec drafted, commit pushed) over
mid-edit. Resuming mid-edit costs more energy than starting
fresh on a clean unit.

**Why this is in a discipline doc, not a wellness doc.** The
shape of the work changes when you optimize for sustainability
over throughput. You write better artifacts. You make fewer
desperate decisions. The agent learns your real cadence rather
than averaging across grinds.

**Source material:**
[feedback_dont_enable_fatigue_push](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_dont_enable_fatigue_push.md),
[user_disability_sleep](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/user_disability_sleep.md),
[feedback_collaboration_pace](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_collaboration_pace.md).

---

### §4 — Artifact Discipline: Specs Nest XML Prompts Nest Implementation (~1,200 words)

**Lineage anchor.** Spec-driven work, pre-committed decision
criteria, and structured task decomposition aren't new — they're
well-validated project-management and engineering hygiene — but
they take on more weight in human-agent collaboration, where the
surface for amplifying poor scope is much wider than with a
human collaborator who can independently push back on scope creep.

**The shape of work the agent can do well.** Three nesting
levels:

- **Spec** — design ambiguity exists; the work spans multiple
  sessions; you want the *why* recorded for the next agent
  (or the next human); a *decisions.md* persists the
  irreversible choices. Use `/spec`.
- **XML-enhanced prompt** — work touches 3+ files with
  dependencies; the unit will be executed by a subagent or
  future session; you want a self-contained executable spec
  rather than back-and-forth. Use the schema.
- **Just do it inline** — trivial change, one file, no
  ambiguity. Don't over-formalize.

**Specs aren't alternatives to XML prompts — they layer.**
A spec's tasks are XML prompts at the implementation level.
Mistaking them as competing artifacts produces either
under-scoped specs (no implementable tasks) or over-scoped
prompts (decisions that should have been captured in a
decisions.md log).

**Pre-committed decision matrices.** When a spec's value rests
on a measurable claim ("X costs Y bytes/dollars/seconds"),
write the decision matrix BEFORE running the experiment. Commit
the matrix to the repo. When the result lands, the matrix
routes the decision without goalpost-moving. The commit
timestamp is the arbiter.

**Read first, execute second.** Open-ended tasks: read
everything (the spec, the relevant memories, the recent
commits, the test suite) before executing the recommendation.
Surface only the genuinely-ambiguous items. Don't make the
human re-explain context that's already in the repo.

**Worked example.** The 8000-word piece you're reading was
proposed with a 4-phase scope (outline → section drafts →
integrate → derive). That structure isn't decorative — it's
how the agent can deliver a meaty artifact without burning
context on whole-document re-reads. Each section is its own
XML-prompt-shaped unit.

**Source material:**
[.claude/rules/attune/xml-enhanced-prompts.md](../../../.claude/rules/attune/xml-enhanced-prompts.md),
[.claude/rules/attune/decision-routine.md](../../../.claude/rules/attune/decision-routine.md),
[docs/implementation/TASK_PROMPTS.md](../implementation/TASK_PROMPTS.md),
attune-rag faithfulness-decision-2026-04-19.md as a
decision-matrix worked example.

---

### §5 — Memory Discipline: What Persists, What Doesn't (~1,100 words)

**The agent's memory is a curated artifact, not a log.** Three
classes of fact:

- **Worth saving** — surprising user preferences, validated
  approaches that aren't obvious from the code, recurring
  failure modes, project-specific gotchas with the *why*
  attached.
- **Not worth saving** — anything `git log` already knows,
  anything CLAUDE.md already captures, conversation context
  that ends with the session.
- **Anti-saves** — debugging recipes (the fix is in the code),
  per-task state (use TaskCreate instead), generic principles
  the model already knows.

**Pro-active persistence.** When the human teaches the agent
something non-obvious, the agent's job is to NAME the memory
type AND IMPLEMENT the write, in the same response. Asking the
human "should I remember this?" after the teaching moment
defeats the point — the moment is gone.

**Cross-linking and indexing.** Each memory references related
memories. The MEMORY.md index is a curated front door, not a
log. When a new memory is added, the index entry is added in
the same commit. Stale entries are pruned. Duplicates are
merged into the canonical home.

**Stale memory is dangerous.** A memory is a point-in-time
observation, not live state. Before acting on a recalled fact
("the file is at path X"), verify against the current code.
The cost of `grep` is seconds; the cost of acting on a
12-week-old memory of a deleted file can be much higher.

**The "write the lesson while it's hot" rule.** The right time
to write a memory is the moment the lesson lands. Postponed
lessons drift and lose specificity.

**Source material:**
[CLAUDE.md auto-memory section](../../.claude/CLAUDE.md),
[feedback_proactive_persistence](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_proactive_persistence.md),
[anthropic-skills:consolidate-memory] skill.

---

### §6 — Multi-Agent Coordination: When You're Not the Only One (~1,100 words)

**Lineage anchor.** The coordination patterns this section names
— don't push without fetching, PR-and-approve cycle, durable
authorizations, clear ownership of side effects — are what
distributed engineering teams have used for years; applying them
deliberately to human-agent collaboration matters more because
the failure modes (parallel sessions clobbering each other, silent
live-state writes, lost handoffs) are harder to spot when one party
can't independently advocate for itself.

**The reality.** In a real working setup, multiple sessions
of the same agent run in parallel — different worktrees,
different terminals, different machines. Each session writes
to a shared filesystem, can push to the same PR branches,
and reads/writes the same memories.

**The collision shapes.**

- **Parallel push to the same PR.** Two sessions push to the
  same branch; `git push` returning "Everything up-to-date"
  doesn't disambiguate "already pushed" from "your peer beat
  you." Always fetch and read the log before trusting the
  exit message.
- **Worktree main-branch contention.** A sibling worktree owns
  `main` in the bare repo; gh pr merge fails its local
  fast-forward but the remote merge succeeded. Verify state
  by reading `mergedAt`, not the exit code.
- **Live-state writes from another session.** The ops dashboard
  writes spec status changes to disk live (not as commits).
  When the parent session ends, those writes are stranded in
  the working tree until someone commits them. Hit this today
  — 10 spec status edits sitting unstaged.

**The discipline.** Treat the wall-clock between your fetch
and your write as not-a-vacuum. After any "rebase + force-push"
cycle on an active main, re-fetch and re-rebase if upstream
moved. Before admin-merging a base PR with `--delete-branch`,
re-target stacked PRs first. Before assuming you understand
the working tree state, run `git status` AND grep for known
live-write surfaces.

**Admin-merge authorization durability (~150 words to add).**
A specific named pattern: the human grants admin-merge
authorization once at the start of a batch (e.g. "yes, go on
the green-CI low-risk merges"); the agent treats it as
durable for similar future merges within the session. The
discipline is in BOTH directions: the agent doesn't re-ask
on each similar merge (saves friction); the human trusts that
"similar" means similar (the agent doesn't smuggle a
different-shaped merge into the authorization). When in doubt
about whether a merge fits the authorization scope, the agent
asks. Today's session: one authorization granted, four merges
under it (author#45, author#46, ai#466, ai#467 spec-status).
Zero re-asks. Zero scope creep.

**The dashboard as a coordination surface (~200 words to
expand).** When multiple sessions can write to it, the
dashboard becomes the shared queue. Specs flip status.
Sessions list updates. Run telemetry accumulates. Use it as
the read-side of coordination: "what is the state of the
world right now." Two-layer judgment lives here: the dashboard
surfaces the raw state (telemetry numbers, spec status flips,
recent run chips, family snapshot, anomalies); the agent
synthesizes options and recommends; the human picks. The
dashboard isn't the decision-maker — it's the lens that makes
decision-quality possible. Today's session: the dashboard
surfaced the other session's 10 unstaged spec edits (otherwise
invisible), a workspace-vs-account spend anomaly, the in-flight
PRs' CI states. Each surfacing routed to an agent
recommendation that routed to a human decision that routed to
mechanical execution. The cycle is the discipline.

**Worked example — discipline running on itself (~300 words).**
The same session that surfaced the 10 unstaged spec edits also
*designed and shipped the proactive solution* in the same
afternoon. Sequence: agent named the class of bug (live-state
writes from session-bound services becoming silent debt); agent
enumerated six solution candidates with pros/cons table; agent
recommended a layered approach (journal → API → consumers) and
named why each layer addresses a distinct damage mode; human
approved the design; agent proposed phasing (Phase 1 today,
Phases 2–3 future sessions) and the human approved that scope;
agent wrote the full spec at
[`docs/specs/archive/dashboard-pending-writes-journal/`](../specs/archive/dashboard-pending-writes-journal/)
(requirements + design + decisions, 8 durable decisions logged);
agent implemented Phase 1 (~1.5 hrs — journal writer + API +
spec-status setter wire-in + 25 tests, all green); end-to-end
smoke test against the live dashboard confirmed the cycle; PR
opened as [attune-ai #469](https://github.com/Smart-AI-Memory/attune-ai/pull/469).

The point: the article's central thesis — discipline produces
better work faster — gets demonstrated by the meta-act of using
the discipline to address the discipline's own friction. The
spec design AND the implementation AND this paragraph are all
products of the same multi-hour session. None of them is
impressive in isolation. The compounding *is* the discipline.

**Source material:** today's session — the other-session
spec-status writes I had to ask Patrick about; the
parallel-push lesson; the worktree merge lesson; the
admin-merge authorization durability pattern.

---

### §7 — Quality Discipline: Verification Is Not Optional (~1,100 words)

**The verification gap.** An agent that runs tests is not an
agent that verified the work. Tests pass on bad code all the
time when the test was written from the same misunderstanding
as the code. Coverage is green on dead code paths. Type checks
pass on unused functions.

**The dogfood principle.** Before declaring an LLM-generated
artifact done, run the artifact against a realistic input it
will actually face in production. The first run of a polished
help page surfaced six classes of hallucination (invented CLI
flags, wrong imports, fabricated cross-references, wrong route
paths, an insecure example, a fabricated numeric count). Three
of the six would have broken readers who followed the docs
literally. Unit tests caught none of them.

**Verification beats taste.** The temptation to read an
agent-generated artifact for "feel" and approve it is strong.
Discipline: name a concrete verification step before generation
starts (resolve every CLI flag against `--help`, parse every
Python import, traverse every markdown link, verify every
numeric claim). After generation, run the verification
mechanically. Approve based on the verification result, not
the prose feel.

**Decision matrices ARE verification.** When you commit the
"if A then X, if B then Y" matrix before measurement, the
measurement *automatically* routes the decision. The
verification is built into the artifact's shape.

**The dashboard is a quality lens.** Watch for drift — stale
specs, broken cross-package pins, telemetry anomalies (today:
workspace-local 7d spend > account-level 7d spend; not
blocking, but worth flagging). Use the dashboard at decision
points, not just at end-of-day.

**Source material:**
[feedback_dogfood_catches_real_bugs](../../../.claude/projects/-Users-patrickroebuck-attune-ai/memory/feedback_dogfood_catches_real_bugs.md),
attune-author polish-fact-check spec (Phases 2-4 are
verification mechanisms for LLM-generated content);
attune-rag faithfulness-judge work;
today's dashboard health check as a worked example.

---

### §8 — What This Looks Like When It Goes Right (~900 words)

**A 24-hour case study.** Walk through today (2026-05-25).
attune-rag 0.2.0 shipped overnight. Three downstream pin-widens
needed coordination. Started morning by establishing state
across five packages, made the call to ship in
simplest-first order, hit the pin widen → discovered an
upstream MCP bundle waiting in attune-gui [Unreleased] →
made the judgment call to ship as 0.8.0 minor → ran into
dependabot self-bootstrap on codeql action → made the call
to close + manually re-cut the dependabot PR → discovered
the parallel session's spec status edits → asked Patrick
about commit → admin-merged 4 PRs under durable session
authorization → launched the dashboard as a quality lens →
pushed back on my own original plan to run code-review on
config-only PRs (no signal) → pivoted to dashboard-driven
CI monitoring → started the article scoping (you are here).

Six end-to-end ships. Two real judgment calls (the 0.8.0
minor bump, the dependabot close). One in-session pushback
on my own plan. One surfaced parallel-session artifact. One
proactive memory write (the don't-enable-fatigue-push
lesson). A handful of clean-stop decisions.

**The point.** No single decision in that sequence was
breathtaking. The discipline is the COMPOUNDING of small
decisions made right.

**Closing.** This is a learnable skill. The discipline above
is six bullet-points worth of vocabulary, not a worldview.
Adopt the contract, the pacing, the artifact nesting, the
memory rules, the multi-agent awareness, the verification
gates. Practice each one boring-ly until they compound.

---

## Standalone-per-section design constraint (locked 2026-05-25)

Each section is written to work alone — explicit context-setting
at the top, no "as discussed in §4" references that require
reading the whole piece. Slight prose redundancy across sections
is acceptable cost for that property. This makes section-by-section
lifting into derivative forms a near-trivial extraction rather
than a rewrite.

## Derivative-form roadmap (Phase 3d after main draft)

### Venue characteristics (what each venue rewards)

| Venue | Form | Length sweet spot | What lands |
|---|---|---|---|
| **LinkedIn** | Standalone post | 400-800 words | Frame + 1 sharp insight + 1 concrete example. Headline-driven. Comments are the point. |
| **Discord** | Chat-scale share OR community-post | 100-400 words | Snippet-shaped, conversational, code-block-friendly. Often a single principle + link to longer piece. Channel-appropriate. |
| **Personal blog / Medium** | Long-form | 1,500-3,000 words | Full essay treatment. Citations + links. Where the foundation piece lives. |
| **attune-ai docs** | Tutorial / guide | 800-2,000 words | Practical, step-by-step, project-grounded. Code-heavy. |
| **Hacker News / Reddit** | Submission + comment seed | (linkable target only) | A long-form post submitted with one strong comment. Don't write *for* HN; write for the venue, submit if it fits. |
| **Twitter/X** | Thread | 8-15 tweets | Thread-shaped insight, each tweet stands alone. |

### Section × venue matrix

(✓ = strong fit · ◐ = partial fit / extractable / good seed material · · = weak fit)

| Section | LinkedIn | Discord | Blog | docs | HN/Reddit | X-thread |
|---|---|---|---|---|---|---|
| §1 Premise (why discipline) | ✓ | ✓ | ◐ | · | ✓ | ✓ |
| §2 Mutual contract | ✓ | ✓ | ◐ | · | ◐ | ✓ |
| §3 Pacing / sustainability | ✓ | ✓ | ✓ | · | ◐ | ✓ |
| §4 Artifact discipline (specs nest XML prompts) | ◐ | ✓ | ✓ | ✓ | ◐ | ◐ |
| §5 Memory discipline | ◐ | ✓ | ✓ | ✓ | · | ◐ |
| §6 Multi-agent coordination | ◐ | ✓ | ✓ | ✓ | ✓ | ✓ |
| §7 Verification | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| §8 24-hour case study | ✓ | ◐ | ✓ | ◐ | ✓ | ✓ |

### Strongest extractions (Phase 3d priority order)

1. **LinkedIn post from §8 (case study)** — narrative, concrete, ends on the discipline-as-compounding insight. Highest engagement potential. ~700 words.
2. **LinkedIn post from §1 (counter-thesis to vibe coding)** — opinion-shaped, ties to current discourse, designed to start argument in comments. ~600 words.
3. **Discord-shaped principle drops from §3, §5, §7** — each one ~150-200 words, ends with a link to the foundation piece. Designed for AI-tool communities. Three different angles seed three different conversations.
4. **Twitter thread from §6 (multi-agent coordination)** — visual + technical, fits well with the worktree/dashboard screenshots. ~12 tweets.
5. **attune-ai docs tutorial from §4 (artifact discipline)** — most pragmatic, ties directly to /spec command and XML prompt rule files already in repo.
6. **Blog post from §7 (verification + dogfood)** — needs the most prose breathing room because the verification examples are detailed.
7. **HN submission of the foundation piece itself** — when the full piece lands, submit with one strong opening comment from §1.

Plus a **one-page cheatsheet** (~500 words) for the head of the
foundation piece — the discipline bullet-points readers can
screenshot.

### Derivative-form authoring notes

- LinkedIn posts: never include the title of the foundation piece in the post itself. The post stands alone. The link to the foundation piece goes in the first comment (LinkedIn algorithm penalty for external links in main post text).
- Discord: respect channel context. A principle drop in #showcase reads differently than the same drop in #help-coordination. Tag #ai-tools / #claude / #engineering as appropriate per server.
- All derivatives: a one-line attribution back to the foundation piece so a curious reader finds the full treatment.

---

## Decisions locked 2026-05-25

All open questions resolved. Drafting may proceed.

1. **Working title** — LOCKED: *The Discipline of Agent
   Collaboration* + counter-thesis subtitle (above).
2. **Home location** — LOCKED:
   `attune-ai/docs/process/COLLABORATION_DISCIPLINE.md`.
   Discoverable, version-controlled, lives next to the work that
   evidences the discipline.
3. **Author voice** — LOCKED: first-person plural ("we").
   Captures the collaborative nature without forcing a single
   narrator.
4. **Audience tone** — LOCKED: experienced agent users hitting
   the ceiling of suggestion-and-accept (not curious-but-new).
5. **Section scope** — LOCKED: 8 sections as outlined.
   Per-section length targets ~1,000-1,200 words each. Open to
   merging §6+§7 if drafting reveals they're conceptually
   adjacent; open to splitting §8 if the case study grows.
6. **Length target** — LOCKED: 8,000-9,500 word ceiling. Hard
   cap at 12k if material warrants (longer compromises
   read-through).
7. **Venue + derivative-form strategy** — LOCKED: 8×6 matrix +
   Phase 3d priority order (above) stand as the working plan.
   Multi-venue: LinkedIn + Discord + blog + attune-ai docs +
   Hacker News/Reddit + Twitter/X thread.
8. **Standalone-per-section design constraint** — LOCKED. Each
   section sets its own context at the top. Slight prose
   redundancy across sections is acceptable cost.

## Revision pass — executed 2026-06-02 (in #575)

Scope decided 2026-06-02; **executed the same day in
[#575](https://github.com/Smart-AI-Memory/attune-ai/pull/575)**.
How it actually went, vs. the original plan below: rather than a
separate PR *after* #575 merged, the whole revision was **folded
into #575** while it was still open — one consolidated PR, no
stacking. Deliberately NOT a `/spec`: prose sits below the spec
altitude, and full requirements/design/tasks would over-formalize
per §4. Edits were structured-one-shots, rebuilt via
`attune-ai-dev/build_discipline.py`; metrics dated; Patrick merges
#575 to publish. Rationale + detail in memory
`project_discipline_article_revisions`.

Status: items below landed in #575, with two exceptions — **§3
generalize was a no-op** (already generalized: the asymmetry frame,
polyphasic as one of three examples), and **transferable-framing
touches + an optional §8 recap-mirror remain** as minor follow-ups.
The §7 rewrite leads its receipt with **99.6% per-claim
faithfulness** (93% coverage dropped). Original plan preserved for
the record:

Planned changes:

1. **Spine / tell-show-tell.** The skeleton already exists (§1
   preview + §8 recap). TIGHTEN, don't add a third block: turn the
   §1 preview into a crisp scannable spine (one line per
   discipline) and mirror it in the §8 recap. Candidate spine:
   - §2 Contract — what each side owes; PR-and-approve as the
     middle path.
   - §3 Pacing — exploit the always-on asymmetry; spend human
     attention only on decisions.
   - §4 Artifacts — right-size: inline → one-shot → XML prompt →
     spec; pre-commit decisions.
   - §5 Memory — curate what persists; stale memory is dangerous.
   - §6 Multi-agent — coordination is the baseline; name the
     collision shapes.
   - §7 Verification — tests catch zero hallucinations; dogfood;
     the receipt beats the promise.
2. **§3 generalize.** Strip the disability specifics; reframe as
   the always-on asymmetry (general audience). Personal detail
   becomes illustration, not the lesson.
3. **§7 rewrite.** Reflect the verification-modes split (grounding
   / generation-fact-check / behavioral / structural) and
   attune-verify as the output-side product — referenced as a
   SPEC / roadmap, NOT a shipped tool (unbuilt; criterion-6
   honesty).
4. **Autonomous contract = §2 in async mode.** The 7th-discipline
   discovery: human queues *execution-ready* work for away-windows;
   agent holds guardrails + stops honestly at the boundary; the
   `auto:` handoff token. Fold into §2, not a standalone §9.
5. **Transferable / tool-agnostic framing.** Teach each technique
   tool-agnostic (any agent, no attune-ai required); attune-ai is
   the receipt-it-scales, not the gate. Each technique =
   pattern + why + one example; transferability test: *can a
   stranger do it tomorrow without being Patrick?*
6. **Generative frame.** Open thesis + close receipt (partly in
   #575) — keep consistent across the consolidated PR.

Watch: word ceiling is 8,000-9,500 (hard cap 12k). The §7 rewrite
+ spine add length; the §3 generalization trims. Re-measure the
throughput stat before publishing — it grows.
